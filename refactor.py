import re

with open("dashboard.py", "r", encoding="utf-8") as f:
    text = f.read()

auth_def = """def is_authenticated():
    \"\"\"Check if the logged-in user has selected an active server.\"\"\"
    return bool(session.get("user") and session.get("active_guild"))"""

text = text.replace("# ─── Routes ───────────────────────────────────────────────────────", auth_def + "\n\n# ─── Routes ───────────────────────────────────────────────────────")

# Replace the authentication check in each route
text = text.replace("if not is_owner():", "if not is_authenticated():")
text = text.replace("return jsonify({\"error\": \"Unauthorized\"}), 403", "return jsonify({\"error\": \"Unauthorized\"}), 403\n    guild_id = session.get(\"active_guild\")")

# Replace no-arg calls with guild_id
text = re.sub(r"load_config\(\)", "load_config(guild_id)", text)
text = re.sub(r"load_claims\(\)", "load_claims(guild_id)", text)
text = re.sub(r"load_giveaways\(\)", "load_giveaways(guild_id)", text)
text = re.sub(r"load_feedback_claims\(\)", "load_feedback_claims(guild_id)", text)
text = re.sub(r"load_feedback_events\(\)", "load_feedback_events(guild_id)", text)
text = re.sub(r"load_message_log\(\)", "load_message_log(guild_id)", text)
text = re.sub(r"load_templates\(\)", "load_templates(guild_id)", text)

# For saves, it's save_config(cfg) -> save_config(guild_id, cfg)
text = re.sub(r"save_config\(([^)]+)\)", r"save_config(guild_id, \1)", text)
text = re.sub(r"save_claims\(([^)]+)\)", r"save_claims(guild_id, \1)", text)
text = re.sub(r"save_giveaways\(([^)]+)\)", r"save_giveaways(guild_id, \1)", text)
text = re.sub(r"save_feedback_claims\(([^)]+)\)", r"save_feedback_claims(guild_id, \1)", text)
text = re.sub(r"save_feedback_events\(([^)]+)\)", r"save_feedback_events(guild_id, \1)", text)
text = re.sub(r"save_message_log\(([^)]+)\)", r"save_message_log(guild_id, \1)", text)
text = re.sub(r"save_templates\(([^)]+)\)", r"save_templates(guild_id, \1)", text)

text = text.replace("cfg = load_config()\n    claims = load_claims()", "cfg = load_config(active_guild)\n    claims = load_claims(active_guild)")

with open("dashboard.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Refactor complete.")
