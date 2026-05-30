from homeassistant.config_entries import ConfigEntry
from homeassistant.util import slugify
from homeassistant.helpers.device_registry import DeviceInfo
from .constants import (
    CONF_DEVICE_MODEL,
    CONF_ENTITY_PREFIX,
    CUSTOM_MODEL,
    DEFAULT_ENTITY_PREFIX,
    DOMAIN,
)


def get_entity_prefix(entry: ConfigEntry) -> str:
    """Return the configured user-visible entity prefix."""
    prefix = entry.options.get(
        CONF_ENTITY_PREFIX,
        entry.data.get(CONF_ENTITY_PREFIX, DEFAULT_ENTITY_PREFIX),
    )
    prefix = str(prefix or "").strip()
    return prefix or DEFAULT_ENTITY_PREFIX


def build_suggested_object_id(entry: ConfigEntry, entity_key: str) -> str:
    """Build a stable English object id including the configured entity prefix."""
    prefix = slugify(get_entity_prefix(entry))
    key = slugify(entity_key)
    if prefix and not key.startswith(f"{prefix}_"):
        return f"{prefix}_{key}"
    return key


def build_entity_id(entity_domain: str, entry: ConfigEntry, entity_key: str) -> str:
    """Build the full preferred entity_id without HA device-name prefixing."""
    return f"{entity_domain}.{build_suggested_object_id(entry, entity_key)}"


def build_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Build device info for one configured ventilation unit."""
    model = entry.data.get(CONF_DEVICE_MODEL, CUSTOM_MODEL)
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="Helios/Vallox",
        model=model,
        name=get_entity_prefix(entry),
    )
