from __future__ import annotations

import ctypes

from shared_core.runtime.hotas_input import (
    WindowsJoystickInputBackend,
    WindowsRawInputBackend,
    _JOYCAPSW,
    _JOYINFOEX,
    _winmm_frame,
)


def _caps() -> _JOYCAPSW:
    caps = _JOYCAPSW()
    for prefix in ("X", "Y", "Z", "R", "U", "V"):
        setattr(caps, f"w{prefix}min", 0)
        setattr(caps, f"w{prefix}max", 65535)
    caps.wNumButtons = 15
    caps.wNumAxes = 6
    return caps


def _info(**positions: int) -> _JOYINFOEX:
    info = _JOYINFOEX()
    info.dwSize = ctypes.sizeof(_JOYINFOEX)
    info.dwFlags = 0xFF
    for name in ("X", "Y", "Z", "R", "U", "V"):
        setattr(info, f"dw{name}pos", positions.get(name, 32767))
    info.dwPOV = 0xFFFF
    return info


def test_winmm_hotas_one_rear_throttle_axis_v_is_user_facing_aux1():
    frame = _winmm_frame(_info(V=65535, U=32767), _caps())
    axes = {axis["logical_name"]: axis for axis in frame["axes"]}

    assert axes["Aux 1"]["raw_name"] == "V"
    assert axes["Aux 1"]["raw_value"] == 65535
    assert axes["Aux 2"]["raw_name"] == "U"
    assert axes["Aux 2"]["raw_value"] == 32767


def test_default_physical_backend_prefers_winmm_over_uncalibrated_raw_input_decoder():
    raw_caps = WindowsRawInputBackend(provider=None).get_capabilities()
    winmm_caps = WindowsJoystickInputBackend().get_capabilities()

    assert raw_caps.backend_priority < winmm_caps.backend_priority
