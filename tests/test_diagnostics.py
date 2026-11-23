"""Offline tests for diagnostics (no sensitive data in the dump).

Run:  <venv with homeassistant>/bin/python tests/test_diagnostics.py
"""
import asyncio
import json
import os
import sys
from datetime import timedelta
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "custom_components")))

from homeassistant.const import CONF_HOST, CONF_PORT  # noqa: E402

from franklinwh_local.const import (  # noqa: E402
    CMD_MODBUS, CMD_OFFGRID, CMD_POWER_FLOW, CONF_CLOUD_PASSWORD, CONF_CLOUD_USERNAME, CONF_SERIAL,
    SOURCE_FALLBACK, SOURCE_DIRECT,
)
from franklinwh_local.diagnostics import async_get_config_entry_diagnostics  # noqa: E402
from franklinwh_local.modules import ModuleStatus  # noqa: E402

results = []


def check(name, got, want):
    results.append(got == want)
    print(("PASS " if got == want else "FAIL ") + f"{name}: {got!r}" + ("" if got == want else f" (want {want!r})"))


HOST = "10.20.30.40"
AGATE_SERIAL = "10060006A02F24170129"
APOWER_SERIAL = "APOWERSERIAL999"
CLOUD_USER = "someone@example.com"
CLOUD_PASS = "super-secret-password"


def _coordinator(data, **extra):
    return SimpleNamespace(update_interval=timedelta(seconds=5), last_update_success=True, data=data, **extra)


def _entry():
    rt = SimpleNamespace(
        serial=AGATE_SERIAL,
        device_serials={1: APOWER_SERIAL},
        source=SOURCE_FALLBACK,
        modules={"generator": ModuleStatus(True, "local", "genEn=1, genStat=1")},
        fast=_coordinator(
            {CMD_POWER_FLOW: {"p_sun": 100, "fhpSn": [APOWER_SERIAL]}},
            active_source=SOURCE_DIRECT, fallback_count=2, last_fallback="2026-11-01 00:00:00",
        ),
        detail=_coordinator({CMD_OFFGRID: {"offgridState": 0}}),
        config=_coordinator({}),
        static=_coordinator({}),
        modbus=_coordinator({CMD_MODBUS: {"temp_ambient": 20.0}}),
    )
    return SimpleNamespace(
        data={CONF_HOST: HOST, CONF_PORT: 9000, CONF_SERIAL: AGATE_SERIAL},
        options={CONF_CLOUD_USERNAME: CLOUD_USER, CONF_CLOUD_PASSWORD: CLOUD_PASS},
        runtime_data=rt,
    )


diagnostics = asyncio.run(async_get_config_entry_diagnostics(None, _entry()))
dump = json.dumps(diagnostics, default=str)

check("host/IP not in dump", HOST in dump, False)
check("aGate serial not in dump", AGATE_SERIAL in dump, False)
check("aPower serial not in dump", APOWER_SERIAL in dump, False)
check("cloud username not in dump", CLOUD_USER in dump, False)
check("cloud password not in dump", CLOUD_PASS in dump, False)
check("entry data redacted", diagnostics["entry"]["data"][CONF_HOST], "**REDACTED**")
check("non-sensitive entry data kept", diagnostics["entry"]["data"][CONF_PORT], 9000)
check("fast tier's fhpSn redacted", diagnostics["coordinators"]["fast"]["last_reply"][str(CMD_POWER_FLOW)]["fhpSn"],
      "**REDACTED**")
check("fast tier's non-sensitive field kept",
      diagnostics["coordinators"]["fast"]["last_reply"][str(CMD_POWER_FLOW)]["p_sun"], 100)
check("data source info present", diagnostics["data_source"],
      {"configured": SOURCE_FALLBACK, "active": SOURCE_DIRECT, "fallback_count": 2,
       "last_fallback": "2026-11-01 00:00:00"})
check("module detection present", diagnostics["modules"]["generator"],
      {"installed": True, "source": "local", "detail": "genEn=1, genStat=1"})
check("modbus tier included", diagnostics["coordinators"]["modbus"]["last_reply"][str(CMD_MODBUS)],
      {"temp_ambient": 20.0})
check("coordinator interval reported", diagnostics["coordinators"]["detail"]["update_interval_s"], 5.0)

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
