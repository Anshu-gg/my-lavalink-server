import re

with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add Tabs to Panel Claims Header
claims_header = '''<div class="panel-header">
                <h1>📜 Giveaway History</h1>
                <p>View past and active giveaways and see exactly who claimed them</p>
            </div>'''
            
tabs_html = claims_header + '''
            <div style="margin-bottom: 20px; display: flex; gap: 10px;">
                <button id="tab-giveaway" onclick="switchClaimTab('giveaway')" class="btn-primary">Giveaways</button>
                <button id="tab-feedback" onclick="switchClaimTab('feedback')" class="btn-secondary">Response Giveaways</button>
            </div>'''

if 'id="tab-giveaway"' not in html:
    html = html.replace(claims_header, tabs_html)

# Add "Response" header to Claims Table
claims_thead = '''<th style="padding: 12px; color: var(--text-muted);">Avatar</th>
                                <th style="padding: 12px; color: var(--text-muted);">Username</th>
                                <th style="padding: 12px; color: var(--text-muted);">User ID</th>
                                <th style="padding: 12px; color: var(--text-muted);">Claimed At</th>'''

claims_thead_new = '''<th style="padding: 12px; color: var(--text-muted); width: 60px;">Avatar</th>
                                <th style="padding: 12px; color: var(--text-muted);">Username</th>
                                <th style="padding: 12px; color: var(--text-muted);">User ID</th>
                                <th style="padding: 12px; color: var(--text-muted);">Claimed At</th>
                                <th id="th-response" style="padding: 12px; color: var(--text-muted); display: none;">Response</th>'''

if 'id="th-response"' not in html:
    # Need to replace the exact block. We'll use regex.
    html = re.sub(r'<th style="padding: 12px; color: var\(--text-muted\); width: 60px;">Avatar</th>\s*<th style="padding: 12px; color: var\(--text-muted\);">Username</th>\s*<th style="padding: 12px; color: var\(--text-muted\);">User ID</th>\s*<th style="padding: 12px; color: var\(--text-muted\);">Claimed At</th>',
                  claims_thead_new, html)


