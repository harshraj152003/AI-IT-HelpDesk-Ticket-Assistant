# Knowledge Article: KB-1002 - Outlook Email and Exchange Authentication Issues

## Scope

Applies to Microsoft Outlook Desktop (macOS/Windows) and Outlook on the Web (OWA).

## Common Symptoms

- Outlook prompts for password in an infinite loop
- Status bar displays "Disconnected" or "Need Password"
- Search indexing not returning recent messages or mailbox synchronization stalled

## Approved Self-Service Steps

1. **Clear Microsoft Identity Cache (macOS Keychain)**:
   - Quit Outlook completely.
   - Open macOS **Keychain Access**, search for `MicrosoftOffice`, `ADAL`, and `Exchange`.
   - Delete cached entries named `Microsoft Office Identities Cache 3` and `Microsoft Office Identities Settings 3`.
   - Restart Outlook and authenticate using your full company email and MFA.
2. **Windows Credential Manager Reset**:
   - Close Outlook.
   - Open **Control Panel** > **Credential Manager** > **Windows Credentials**.
   - Remove any entries starting with `MicrosoftOffice16_Data:ADAL` or `msteams`.
   - Restart Outlook and sign in.
3. **Outlook Safe Mode Test**:
   - On Windows: Run `outlook.exe /safe` to check if a conflicting third-party add-in is freezing synchronization.
   - Disable suspect COM add-ins under File > Options > Add-ins.
4. **Webmail Verification**:
   - Access `outlook.office.com` via an incognito browser window to verify if your mailbox is healthy on the server.

## Escalation Path

If webmail also fails or credentials are rejected repeatedly, route to **IT-Enterprise-Applications**.
