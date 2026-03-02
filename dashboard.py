"""
Web Dashboard — Flask server for managing the Discord bot via browser.
Secured with Discord OAuth2 so only the bot owner can access it.
"""

import os
import json
import requests
from flask import Flask, render_template, request, redirect, session, jsonify, url_for, Response
from dotenv import load_dotenv

load_dotenv()

import datetime

app = Flask(__name__)

# ─── Discord OAuth2 Config ────────────────────────────────────────
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:5000/callback")
DISCORD_API = "https://discord.com/api/v10"
OAUTH2_URL = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds&prompt=consent"


# Load or generate a persistent secret key for sessions
SECRET_KEY_FILE = os.path.join(os.path.dirname(__file__), ".secret_key")
if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, "rb") as f:
        app.secret_key = f.read()
else:
    app.secret_key = os.urandom(24)
    with open(SECRET_KEY_FILE, "wb") as f:
        f.write(app.secret_key)

# ─── Config ───────────────────────────────────────────────────────
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=1)
if os.getenv("RENDER"):
    app.config['SESSION_COOKIE_SECURE'] = True # Secure cookies in production
else:
    app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True

# ─── Paths ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
ADMIN_ACCOUNTS_FILE = os.path.join(BASE_DIR, "admin_accounts.json")
AUDIT_LOGS_FILE = os.path.join(BASE_DIR, "audit_logs.json")

def get_guild_file(guild_id, filename):
    folder = os.path.join(BASE_DIR, "data", str(guild_id))
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, filename)