# Update JavaScript block
js_to_replace = '''        // ─── Auto-update Claim Count and List ──────────────────
        let currentViewingEventId = null;
        let lastHistoryData = {};
        let activeEventId = null;

        function showEventsList() {
            currentViewingEventId = null;
            document.getElementById('view-events-list').style.display = 'block';
            document.getElementById('view-event-claims').style.display = 'none';
            document.getElementById('btn-back-events').style.display = 'none';
            document.getElementById('claims-view-title').textContent = 'All Events';
            renderEventsTable();
        }

        function showEventClaims(eventId) {
            currentViewingEventId = eventId;
            document.getElementById('view-events-list').style.display = 'none';
            document.getElementById('view-event-claims').style.display = 'block';
            document.getElementById('btn-back-events').style.display = 'inline-block';

            const event = lastHistoryData[eventId];
            if (event) {
                const title = event.title || 'Legacy Gift';
                let count = Object.keys(event.claims || {}).length;
                if (event.past_resets) {
                    event.past_resets.forEach(r => { count += Object.keys(r.claims || {}).length; });
                }
                document.getElementById('claims-view-title').innerHTML = `Claims for <strong>${title}</strong> <span class="claim-badge">${count} claimed</span>`;
                renderClaimsTable(event);
            }
        }

        function renderEventsTable() {
            const tbody = document.getElementById('events-table-body');
            if (!tbody) return;
            const entries = Object.entries(lastHistoryData).sort((a, b) => {
                return new Date(b[1].created_at || 0) - new Date(a[1].created_at || 0);
            });

            if (entries.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="padding: 12px; text-align: center; color: #888;">No giveaways found.</td></tr>';
                return;
            }

            let rows = '';
            for (const [id, data] of entries) {
                let count = Object.keys(data.claims || {}).length;
                if (data.past_resets) {
                    data.past_resets.forEach(r => { count += Object.keys(r.claims || {}).length; });
                }
                const d = new Date(data.created_at);
                const dateStr = isNaN(d) ? 'Unknown Date' : d.toLocaleString();
                const isActive = (id === activeEventId);
                const statusBadge = isActive ? '<span style="color:#57F287; font-weight:bold;">🟢 Active</span>' : '<span style="color:#888;">⚪ Ended</span>';

                rows += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); cursor: pointer;" onclick="showEventClaims('${id}')" class="event-row-hover">
                        <td style="padding: 12px;">${statusBadge}</td>
                        <td style="padding: 12px; color: white;"><strong>${data.title || 'Gift'}</strong></td>
                        <td style="padding: 12px; color: #aaa; font-size: 0.9em;">${dateStr}</td>
                        <td style="padding: 12px;"><span class="claim-badge">${count}</span></td>
                        <td style="padding: 12px; text-align:right;"><button class="btn-secondary btn-sm">View Claims</button></td>
                    </tr>
                `;
            }
            tbody.innerHTML = rows;
        }

        function buildClaimRows(claims) {
            let rows = '';
            for (const [userId, data] of Object.entries(claims)) {
                const d = new Date(data.claimed_at);
                const dateStr = isNaN(d) ? 'Unknown Date' : d.toLocaleString();
                const avatarUrl = data.avatar ? proxyUrl(data.avatar) : 'https://cdn.discordapp.com/embed/avatars/0.png';

                rows += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 12px;"><img src="${avatarUrl}" style="width:32px; height:32px; border-radius:50%; object-fit:cover;"></td>
                        <td style="padding: 12px; color: white;"><strong>${data.username}</strong></td>
                        <td style="padding: 12px; font-family: monospace; color: #aaa;">${userId}</td>
                        <td style="padding: 12px; color: #888; font-size: 0.9em;">${dateStr}</td>
                    </tr>
                `;
            }
            return rows;
        }

        function renderClaimsTable(eventData) {
            const tbody = document.getElementById('claims-table-body');
            if (!tbody) return;

            let rows = '';
            const currentClaims = eventData.claims || {};

            // Current Claims
            if (Object.keys(currentClaims).length > 0) {
                if (eventData.past_resets && eventData.past_resets.length > 0) {
                    rows += '<tr><td colspan="4" style="padding: 8px 12px; background: rgba(88, 101, 242, 0.1); color: var(--text-color); font-weight: bold; border-bottom: 1px solid var(--border-color); font-size: 0.9em;">Current Claims (After Reset)</td></tr>';
                }
                rows += buildClaimRows(currentClaims);
            }

            // Past Resets
            if (eventData.past_resets && eventData.past_resets.length > 0) {
                // Show most recent reset first
                for (let i = eventData.past_resets.length - 1; i >= 0; i--) {
                    const resetGroup = eventData.past_resets[i];
                    if (Object.keys(resetGroup.claims).length > 0) {
                        const rDate = new Date(resetGroup.reset_at).toLocaleString();
                        rows += `<tr><td colspan="4" style="padding: 8px 12px; background: rgba(255, 60, 60, 0.1); color: #ff8888; font-weight: bold; border-top: 2px solid rgba(255,60,60,0.5); border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9em;">Archived Claims (Before Reset on ${rDate})</td></tr>`;
                        rows += buildClaimRows(resetGroup.claims);
                    }
                }
            }

            if (rows === '') {
                tbody.innerHTML = '<tr><td colspan="4" style="padding: 12px; text-align: center; color: #888;">No one has claimed this yet.</td></tr>';
            } else {
                tbody.innerHTML = rows;
            }
        }

        async function refreshClaimsList() {
            try {
                const res = await fetch('/api/giveaway');
                if (res.ok) {
                    const result = await res.json();

                    if (result.claims_count !== undefined) {
                        const badges = document.querySelectorAll('.claim-badge');
                        badges.forEach(badge => {
                            // Don't overwrite the drilldown badge
                            if (badge.closest('#claims-view-title') === null) {
                                badge.textContent = result.claims_count + ' claimed';
                            }
                        });
                    }

                    if (result.history) {
                        lastHistoryData = result.history;
                        // Figure out which is active
                        activeEventId = null;
                        if (result.giveaway && result.giveaway.active) {
                            activeEventId = result.giveaway.event_id;
                        }

                        // Re-render whatever view we are currently on
                        if (currentViewingEventId) {
                            showEventClaims(currentViewingEventId);
                        } else {
                            renderEventsTable();
                        }
                    }
                }
            } catch (err) { console.error(err); }
        }

        setInterval(refreshClaimsList, 5000);'''

