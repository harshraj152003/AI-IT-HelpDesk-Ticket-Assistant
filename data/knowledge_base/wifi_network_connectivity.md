# Knowledge Article: KB-1005 - Office Wi-Fi and 802.1X Certificate Authentication

## Scope

Applies to the corporate wireless networks `Corp-Secure-WLAN` and `Corp-Guest`.

## Common Symptoms

- "Unable to join network Corp-Secure-WLAN"
- Certificate expiration prompt for RADIUS/802.1X
- Connected with "No Internet Access" while inside corporate offices

## Approved Self-Service Steps

1. **Forget Network and Re-Authenticate**:
   - Go to Wi-Fi settings, select `Corp-Secure-WLAN`, and choose "Forget Network".
   - Toggle Wi-Fi off and back on.
   - Select `Corp-Secure-WLAN`, enter your corporate username and password, and accept the `radius.corporate.internal` root certificate when prompted.
2. **Device Certificate Validity Check**:
   - Check device management portal (Intune Company Portal or Jamf Self Service) to confirm your device management profile is compliant and device health attestation is green.
3. **Toggle Airplane Mode**:
   - Enable Airplane mode for 10 seconds to cycle Wi-Fi and Bluetooth radio adapters.

## Escalation Path

If 802.1X certificates fail to renew or device is marked non-compliant in Intune, route to **IT-Network-Operations**.