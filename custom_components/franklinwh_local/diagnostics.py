"""Diagnostics support for FranklinWH Local."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from . import AgateConfigEntry
from .const import CONF_CLOUD_PASSWORD, CONF_CLOUD_USERNAME, CONF_SERIAL
from .coordinator import AgateCoordinator, ModbusCoordinator

# Keys redacted wherever they appear, including inside a coordinator's raw replies: the
# aGate serial (entry data, and identity/1101 reply field IBG_SN), aPower serials (1105
# devSN, and the 1301 power-flow reply's fhpSn list), the host/IP, and cloud credentials.
TO_REDACT = {
    CONF_HOST, CONF_SERIAL, CONF_CLOUD_USERNAME, CONF_CLOUD_PASSWORD,
    "serial", "device_serials", "IBG_SN", "devSN", "fhpSn",
}


def _tier_diagnostics(coordinator: AgateCoordinator | ModbusCoordinator) -> dict[str, Any]:
    return {
        "update_interval_s": coordinator.update_interval.total_seconds() if coordinator.update_interval else None,
        "last_update_success": coordinator.last_update_success,
        "last_reply": {str(key): reply for key, reply in (coordinator.data or {}).items()},
    }


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: AgateConfigEntry) -> dict[str, Any]:
    """Entry config, data source/fallback state, module detection and each tier's last reply."""
    rt = entry.runtime_data
    diagnostics: dict[str, Any] = {
        "entry": {
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "data_source": {
            "configured": rt.source,
            "active": rt.fast.active_source,
            "fallback_count": rt.fast.fallback_count,
            "last_fallback": rt.fast.last_fallback,
        },
        "modules": {
            module: {"installed": status.installed, "source": status.source, "detail": status.detail}
            for module, status in rt.modules.items()
        },
        "coordinators": {
            "fast": _tier_diagnostics(rt.fast),
            "detail": _tier_diagnostics(rt.detail),
            "config": _tier_diagnostics(rt.config),
            "static": _tier_diagnostics(rt.static),
        },
    }
    if rt.modbus is not None:
        diagnostics["coordinators"]["modbus"] = _tier_diagnostics(rt.modbus)
    return async_redact_data(diagnostics, TO_REDACT)
