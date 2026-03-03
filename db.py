"""
db.py — Centralized MongoDB storage layer.
Replaces all JSON file I/O with MongoDB Atlas operations.
Every load/save function has the same signature as the old JSON helpers
so the rest of the codebase needs minimal changes.
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# ─── Connection ───────────────────────────────────────────────────

_client = None
_db = None


def get_db():
    """Return the MongoDB database instance, connecting lazily on first call."""
    global _client, _db
    if _db is not None:
        return _db

    uri = os.getenv("MONGODB_URI", "")
    if not uri:
        raise RuntimeError(
            "MONGODB_URI environment variable is not set. "
            "Add it to your .env file or Render environment variables."
        )

    _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    # Force a connection test on first call
    _client.admin.command("ping")
    _db = _client["discord_bot"]
    print("✅ Connected to MongoDB Atlas")
    return _db


# ─── Internal helpers ─────────────────────────────────────────────

def _load_guild_doc(collection_name, guild_id, default=None):
    """Load a guild-scoped document. Returns `default` if not found."""
    if default is None:
        default = {}
    db = get_db()
    doc = db[collection_name].find_one({"guild_id": str(guild_id)})
    if doc is None:
        return default
    doc.pop("_id", None)
    doc.pop("guild_id", None)
    return doc.get("data", default)


def _save_guild_doc(collection_name, guild_id, data):
    """Save a guild-scoped document (upsert)."""
    db = get_db()
    db[collection_name].update_one(
        {"guild_id": str(guild_id)},
        {"$set": {"guild_id": str(guild_id), "data": data}},
        upsert=True,
    )


def _load_global_doc(collection_name, default=None):
    """Load a global (non-guild) document."""
    if default is None:
        default = {}
    db = get_db()
    doc = db[collection_name].find_one({"_id": "main"})
    if doc is None:
        return default
    doc.pop("_id", None)
    return doc.get("data", default)


def _save_global_doc(collection_name, data):
    """Save a global (non-guild) document (upsert)."""
    db = get_db()
    db[collection_name].update_one(
        {"_id": "main"},
        {"$set": {"_id": "main", "data": data}},
        upsert=True,
    )


# ═══════════════════════════════════════════════════════════════════
#  GUILD-SCOPED DATA
# ═══════════════════════════════════════════════════════════════════

# ─── Config ───────────────────────────────────────────────────────

def load_config(guild_id=None):
    """Read guild config. Returns empty dict if no guild_id or not found."""
    if not guild_id:
        return {}
    return _load_guild_doc("configs", guild_id, {})


def save_config(guild_id, data):
    """Write updated guild config."""
    if not guild_id:
        return
    _save_guild_doc("configs", guild_id, data)


# ─── Claims ──────────────────────────────────────────────────────

def load_claims(guild_id):
    return _load_guild_doc("claims", guild_id, {})


def save_claims(guild_id, data):
    _save_guild_doc("claims", guild_id, data)


# ─── Giveaways ───────────────────────────────────────────────────

def load_giveaways(guild_id):
    return _load_guild_doc("giveaways", guild_id, {})


def save_giveaways(guild_id, data):
    _save_guild_doc("giveaways", guild_id, data)


# ─── Feedback Claims ─────────────────────────────────────────────

def load_feedback_claims(guild_id):
    return _load_guild_doc("feedback_claims", guild_id, {})


def save_feedback_claims(guild_id, data):
    _save_guild_doc("feedback_claims", guild_id, data)


# ─── Feedback Events ─────────────────────────────────────────────

def load_feedback_events(guild_id):
    return _load_guild_doc("feedback_events", guild_id, {})


def save_feedback_events(guild_id, data):
    _save_guild_doc("feedback_events", guild_id, data)


# ─── Message Log ─────────────────────────────────────────────────

def load_message_log(guild_id):
    return _load_guild_doc("message_logs", guild_id, [])


def save_message_log(guild_id, data):
    _save_guild_doc("message_logs", guild_id, data)


# ─── Templates ───────────────────────────────────────────────────

def load_templates(guild_id):
    return _load_guild_doc("templates", guild_id, [])


def save_templates(guild_id, data):
    _save_guild_doc("templates", guild_id, data)


# ═══════════════════════════════════════════════════════════════════
#  GLOBAL DATA
# ═══════════════════════════════════════════════════════════════════

# ─── Admin Accounts ──────────────────────────────────────────────

def load_admin_accounts():
    return _load_global_doc("admin_accounts", {})


def save_admin_accounts(data):
    _save_global_doc("admin_accounts", data)


# ─── Audit Logs ──────────────────────────────────────────────────

def load_audit_logs():
    return _load_global_doc("audit_logs", [])


def save_audit_logs(data):
    _save_global_doc("audit_logs", data)


# ─── Owner ───────────────────────────────────────────────────────

def load_owner():
    return _load_global_doc("owner", {})


def save_owner(data):
    _save_global_doc("owner", data)


# ─── Server Logins ───────────────────────────────────────────────

def load_server_logins():
    return _load_global_doc("server_logins", {})


def save_server_logins(data):
    _save_global_doc("server_logins", data)
