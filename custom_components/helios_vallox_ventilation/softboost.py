"""Softboost controller for Helios/Vallox ventilation.
This module owns the HA-specific Soft Remote Control state machine.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
import logging
import time
from typing import Any
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from .constants import (
    DOMAIN,
    SOFTBOOST_STORAGE_VERSION,
    SOFTBOOST_STORAGE_KEY_SUFFIX,
    DEFAULT_SOFTBOOST_LEVEL,
    DEFAULT_SOFTBOOST_DURATION_SECONDS,
    FIREPLACE_RESTORE_DELAY_SECONDS,
)


_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SoftBoostState:
    """Persisted runtime state for one ventilation device."""

    active: bool = False
    original_fanspeed: int | None = None
    level: int = DEFAULT_SOFTBOOST_LEVEL
    duration_seconds: int = DEFAULT_SOFTBOOST_DURATION_SECONDS
    started_at_ts: float | None = None
    end_at_ts: float | None = None
    fireplace_mode: bool = False
    fireplace_restore_at_ts: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SoftBoostState:
        """Create state from persisted storage data."""
        if not data:
            return cls()

        return cls(
            active=bool(data.get("active", False)),
            original_fanspeed=_as_optional_int(data.get("original_fanspeed")),
            level=_as_int(data.get("level"), DEFAULT_SOFTBOOST_LEVEL),
            duration_seconds=_as_int(
                data.get("duration_seconds"),
                DEFAULT_SOFTBOOST_DURATION_SECONDS,
            ),
            started_at_ts=_as_optional_float(data.get("started_at_ts")),
            end_at_ts=_as_optional_float(data.get("end_at_ts")),
            fireplace_mode=bool(data.get("fireplace_mode", False)),
            fireplace_restore_at_ts=_as_optional_float(
                data.get("fireplace_restore_at_ts")
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-serializable state data."""
        return asdict(self)


