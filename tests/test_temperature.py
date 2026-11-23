"""Offline tests for the aGate temperature scale (upstream issue npds188#8).

Run:  <venv with homeassistant>/bin/python tests/test_temperature.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "custom_components")))

from franklinwh_local.const import CMD_POWER_FLOW  # noqa: E402
from franklinwh_local.coordinator import to_fast_data  # noqa: E402
from franklinwh_local.sensor import _agate_temperature  # noqa: E402

results = []


def check(name, got, want):
    results.append(got == want)
    print(("PASS " if got == want else "FAIL ") + f"{name}: {got!r}" + ("" if got == want else f" (want {want!r})"))


# Direct Connect (1301): t_amb is tenths of a degree C (other reporters see ~200-206 there
# for ~20 C; this site reads 142, i.e. 14.2 C).
check("Direct Connect: t_amb 142 -> 14.2 C", _agate_temperature({"t_amb": 142}), 14.2)
check("Direct Connect: t_amb 206 -> 20.6 C", _agate_temperature({"t_amb": 206}), 20.6)
check("Direct Connect: missing t_amb -> None", _agate_temperature({}), None)

# Modbus-sourced power flow (coordinator.to_fast_data): t_amb is filled from the SunSpec
# snapshot's temp_ambient, already in whole degrees C — must not be scaled a second time.
check("Modbus: t_amb already in degrees stays as-is",
      _agate_temperature({"source": "modbus", "t_amb": 14.2}), 14.2)
check("Modbus: missing t_amb -> None", _agate_temperature({"source": "modbus"}), None)

# End-to-end through to_fast_data(), as coordinator.py actually builds the Modbus flow dict.
MODBUS_SNAPSHOT = {
    "temp_ambient": 14.2, "grid_power": 100.0, "home_power": 200.0, "battery_power": -50.0,
    "solar_power": 0.0, "soc": 90.0, "mode_type": 1, "grid_voltage": 240.0,
    "grid_frequency": 60.0, "grid_current": 1.0, "conn_state": 1,
}
fast_data = to_fast_data(MODBUS_SNAPSHOT, None, [])
check("integration: Modbus snapshot through to_fast_data -> 14.2 C",
      _agate_temperature(fast_data[CMD_POWER_FLOW]), 14.2)

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
