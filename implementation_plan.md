# Web Dashboard for Discord Bot

A browser-based dashboard (like Carl-bot / Sapphire) to manage bot settings without typing commands. Built with **Flask** (Python) running alongside the bot.

## Architecture

```
User Browser  ──▶  Flask Web Server (port 5000)
                        │
                        ▼
                   config.json  ◀──  Discord Bot (discord.py)
```

Both the dashboard and bot read/write the **same [config.json](file:///c:/Users/Anshu/Documents/discord%20bot/config.json)**, so changes are instant.

---

## Proposed Changes

### New Dependencies

- `flask` — lightweight web framework
- `flask-cors` — for cross-origin support
- `requests` — for Discord OAuth2 API calls

---

### Dashboard Backend

#### [NEW] [dashboard.py](file:///c:/Users/Anshu/Documents/discord%20bot/dashboard.py)

Flask web server with these routes:

| Route | Purpose |
|-------|---------|
| `/` | Dashboard home — shows all settings |
| `/login` | Redirects to Discord OAuth2 |
| `/callback` | Handles Discord login callback |
| `/logout` | Clears session |
| `/api/config` (GET) | Returns current config |
| `/api/config` (POST) | Updates config (prefix, welcome, nickname, etc.) |
| `/api/giveaway/stop` (POST) | Stops the active giveaway |
| `/api/admin/logs` (GET) | Fetch dashboard access logs (Owner only) |
| `/api/admin/accounts` | Creates/Manages global dashboard accounts and maps them to multiple servers |

Only **you** (the bot owner) can access the dashboard entirely — secured with Discord OAuth2 login. 

For other Admins, we will restructure the login architecture. Instead of one ID/Password per server, the Bot Owner will create **Admin Accounts**. 
An Admin Account will consist of:
1. `Login ID`
2. `Password`
3. `Authorized Servers` (An array of Server IDs this account is allowed to manage)

When an Admin logs with their ID and password, the dashboard will show them a list of *only* the servers they are authorized to manage. They can then click between them seamlessly.

---

### Dashboard Audit Logging

#### [NEW] [audit_logs.json](file:///c:/Users/Anshu/Documents/discord%20bot/audit_logs.json)

A global file tracking who logged into the dashboard, and what servers they navigated to:
```json
[
  {
    "timestamp": "2026-03-02T22:00:00Z",
    "discord_username": "Anny",
    "action": "LOGIN_ATTEMPT",
    "dashboard_login_id": "TeamAlphaAdmin",
    "status": "Success",
    "ip_address": "127.0.0.1"
  },
  {
    "timestamp": "2026-03-02T22:05:00Z",
    "discord_username": "Anny",
    "action": "MANAGE_SERVER",
    "dashboard_login_id": "TeamAlphaAdmin",
    "guild_id": "server_id_here",
    "status": "Success",
    "ip_address": "127.0.0.1"
  }
]
```

### Dashboard Account Management

#### [NEW] [admin_accounts.json](file:///c:/Users/Anshu/Documents/discord%20bot/admin_accounts.json)

Replaces `server_logins.json`. Maps a `login_id` to a password and an array of allowed `guild_id`s.

#### [MODIFY] [dashboard.py](file:///c:/Users/Anshu/Documents/discord%20bot/dashboard.py)

- Add a `log_dashboard_action()` helper function for Audit logs.
- Replace `load_server_logins()` with `load_admin_accounts()`.
- Update `/api/server-login` to authenticate an account, verify the `guild_id` is within the account's allowed `authorized_servers`, and then grant the session.
- Create `/api/admin/accounts` to allow the Bot Owner to create `Login IDs`, set passwords, and grant access to multiple servers simultaneously.

#### [MODIFY] [templates/admin.html](file:///c:/Users/Anshu/Documents/discord%20bot/templates/admin.html)

- Redesign the UI into three Tabs: **Server Permissions**, **Admin Accounts**, and **Audit Logs**.
- **Admin Accounts**: Create user accounts and check checkboxes for which servers they can manage (1 server, or 5 servers, it's up to you).
- **Audit Logs**: A table that fetches from `/api/admin/logs` to display recent login attempts and actions.


---

### Dashboard Frontend

#### [NEW] [templates/dashboard.html](file:///c:/Users/Anshu/Documents/discord%20bot/templates/dashboard.html)

A single-page dark-themed dashboard with:
- **Sidebar** — navigation (Settings, Welcome, Giveaways)
- **Settings panel** — edit prefix, nickname prefix
- **Welcome panel** — edit welcome channel ID, welcome message
- **Giveaway panel** — create/stop giveaways, see claim count
- Modern dark UI with purple/blue accents (Discord-style)

#### [NEW] [static/style.css](file:///c:/Users/Anshu/Documents/discord%20bot/static/style.css)

Dark theme styling matching Discord's aesthetic.

---

### Bot Integration

#### [MODIFY] [bot.py](file:///c:/Users/Anshu/Documents/discord%20bot/bot.py)

- Import and start the Flask dashboard in a separate thread so both run simultaneously
- One command: `python bot.py` starts **both** the bot and the dashboard

---

### Config Updates

#### [MODIFY] [config.json](file:///c:/Users/Anshu/Documents/discord%20bot/config.json)

Add fields for dashboard settings:
```json
{
  "owner_id": "",
  "dashboard_secret": "change-this-to-a-random-string"
}
```

#### [MODIFY] [.env](file:///c:/Users/Anshu/Documents/discord%20bot/.env)

Add Discord OAuth2 credentials:
```
DISCORD_CLIENT_ID=your-client-id
DISCORD_CLIENT_SECRET=your-client-secret
DISCORD_REDIRECT_URI=http://localhost:5000/callback
```

---

> [!IMPORTANT]
> To enable Discord OAuth2 login, you need to:
> 1. Go to [Discord Developer Portal](https://discord.com/developers/applications) → your bot app
> 2. Go to **OAuth2** → add redirect URL: `http://localhost:5000/callback`
> 3. Copy the **Client ID** and **Client Secret** into [.env](file:///c:/Users/Anshu/Documents/discord%20bot/.env)
> 4. Set your Discord user ID as `owner_id` in [config.json](file:///c:/Users/Anshu/Documents/discord%20bot/config.json)

---

## Verification Plan

### Automated Tests
- Run `python bot.py` — confirm both the bot and dashboard start
- Visit `http://localhost:5000` — confirm the dashboard loads

### Manual Verification
- Log in via Discord OAuth2
- Change the prefix from the dashboard → verify it works in Discord
- Set welcome settings from dashboard → verify with `!testwelcome`
- Create a giveaway from dashboard → verify `!free` works
