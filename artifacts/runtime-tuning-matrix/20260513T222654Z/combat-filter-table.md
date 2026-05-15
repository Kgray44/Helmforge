# Combat Filter Runtime Matrix

| Item | Status | Evidence |
|---|---|---|
| Inactive base filtering | covered | combat filter parameters have no effect while combat is inactive |
| Combat alpha override | covered | combat_center_alpha and combat_edge_alpha become effective filter values |
| Combat slew override | covered | combat_same_slew and combat_reverse_slew limit same/reverse motion |
| Mode transition | covered | inactive -> active -> inactive preserves previous output state |
| Per-axis independence | covered | each axis reports its own effective combat filter values |
| Invalid combat values | covered | invalid combat filter values fall back to base finite values |
