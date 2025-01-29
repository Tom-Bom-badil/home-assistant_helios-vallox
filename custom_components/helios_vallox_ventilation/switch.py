import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)


# platform setup
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if discovery_info is None:
        return

    coordinator = hass.data[DOMAIN]["coordinator"]
    entities = []
    switch_config = discovery_info.get("switches", [])

    for switch in switch_config:
        name = switch.get("name")
        if not name:
            _LOGGER.warning("Switch configuration missing 'name'. Skipping entry.")
            continue
        entities.append(
            HeliosSwitch(
                name=name,
                variable=name,
                coordinator=coordinator,
                description=switch.get("description"),
                icon=switch.get("icon"),
                unique_id=f"ventilation_{name}",
            )
        )

    async_add_entities(entities)
    hass.data.setdefault("ventilation_entities", []).extend(entities)
    _LOGGER.debug(f"Added {len(entities)} switches for Helios/Vallox and registered it with coordinator {coordinator.coordinator}.")


# switch class
class HeliosSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, name, variable, coordinator, description=None, icon=None, unique_id=None):
        super().__init__(coordinator.coordinator)
        self._attr_name = f"Ventilation {name}"
        self._variable = variable
        self._coordinator = coordinator
        self._description = description
        self._attr_icon = icon
        self._attr_unique_id = unique_id
        self._attr_is_on = None
        # _LOGGER.debug(f"Registering switch '{name}' with coordinator: {coordinator.coordinator}")

    @property
    def is_on(self):
        value = self.coordinator.data.get(self._variable)
        return value == "on" or value is True

    # additional state attributes
    @property
    def extra_state_attributes(self):
        return {
            "description": self._description,
        }

    # turn on
    async def async_turn_on(self, **kwargs):
        await self._coordinator.turn_on(self._variable)
        self._attr_is_on = True
        self.async_write_ha_state()

    # turn off
    async def async_turn_off(self, **kwargs):
        await self._coordinator.turn_off(self._variable)
        self._attr_is_on = False
        self.async_write_ha_state()

    # update
    async def async_update(self):
        await self.coordinator.async_request_refresh()

    # add entity
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_write_ha_state()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    # update entity
    def _handle_coordinator_update(self):
        new_value = self.coordinator.data.get(self._variable)
        if new_value is not None:
            self._attr_is_on = new_value == "on" or new_value is True
        self.async_write_ha_state()
