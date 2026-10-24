# Knowledge Article: KB-1006 - Microsoft 365 License and Software Provisioning

## Scope

Applies to Microsoft 365 Apps (Word, Excel, PowerPoint, Teams, Copilot) licensing activations.

## Common Symptoms

- "Unlicensed Product" or "View Only Mode" banner in Office apps
- Unable to edit documents or save files to OneDrive
- Copilot icon missing in Microsoft 365 apps

## Approved Self-Service Steps

1. **Sign Out and Reactivate**:
   - In Word or Excel, click on your profile avatar in the upper right.
   - Choose "Sign Out" from all accounts.
   - Restart the application and sign in with your primary enterprise email (`user@company.com`).
2. **Clear Cached Office Credentials (Windows)**:
   - Close all Office applications.
   - Open Command Prompt and navigate to `C:\Program Files\Microsoft Office\Office16`.
   - Run `cscript ospp.vbs /dstatus` to inspect current product key status.
3. **M365 Self-Service Portal Re-Sync**:
   - Navigate to `https://portal.office.com/account#subscriptions` in your browser.
   - Confirm an active Microsoft 365 E5 license is assigned to your account.

## Escalation Path

If the subscription status says "Suspended" or "Expired", route ticket to **IT-Enterprise-Applications**.
