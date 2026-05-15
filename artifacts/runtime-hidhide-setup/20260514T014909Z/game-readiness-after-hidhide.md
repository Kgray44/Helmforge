# Game Readiness After HidHide

[x] 1. HidHide installed.
[ ] 2. HidHide enabled.
[ ] 3. Physical HOTAS selected/hidden by VID/PID.
[x] 4. vJoy not hidden.
[x] 5. Bridge/Python/HelmForge executable allow-listed.
[x] 6. Target game not allow-listed.
[ ] 7. Bridge still detects physical HOTAS.
[ ] 8. vJoy detected.
[ ] 9. Physical HOTAS input reaches Bridge after hiding.
[ ] 10. Runtime output intent changes.
[ ] 11. vJoy write calls accepted.
[ ] 12. Target game should bind to vJoy Device 1.
[ ] 13. If the game sees both physical HOTAS and vJoy, double input may occur.
[ ] 14. If HelmForge stops seeing HOTAS, allow-list is wrong.
[ ] 15. If game does not see vJoy, vJoy may be hidden/disabled or game may need restart.
[ ] 16. Reconnect HOTAS and restart game after changing HidHide settings if needed.
[ ] 17. vJoy readback remains not implemented unless separately proven.

Manual game-facing visibility checklist:
- Open joy.cpl.
- Confirm vJoy Device 1 appears.
- Confirm physical Thrustmaster HOTAS does not appear to game-facing contexts after HidHide is enabled.
- If both physical HOTAS and vJoy appear in the game, double input may occur.
- Target game should bind to vJoy Device 1.
- Do not bind the physical HOTAS directly when using HelmForge remapping.
- If HelmForge stops seeing HOTAS, the allow-list is wrong.
- If the game does not see vJoy, vJoy may be hidden, disabled, or the game may need restart.
- Restart the game after changing HidHide settings.
