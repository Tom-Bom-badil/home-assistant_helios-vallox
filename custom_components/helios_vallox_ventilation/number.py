import logging
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger("helios_vallox.number")

# platform setup
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if discovery_info is None:
        return
    coordinator = hass.data[DOMAIN]["coordinator"]
    entities = []
    number_config = discovery_info.get("numbers", [])
    for number in number_config:
        name = number.get("name")
        if not name:
            _LOGGER.warning("Number configuration missing 'name'. Skipping entry.")
            continue
        entities.append(
            HeliosNumber(
                name=name,
                variable=name,
                coordinator=coordinator,
                icon=number.get("icon"),
                unique_id=f"ventilation_{name}",
                description=number.get("description"),
                unit_of_measurement=number.get("unit_of_measurement"),
                device_class=number.get("device_class"),
                min_value=number.get("min_value"),
                max_value=number.get("max_value"),
                step=number.get("step", 1),
                factory_setting=number.get("factory_setting"),
                mode=number.get("mode", "box"),
            )
        )
    async_add_entities(entities)
    hass.data.setdefault("ventilation_entities", []).extend(entities)

# number class
class HeliosNumber(CoordinatorEntity, NumberEntity):
    def __init__(
        self,
        name,
        variable,
        coordinator,
        icon=None,
        unique_id=None,
        description=None,
        unit_of_measurement=None,
        device_class=None,
        min_value=None,
        max_value=None,
        step=1,
        factory_setting=None,
        mode="box",
    ):
        super().__init__(coordinator.coordinator)
        self._attr_name = f"Ventilation {name}"
        self._variable = variable
        self._coordinator = coordinator
        self._attr_icon = icon
        self._attr_unique_id = unique_id
        self._attr_description = description
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_device_class = device_class
        self._attr_native_min_value = min_value if min_value is not None else 0
        self._attr_native_max_value = max_value if max_value is not None else 255
        self._attr_native_step = step
        self._attr_factory_setting = factory_setting
        self._attr_mode = NumberMode.BOX if mode == "box" else NumberMode.SLIDER

    @property
    def native_value(self):
        return self.coordinator.data.get(self._variable)

    async def async_set_native_value(self, value: float) -> None:
        int_value = int(value)
        await self.hass.async_add_executor_job(
            self._coordinator.write_value, self._variable, int_value
        )
        self.async_write_ha_state()

    # additional state attributes
    @property
    def extra_state_attributes(self):
        attributes = {
            "factory_setting": self._attr_factory_setting,
            "description": self._attr_description,
        }
        return {k: v for k, v in attributes.items() if v is not None}

    # add entity
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_write_ha_state()

    # update entity
    def _handle_coordinator_update(self):
        super()._handle_coordinator_update()
