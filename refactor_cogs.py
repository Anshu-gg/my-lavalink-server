import os
import re

cogs_dir = os.path.join("cogs")

# 1. Simple replacements for self.bot.load_config() -> (ctx.guild.id)
for filename in os.listdir(cogs_dir):
    if not filename.endswith(".py"): continue
    
    filepath = os.path.join(cogs_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
        
    original_text = text
    
    # Replace normal self.bot.load_config calls
    text = re.sub(r"self\.bot\.load_config\(\)", r"self.bot.load_config(ctx.guild.id)", text)
    text = re.sub(r"self\.bot\.save_config\(([^),]+)\)", r"self.bot.save_config(ctx.guild.id, \1)", text)

    # Freegift.py specifics
    if filename == "freegift.py":
        new_header = """
def get_guild_file(guild_id, filename):
    base_dir = os.path.dirname(os.path.dirname(__file__))
    folder = os.path.join(base_dir, "data", str(guild_id))
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, filename)

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
"""
        # Replace the top declarations
        text = re.sub(r"(?s)CLAIMS_FILE = .*?def save_giveaways\(data\):\n.*?json\.dump\(data, f, indent=2\)\n+", new_header + "\n", text)
        
        # Replace calls
        text = re.sub(r"load_giveaways\(\)", r"load_giveaways(ctx.guild.id)", text)
        text = re.sub(r"load_claims\(\)", r"load_claims(ctx.guild.id)", text)
        text = re.sub(r"save_giveaways\(([^)]+)\)", r"save_giveaways(ctx.guild.id, \1)", text)
        text = re.sub(r"save_claims\(([^)]+)\)", r"save_claims(ctx.guild.id, \1)", text)
        
    # Feedbackgift.py specifics
    elif filename == "feedbackgift.py":
        # Delete _load_config and rewrite _load_claims, _save_claims
        new_methods = """
    def get_guild_file(self, guild_id, filename):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        folder = os.path.join(base_dir, "data", str(guild_id))
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, filename)

    def _load_claims(self, guild_id):
        path = self.get_guild_file(guild_id, "feedback_claims.json")
        if not os.path.exists(path): return {}
        with open(path, "r", encoding="utf-8") as f: return json.load(f)

    def _save_claims(self, guild_id, data):
        with open(self.get_guild_file(guild_id, "feedback_claims.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
"""
        # Replace the class methods definitions
        text = re.sub(r"(?s)    def _load_config\(self\):.*?    def _save_claims\(self, data\):\n.*?json\.dump\(data, f, indent=2\)", new_methods, text)
        text = re.sub(r"self\._load_config\(\)", r"self.bot.load_config(ctx.guild.id)", text)
        text = re.sub(r"self\._load_claims\(\)", r"self._load_claims(ctx.guild.id)", text)
        text = re.sub(r"self\._save_claims\(([^)]+)\)", r"self._save_claims(ctx.guild.id, \1)", text)

    # Customcmds.py specifics
    elif filename == "customcmds.py":
        # Remove _load_config
        text = re.sub(r"(?s)    def _load_config\(self\):.*?(?=    @commands\.command)", "", text)
        text = re.sub(r"self\._load_config\(\)", r"self.bot.load_config(ctx.guild.id)", text)
        # Note: customcmds uses message.guild.id in on_message
        text = re.sub(r"self\.bot\.load_config\(message\.guild\.id\)", r"self.bot.load_config(message.guild.id if message.guild else None)", text)

    if text != original_text:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Refactored {filename}")
