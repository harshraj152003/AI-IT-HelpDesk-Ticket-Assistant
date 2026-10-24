# Knowledge Article: KB-1003 - Laptop Battery Health and Power Issues

## Scope

Applies to MacBook Pro M1/M2/M3, Dell Latitude 5000/7000 series, and Lenovo ThinkPad X1 Carbon.

## Common Symptoms

- Laptop battery draining rapidly (under 1 hour on full charge)
- "Service Recommended" or "Plugged in, not charging" indicator
- Device shuts down unexpectedly under normal load

## Approved Self-Service Steps

1. **Battery Diagnostic Report**:
   - On Windows (Dell/ThinkPad): Open Command Prompt as Administrator and execute `powercfg /batteryreport`. Check the "Full Charge Capacity" vs "Design Capacity". If full charge capacity is under 60%, replacement is warranted.
   - On macOS: Option-click the Apple logo > System Information > Power. Check "Cycle Count" and "Condition". Normal condition is typically under 1000 cycles.
2. **EC (Embedded Controller) / SMC Reset**:
   - ThinkPad / Dell: Shut down laptop, unplug AC power, press and hold the power button for 30 seconds to discharge residual power. Reconnect charger and power on.
   - MacBook (Apple Silicon): Shut down completely, connect the official 96W/140W USB-C charger, and restart after 60 seconds.
3. **Firmware & BIOS Power Management Update**:
   - Check Dell Command | Update or Lenovo Commercial Vantage for pending battery firmware fixes.

## Escalation Path

If battery health is degraded below 60% or battery swelling is detected, route to **IT-Hardware-EndUser-Support** for immediate hardware replacement.
