const API_URL = "http://localhost:8000/chat";
let sessionId = null;

const AMBIGUITIES = {
    "A01_LESSEE_FARMER": "PM-KISAN rules for lessee farmers are state-dependent and formally ambiguous at center.",
    "A04_SECC_STALENESS": "SECC 2011 data is outdated; families who became poor after 2011 may be missed.",
    "A10_WIDOW_REMARRIAGE_STATUS": "Remarriage status is often not updated in government records, leading to irregular benefits.",
    "A12_AADHAAR_NO_BANK": "User has Aadhaar but no linked bank account, blocking DBT payments."
};

function addMessage(text, sender) {
    const scroll = document.getElementById('chat-scroll');
    const msg = document.createElement('div');
    msg.className = `message message-${sender}`;
    msg.innerText = text;
    scroll.appendChild(msg);
    scroll.scrollTop = scroll.scrollHeight;
}

function renderProfile(profileDict, completionPct, ambiguities) {
    const container = document.getElementById('profile-data');
    container.innerHTML = '';
    
    // Convert flat dict ignoring _confidence keys
    for (const [key, val] of Object.entries(profileDict)) {
        if (!key.endsWith("_confidence") && key !== "session_id" && key !== "channel" && key !== "language_preference") {
            if (key === "created_at" || key === "last_updated_at" || key === "turn_count" || key === "contradiction_log") continue;

            const displayKey = key.replace(/_/g, ' ').replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
            
            const row = document.createElement('div');
            row.className = 'data-row';
            row.innerHTML = `
                <div class="data-key">${displayKey}</div>
                <div class="data-value ${val === null ? 'none' : ''}">${val === null ? 'not defined' : val}</div>
            `;
            container.appendChild(row);
        }
    }

    const panel = document.getElementById('ambiguity-panel');
    const list = document.getElementById('ambiguity-list');
    
    if (ambiguities && ambiguities.length > 0) {
        panel.style.display = 'block';
        list.innerHTML = ambiguities.map(id => `<div class="ambiguity-item"><strong>${id}</strong>: ${AMBIGUITIES[id]}</div>`).join('');
    } else {
        panel.style.display = 'none';
        list.innerHTML = '';
    }
}

function getStatusColor(status) {
    switch(status) {
        case 'QUALIFIED': return '#10b981';
        case 'LIKELY_QUALIFIED': return '#10b981';
        case 'INELIGIBLE': return '#ef4444';
        case 'AMBIGUOUS': return '#8b5cf6';
        case 'BLOCKED': return '#f59e0b';
        case 'REQUIRES_VERIFICATION': return '#3b82f6';
        default: return '#9ca3af';
    }
}

function showAudit(scheme) {
    const modal = document.getElementById('modal-overlay');
    const body = document.getElementById('modal-body');
    
    let failsHtml = scheme.failed_hard_conditions.map(f => `<li>${f} (Failed hard condition)</li>`).join('');
    failsHtml += scheme.triggered_exclusions.map(e => `<li>${e} (Exclusion triggered)</li>`).join('');
    
    body.innerHTML = `
        <div class="modal-title">
            <div class="logo-icon">${scheme.scheme_id.charAt(1)}</div>
            ${scheme.scheme_name} Detail
        </div>
        <div class="modal-section">
            <div class="modal-label">Ministry</div>
            <div class="modal-text">Central Government Scheme</div>
        </div>
        <div class="modal-section">
            <div class="modal-label">Status</div>
            <div class="modal-text" style="color:${getStatusColor(scheme.status)}; font-weight:700">${scheme.status.toUpperCase()}</div>
        </div>
        ${failsHtml ? `
        <div class="modal-section">
            <div class="modal-label">Disqualification Reasons</div>
            <ul style="color:#ef4444; font-size:0.9rem; padding-left:1rem">
                ${failsHtml}
            </ul>
        </div>
        ` : ''}
        <div class="modal-section">
            <div class="modal-label">Details</div>
            <div class="audit-step audit-pass">
                <div>${scheme.explanation}</div>
            </div>
            ${scheme.next_action ? `
            <div class="audit-step audit-pass">
                <div style="font-weight:700; font-size: 0.7rem; opacity:0.6">NEXT ACTION</div>
                <div>${scheme.next_action}</div>
            </div>` : ''}
        </div>
        <button onclick="document.getElementById('modal-overlay').style.display='none'" style="width:100%; padding:0.75rem; border-radius:0.75rem; background:#f1f5f9; border:1px solid var(--border); color:var(--text-primary); font-weight:600; cursor:pointer">Close Audit</button>
    `;

    modal.style.display = 'flex';
}