class SoftBoostController:
    """Controller for the YAML-free Soft Remote Control boost logic."""

    def __init__(self, hass: HomeAssistant, entry_id: str, coordinator) -> None:
        """Initialize controller for one config entry / ventilation device."""
        self.hass = hass
        self.entry_id = entry_id
        self._coordinator = coordinator
        self._store: Store[dict[str, Any]] = Store(
            hass,
            SOFTBOOST_STORAGE_VERSION,
            f"{DOMAIN}.{SOFTBOOST_STORAGE_KEY_SUFFIX}.{entry_id}",
        )
        self._state = SoftBoostState()

        self._listeners: list[Callable[[], None]] = []
        self._unsub_end_callback: Callable[[], None] | None = None
        self._unsub_fireplace_callback: Callable[[], None] | None = None
        self._unsub_tick_callback: Callable[[], None] | None = None

    @property
    def state(self) -> SoftBoostState:
        """Return current in-memory softboost state."""
        return self._state

    @property
    def is_active(self) -> bool:
        """Return True if softboost is currently active."""
        return self._state.active

    @property
    def remaining_seconds(self) -> int:
        """Return remaining softboost time in seconds."""
        return self._remaining_seconds()

    @property
    def remaining_text(self) -> str:
        """Return remaining softboost time as mm:ss text for the dashboard."""
        return format_remaining(self.remaining_seconds)

    async def async_load(self) -> None:
        """Load persisted state from Home Assistant storage."""
        raw_state = await self._store.async_load()
        self._state = SoftBoostState.from_dict(raw_state)

    async def async_restore_after_startup(self) -> None:
        """Restore or clean up persisted Softboost state after HA startup."""
        if not self._state.active:
            return
        if self.has_expired():
            _LOGGER.warning(
                "Softboost expired while Home Assistant was offline. "
                "Cleaning up without restoring previous fan speed."
            )
            # output_fan_off = 0 is the safe normal state after restart.
            await self._async_write_value("output_fan_off", 0, 0, 1)

            self.mark_stopped()
            await self.async_save()
            self._notify_listeners()
            return
        # Softboost is still within its planned runtime.
        # Recreate callbacks and continue countdown until the original end time.
        if (
            self._state.fireplace_restore_at_ts is not None
            and self._state.fireplace_restore_at_ts <= _now_ts()
        ):
            # Fireplace restore time passed during HA downtime.
            # Restore output fan now, but keep Softboost running.
            await self._async_write_value("output_fan_off", 0, 0, 1)
        self._schedule_callbacks()
        self._notify_listeners()

    async def async_save(self) -> None:
        """Persist current runtime state."""
        await self._store.async_save(self._state.as_dict())

    async def async_clear(self) -> None:
        """Clear persisted and in-memory softboost state."""
        self._state = SoftBoostState()
        await self._store.async_remove()

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a listener for visible Softboost state updates."""
        self._listeners.append(listener)

        def remove_listener() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove_listener

    async def async_start(self) -> bool:
        """Start Softboost and write the selected level to the ventilation unit."""
        if self._state.active:
            return True

        original_fanspeed = self._current_fanspeed()
        if original_fanspeed is None:
            _LOGGER.warning("Cannot start Softboost: current fanspeed is unknown")
            return False

        level = self._clamp(self._state.level, 1, 8)
        duration_seconds = self._clamp(
            self._state.duration_seconds,
            15 * 60,
            90 * 60,
        )
        fireplace_mode = bool(self._state.fireplace_mode)

        # Fireplace mode: temporarily switch off output fan before changing level.
        if fireplace_mode:
            if not await self._async_write_value("output_fan_off", 1, 0, 1):
                _LOGGER.warning(
                    "Cannot start Softboost: failed to switch output fan off"
                )
                return False

        if not await self._async_write_value("fanspeed", level, 1, 8):
            _LOGGER.warning("Cannot start Softboost: failed to write fanspeed")
            if fireplace_mode:
                await self._async_write_value("output_fan_off", 0, 0, 1)
            return False

        self.prepare_start_state(
            original_fanspeed=original_fanspeed,
            level=level,
            duration_seconds=duration_seconds,
            fireplace_mode=fireplace_mode,
        )

        await self.async_save()
        self._schedule_callbacks()
        self._notify_listeners()
        return True


    async def async_stop(self, *, restore_fanspeed: bool = True) -> None:
        """Stop Softboost and optionally restore the previous fanspeed."""
        if not self._state.active:
            self._notify_listeners()
            return
        self._cancel_callbacks()
        # output_fan_off = 0 is the safe normal state and can always be written.
        await self._async_write_value("output_fan_off", 0, 0, 1)
        if restore_fanspeed and self._state.original_fanspeed is not None:
            await self._async_write_value(
                "fanspeed",
                self._clamp(self._state.original_fanspeed, 1, 8),
                1,
                8,
            )
        self.mark_stopped()
        await self.async_save()
        self._notify_listeners()


    def prepare_start_state(
        self,
        *,
        original_fanspeed: int,
        level: int,
        duration_seconds: int,
        fireplace_mode: bool,
    ) -> SoftBoostState:
        """Prepare runtime state for a new softboost run."""
        now_ts = _now_ts()
        end_at_ts = now_ts + duration_seconds

        self._state = SoftBoostState(
            active=True,
            original_fanspeed=original_fanspeed,
            level=level,
            duration_seconds=duration_seconds,
            started_at_ts=now_ts,
            end_at_ts=end_at_ts,
            fireplace_mode=fireplace_mode,
            fireplace_restore_at_ts=now_ts + FIREPLACE_RESTORE_DELAY_SECONDS,
        )
        return self._state

    def mark_stopped(self) -> None:
        """Mark softboost as stopped while preserving user settings."""
        level = self._state.level
        duration_seconds = self._state.duration_seconds

        self._state = SoftBoostState(
            active=False,
            level=level,
            duration_seconds=duration_seconds,
            fireplace_mode=False,
        )

    def has_expired(self) -> bool:
        """Return True if persisted softboost end time is in the past."""
        return bool(self._state.end_at_ts and self._state.end_at_ts <= _now_ts())

    def _remaining_seconds(self) -> int:
        """Calculate remaining time from numeric backend timestamp."""
        if not self._state.active or not self._state.end_at_ts:
            return 0

        return max(0, int(round(self._state.end_at_ts - _now_ts())))

    def _current_fanspeed(self) -> int | None:
        """Return the latest known fanspeed from coordinator data."""
        data = self._coordinator.coordinator.data or {}
        return _as_optional_int(data.get("fanspeed"))

    def _was_overridden(self) -> bool:
        """Return True if the real fan speed was changed outside Softboost."""
        current_fanspeed = self._current_fanspeed()
        return (
            self._state.active
            and current_fanspeed is not None
            and current_fanspeed != self._state.level
        )

    async def _async_write_value(
        self,
        variable: str,
        value: int,
        min_value: int | None = None,
        max_value: int | None = None,
    ) -> bool:
        """Write a value through the existing coordinator."""
        return await self.hass.async_add_executor_job(
            self._coordinator.write_value,
            variable,
            value,
            min_value,
            max_value,
        )

    def _schedule_callbacks(self) -> None:
        """Schedule end, fireplace restore and countdown updates."""
        self._cancel_callbacks()

        if not self._state.active or not self._state.end_at_ts:
            return

        now_ts = _now_ts()
        end_delay = max(0, self._state.end_at_ts - now_ts)

        self._unsub_end_callback = async_call_later(
            self.hass,
            end_delay,
            self._handle_end,
        )

        if self._state.fireplace_restore_at_ts is not None:
            fireplace_delay = max(0, self._state.fireplace_restore_at_ts - now_ts)
            self._unsub_fireplace_callback = async_call_later(
                self.hass,
                fireplace_delay,
                self._handle_fireplace_restore,
            )

        self._schedule_tick()

    @callback
    def _handle_end(self, _now=None) -> None:
        """Stop Softboost when the planned end time is reached."""
        self.hass.async_create_task(self.async_stop())


    @callback
    def _handle_fireplace_restore(self, _now=None) -> None:
        """Restore output fan when fireplace delay has passed."""
        self.hass.async_create_task(self._async_restore_output_fan())


    def _schedule_tick(self) -> None:
        """Schedule next visible countdown update."""
        if self._unsub_tick_callback is not None:
            self._unsub_tick_callback()
            self._unsub_tick_callback = None

        if not self._state.active:
            return

        self._unsub_tick_callback = async_call_later(
            self.hass,
            1,
            self._handle_tick,
        )


    @callback
    def _handle_tick(self, _now=None) -> None:
        """Update countdown, stop on end, or cancel when overridden."""
        if not self._state.active:
            return
        if self._was_overridden():
            _LOGGER.info(
                "Softboost was cancelled because fan speed changed outside Softboost: "
                "current=%s, softboost=%s",
                self._current_fanspeed(),
                self._state.level,
            )
            self.hass.async_create_task(self.async_stop(restore_fanspeed=False))
            return
        if self.remaining_seconds <= 0:
            self.hass.async_create_task(self.async_stop())
            return
        self._notify_listeners()
        self._schedule_tick()


    @callback
    def _notify_listeners(self) -> None:
        """Notify Softboost entities to update their HA state."""
        for listener in list(self._listeners):
            self.hass.async_create_task(self._async_call_listener(listener))


    async def _async_call_listener(self, listener: Callable[[], None]) -> None:
        """Call one HA state listener safely in the event loop."""
        listener()

    async def _async_restore_output_fan(self) -> None:
        """Restore output fan to normal state."""
        await self._async_write_value("output_fan_off", 0, 0, 1)
        self._notify_listeners()

    def _cancel_callbacks(self) -> None:
        """Cancel all scheduled Softboost callbacks."""
        for unsub in (
            self._unsub_end_callback,
            self._unsub_fireplace_callback,
            self._unsub_tick_callback,
        ):
            if unsub is not None:
                unsub()

        self._unsub_end_callback = None
        self._unsub_fireplace_callback = None
        self._unsub_tick_callback = None


    @staticmethod
    def _clamp(value: int, min_value: int, max_value: int) -> int:
        """Clamp integer value to a safe range."""
        return max(min_value, min(max_value, int(value)))


def format_remaining(seconds: int) -> str:
    """Format seconds as mm:ss for the visible remaining sensor."""
    seconds = max(0, int(seconds))
    minutes, rest = divmod(seconds, 60)
    return f"{minutes}:{rest:02d}"


def _now_ts() -> float:
    """Return backend-side numeric timestamp"""
    return time.time()


def _as_int(value: Any, default: int) -> int:
    """Convert value to int with fallback."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_optional_int(value: Any) -> int | None:
    """Convert value to optional int."""
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_optional_float(value: Any) -> float | None:
    """Convert value to optional float."""
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None