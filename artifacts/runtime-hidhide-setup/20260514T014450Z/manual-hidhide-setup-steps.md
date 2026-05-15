# Manual HidHide Setup Steps

These steps are intentionally explicit because HidHide is a driver/filter configuration surface.

1. Open HidHide Configuration Client.
2. Applications tab:
   - Add `C:\Users\kkids\AppData\Local\Programs\Python\Python312\python.exe`.
   - Add `C:\Users\kkids\AppData\Local\Programs\Python\Python312\pythonw.exe`.
3. Devices tab:
   - Select only physical Thrustmaster HOTAS One entries matching `VID_044F&PID_B68D`.
   - Physical HOTAS candidate: `HID-compliant game controller` / `HID\VID_044F&PID_B68D\8&39EC0CDD&0&0000`.
   - Physical HOTAS candidate: `USB Input Device` / `USB\VID_044F&PID_B68D\7&18CB956B&0&3`.
   - vJoy must remain visible; do not select vJoy entry `vJoy Driver` / `{D6E55CA0-1A2E-4234-AAF3-3852170B492F}\VJOYRAWPDO\1&2D595CA7&0&VJOYINSTANCE00`.
   - vJoy must remain visible; do not select vJoy entry `vJoy Device` / `ROOT\HIDCLASS\0000`.
4. In the client, enable device hiding.
5. Reconnect the HOTAS if needed.
6. Rerun:
   `python scripts/hidhide_setup_probe.py --verify --real-hotas-check --real-vjoy-writes`