new_js = '''        // ─── Auto-update Claim Count and List ──────────────────
        let currentViewingEventId = null;
        let lastHistoryData = {};
        let activeEventId = null;
        let currentClaimsTab = 'giveaway'; // 'giveaway' or 'feedback'
        
        function switchClaimTab(tab) {
            currentClaimsTab = tab;
            document.getElementById('tab-giveaway').className = tab === 'giveaway' ? 'btn-primary' : 'btn-secondary';
            document.getElementById('tab-feedback').className = tab === 'feedback' ? 'btn-primary' : 'btn-secondary';
            
            if (tab === 'feedback') {
                document.getElementById('th-response').style.display = 'table-cell';
            } else {
                document.getElementById('th-response').style.display = 'none';
            }
            
            showEventsList();
            refreshClaimsList();
        }

        function showEventsList() {
            currentViewingEventId = null;
            document.getElementById('view-events-list').style.display = 'block';
            document.getElementById('view-event-claims').style.display = 'none';
            document.getElementById('btn-back-events').style.display = 'none';
            document.getElementById('claims-view-title').textContent = currentClaimsTab === 'giveaway' ? 'Giveaway Events' : 'Response Giveaways';
            renderEventsTable();
        }

        function showEventClaims(eventId) {
            currentViewingEventId = eventId;
            document.getElementById('view-events-list').style.display = 'none';
            document.getElementById('view-event-claims').style.display = 'block';
            document.getElementById('btn-back-events').style.display = 'inline-block';

            const event = lastHistoryData[eventId];
            if (event) {
                const title = event.title || 'Legacy Gift';
                let count = Object.keys(event.claims || {}).length;
                if (event.past_resets) {
                    event.past_resets.forEach(r => { count += Object.keys(r.claims || {}).length; });
                }
                document.getElementById('claims-view-title').innerHTML = `Claims for <strong>${title}</strong> <span class="claim-badge">${count} claimed</span>`;
                renderClaimsTable(event);
            }
        }

        function renderEventsTable() {
            const tbody = document.getElementById('events-table-body');
            if (!tbody) return;
            const entries = Object.entries(lastHistoryData).sort((a, b) => {
                return new Date(b[1].created_at || 0) - new Date(a[1].created_at || 0);
            });

            if (entries.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="padding: 12px; text-align: center; color: #888;">No events found.</td></tr>';
                return;
            }

            let rows = '';
            for (const [id, data] of entries) {
                let count = Object.keys(data.claims || {}).length;
                if (data.past_resets) {
                    data.past_resets.forEach(r => { count += Object.keys(r.claims || {}).length; });
                }
                const d = new Date(data.created_at);
                const dateStr = isNaN(d) ? 'Unknown Date' : d.toLocaleString();
                const isActive = (id === activeEventId);
                const statusBadge = isActive ? '<span style="color:#57F287; font-weight:bold;">🟢 Active</span>' : '<span style="color:#888;">⚪ Ended</span>';

                rows += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); cursor: pointer;" onclick="showEventClaims('${id}')" class="event-row-hover">
                        <td style="padding: 12px;">${statusBadge}</td>
                        <td style="padding: 12px; color: white;"><strong>${data.title || 'Gift'}</strong></td>
                        <td style="padding: 12px; color: #aaa; font-size: 0.9em;">${dateStr}</td>
                        <td style="padding: 12px;"><span class="claim-badge">${count}</span></td>
                        <td style="padding: 12px; text-align:right;"><button class="btn-secondary btn-sm">View Claims</button></td>
                    </tr>
                `;
            }
            tbody.innerHTML = rows;
        }

        function buildClaimRows(claims) {
            let rows = '';
            const colspan = currentClaimsTab === 'feedback' ? 5 : 4;
            
            for (const [userId, data] of Object.entries(claims)) {
                const d = new Date(data.claimed_at);
                const dateStr = isNaN(d) ? 'Unknown Date' : d.toLocaleString();
                const avatarUrl = data.avatar ? proxyUrl(data.avatar) : 'https://cdn.discordapp.com/embed/avatars/0.png';

                let responseTd = '';
                if (currentClaimsTab === 'feedback') {
                    const responseText = data.response ? data.response : '<i style="color:#888">No response yet</i>';
                    responseTd = `<td style="padding: 12px; color: #e1e1e1;">${responseText}</td>`;
                }

                rows += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 12px;"><img src="${avatarUrl}" style="width:32px; height:32px; border-radius:50%; object-fit:cover;"></td>
                        <td style="padding: 12px; color: white;"><strong>${data.username}</strong></td>
                        <td style="padding: 12px; font-family: monospace; color: #aaa;">${userId}</td>
                        <td style="padding: 12px; color: #888; font-size: 0.9em;">${dateStr}</td>
                        ${responseTd}
                    </tr>
                `;
            }
            return rows;
        }

        function renderClaimsTable(eventData) {
            const tbody = document.getElementById('claims-table-body');
            if (!tbody) return;

            const colspan = currentClaimsTab === 'feedback' ? 5 : 4;
            let rows = '';
            const currentClaims = eventData.claims || {};

            // Current Claims
            if (Object.keys(currentClaims).length > 0) {
                if (eventData.past_resets && eventData.past_resets.length > 0) {
                    rows += `<tr><td colspan="${colspan}" style="padding: 8px 12px; background: rgba(88, 101, 242, 0.1); color: var(--text-color); font-weight: bold; border-bottom: 1px solid var(--border-color); font-size: 0.9em;">Current Claims (After Reset)</td></tr>`;
                }
                rows += buildClaimRows(currentClaims);
            }

            // Past Resets
            if (eventData.past_resets && eventData.past_resets.length > 0) {
                // Show most recent reset first
                for (let i = eventData.past_resets.length - 1; i >= 0; i--) {
                    const resetGroup = eventData.past_resets[i];
                    if (Object.keys(resetGroup.claims).length > 0) {
                        const rDate = new Date(resetGroup.reset_at).toLocaleString();
                        rows += `<tr><td colspan="${colspan}" style="padding: 8px 12px; background: rgba(255, 60, 60, 0.1); color: #ff8888; font-weight: bold; border-top: 2px solid rgba(255,60,60,0.5); border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9em;">Archived Claims (Before Reset on ${rDate})</td></tr>`;
                        rows += buildClaimRows(resetGroup.claims);
                    }
                }
            }

            if (rows === '') {
                tbody.innerHTML = `<tr><td colspan="${colspan}" style="padding: 12px; text-align: center; color: #888;">No one has claimed this yet.</td></tr>`;
            } else {
                tbody.innerHTML = rows;
            }
        }

        async function refreshClaimsList() {
            try {
                const endpoint = currentClaimsTab === 'giveaway' ? '/api/giveaway' : '/api/feedback';
                const res = await fetch(endpoint);
                if (res.ok) {
                    const result = await res.json();

                    if (result.claims_count !== undefined) {
                        const badges = document.querySelectorAll('.claim-badge');
                        badges.forEach(badge => {
                            // Don't overwrite the drilldown badge
                            if (badge.closest('#claims-view-title') === null) {
                                // Find the relevant status div based on current tab
                                const parentId = currentClaimsTab === 'giveaway' ? 'giveaway-status' : 'feedback-status';
                                if (badge.closest(`#${parentId}`)) {
                                    badge.textContent = result.claims_count + ' claimed';
                                }
                            }
                        });
                    }

                    if (result.history) {
                        lastHistoryData = result.history;
                        // Figure out which is active
                        activeEventId = null;
                        if (result.giveaway && result.giveaway.active) {
                            activeEventId = result.giveaway.event_id;
                        }

                        // Re-render whatever view we are currently on
                        if (currentViewingEventId) {
                            showEventClaims(currentViewingEventId);
                        } else {
                            renderEventsTable();
                        }
                    }
                }
            } catch (err) { console.error(err); }
        }

        setInterval(refreshClaimsList, 5000);'''

if "currentClaimsTab =" not in html:
    html = html.replace(js_to_replace, new_js)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)
