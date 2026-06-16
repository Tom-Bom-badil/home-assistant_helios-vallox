import logging
import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .constants import DOMAIN
from .device_info import build_device_info, get_entity_prefix


_LOGGER = logging.getLogger("helios_vallox.fan")
FAN_SPEED_COUNT = 8


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the default fan entity for one ventilation unit."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HeliosValloxFan(coordinator, entry)])


class HeliosValloxFan(CoordinatorEntity, FanEntity):
    """Default fan entity for HomeKit / Google Home / Alexa / HA Voice."""

    _attr_has_entity_name = False
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = FAN_SPEED_COUNT
    _attr_preset_modes = None


    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator.coordinator)
        self._coordinator = coordinator
        self._entry = entry

        object_id = slugify(get_entity_prefix(entry)).rstrip("_") or "ventilation"

        self.entity_id = f"fan.{object_id}"
        self._attr_unique_id = f"{entry.entry_id}_fan"
        _attr_has_entity_name = True
        _attr_name = None
        # self._attr_name = get_entity_prefix(entry)
        self._attr_icon = "mdi:fan"



    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self._entry)


    @property
    def is_on(self) -> bool | None:
        """Return True if the ventilation unit is switched on."""
        if self.coordinator.data is None:
            return None
        powerstate = self.coordinator.data.get("powerstate")
        if powerstate is None:
            return None
        return bool(powerstate)


    @property
    def percentage(self) -> int | None:
        """Return the current fan speed as percentage."""
        if self.coordinator.data is None:
            return None
        if not self.coordinator.data.get("powerstate"):
            return 0
        try:
            fanspeed = int(self.coordinator.data.get("fanspeed"))
        except (TypeError, ValueError):
            return None
        fanspeed = max(1, min(FAN_SPEED_COUNT, fanspeed))
        return round(fanspeed * 100 / FAN_SPEED_COUNT)
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the ventilation unit."""
        if percentage is not None:
            await self.async_set_percentage(percentage)
            return

        await self.hass.async_add_executor_job(
            self._coordinator.write_value,
            "powerstate",
            1,
        )
        self.async_write_ha_state()


    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the ventilation unit."""
        await self.hass.async_add_executor_job(
            self._coordinator.write_value,
            "powerstate",
            0,
        )
        self.async_write_ha_state()


    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed percentage."""
        percentage = max(0, min(100, int(percentage)))
        if percentage == 0:
            await self.async_turn_off()
            return
        fanspeed = self._percentage_to_fanspeed(percentage)
        # Ensure the unit is on before setting the fan speed.
        if not self.coordinator.data or not self.coordinator.data.get("powerstate"):
            await self.hass.async_add_executor_job(
                self._coordinator.write_value,
                "powerstate",
                1,
            )
        await self.hass.async_add_executor_job(
            self._coordinator.write_value,
            "fanspeed",
            fanspeed,
            1,
            FAN_SPEED_COUNT,
        )
        self.async_write_ha_state()


    @staticmethod
    def _percentage_to_fanspeed(percentage: int) -> int:
        """Convert 1-100% to fan speed level 1-8."""
        fanspeed = math.ceil(percentage * FAN_SPEED_COUNT / 100)
        return max(1, min(FAN_SPEED_COUNT, fanspeed))