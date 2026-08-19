import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from time import monotonic
from typing import Any, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .api import HeliosBase


_LOGGER = logging.getLogger("helios_vallox.coordinator")
RunFinishedCallback = Callable[[], None]
UpdateMethod = Callable[[], Awaitable[dict[str, Any]]]


class HeliosDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, Any]]
):
    """Data coordinator with timestamps for every completed full read."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        update_method: UpdateMethod,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="Helios Vallox Data Coordinator",
            update_method=update_method,
            update_interval=timedelta(seconds=59),
        )

        self.last_run: datetime | None = None
        self.last_successful_full_run: datetime | None = None
        self.last_unsuccessful_run: datetime | None = None
        self.last_run_success: bool | None = None

        self._run_finished_listeners: set[RunFinishedCallback] = set()

    @callback
    def async_add_run_finished_listener(
        self,
        update_callback: RunFinishedCallback,
    ) -> Callable[[], None]:
        """Register a listener called after every completed coordinator run."""
        self._run_finished_listeners.add(update_callback)

        @callback
        def remove_listener() -> None:
            self._run_finished_listeners.discard(update_callback)

        return remove_listener

    @callback
    @override
    def _async_refresh_finished(self) -> None:
        """Store run timestamps and notify the connection entity."""
        super()._async_refresh_finished()

        now = dt_util.utcnow()

        self.last_run = now
        self.last_run_success = self.last_update_success

        if self.last_update_success:
            self.last_successful_full_run = now
        else:
            self.last_unsuccessful_run = now

        if self.hass.is_stopping:
            return

        for update_callback in tuple(self._run_finished_listeners):
            try:
                update_callback()
            except Exception:
                self.logger.exception(
                    "Unexpected error updating run-finished listener %s",
                    id(update_callback),
                )


class HeliosCoordinator:
    """Coordinate communication with a Helios/Vallox ventilation unit."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        ip: str,
        port: int,
        config_data: dict | None = None,
    ) -> None:
        self._hass = hass
        self._config_entry = config_entry
        self._ip = ip
        self._port = port
        self._capabilities = {"co2": False, "rh": False}

        self._helios = HeliosBase(
            hass,
            ip,
            port,
            config_data=config_data,
        )

        self._coordinator = HeliosDataUpdateCoordinator(
            hass,
            config_entry,
            self._async_update_data,
        )

    @property
    def coordinator(self) -> HeliosDataUpdateCoordinator:
        """Return the Home Assistant data update coordinator."""
        return self._coordinator

    async def setup_coordinator(self) -> None:
        """Perform the initial full read."""
        await self._coordinator.async_config_entry_first_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Read all known registers from the ventilation unit."""
        started = monotonic()

        _LOGGER.debug(
            "Coordinator update started for '%s' (%s:%s).",
            self._config_entry.title,
            self._ip,
            self._port,
        )

        try:
            data = await self._hass.async_add_executor_job(
                self._helios.readAllValues
            )
        except Exception as err:
            elapsed = monotonic() - started

            _LOGGER.debug(
                "Coordinator update raised an unexpected exception for "
                "'%s' after %.2f s.",
                self._config_entry.title,
                elapsed,
                exc_info=True,
            )

            raise UpdateFailed(
                f"Unexpected error reading ventilation data: {err}"
            ) from err

        read_elapsed = monotonic() - started

        if not data:
            _LOGGER.debug(
                "Coordinator update failed for '%s' after %.2f s: "
                "full read returned no data.",
                self._config_entry.title,
                read_elapsed,
            )

            raise UpdateFailed(
                "Ventilation unit returned no data during full read"
            )

        unavailable_values = sorted(
            key
            for key, value in data.items()
            if value is None
        )

        _LOGGER.debug(
            "Coordinator full read completed for '%s' in %.2f s: "
            "%d values received, %d unavailable: %s.",
            self._config_entry.title,
            read_elapsed,
            len(data),
            len(unavailable_values),
            ", ".join(unavailable_values) or "none",
        )

        self._capabilities = self._detect_capabilities(data)

        _LOGGER.debug(
            "Coordinator capabilities for '%s': CO2=%s, rH=%s.",
            self._config_entry.title,
            self._capabilities["co2"],
            self._capabilities["rh"],
        )

        _LOGGER.debug(
            "Coordinator update finished successfully for '%s' "
            "in %.2f s.",
            self._config_entry.title,
            monotonic() - started,
        )

        return data

    def has_capability(self, capability: str) -> bool:
        """Return whether the ventilation supports a capability."""
        return self._capabilities.get(capability, False)

    @staticmethod
    def _detect_capabilities(
        data: dict | None,
    ) -> dict[str, bool]:
        """Detect optional hardware features from the latest read data."""
        data = data or {}

        return {
            "co2": any(
                data.get(f"co2_sensor{i}_present")
                for i in range(1, 6)
            ),
            "rh": any(
                HeliosCoordinator._is_valid_rh_raw(data.get(key))
                for key in (
                    "rh_sensor1_raw",
                    "rh_sensor2_raw",
                )
            ),
        }

    @staticmethod
    def _is_valid_rh_raw(value) -> bool:
        """Return whether a raw humidity value represents a sensor."""
        try:
            return 0x33 <= int(value) <= 0xFF
        except (TypeError, ValueError):
            return False

    def write_value(
        self,
        variable,
        value,
        min_value=None,
        max_value=None,
    ):
        """Write a single register or handled pseudo-register."""
        try:
            if variable == "co2_setting_value":
                return self.write_co2_setting_value(
                    value,
                    min_value,
                    max_value,
                )

            result = self._helios.writeValue(
                variable,
                value,
                min_value,
                max_value,
            )

            if result:
                self._update_local_data({variable: value})

            return result

        except Exception as err:
            _LOGGER.error(
                "Error writing %s to %s: %s",
                value,
                variable,
                err,
                exc_info=True,
            )
            return False

    def reset_service_reminder(self):
        """Reset the service reminder."""
        try:
            result = self._helios.resetServiceReminder()

            if result:
                service_interval = None

                if self._coordinator.data:
                    service_interval = self._coordinator.data.get(
                        "service_interval"
                    )

                self._update_local_data(
                    {
                        "service_due_months": service_interval,
                        "service_requested": False,
                    }
                )

            return result

        except Exception as err:
            _LOGGER.error(
                "Error resetting service reminder: %s",
                err,
                exc_info=True,
            )
            return False

    def _update_local_data(self, values: dict) -> None:
        """Update cached values after a write without performing a bus read."""
        new_data = (
            self._coordinator.data.copy()
            if self._coordinator.data
            else {}
        )

        new_data.update(values)

        new_data = self._helios._addCalculationsToReadings(new_data)

        self._hass.loop.call_soon_threadsafe(
            self._coordinator.async_set_updated_data,
            new_data,
        )

    def write_co2_setting_value(
        self,
        value,
        min_value=None,
        max_value=None,
    ):
        """Write the combined 16-bit CO2 setpoint."""
        try:
            min_value = 500 if min_value is None else min_value
            max_value = 2000 if max_value is None else max_value

            value = int(round(float(value) / 50) * 50)
            value = max(
                int(min_value),
                min(int(max_value), value),
            )

            upper = value // 256
            lower = value % 256

            # Write the lower byte first. The mainboard appears to
            # latch/apply the value when the upper byte is written.
            lower_ok = self._helios.writeValue(
                "co2_setting_lower_byte",
                lower,
                0,
                255,
            )
            upper_ok = self._helios.writeValue(
                "co2_setting_upper_byte",
                upper,
                0,
                255,
            )

            if upper_ok and lower_ok:
                self._update_local_data(
                    {
                        "co2_setting_lower_byte": lower,
                        "co2_setting_upper_byte": upper,
                        "co2_setting_value": value,
                    }
                )
                return True

            return False

        except Exception as err:
            _LOGGER.error(
                "Error writing CO2 setting value %s: %s",
                value,
                err,
                exc_info=True,
            )
            return False

    async def turn_on(self, variable):
        """Turn on a writable bit variable."""
        await self._hass.async_add_executor_job(
            self.write_value,
            variable,
            1,
        )

    async def turn_off(self, variable):
        """Turn off a writable bit variable."""
        await self._hass.async_add_executor_job(
            self.write_value,
            variable,
            0,
        )
