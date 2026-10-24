# Knowledge Article: KB-1001 - VPN Connectivity and Gateway Troubleshooting

## Scope

Applies to Cisco AnyConnect and GlobalProtect VPN clients on Windows 11 and macOS.

## Common Symptoms

- "Connection attempt has timed out"
- Constant reconnect loop
- Internal corporate websites (GitLab, Confluence, Intranet) unreachable while connected

## Approved Self-Service Steps

1. **Network Adapter Reset**:
   - Disconnect from VPN.
   - Disconnect and reconnect your local Wi-Fi or Ethernet connection.
   - Wait 15 seconds to ensure you have a fresh DHCP lease and public IP.
2. **Clear DNS Cache**:
   - On Windows: Open Command Prompt as Administrator and run `ipconfig /flushdns`.
   - On macOS: Open Terminal and run `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`.
3. **Cisco AnyConnect Profile Refresh**:
   - Exit the AnyConnect client completely from the system tray or menu bar.
   - Delete temporary preferences in `~/Library/Preferences/Cisco` (macOS) or `%LOCALAPPDATA%\Cisco\Cisco AnyConnect Secure Mobility Client` (Windows).
   - Relaunch AnyConnect, select gateway `vpn.corporate.internal`, and sign in via SSO.
4. **MFA Verification**:
   - Ensure your Microsoft Authenticator push notification was approved and did not time out.

## Escalation Path

If these steps fail to restore connectivity, capture your public IP (`curl ifconfig.me`) and AnyConnect Diagnostic (DART) log bundle, then route to **IT-Network-Operations**.