def load_config(guild_id):
    path = get_guild_file(guild_id, "config.json")
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_config(guild_id, data):
    with open(get_guild_file(guild_id, "config.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_claims(guild_id):
    path = get_guild_file(guild_id, "claims.json")
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_claims(guild_id, data):
    with open(get_guild_file(guild_id, "claims.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_giveaways(guild_id):
    path = get_guild_file(guild_id, "giveaways.json")
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_giveaways(guild_id, data):
    with open(get_guild_file(guild_id, "giveaways.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_feedback_claims(guild_id):
    path = get_guild_file(guild_id, "feedback_claims.json")
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_feedback_claims(guild_id, data):
    with open(get_guild_file(guild_id, "feedback_claims.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_feedback_events(guild_id):
    path = get_guild_file(guild_id, "feedback_events.json")
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_feedback_events(guild_id, data):
    with open(get_guild_file(guild_id, "feedback_events.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_message_log(guild_id):
    path = get_guild_file(guild_id, "message_log.json")
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_message_log(guild_id, data):
    with open(get_guild_file(guild_id, "message_log.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_templates(guild_id):
    path = get_guild_file(guild_id, "templates.json")
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_templates(guild_id, data):
    with open(get_guild_file(guild_id, "templates.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_admin_accounts():
    if not os.path.exists(ADMIN_ACCOUNTS_FILE):
        return {}
    with open(ADMIN_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_admin_accounts(data):
    with open(ADMIN_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def log_dashboard_action(action, login_id="", guild_id="", status="Success"):
    """Helper to log dashboard access attempts and actions."""
    user = session.get("user")
    if not user:
        return
        
    log_entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "discord_username": user.get("username", "Unknown"),
        "discord_id": user.get("id", "Unknown"),
        "action": action,
        "dashboard_login_id": login_id,
        "guild_id": guild_id,
        "status": status,
        "ip_address": request.remote_addr
    }
    
    logs = []
    if os.path.exists(AUDIT_LOGS_FILE):
        try:
            with open(AUDIT_LOGS_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            pass
            
    # keep only the last 500 logs to prevent file bloating
    logs.insert(0, log_entry)
    logs = logs[:500]
    
    with open(AUDIT_LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


def is_owner():
    """Check if the logged-in user is the bot owner."""
    user = session.get("user")
    if not user:
        return False
        
    # Highest Priority: Environment variable override
    env_owner_id = os.getenv("OWNER_ID")
    if env_owner_id:
        return str(user["id"]) == str(env_owner_id).strip()
        
    owner_file = os.path.join(BASE_DIR, "owner.json")
    if not os.path.exists(owner_file):
        # If no owner.json, fetch the true owner from Discord application info
        token = os.getenv("DISCORD_TOKEN")
        if token:
            try:
                resp = requests.get(f"{DISCORD_API}/oauth2/applications/@me", headers={"Authorization": f"Bot {token}"}, timeout=10)
                if resp.status_code == 200:
                    app_data = resp.json()
                    real_owner_id = ""
                    if "team" in app_data and app_data["team"]:
                        real_owner_id = app_data["team"]["owner_user_id"]
                    elif "owner" in app_data:
                        real_owner_id = app_data["owner"]["id"]
                        
                    if real_owner_id:
                        with open(owner_file, "w", encoding="utf-8") as f:
                            json.dump({"owner_id": real_owner_id}, f, indent=2)
                        return str(user["id"]) == str(real_owner_id)
            except Exception:
                pass
                
        # If token fails or is missing, fall back to first login (dangerous on cloud, but backwards compatible locally)
        with open(owner_file, "w", encoding="utf-8") as f:
            json.dump({"owner_id": user["id"]}, f, indent=2)
        return True
        
    with open(owner_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    return str(user["id"]) == str(data.get("owner_id"))


def is_authenticated():
    """Check if the logged-in user has selected an active server."""
    return bool(session.get("user") and session.get("active_guild"))


def extract_channel_id(input_str):
    """
    Extract a channel ID from a raw ID string or a Discord channel URL.
    Examples:
      '1478077469150941267' -> '1478077469150941267'
      'https://discord.com/channels/123/1478077469150941267' -> '1478077469150941267'
    """
    input_str = str(input_str).strip()
    if not input_str:
        return ""
    
    # If it's a URL, split by '/' and take the last part
    if "discord.com/channels/" in input_str or "ptb.discord.com/channels/" in input_str or "canary.discord.com/channels/" in input_str:
        parts = input_str.split('/')
        input_str = parts[-1].strip()
        
    # Final check: A valid Discord channel ID is strictly numeric.
    # We strip any weird punctuation they might have typed.
    import re
    cleaned = re.sub(r'[^0-9]', '', input_str)
    return cleaned


# ─── Routes ───────────────────────────────────────────────────────

@app.route("/")
def home():
    """Dashboard home page."""
    user = session.get("user")
    if not user:
        return render_template("login.html", oauth_url=OAUTH2_URL)
        
    active_guild = session.get("active_guild")
    if not active_guild:
        return redirect("/servers")
        
    admin_guilds = session.get("admin_guilds", [])
    active_server_name = "Unknown Server"
    for g in admin_guilds:
        if str(g["id"]) == str(active_guild):
            active_server_name = g["name"]
            break
            
    cfg = load_config(active_guild)
    claims = load_claims(active_guild)
    return render_template("dashboard.html", user=user, active_server=active_server_name, config=cfg, claims_count=len(claims), is_owner=is_owner())


@app.route("/login")
def login():
    """Redirect to Discord OAuth2."""
    return redirect(OAUTH2_URL)


@app.route("/callback")
def callback():
    """Handle Discord OAuth2 callback."""
    code = request.args.get("code")
    if not code:
        return redirect("/")

    # Exchange code for access token
    token_response = requests.post(
        f"{DISCORD_API}/oauth2/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10
    )

    if token_response.status_code != 200:
        return "❌ Failed to authenticate with Discord.", 400

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    # Get user info
    user_response = requests.get(
        f"{DISCORD_API}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )

    if user_response.status_code != 200:
        return "❌ Failed to fetch user info.", 400

    user_data = user_response.json()
    
    session.permanent = False  # Ensure cookie expires when browser closes
    session["user"] = {
        "id": user_data["id"],
        "username": user_data["username"],
        "discriminator": user_data.get("discriminator", "0"),
        "avatar": user_data.get("avatar", ""),
        "global_name": user_data.get("global_name", user_data["username"]),
    }
    
    # Get user guilds
    guilds_response = requests.get(
        f"{DISCORD_API}/users/@me/guilds",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )
    
    admin_guilds = []
    if guilds_response.status_code == 200:
        for g in guilds_response.json():
            # Check for Administrator permission (0x8)
            perms = int(g.get("permissions", 0))
            if (perms & 0x8) == 0x8:
                admin_guilds.append({
                    "id": g["id"],
                    "name": g["name"],
                    "icon": g.get("icon", "")
                })
                
    session["admin_guilds"] = admin_guilds

    return redirect("/servers")


@app.route("/logout")
def logout():
    """Clear session and log out."""
    session.clear()
    return redirect("/")


@app.route("/servers")
def servers():
    """Render the server selection page."""
    user = session.get("user")
    if not user:
        return redirect("/login")
        
    admin_guilds = session.get("admin_guilds", [])
    
    # Fetch bot's guilds to find the intersection
    token = os.getenv("DISCORD_TOKEN")
    try:
        bot_guilds_response = requests.get(
            f"{DISCORD_API}/users/@me/guilds",
            headers={"Authorization": f"Bot {token}"},
            timeout=10
        )
        bot_guild_ids = set()
        if bot_guilds_response.status_code == 200:
            for g in bot_guilds_response.json():
                bot_guild_ids.add(g["id"])
    except requests.exceptions.RequestException:
        bot_guild_ids = set() # Fail gracefully if Discord API is unreachable
            
    # Include only guilds where the bot is also present
    valid_guilds = [g for g in admin_guilds if g["id"] in bot_guild_ids]
    
    return render_template("server_select.html", user=user, guilds=valid_guilds, is_owner=is_owner())


@app.route("/api/owner-login", methods=["POST"])
def owner_login():
    """Allow the Bot Owner to bypass the normal server credentials."""
    if not is_owner():
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    guild_id = data.get("guild_id")
    
    if not guild_id:
        return jsonify({"error": "Missing guild_id"}), 400
        
    session["active_guild"] = guild_id
    return jsonify({"success": True})


@app.route("/api/server-login", methods=["POST"])
def server_login():
    """Verify Admin Account ID/Pass and check if they are authorized for the specific server."""
    user = session.get("user")
    if not user:
        return jsonify({"success": False, "error": "Not logged in with Discord"}), 401
        
    data = request.json
    guild_id = data.get("guild_id")
    login_id = data.get("login_id")
    password = data.get("password")
    
    accounts = load_admin_accounts()
    
    # Track attempt
    if login_id not in accounts:
        log_dashboard_action("LOGIN_ATTEMPT", login_id, guild_id, "Failed - Unknown Account")
        return jsonify({"success": False, "error": "Invalid Dashboard Login ID."}), 403
        
    account = accounts[login_id]
    
    if account["password"] != password:
        log_dashboard_action("LOGIN_ATTEMPT", login_id, guild_id, "Failed - Bad Password")
        return jsonify({"success": False, "error": "Invalid Password."}), 403
        
    if guild_id not in account.get("authorized_servers", []):
        log_dashboard_action("LOGIN_ATTEMPT", login_id, guild_id, "Failed - Unauthorized Server")
        return jsonify({"success": False, "error": "Your account is not authorized to manage this server."}), 403
        
    # Success
    session["active_guild"] = guild_id
    log_dashboard_action("LOGIN_SUCCESS", login_id, guild_id, "Success")
    return jsonify({"success": True})


@app.route("/admin")
def admin_dashboard():
    """Global Bot Owner dashboard to manage Admin Accounts and Audit Logs."""
    if not is_owner():
        return redirect("/")
        
    user = session.get("user")
    
    # Fetch bot's guilds
    token = os.getenv("DISCORD_TOKEN")
    try:
        bot_guilds_response = requests.get(
            f"{DISCORD_API}/users/@me/guilds",
            headers={"Authorization": f"Bot {token}"},
            timeout=10
        )
        bot_guilds = []
        if bot_guilds_response.status_code == 200:
            bot_guilds = bot_guilds_response.json()
    except requests.exceptions.RequestException:
        bot_guilds = []
        
    accounts = load_admin_accounts()
    logs = []
    if os.path.exists(AUDIT_LOGS_FILE):
        try:
            with open(AUDIT_LOGS_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            pass
        
    return render_template("admin.html", user=user, servers=bot_guilds, accounts=accounts, logs=logs, active_guild=session.get("active_guild"))


@app.route("/api/admin/accounts", methods=["POST"])
def admin_create_account():
    """Create or update an Admin Account with authorized servers."""
    if not is_owner():
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    login_id = data.get("login_id")
    password = data.get("password")
    authorized_servers = data.get("authorized_servers", [])
    
    if not login_id or not password:
        return jsonify({"error": "Missing login ID or password"}), 400
        
    accounts = load_admin_accounts()
    accounts[login_id] = {
        "password": password,
        "authorized_servers": authorized_servers,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    save_admin_accounts(accounts)
    
    return jsonify({"success": True})


@app.route("/api/admin/accounts/<login_id>", methods=["DELETE"])
def admin_delete_account(login_id):
    """Delete an Admin Account."""
    if not is_owner():
        return jsonify({"error": "Unauthorized"}), 403
        
    accounts = load_admin_accounts()
    if login_id in accounts:
        del accounts[login_id]
        save_admin_accounts(accounts)
        
    return jsonify({"success": True})


# ─── API Endpoints ────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
def get_config():
    """Return current bot config."""
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")
    cfg = load_config(guild_id)
    # Don't expose secrets
    safe_cfg = {k: v for k, v in cfg.items() if k not in ("dashboard_secret",)}
    return jsonify(safe_cfg)


@app.route("/api/config", methods=["POST"])
def update_config():
    """Update bot config from dashboard."""
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")

    data = request.json
    cfg = load_config(guild_id)

    # Only allow updating specific fields
    allowed_fields = ["prefix", "nickname_prefix", "welcome_channel_id", "welcome_message"]
    for field in allowed_fields:
        if field in data:
            if field == "welcome_channel_id":
                cfg[field] = extract_channel_id(data[field])
            else:
                cfg[field] = data[field]

    save_config(guild_id, cfg)
    return jsonify({"success": True, "config": cfg})


@app.route("/api/giveaway", methods=["GET"])
def get_giveaway():
    """Return current giveaway info."""
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")
    cfg = load_config(guild_id)
    g_data = load_giveaways(guild_id)
    
    gift = cfg.get("free_gift", {})
    event_id = gift.get("event_id")
    active_claims = {}
    
    if event_id and event_id in g_data:
        active_claims = g_data[event_id].get("claims", {})
    else:
        # Legacy fallback if no event_id was set (the old active giveaway)
        active_claims = load_claims(guild_id)
        
        # Ensure it exists in g_data so the UI can render it
        if gift and gift.get("active"):
            # Mock a history entry for the UI to display the active event
            import time, datetime
            mock_id = event_id or "legacy_active"
            gift["event_id"] = mock_id
            
            g_data[mock_id] = {
                "title": gift.get("title", "Legacy Gift"),
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "claims": active_claims
            }
            
    return jsonify({
        "giveaway": gift,
        "claims_count": len(active_claims),
        "claims": active_claims,
        "history": g_data
    })


@app.route("/api/giveaway", methods=["POST"])
def create_giveaway():
    """Create or update a giveaway with full custom embed data."""
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")

    import time, datetime
    event_id = str(int(time.time()))

    data = request.json
    cfg = load_config(guild_id)
    cfg["free_gift"] = {
        "event_id": event_id,
        "title": data.get("title", "Free Gift"),
        "description": data.get("description", ""),
        "gift_link": data.get("gift_link", ""),
        "message_text": data.get("message_text", ""),
        "active": True,
        # Custom embed data for DM
        "embed": {
            "color": data.get("color", "#FFD700"),
            "author_name": data.get("author_name", ""),
            "author_icon": data.get("author_icon", ""),
            "thumbnail": data.get("thumbnail", ""),
            "image": data.get("image", ""),
            "footer_text": data.get("footer_text", ""),
            "footer_icon": data.get("footer_icon", ""),
            "fields": data.get("fields", []),
        },
    }
    save_config(guild_id, cfg)
    
    g_data = load_giveaways(guild_id)
    g_data[event_id] = {
        "title": cfg["free_gift"]["title"],
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "claims": {}
    }
    save_giveaways(guild_id, g_data)
    save_claims(guild_id, {})
    return jsonify({"success": True, "giveaway": cfg["free_gift"]})


@app.route("/api/giveaway/stop", methods=["POST"])
def stop_giveaway():
    """Stop the active giveaway."""
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")

    cfg = load_config(guild_id)
    event_id = None
    if "free_gift" in cfg:
        cfg["free_gift"]["active"] = False
        event_id = cfg["free_gift"].get("event_id")
        save_config(guild_id, cfg)

    g_data = load_giveaways(guild_id)
    if event_id and event_id in g_data:
        claims_count = len(g_data[event_id].get("claims", {}))
    else:
        claims_count = len(load_claims(guild_id))

    return jsonify({"success": True, "claims_count": claims_count})


@app.route("/api/giveaway/reset", methods=["POST"])
def reset_claims():
    """Reset claims without stopping the giveaway."""
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")

    cfg = load_config(guild_id)
    gift = cfg.get("free_gift")
    if not gift or not gift.get("active"):
        save_claims(guild_id, {})
        return jsonify({"success": True})

    import time, datetime
    old_event_id = gift.get("event_id")
    g_data = load_giveaways(guild_id)
    
    if old_event_id and old_event_id in g_data:
        import copy
        resets = g_data[old_event_id].get("past_resets", [])
        current_claims = g_data[old_event_id].get("claims", {})
        if current_claims:
            resets.append({
                "reset_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "claims": copy.deepcopy(current_claims)
            })
            g_data[old_event_id]["past_resets"] = resets
            g_data[old_event_id]["claims"] = {}
            # Title cleanup just in case previous patch applied it
            if g_data[old_event_id]["title"].endswith(" (Before Reset)"):
                g_data[old_event_id]["title"] = g_data[old_event_id]["title"].replace(" (Before Reset)", "")
            
            save_giveaways(guild_id, g_data)
    
    save_claims(guild_id, {})
    return jsonify({"success": True})


# ─── Feedback System Endpoints ────────────────────────────────────

@app.route("/api/feedback", methods=["GET"])
def get_feedback():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")
    cfg = load_config(guild_id)
    events = load_feedback_events(guild_id)
    
    gift = cfg.get("feedback_gift", {})
    event_id = gift.get("event_id")
    active_claims = {}
    
    if event_id and event_id in events:
        active_claims = events[event_id].get("claims", {})
    else:
        active_claims = load_feedback_claims(guild_id)
            
    return jsonify({
        "giveaway": gift,
        "claims_count": len(active_claims),
        "claims": active_claims,
        "history": events
    })


@app.route("/api/feedback", methods=["POST"])
def create_feedback():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")

    import time, datetime
    event_id = str(int(time.time()))

    data = request.json
    cfg = load_config(guild_id)
    cfg["feedback_gift"] = {
        "event_id": event_id,
        "title": data.get("title", "Feedback Reward"),
        "description": data.get("description", ""),
        "gift_link": data.get("gift_link", ""),
        "message_text": data.get("message_text", ""),
        "log_channel_id": extract_channel_id(data.get("log_channel_id", "")),
        "admin_id": data.get("admin_id", ""),
        "response_prompt": data.get("response_prompt", ""),
        "active": True,
        "embed": {
            "color": data.get("color", "#5865F2"),
            "author_name": data.get("author_name", ""),
            "author_icon": data.get("author_icon", ""),
            "thumbnail": data.get("thumbnail", ""),
            "image": data.get("image", ""),
            "footer_text": data.get("footer_text", ""),
            "footer_icon": data.get("footer_icon", ""),
            "fields": data.get("fields", []),
        },
    }
    save_config(guild_id, cfg)
    
    events = load_feedback_events(guild_id)
    events[event_id] = {
        "title": cfg["feedback_gift"]["title"],
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "claims": {}
    }
    save_feedback_events(guild_id, events)
    save_feedback_claims(guild_id, {})
    return jsonify({"success": True, "giveaway": cfg["feedback_gift"]})


@app.route("/api/feedback/stop", methods=["POST"])
def stop_feedback():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")

    cfg = load_config(guild_id)
    event_id = None
    if "feedback_gift" in cfg:
        cfg["feedback_gift"]["active"] = False
        event_id = cfg["feedback_gift"].get("event_id")
        save_config(guild_id, cfg)

    events = load_feedback_events(guild_id)
    if event_id and event_id in events:
        claims_count = len(events[event_id].get("claims", {}))
    else:
        claims_count = len(load_feedback_claims(guild_id))

    return jsonify({"success": True, "claims_count": claims_count})


@app.route("/api/feedback/reset", methods=["POST"])
def reset_feedback():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")

    cfg = load_config(guild_id)
    gift = cfg.get("feedback_gift")
    if not gift or not gift.get("active"):
        save_feedback_claims(guild_id, {})
        return jsonify({"success": True})

    import time, datetime
    old_event_id = gift.get("event_id")
    events = load_feedback_events(guild_id)
    
    if old_event_id and old_event_id in events:
        import copy
        resets = events[old_event_id].get("past_resets", [])
        current_claims = events[old_event_id].get("claims", {})
        if current_claims:
            resets.append({
                "reset_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "claims": copy.deepcopy(current_claims)
            })
            events[old_event_id]["past_resets"] = resets
            events[old_event_id]["claims"] = {}
            if events[old_event_id]["title"].endswith(" (Before Reset)"):
                events[old_event_id]["title"] = events[old_event_id]["title"].replace(" (Before Reset)", "")
            save_feedback_events(guild_id, events)
    
    save_feedback_claims(guild_id, {})
    return jsonify({"success": True})


# ─── Commands API ─────────────────────────────────────────────────

@app.route("/api/commands", methods=["GET"])
def get_commands():
    """Return all built-in bot commands."""
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")
    cfg = load_config(guild_id)
    prefix = cfg.get("prefix", "!")

    # We can't directly access the bot object's command list from Flask,
    # so we build a static list from the known cog files.
    # The bot also exposes get_commands_list() but it's in the bot's thread.
    builtin = [
        {"name": "help", "help": "Display all commands with descriptions.", "cog": "Help"},
        {"name": "free", "help": "Claim the current free gift! The bot will DM you the details.", "cog": "FreeGiveaway"},
        {"name": "setfree", "help": "Set the free gift message. Usage: !setfree Title | Description | Link/Code", "cog": "FreeGiveaway", "admin_only": True},
        {"name": "stopfree", "help": "Deactivate the current free gift giveaway.", "cog": "FreeGiveaway", "admin_only": True},
        {"name": "reward", "help": "Claim the active feedback reward.", "cog": "FeedbackGift"},
        {"name": "dm", "help": "DM a user. Usage: !dm @user Your message here", "cog": "DirectMessage", "admin_only": True},
        {"name": "embed", "help": "Create a rich embed. Usage: !embed Title | Description | Color(hex)", "cog": "Embed"},
        {"name": "announce", "help": "Send a fancy announcement embed. Usage: !announce Your message here", "cog": "Embed"},
        {"name": "setprefix", "help": "Change the command prefix. Usage: !setprefix ?", "cog": "SetPrefix", "admin_only": True},
        {"name": "setnickprefix", "help": "Set the nickname prefix for joining members. Usage: !setnickprefix AC", "cog": "SetNickPrefix", "admin_only": True},
        {"name": "setwelcome", "help": "Set the welcome channel and message. Usage: !setwelcome #channel Welcome, {user}!", "cog": "SetWelcome", "admin_only": True},
        {"name": "testwelcome", "help": "Preview the welcome message as if you just joined.", "cog": "SetWelcome", "admin_only": True},
        {"name": "mute", "help": "Timeout a user. Usage: !mute @user [duration like 10m, 1h, 1d]", "cog": "Moderation", "admin_only": True},
        {"name": "unmute", "help": "Remove timeout from a user. Usage: !unmute @user", "cog": "Moderation", "admin_only": True},
        {"name": "kick", "help": "Kick a user from the server. Usage: !kick @user [reason]", "cog": "Moderation", "admin_only": True},
        {"name": "ban", "help": "Ban a user from the server. Usage: !ban @user [reason]", "cog": "Moderation", "admin_only": True},
        {"name": "setrole", "help": "Add a role to a user. Usage: !setrole @user @role", "cog": "Moderation", "admin_only": True},
        {"name": "removerole", "help": "Remove a role from a user. Usage: !removerole @user @role", "cog": "Moderation", "admin_only": True},
        {"name": "purge", "help": "Delete messages in bulk. Usage: !purge [number] (max 100)", "cog": "Moderation", "admin_only": True},
    ]

    custom = cfg.get("custom_commands", {})
    return jsonify({"builtin": builtin, "custom": custom, "prefix": prefix})


@app.route("/api/custom-commands", methods=["GET"])
def get_custom_commands():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")
    cfg = load_config(guild_id)
    return jsonify({"custom_commands": cfg.get("custom_commands", {})})


@app.route("/api/custom-commands", methods=["POST"])
def save_custom_command():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")

    data = request.json
    cmd_name = data.get("name", "").strip().lower()
    if not cmd_name:
        return jsonify({"error": "Command name is required"}), 400

    # Don't allow overriding built-in commands
    builtin_names = ["help", "free", "setfree", "stopfree", "reward", "dm",
                     "embed", "announce", "setprefix", "setnickprefix",
                     "setwelcome", "testwelcome", "mute", "unmute", "kick",
                     "ban", "setrole", "removerole", "purge"]
    if cmd_name in builtin_names:
        return jsonify({"error": f"'{cmd_name}' is a built-in command and cannot be overridden"}), 400

    cfg = load_config(guild_id)
    if "custom_commands" not in cfg:
        cfg["custom_commands"] = {}

    cmd_type = data.get("type", "text")
    action = data.get("action", "none")

    cmd_entry = {
        "type": cmd_type,
        "admin_only": data.get("admin_only", False),
        "action": action,
    }

    # Action-specific fields
    if action in ("mute",):
        cmd_entry["action_duration"] = data.get("action_duration", 10)
    if action in ("kick", "ban"):
        cmd_entry["action_reason"] = data.get("action_reason", "")
    if action in ("addrole", "removerole"):
        cmd_entry["action_role_id"] = data.get("action_role_id", "")

    # Response config
    if cmd_type == "embed":
        cmd_entry["embed"] = {
            "title": data.get("embed_title", ""),
            "description": data.get("embed_description", ""),
            "color": data.get("embed_color", "#5865F2"),
            "image": data.get("embed_image", ""),
            "thumbnail": data.get("embed_thumbnail", ""),
            "footer_text": data.get("embed_footer_text", ""),
            "footer_icon": data.get("embed_footer_icon", ""),
        }
    elif cmd_type == "text":
        cmd_entry["response"] = data.get("response", "")

    cfg["custom_commands"][cmd_name] = cmd_entry
    save_config(guild_id, cfg)
    return jsonify({"success": True, "command": cmd_entry})


@app.route("/api/custom-commands", methods=["DELETE"])
def delete_custom_command():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")

    data = request.json
    cmd_name = data.get("name", "").strip().lower()
    if not cmd_name:
        return jsonify({"error": "Command name is required"}), 400

    cfg = load_config(guild_id)
    custom = cfg.get("custom_commands", {})
    if cmd_name in custom:
        del custom[cmd_name]
        cfg["custom_commands"] = custom
        save_config(guild_id, cfg)
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Command not found"}), 404


# ─── Image Proxy (for preview CORS) ───────────────────────────────

@app.route("/api/proxy-image")
def proxy_image():
    """Proxy external images to bypass CORS for live preview."""
    url = request.args.get("url", "")
    if not url:
        return "", 400
    try:
        resp = requests.get(url, timeout=10, stream=True)
        content_type = resp.headers.get("Content-Type", "").lower()
        if not content_type.startswith("image/"):
            return "Not an image", 415
        return Response(resp.content, content_type=content_type)
    except requests.exceptions.Timeout:
        return "Image fetch timed out", 504
    except Exception:
        return "", 404


# ─── Embed Builder API ────────────────────────────────────────────

@app.route("/api/embed/send", methods=["POST"])
def send_embed():
    """Send a custom embed to a Discord channel using the bot token."""
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")

    data = request.json
    channel_id = extract_channel_id(data.get("channel_id", ""))
    if not channel_id:
        return jsonify({"error": "Channel ID is required"}), 400

    # Build the Discord embed object
    embed = {}
    if data.get("title"):
        embed["title"] = data["title"]
    if data.get("description"):
        embed["description"] = data["description"]
    if data.get("color"):
        import numbers
        if isinstance(data["color"], numbers.Integral):
            embed["color"] = data["color"]
        else:
            # Convert hex color to integer
            hex_color = str(data["color"]).lstrip("#")
            try:
                embed["color"] = int(hex_color, 16)
            except ValueError:
                embed["color"] = 5793266  # Default blurple

    if data.get("author_name"):
        embed["author"] = {"name": data["author_name"]}
        if data.get("author_icon"):
            embed["author"]["icon_url"] = data["author_icon"]

    if data.get("thumbnail"):
        embed["thumbnail"] = {"url": data["thumbnail"]}
    if data.get("image"):
        embed["image"] = {"url": data["image"]}

    if data.get("footer_text"):
        embed["footer"] = {"text": data["footer_text"]}
        if data.get("footer_icon"):
            embed["footer"]["icon_url"] = data["footer_icon"]

    # Add fields
    fields = data.get("fields", [])
    if fields:
        embed["fields"] = []
        for field in fields:
            if field.get("name") and field.get("value"):
                embed["fields"].append({
                    "name": field["name"],
                    "value": field["value"],
                    "inline": field.get("inline", False),
                })

    # Send via Discord REST API
    bot_token = os.getenv("DISCORD_TOKEN", "")
    message_content = data.get("message_content", "")

    payload = {"embeds": [embed]}
    if message_content:
        payload["content"] = message_content

    try:
        response = requests.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            json=payload,
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
            },
            timeout=10
        )

        if response.status_code in (200, 201):
            import datetime
            msg_data = response.json()
            message_id = msg_data.get("id", "")

            # ── Save to message log ──────────────────────────────
            log = load_message_log(guild_id)
            log.insert(0, {
                "id": message_id,
                "channel_id": channel_id,
                "sent_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "label": data.get("title") or data.get("message_content") or "(no title)",
                "payload": data,          # full original form data
                "embed_snapshot": embed,  # the built embed as sent
            })
            # Keep log to last 50 entries
            save_message_log(guild_id, log[:50])

            return jsonify({"success": True, "message_id": message_id})
        else:
            try:
                error_data = response.json()
                return jsonify({"error": error_data.get("message", f"Failed to send (Discord returned {response.status_code})")}), 400
            except Exception:
                return jsonify({"error": f"Discord API returned an unexpected error ({response.status_code})"}), 400

    except Exception as e:
        return jsonify({"error": f"Backend Error: {str(e)}"}), 500


# ─── Message Log Endpoints ────────────────────────────────────────

@app.route("/api/messages", methods=["GET"])
def get_message_log():
    """Return the full sent-message log."""
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")
    return jsonify({"messages": load_message_log(guild_id)})


@app.route("/api/messages/edit", methods=["POST"])
def edit_discord_message():
    """Edit an existing Discord message in-place (no delete/re-send)."""
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")

    import datetime
    data = request.json
    message_id = str(data.get("message_id", "")).strip()
    channel_id  = extract_channel_id(data.get("channel_id", ""))
    if not message_id or not channel_id:
        return jsonify({"error": "message_id and channel_id are required"}), 400

    # Build updated embed (same logic as send)
    embed = {}
    if data.get("title"):       embed["title"] = data["title"]
    if data.get("description"): embed["description"] = data["description"]
    if data.get("color"):
        import numbers
        if isinstance(data["color"], numbers.Integral):
            embed["color"] = data["color"]
        else:
            try:    embed["color"] = int(str(data["color"]).lstrip("#"), 16)
            except: embed["color"] = 5793266
    if data.get("author_name"):
        embed["author"] = {"name": data["author_name"]}
        if data.get("author_icon"): embed["author"]["icon_url"] = data["author_icon"]
    if data.get("thumbnail"): embed["thumbnail"] = {"url": data["thumbnail"]}
    if data.get("image"):     embed["image"]     = {"url": data["image"]}
    if data.get("footer_text"):
        embed["footer"] = {"text": data["footer_text"]}
        if data.get("footer_icon"): embed["footer"]["icon_url"] = data["footer_icon"]
    fields = data.get("fields", [])
    if fields:
        embed["fields"] = [{"name": f["name"], "value": f["value"], "inline": f.get("inline", False)}
                           for f in fields if f.get("name") and f.get("value")]

    bot_token = os.getenv("DISCORD_TOKEN", "")
    payload = {"embeds": [embed]}
    if data.get("message_content"):
        payload["content"] = data["message_content"]

    try:
        response = requests.patch(
            f"{DISCORD_API}/channels/{channel_id}/messages/{message_id}",
            json=payload,
            headers={"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code == 200:
            # Update the log entry
            log = load_message_log(guild_id)
            for entry in log:
                if entry.get("id") == message_id:
                    entry["payload"] = data
                    entry["embed_snapshot"] = embed
                    entry["label"] = data.get("title") or data.get("message_content") or entry["label"]
                    entry["edited_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    break
            save_message_log(guild_id, log)
            return jsonify({"success": True})
        else:
            try:
                err = response.json()
                return jsonify({"error": err.get("message", f"Failed to edit (Discord returned {response.status_code})")}), 400
            except Exception:
                return jsonify({"error": f"Discord API returned an unexpected error ({response.status_code})"}), 400
    except Exception as e:
        return jsonify({"error": f"Backend Error: {str(e)}"}), 500


@app.route("/api/messages/delete", methods=["POST"])
def delete_log_entry():
    """Remove a message from the local log only (does NOT delete it from Discord)."""
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")
    message_id = str(request.json.get("message_id", "")).strip()
    if not message_id:
        return jsonify({"error": "message_id is required"}), 400
    log = load_message_log(guild_id)
    log = [e for e in log if e.get("id") != message_id]
    save_message_log(guild_id, log)
    return jsonify({"success": True})



# ─── Templates CRUD ────────────────────────────────────────────

@app.route("/api/templates", methods=["GET"])
def get_templates():
    if not is_authenticated(): return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")
    return jsonify({"templates": load_templates(guild_id)})


@app.route("/api/templates", methods=["POST"])
def save_template_endpoint():
    """Create or update a named template."""
    if not is_authenticated(): return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")
    import datetime
    data     = request.json
    name     = data.get("name", "").strip()
    if not name: return jsonify({"error": "Template name is required"}), 400

    payload  = data.get("payload", {})
    templates = load_templates(guild_id)
    # Update existing or append new
    for t in templates:
        if t["name"] == name:
            t["payload"]     = payload
            t["updated_at"]  = datetime.datetime.now(datetime.timezone.utc).isoformat()
            save_templates(guild_id, templates)
            return jsonify({"success": True, "action": "updated"})
    templates.insert(0, {
        "name":       name,
        "payload":    payload,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    save_templates(guild_id, templates)
    return jsonify({"success": True, "action": "created"})


@app.route("/api/templates", methods=["DELETE"])
def delete_template_endpoint():
    if not is_authenticated(): return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")
    name = (request.json or {}).get("name", "").strip()
    if not name: return jsonify({"error": "Template name is required"}), 400
    templates = load_templates(guild_id)
    templates = [t for t in templates if t["name"] != name]
    save_templates(guild_id, templates)
    return jsonify({"success": True})


@app.route("/api/templates/send", methods=["POST"])
def send_template():
    """Send a saved template to a Discord channel."""
    if not is_authenticated(): return jsonify({"error": "Unauthorized"}), 403
    guild_id = session.get("active_guild")
    import datetime
    data        = request.json
    name        = data.get("name", "").strip()
    channel_id  = extract_channel_id(data.get("channel_id", ""))
    if not name or not channel_id:
        return jsonify({"error": "name and channel_id are required"}), 400

    templates = load_templates(guild_id)
    tmpl = next((t for t in templates if t["name"] == name), None)
    if not tmpl: return jsonify({"error": "Template not found"}), 404

    p = tmpl["payload"]
    
    # If the payload is already in Discord format (has embeds array or standard content string)
    if "embeds" in p or ("content" in p and "message_content" not in p):
        payload_to_send = p
    else:
        # Fallback: converts old flat payload format to Discord format
        embed = {}
        if p.get("title"):       embed["title"]       = p["title"]
        if p.get("description"): embed["description"]  = p["description"]
        if p.get("color"):
            try:    embed["color"] = int(p["color"].lstrip("#"), 16)
            except: embed["color"] = 5793266
        if p.get("author_name"):
            embed["author"] = {"name": p["author_name"]}
            if p.get("author_icon"): embed["author"]["icon_url"] = p["author_icon"]
        if p.get("thumbnail"): embed["thumbnail"] = {"url": p["thumbnail"]}
        if p.get("image"):     embed["image"]     = {"url": p["image"]}
        if p.get("footer_text"):
            embed["footer"] = {"text": p["footer_text"]}
            if p.get("footer_icon"): embed["footer"]["icon_url"] = p["footer_icon"]
        fields = p.get("fields", [])
        if fields:
            embed["fields"] = [{"name": f["name"], "value": f["value"], "inline": f.get("inline", False)}
                               for f in fields if f.get("name") and f.get("value")]

        payload_to_send = {"embeds": [embed]}
        if p.get("message_content"): payload_to_send["content"] = p["message_content"]

    bot_token = os.getenv("DISCORD_TOKEN", "")
    try:
        resp = requests.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            json=payload_to_send,
            headers={"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"},
            timeout=10
        )
        if resp.status_code in (200, 201):
            msg_id = resp.json().get("id", "")
            log = load_message_log(guild_id)
            log.insert(0, {
                "id": msg_id, "channel_id": channel_id,
                "sent_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "label": name, "payload": p, "embed_snapshot": embed,
            })
            save_message_log(guild_id, log[:50])
            return jsonify({"success": True, "message_id": msg_id})
        else:
            try:
                err_data = resp.json()
                return jsonify({"error": err_data.get("message", f"Failed to send (Discord returned {resp.status_code})")}), 400
            except Exception:
                return jsonify({"error": f"Discord API returned an unexpected error ({resp.status_code})"}), 400
    except Exception as e:
        return jsonify({"error": f"Backend Error: {str(e)}"}), 500


# ─── Run (used when started from bot.py in a thread) ───────────────

def run_dashboard():
    """Start the Flask dashboard server."""
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