function renderSchemes(schemes) {
    const grid = document.getElementById('schemes-grid');
    grid.innerHTML = '';

    schemes.forEach(s => {
        const card = document.createElement('div');
        card.className = 'scheme-card';
        card.onclick = () => showAudit(s);
        
        card.innerHTML = `
            <div class="scheme-card-header">
                <div class="scheme-id">${s.scheme_id}</div>
                <div class="scheme-status status-${s.status}">${s.status.replace('_', ' ')}</div>
            </div>
            <div class="scheme-name">${s.scheme_name}</div>
            <div class="scheme-ministry">${s.benefit_summary}</div>
            <div class="conf-container">
                <div class="conf-header">
                    <div class="conf-label">Confidence Score</div>
                    <div class="conf-value">${(s.confidence_score * 100).toFixed(0)}%</div>
                </div>
                <div class="conf-track">
                    <div class="conf-bar status-${s.status}" style="width: ${s.confidence_score * 100}%; background: ${getStatusColor(s.status)}"></div>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

async function processInput(text) {
    if (!text.trim()) return;

    if (text.toLowerCase().includes("reset")) {
        sessionId = null;
        document.getElementById('chat-scroll').innerHTML = '';
        addMessage("Session reset. Namaste! Kripya apna age aur kaam batayein.", 'bot');
        document.getElementById('profile-data').innerHTML = '';
        document.getElementById('schemes-grid').innerHTML = '';
        document.getElementById('ambiguity-panel').style.display = 'none';
        return;
    }

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: text,
                channel: "web"
            })
        });

        if (!response.ok) {
            throw new Error(`API returned ${response.status}`);
        }

        const data = await response.json();
        sessionId = data.session_id;

        // Collect all global ambiguities from schemes
        let allAmbigs = new Set();
        data.scheme_matches.forEach(s => {
            s.ambiguity_flags.forEach(am => allAmbigs.add(am));
        });

        renderProfile(data.profile_snapshot, data.profile_completion_pct, Array.from(allAmbigs));
        renderSchemes(data.scheme_matches);
        renderTouchbars(data.gap_analysis);
        addMessage(data.reply, 'bot');
        
    } catch (e) {
        console.error("Backend request failed", e);
        addMessage("Backend API error. Ensure FastAPI is running on port 8000.", 'bot');
    }
}

document.getElementById('send-btn').onclick = () => {
    const input = document.getElementById('chat-input');
    if (input.value) {
        const text = input.value;
        addMessage(text, 'user');
        input.value = '';
        processInput(text);
    }
};

document.getElementById('chat-input').onkeypress = (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('send-btn').click();
    }
};

function renderTouchbars(gapAnalysis) {
    const container = document.getElementById('touchbar-container');
    container.innerHTML = '';
    if (!gapAnalysis || gapAnalysis.length === 0) return;

    const topGap = gapAnalysis[0].field;

    const SUGGESTIONS = {
        "state": ["Rajasthan", "Bihar", "Uttar Pradesh", "Maharashtra"],
        "residence_type": ["Gaon (Rural)", "Shahar (Urban)"],
        "occupation": ["Farmer", "Street Vendor", "Labourer", "Other"],
        "marital_status": ["Widow", "Married", "Unmarried"],
        "gender": ["Female", "Male"],
        "land_ownership_status": ["I own active farm land", "I am a lessee farmer"],
        "housing_status": ["Kaccha house", "Pucca house"],
        "bank_account_linked_aadhaar": ["Bank account is linked", "Not linked"],
        "secc_2011_listed": ["Yes, in SECC List", "Not sure"],
        "income_tax_payer": ["I don't pay income tax", "I pay income tax"]
    };

    if (SUGGESTIONS[topGap]) {
        SUGGESTIONS[topGap].forEach(text => {
            const pill = document.createElement('div');
            pill.className = 'touchbar-pill';
            pill.innerText = text;
            pill.onclick = () => {
                document.getElementById('chat-input').value = text;
                document.getElementById('send-btn').click();
            };
            container.appendChild(pill);
        });
    }
}

window.onload = async () => {
    addMessage("Namaste! Main Kalam Assistant hoon. Aapka swagat hai. Shuruwat karne ke liye apna State bataein aur kisi bare mai (e.g., 'Main Rajasthan se hu, meri umr 45 hai')", "bot");
    try {
        const response = await fetch("http://localhost:8000/init");
        if (response.ok) {
            const data = await response.json();
            sessionId = data.session_id;

            let allAmbigs = new Set();
            data.scheme_matches.forEach(s => {
                s.ambiguity_flags.forEach(am => allAmbigs.add(am));
            });
            renderProfile(data.profile_snapshot, data.profile_completion_pct, Array.from(allAmbigs));
            renderSchemes(data.scheme_matches);
            renderTouchbars(data.gap_analysis);
        }
    } catch (e) {
        console.error("Initialization failed", e);
    }
};

