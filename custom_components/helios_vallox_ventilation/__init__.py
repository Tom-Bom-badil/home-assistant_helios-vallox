import os, shutil, logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify
from homeassistant.components import persistent_notification
from homeassistant.exceptions import HomeAssistantError
from .device_info import get_entity_prefix
from .constants import DOMAIN
from .coordinator import HeliosCoordinator
from .schema import SERVICE_WRITE_VALUE_SCHEMA
from .softboost import SoftBoostController


try:
    from ._local_dev_overrides import (
        DEVELOPER_MODE,
        apply_local_function_overrides,
        apply_local_log_overrides,
    )
except ModuleNotFoundError:
    DEVELOPER_MODE = False
else:
    if DEVELOPER_MODE:
        apply_local_function_overrides()
        apply_local_log_overrides()


_LOGGER = logging.getLogger("helios_vallox.__init__")
PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.FAN,
    Platform.BUTTON,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Handle legacy YAML configuration gracefully."""
    if DOMAIN in config:
        message = (
            "Legacy YAML configuration for Helios/Vallox was detected. "
            "v2026.06+ is configured through Settings > Devices & Services. "
            "Please remove the old `helios_vallox_ventilation:` YAML block "
            "and the old `packages: helios_vallox:` from configuration.yaml."
            "Also, delete `user_conf.yaml` file if you copied it to /packages."
        )
        _LOGGER.warning(message)
        persistent_notification.async_create(
            hass,
            message,
            title="Helios/Vallox: Legacy YAML configuration detected.",
            notification_id=f"{DOMAIN}_legacy_yaml",
        )
    return True


async def async_install_frontend_files(hass: HomeAssistant) -> None:
    """Copy dashboard frontend files to /www/community/helios_vallox_ventilation if needed."""

    def _install() -> None:
        source_dir = hass.config.path("custom_components", DOMAIN, "frontend")
        target_dir = hass.config.path("www", "community", DOMAIN)

        if not os.path.isdir(source_dir):
            _LOGGER.debug(
                "[Helios/Vallox] Frontend source folder not found: %s",
                source_dir,
            )
            return

        os.makedirs(target_dir, exist_ok=True)

        for entry in os.scandir(source_dir):
            if not entry.is_file():
                continue

            src = entry.path
            dst = os.path.join(target_dir, entry.name)

            if os.path.isfile(dst):
                try:
                    if os.path.getsize(src) == os.path.getsize(dst):
                        _LOGGER.debug(
                            "[Helios/Vallox] Skipping frontend file (already up to date): %s",
                            entry.name,
                        )
                        continue
                except OSError as err:
                    _LOGGER.debug(
                        "[Helios/Vallox] Size check failed for %s: %s",
                        entry.name,
                        err,
                    )

            shutil.copy2(src, dst)
            _LOGGER.debug(
                "[Helios/Vallox] Copied frontend file: %s",
                entry.name,
            )

    await hass.async_add_executor_job(_install)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    config_data = {**entry.data, **entry.options}
    ip_address = config_data[CONF_IP_ADDRESS]
    port = config_data[CONF_PORT]
    coordinator = HeliosCoordinator(
        hass=hass,
        config_entry=entry,
        ip=ip_address,
        port=port,
        config_data=config_data,
    )
    await coordinator.setup_coordinator()

    # Load per-device Softboost runtime state.
    # The controller is attached to the existing coordinator to keep hass.data unchanged.
    softboost = SoftBoostController(hass, entry.entry_id, coordinator)
    await softboost.async_load()
    coordinator.softboost = softboost
    await softboost.async_restore_after_startup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Copy ready-made frontend files for Lovelace
    await async_install_frontend_files(hass)

    # Register write service (once per domain)
    if not hass.services.has_service(DOMAIN, "write_value"):

#---
        async def handle_write_service(call):
            target_entry_id = call.data.get("entry_id")
            coord = None

            if target_entry_id:
                # 1) Try real config entry_id first
                coord = hass.data[DOMAIN].get(target_entry_id)

                # 2) Fallback: treat entry_id as unique device name
                if coord is None:
                    target_slug = slugify(target_entry_id)
                    for entry in hass.config_entries.async_entries(DOMAIN):
                        if slugify(get_entity_prefix(entry)) == target_slug:
                            coord = hass.data[DOMAIN].get(entry.entry_id)
                            break
            else:
                # 3) Backward-compatible fallback for single-device installations
                coordinators = [
                    item
                    for item in hass.data[DOMAIN].values()
                    if isinstance(item, HeliosCoordinator)
                ]

                if len(coordinators) == 1:
                    coord = coordinators[0]
                else:
                    raise HomeAssistantError(
                        "write_value requires entry_id when multiple ventilation "
                        "devices are configured"
                    )

            if coord is None:
                raise HomeAssistantError(
                    "No ventilation device found for entry_id or unique device "
                    f"name: {target_entry_id}"
                )

            variable = call.data["variable"]
            value = call.data["value"]

            try:
                success = await hass.async_add_executor_job(
                    coord.write_value,
                    variable,
                    value,
                )
            except Exception as err:
                _LOGGER.error(
                    "Error handling write service for %s=%s: %s",
                    variable,
                    value,
                    err,
                    exc_info=True,
                )
                raise HomeAssistantError(
                    f"Failed to write {variable}={value} to ventilation unit"
                ) from err

            if not success:
                raise HomeAssistantError(
                    f"Failed to write {variable}={value} to ventilation unit"
                )

        hass.services.async_register(
            DOMAIN, "write_value", handle_write_service, schema=SERVICE_WRITE_VALUE_SCHEMA
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator = hass.data[DOMAIN].get(entry.entry_id)

        if coordinator is not None and getattr(coordinator, "softboost", None) is not None:
            coordinator.softboost.async_unload()

        hass.data[DOMAIN].pop(entry.entry_id)

        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "write_value")

    return unload_ok
