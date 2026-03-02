import re

with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add nav item
nav_item = """<a href="#" class="nav-item" data-panel="giveaway">
                <span class="nav-icon">🎁</span> Giveaway
            </a>"""
new_nav = nav_item + """\n            <a href="#" class="nav-item" data-panel="feedback">
                <span class="nav-icon">💬</span> Feedback Gift
            </a>"""

if "data-panel=\"feedback\"" not in html:
    html = html.replace(nav_item, new_nav)

# Extract giveaway panel
panel_match = re.search(r'(<!-- ─── Giveaway Panel ──────────────────────────────── -->.*?)</section>', html, re.DOTALL)
if panel_match and "id=\"panel-feedback\"" not in html:
    giveaway_panel = panel_match.group(1) + '</section>'
    
    # Modify it for feedback
    feedback_panel = giveaway_panel.replace('Giveaway Manager', 'Feedback Reward Manager')
    feedback_panel = feedback_panel.replace('Giveaway Panel', 'Feedback Panel')
    feedback_panel = feedback_panel.replace('id="panel-giveaway"', 'id="panel-feedback"')
    feedback_panel = feedback_panel.replace('<code>!free</code>', '<code>!reward</code>')
    feedback_panel = feedback_panel.replace('config.free_gift.title', 'config.feedback_gift.title')
    feedback_panel = feedback_panel.replace('config.get(\'free_gift\'', 'config.get(\'feedback_gift\'')
    feedback_panel = feedback_panel.replace('config.free_gift', 'config.feedback_gift')
    feedback_panel = feedback_panel.replace('stopGiveaway()', 'stopFeedback()')
    feedback_panel = feedback_panel.replace('id="giveaway-status"', 'id="feedback-status"')
    feedback_panel = feedback_panel.replace('Active Giveaway:', 'Active Feedback Event:')
    feedback_panel = feedback_panel.replace('No active giveaway', 'No active feedback event')
    
    # Replace the ID prefixes for inputs
    feedback_panel = feedback_panel.replace('id="gift_', 'id="fb_')
    feedback_panel = feedback_panel.replace('for="gift_', 'for="fb_')
    feedback_panel = feedback_panel.replace('id="gift-', 'id="fb-')
    
    # Provide the logging inputs
    log_inputs = """
                    <div class="card">
                        <h3>🔗 Logging Setup</h3>
                        <div class="form-group">
                            <label for="fb_log_channel">Log Channel ID</label>
                            <input type="text" id="fb_log_channel" placeholder="Where to send user responses" value="{{ config.get('feedback_gift', {}).get('log_channel_id', '') }}">
                        </div>
                        <div class="form-group">
                            <label for="fb_admin_id">Admin User ID</label>
                            <input type="text" id="fb_admin_id" placeholder="Who to ping when they respond" value="{{ config.get('feedback_gift', {}).get('admin_id', '') }}">
                        </div>
                    </div>
    """
    feedback_panel = feedback_panel.replace('<!-- Color -->', log_inputs + '\n                    <!-- Color -->')
    
    # Replace JS calls
    feedback_panel = feedback_panel.replace('updateGiftPreview()', 'updateFbPreview()')
    feedback_panel = feedback_panel.replace('setGiftColor(', 'setFbColor(')
    feedback_panel = feedback_panel.replace('addGiftField()', 'addFbField()')
    feedback_panel = feedback_panel.replace('createGiveaway()', 'createFeedback()')
    feedback_panel = feedback_panel.replace('resetClaims()', 'resetFbClaims()')
    feedback_panel = feedback_panel.replace('clearGiveawayEmbed()', 'clearFbEmbed()')
    feedback_panel = feedback_panel.replace('Launch Giveaway', 'Launch Feedback Reward')
    
    # Insert before claims
    claims_marker = '<!-- ─── Claims Log Panel ────────────────────────────── -->'
    if claims_marker in html:
        html = html.replace(claims_marker, feedback_panel + '\n\n        ' + claims_marker)

# Copy the JS for giveaway out
js_match = re.search(r'(// ─── Giveaway ────────────────────────────────────────.*?)(?=// ═══════════════════════════════════════════════════════)', html, re.DOTALL)
if js_match and 'function setFbColor' not in html:
    giveaway_js = js_match.group(1)
    
    fb_js = giveaway_js.replace('Giveaway', 'Feedback System')
    fb_js = fb_js.replace('giftFields', 'fbFields')
    fb_js = fb_js.replace('setGiftColor', 'setFbColor')
    fb_js = fb_js.replace('gift_color', 'fb_color')
    fb_js = fb_js.replace('gift-color-label', 'fb-color-label')
    fb_js = fb_js.replace('updateGiftPreview', 'updateFbPreview')
    fb_js = fb_js.replace('addGiftField', 'addFbField')
    fb_js = fb_js.replace('removeGiftField', 'removeFbField')
    fb_js = fb_js.replace('renderGiftFields', 'renderFbFields')
    fb_js = fb_js.replace('updateGiftFieldData', 'updateFbFieldData')
    fb_js = fb_js.replace('gift-fields-container', 'fb-fields-container')
    fb_js = fb_js.replace('gift_title', 'fb_title')
    fb_js = fb_js.replace('gift_description', 'fb_description')
    fb_js = fb_js.replace('gift_link', 'fb_link')
    fb_js = fb_js.replace('gift_message', 'fb_message')
    fb_js = fb_js.replace('gift_color', 'fb_color')
    fb_js = fb_js.replace('gift_author_name', 'fb_author_name')
    fb_js = fb_js.replace('gift_author_icon', 'fb_author_icon')
    fb_js = fb_js.replace('gift_thumbnail', 'fb_thumbnail')
    fb_js = fb_js.replace('gift_image', 'fb_image')
    fb_js = fb_js.replace('gift_footer_text', 'fb_footer_text')
    fb_js = fb_js.replace('gift_footer_icon', 'fb_footer_icon')
    fb_js = fb_js.replace('gift-preview', 'fb-preview')
    fb_js = fb_js.replace('createGiveaway', 'createFeedback')
    fb_js = fb_js.replace('stopGiveaway', 'stopFeedback')
    fb_js = fb_js.replace('resetClaims', 'resetFbClaims')
    fb_js = fb_js.replace('clearGiveawayEmbed', 'clearFbEmbed')
    fb_js = fb_js.replace('/api/giveaway', '/api/feedback')
    fb_js = fb_js.replace('Launched!', 'Feedback Reward Launched!')
    fb_js = fb_js.replace('Stop Giveaway?', 'Stop Feedback Reward?')
    
    # Inject extra fields mapping
    extra_data = '''data.log_channel_id = document.getElementById('fb_log_channel').value;
                data.admin_id = document.getElementById('fb_admin_id').value;'''
    fb_js = fb_js.replace('fields: fbFields.filter(f => f.name && f.value),',
                          'fields: fbFields.filter(f => f.name && f.value),\n                log_channel_id: document.getElementById(\'fb_log_channel\').value,\n                admin_id: document.getElementById(\'fb_admin_id\').value,')

    # Add fb JS right after giveaway JS
    html = html.replace(giveaway_js, giveaway_js + '\n        ' + fb_js)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)
