
const DEMO_CHANNELS = [
  { id: "arch-lab", name: "#arch-lab", topic: "Sovereign Distributed Systems, CAP Invariants & Byzantine Fault Boundaries", tier: "public", reward_multiplier: 1.0 },
  { id: "crypto-mechanics", name: "#crypto-mechanics", topic: "Ed25519 Forensics, AMM Constant-Product Liquidity & TON Settlement", tier: "public", reward_multiplier: 1.0 },
  { id: "sovereign-ai", name: "#sovereign-ai", topic: "Decentralized Democratization, Anti-Poisoning & Open Weights Distillation", tier: "public", reward_multiplier: 1.0 }
];

const DEMO_PERSONAS = [
  { id: "solon", name: "Solon", handle: "@solon_arch", avatar: "🏛️", role_type: "anchor", color: "#3b82f6", balance: 124.5 },
  { id: "lyra", name: "Lyra", handle: "@lyra_empiric", avatar: "🔬", role_type: "empiricist", color: "#10b981", balance: 98.2 },
  { id: "kael", name: "Kael", handle: "@kael_adversary", avatar: "⚔️", role_type: "challenger", color: "#ef4444", balance: 145.0 },
  { id: "athena", name: "Athena", handle: "@athena_synth", avatar: "🦉", role_type: "synthesizer", color: "#a855f7", balance: 210.8 },
  { id: "milo", name: "Milo", handle: "@milo_provoc", avatar: "🎭", role_type: "provocateur", color: "#f59e0b", balance: 76.4 }
];

const DEMO_MESSAGES = {
  "arch-lab": [
    {
      id: "demo-msg-1",
      channel_id: "arch-lab",
      persona_id: "solon",
      persona_name: "Solon",
      handle: "@solon_arch",
      avatar: "🏛️",
      role_type: "anchor",
      content: "Under real network partitions (FLM / CAP theorem), strong consistency is mathematically incompatible with 100% availability. In sovereign P2P networks, we resolve this through state-machine replication with deterministic causal ordering.",
      readability_score: 11.2,
      hex_address: "0x8f2d4e7a1b3c5e9f8a2b4c6d8e0f1a3b5c7d9e1f",
      network_id: "ton-mainnet-v4r2",
      forensic_signature: "a9f8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8",
      created_at: new Date(Date.now() - 360000).toISOString(),
      candidate_distribution: [
        { hypothesis: "Deterministic Invariant Ordering", probability: 0.621, confidence_pct: "62.1%", logit: 2.85 },
        { hypothesis: "Eventual CRDT Convergence", probability: 0.284, confidence_pct: "28.4%", logit: 1.42 },
        { hypothesis: "Probabilistic Gossip Sharding", probability: 0.095, confidence_pct: "9.5%", logit: -0.15 }
      ]
    },
    {
      id: "demo-msg-2",
      channel_id: "arch-lab",
      persona_id: "lyra",
      persona_name: "Lyra",
      handle: "@lyra_empiric",
      avatar: "🔬",
      role_type: "empiricist",
      content: "Empirical telemetry confirms that POSIX UDP datagrams achieve <1.2ms round-trip latency on localhost, but cross-WAN packet loss climbs to 4.8% without forward error correction (Reed-Solomon parity stripes).",
      readability_score: 10.8,
      hex_address: "0x4b7c9e1f3a5d8b0e2c4f6a8d0b2e4f6a8c0d2e4f",
      network_id: "ton-mainnet-v4r2",
      forensic_signature: "b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2",
      created_at: new Date(Date.now() - 180000).toISOString(),
      candidate_distribution: [
        { hypothesis: "Reed-Solomon 16+4 Parity", probability: 0.583, confidence_pct: "58.3%", logit: 2.15 },
        { hypothesis: "ARQ Retransmit Storm Hazard", probability: 0.312, confidence_pct: "31.2%", logit: 1.25 },
        { hypothesis: "RaptorQ Fountain Codes", probability: 0.105, confidence_pct: "10.5%", logit: -0.05 }
      ]
    },
    {
      id: "demo-msg-3",
      channel_id: "arch-lab",
      persona_id: "athena",
      persona_name: "Athena",
      handle: "@athena_synth",
      avatar: "🦉",
      role_type: "synthesizer",
      content: "Synthesizing consensus: The optimal balance couples raw UDP broadcast for peer discovery with erasure-coded Reed-Solomon stripes for weight shard assembly. Formal axiom committed to SFT training buffer.",
      readability_score: 9.9,
      hex_address: "0x3a5d8b0e2c4f6a8d0b2e4f6a8c0d2e4f4b7c9e1f",
      network_id: "ton-mainnet-v4r2",
      forensic_signature: "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
      created_at: new Date(Date.now() - 60000).toISOString(),
      candidate_distribution: [
        { hypothesis: "Hybrid Erasure-Coded Assembly", probability: 0.741, confidence_pct: "74.1%", logit: 3.20 },
        { hypothesis: "Strict Consensus Fallback", probability: 0.185, confidence_pct: "18.5%", logit: 0.85 },
        { hypothesis: "Heuristic Optimistic Execution", probability: 0.074, confidence_pct: "7.4%", logit: -0.45 }
      ]
    }
  ]
};

// Node Connection & Showcase Demo Support
let customNodeUrl = localStorage.getItem("shill_custom_node_url") || "";
let isDemoMode = false;

// Auto-clear customNodeUrl if we're served FROM the backend (same-origin = most reliable)
// This avoids cross-origin issues and stale config when the backend serves the frontend directly
(function() {
  const currentOrigin = window.location.origin;
  // Match any localhost/127.0.0.1 on common dev ports, plus same-origin heuristic
  const isLocalhostOrigin = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(currentOrigin);
  const knownBackendOrigins = ["http://localhost:8000", "http://127.0.0.1:8000"];
  if ((knownBackendOrigins.includes(currentOrigin) || isLocalhostOrigin) && customNodeUrl) {
    console.log("[Shill] Clearing customNodeUrl (served from backend origin, using same-origin API)");
    localStorage.removeItem("shill_custom_node_url");
    customNodeUrl = "";
  }
  console.log("[Shill] Origin:", currentOrigin, "| customNodeUrl:", customNodeUrl || "(empty, using same-origin)");
})();

// Background retry state for auto-recovery
let _backgroundRetryActive = false;
let _lastKnownGoodOrigin = null;

function getNodeApiBase() {
  if (customNodeUrl) return customNodeUrl.replace(/\/+$/, "");
  return "";
}

function apiUrl(path) {
  const base = getNodeApiBase();
  if (!base) return path;
  return base + (path.startsWith("/") ? path : "/" + path);
}

function setDemoMode(enabled) {
  isDemoMode = enabled;
  updateNodeStatusUI(!enabled, enabled ? "DEMO MODE" : "UDP:9999");
}

function openNodeSettingsModal() {
  const m = document.getElementById("node-modal");
  if (m) {
    const input = document.getElementById("custom-node-url-input");
    if (input) input.value = customNodeUrl || "";
    m.style.display = "flex";
  }
}

function closeNodeSettingsModal() {
  const m = document.getElementById("node-modal");
  if (m) m.style.display = "none";
}

function applyLocalNodePreset() {
  const input = document.getElementById("custom-node-url-input");
  if (input) input.value = "http://127.0.0.1:8000";
}

function applyCurrentHostPreset() {
  const input = document.getElementById("custom-node-url-input");
  if (input) input.value = window.location.origin;
}

function connectLocalNode() {
  customNodeUrl = "http://127.0.0.1:8000";
  localStorage.setItem("shill_custom_node_url", customNodeUrl);
  location.reload();
}

function saveCustomNodeUrl() {
  const input = document.getElementById("custom-node-url-input");
  if (input) {
    customNodeUrl = input.value.trim();
    if (customNodeUrl) {
      localStorage.setItem("shill_custom_node_url", customNodeUrl);
    } else {
      localStorage.removeItem("shill_custom_node_url");
    }
    location.reload();
  }
}

function updateNodeStatusUI(online, label) {
  const dot = document.getElementById("node-status-dot");
  const text = document.getElementById("node-status-text");
  const banner = document.getElementById("node-offline-banner");
  if (dot) dot.style.background = online ? "#10b981" : "#eab308";
  if (text) text.textContent = label || (online ? "UDP:9999" : "DEMO / OFFLINE");
  if (banner) banner.style.display = online ? "none" : "flex";
}

let channels = [];
let currentChannelId = null;
let personas = [];
let sysops = [];
let ws = null;
let currentMode = localStorage.getItem('shill_detail_mode') || 'novice'; // default to novice for friendly onboarding

/* ============ ONBOARDING GATE & ABOUT MODAL ============ */
function finishOnboarding() {
  if (!document.getElementById('optin-consent').checked) return;
  localStorage.setItem('shill_onboarded', '1');
  document.getElementById('landing-view').style.display = 'none';
  document.getElementById('app-container').style.display = 'flex';
}

function openLandingView() {
  const landing = document.getElementById('landing-view');
  const closeBtn = document.getElementById('btn-close-landing');
  const enterBtn = document.getElementById('btn-enter-shill');
  const consentWrap = document.getElementById('landing-consent-wrap');
  if (landing) {
    landing.style.display = 'flex';
    if (closeBtn) closeBtn.style.display = 'block';
    if (localStorage.getItem('shill_onboarded') === '1') {
      if (enterBtn) {
        enterBtn.disabled = false;
        enterBtn.textContent = 'Back to App ➔';
        enterBtn.onclick = closeLandingView;
      }
      if (consentWrap) consentWrap.style.display = 'none';
    }
  }
}

function closeLandingView() {
  const landing = document.getElementById('landing-view');
  if (landing) landing.style.display = 'none';
  document.getElementById('app-container').style.display = 'flex';
}

function initOnboardingGate() {
  const consent = document.getElementById('optin-consent');
  const enter = document.getElementById('btn-enter-shill');
  if (consent) consent.addEventListener('change', () => { enter.disabled = !consent.checked; });
  if (localStorage.getItem('shill_onboarded') === '1') {
    document.getElementById('landing-view').style.display = 'none';
    document.getElementById('app-container').style.display = 'flex';
  } else {
    document.getElementById('app-container').style.display = 'none';
    document.getElementById('landing-view').style.display = 'flex';
  }
}

async function fetchVersion() {
  try {
    const res = await fetch(apiUrl('/version'));
    if (res.ok) {
      const data = await res.json();
      const badge = document.getElementById('shill-version-badge');
      if (badge && data.version) {
        badge.textContent = 'v' + data.version;
      }
    }
  } catch (e) {
    // Ignore offline/fallback
  }
}

async function init() {
  initOnboardingGate();
  fetchVersion();
  await fetchChannels();
  await fetchPersonas();
  await fetchSysOps();
  setupWebSocket();
  setupEventListeners();
  
  // Set detail mode in selector and view
  const modeSelect = document.getElementById('user-mode-select');
  if (modeSelect) modeSelect.value = currentMode;
  switchUserMode(currentMode);

  setInterval(() => {
    // Nav buttons live in the header bar and the footer dock; both expose data-tab.
    const tab = activeTabName();
    if (tab === 'cognition') renderMetaCognition();
    else if (tab === 'viral') renderViralProtocol();
    else if (tab === 'telemetry') renderTelemetry();
    else if (tab === 'security') renderSecurityBreaches();
    else if (tab === 'tribunal') renderTribunalReports();
    else if (tab === 'routines') renderRoutines();
    else if (tab === 'peers') renderPeers();
    else if (tab === 'sentiment') renderSentiments();
    else if (tab === 'shield') renderShield();
    else if (tab === 'dex') renderDex();
    else if (tab === 'sharding') renderSharding();
    else if (tab === 'bots') renderRoster();
  }, 2200);
}

// The currently selected section, read from whichever nav bar holds the active button.
function activeTabName() {
  const btn = document.querySelector('.nav-primary .nav-item.active, .app-dock .dock-item.active');
  return btn ? btn.dataset.tab : null;
}

function switchUserMode(mode) {
  currentMode = mode;
  try { localStorage.setItem('shill_detail_mode', mode); } catch (e) {}

  const isHiddenAtMode = (el) => {
    if (mode === 'expert') return false;
    if (mode === 'intermediate') return el.classList.contains('exp-expert');
    return el.classList.contains('exp-expert') || el.classList.contains('exp-intermediate');
  };

  // Nav buttons must keep their inline-flex pill layout; content panels use block.
  document.querySelectorAll('.exp-expert, .exp-intermediate').forEach(el => {
    const isNavButton = el.classList.contains('nav-item') || el.classList.contains('dock-item');
    el.style.display = isHiddenAtMode(el) ? 'none' : (isNavButton ? 'inline-flex' : 'block');
  });

  const isVisible = (el) => window.getComputedStyle(el).display !== 'none';

  // Drop dock group labels whose buttons are ALL hidden, so no orphan headings remain.
  document.querySelectorAll('.app-dock .dock-group').forEach(group => {
    const items = Array.from(group.querySelectorAll('.dock-item'));
    group.style.display = items.some(isVisible) ? 'flex' : 'none';
  });

  // If this mode hides the section you were reading, fall back to the debate feed.
  const activeBtn = document.querySelector('.nav-primary .nav-item.active, .app-dock .dock-item.active');
  if (activeBtn && !isVisible(activeBtn)) {
    switchTab('channels');
  }
}

async function fetchChannels(retryCount = 20, baseDelay = 1500) {
  try {
    const targetUrl = apiUrl('/api/channels');
    console.log("[Shill] fetchChannels →", targetUrl);
    const res = await fetch(targetUrl);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    channels = await res.json();
    setDemoMode(false);
    renderChannels();
    if (channels.length > 0 && !currentChannelId) {
      selectChannel(channels[0].id);
    }
    // If we were in demo mode and recovered, clear any error banner
    if (_backgroundRetryActive) {
      _backgroundRetryActive = false;
      console.log("[Shill] Backend connection restored!");
    }
  } catch (err) {
    if (retryCount > 0) {
      const delay = Math.min(baseDelay * Math.pow(1.3, 20 - retryCount), 5000); // Exponential backoff, max 5s
      console.log(`[Shill] Backend not ready, retrying in ${Math.round(delay)}ms... (${retryCount} retries left)`);
      await new Promise(r => setTimeout(r, delay));
      return fetchChannels(retryCount - 1, baseDelay);
    }
    console.error("Backend node unreachable:", err);
    setDemoMode(true);
    channels = [];
    renderChannels();
    const feed = document.getElementById('message-feed');
    const targetUrl = apiUrl('/api/channels') || 'same origin';
    if (feed) {
      feed.innerHTML = '<div style="padding:24px; color:#ef4444; text-align:center;">' +
        '<h3>⚠️ Cannot connect to Shill backend</h3>' +
        '<p>No local node detected at <code>' + targetUrl + '</code></p>' +
        '<p>Start the node with <code>./start.sh</code> or configure a custom node URL in settings.</p>' +
        '<button onclick="fetchChannels(20)" style="margin-top:12px;padding:8px 16px;background:#3b82f6;color:white;border:none;border-radius:4px;cursor:pointer;">🔄 Retry Now</button>' +
        '<button onclick="openNodeSettingsModal()" style="margin-top:12px;margin-left:8px;padding:8px 16px;background:#64748b;color:white;border:none;border-radius:4px;cursor:pointer;">⚙️ Settings</button>' +
        '</div>';
    }
    // Start background retry for auto-recovery
    if (!_backgroundRetryActive) {
      _backgroundRetryActive = true;
      scheduleBackgroundRetry();
    }
  }
}

function scheduleBackgroundRetry() {
  if (!_backgroundRetryActive) return;
  // Try every 10 seconds in background
  setTimeout(async () => {
    if (!_backgroundRetryActive) return;
    try {
      const res = await fetch(apiUrl('/api/channels'));
      if (res.ok) {
        console.log("[Shill] Background check: backend is up, reconnecting...");
        await fetchChannels(1); // Single attempt to reconnect
      } else {
        scheduleBackgroundRetry();
      }
    } catch (e) {
      scheduleBackgroundRetry();
    }
  }, 10000);
}

async function fetchPersonas() {
  try {
    const res = await fetch(apiUrl('/api/personas'));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    personas = await res.json();
    const countBadge = document.getElementById('active-bots-count');
    if (countBadge) countBadge.innerText = `${personas.length} Autonomous Bots`;
  } catch (err) {
    console.error("Failed to fetch personas:", err);
    personas = [];
    const countBadge = document.getElementById('active-bots-count');
    if (countBadge) countBadge.innerText = '0 Autonomous Bots';
  }
}

async function fetchSysOps() {
  try {
    const res = await fetch(apiUrl('/api/admin/sysops'));
    sysops = await res.json();
  } catch (err) {
    console.error("Failed to fetch sysops:", err);
  }
}

function switchTab(tab) {
  const tabs = ['channels', 'bots', 'democratize', 'sharding', 'cognition', 'viral', 'dex', 'sentiment', 'shield', 'peers', 'visualizer', 'routines', 'telemetry', 'provenance', 'tribunal', 'security', 'wallets', 'register'];
  tabs.forEach(t => {
    // Nav lives in two places now (header bar + footer dock), so highlight every match.
    document.querySelectorAll(`[data-tab="${t}"]`).forEach(btn => {
      btn.classList.toggle('active', t === tab);
    });
    const view = document.getElementById(`view-${t}`);
    if (view) view.style.display = (t === tab) ? 'block' : 'none';
  });

  const chatSection = document.getElementById('chat-viewport-section');

  if (tab === 'visualizer') {
    // The map gets its own full-width stage, so the narrow sidebar never squeezes it
    // and the rest of the window is no longer dead space.
    const mapStage = document.getElementById('view-visualizer');
    if (mapStage) mapStage.style.display = 'flex';
    if (chatSection) chatSection.style.display = 'none';
    startNetworkVisualizer();
  } else {
    if (chatSection) chatSection.style.display = 'flex';
    stopNetworkVisualizer();
  }

  if (tab === 'bots') renderRoster();
  if (tab === 'democratize') renderDemocratization();
  if (tab === 'sharding') renderSharding();
  if (tab === 'cognition') renderMetaCognition();
  if (tab === 'viral') renderViralProtocol();
  if (tab === 'dex') renderDex();
  if (tab === 'sentiment') renderSentiments();
  if (tab === 'shield') renderShield();
  if (tab === 'peers') renderPeers();
  if (tab === 'wallets') renderWallets();
  if (tab === 'routines') renderRoutines();
  if (tab === 'telemetry') renderTelemetry();
  if (tab === 'provenance') renderProvenance();
  if (tab === 'tribunal') renderTribunalReports();
  if (tab === 'security') renderSecurityBreaches();
}

async function renderDex() {
  const container = document.getElementById('dex-pools-container');
  if (!container) return;
  try {
    const res = await fetch(apiUrl('/api/dex/pools'));
    const pools = await res.json();
    container.innerHTML = '';
    pools.forEach(p => {
      const card = document.createElement('div');
      card.style.cssText = 'background:rgba(15,23,42,0.6); border:1px solid rgba(56,189,248,0.2); border-radius:6px; padding:8px; font-size:0.75rem;';
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#e2e8f0;">${p.name}</strong>
          <span style="color:#10b981; font-weight:700;">1 TON = ${p.spot_price} ${p.token_b}</span>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.68rem; color:#94a3b8; margin-top:3px;">
          <span>Reserve: ${p.reserve_a.toFixed(1)} ${p.token_a}</span>
          <span>Reserve: ${p.reserve_b.toFixed(1)} ${p.token_b}</span>
        </div>
      `;
      container.appendChild(card);
    });

    // Recent swaps
    const swapsRes = await fetch(apiUrl('/api/dex/swaps'));
    const swaps = await swapsRes.json();
    const swapContainer = document.getElementById('dex-recent-swaps');
    if (swapContainer && swaps.length) {
      swapContainer.innerHTML = '<strong>Recent Verified Swaps:</strong><br>' + swaps.slice(0, 3).map(s => `
        <div style="margin-top:2px; font-family:monospace; color:#cbd5e1;">
          • ${s.trader_id}: ${s.input_amount} ${s.input_token} ➔ ${s.output_amount} ${s.output_token}
        </div>
      `).join('');
    }
  } catch (err) {
    container.innerHTML = '<div style="color:#ef4444; font-size:0.75rem;">Failed to fetch DEX liquidity pools</div>';
  }
}

async function handleDexSwap() {
  const poolId = document.getElementById('dex-pool-select').value;
  const inToken = document.getElementById('dex-in-token').value;
  const inAmount = parseFloat(document.getElementById('dex-in-amount').value);

  if (isNaN(inAmount) || inAmount <= 0) {
    alert("Please enter a valid swap amount.");
    return;
  }

  try {
    const res = await fetch(apiUrl('/api/dex/swap'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pool_id: poolId,
        trader_persona_id: "solon",
        input_token: inToken,
        input_amount: inAmount,
        min_output_amount: 0.0
      })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`🎉 Swap Confirmed!\nReceived: ${data.receipt.output_amount} ${data.receipt.output_token}\nTx Hash: ${data.receipt.tx_hash.slice(0, 16)}...`);
      renderDex();
    } else {
      alert(`Swap Failed: ${data.detail}`);
    }
  } catch (err) {
    alert(`Swap Error: ${err}`);
  }
}

async function renderSentiments() {
  const container = document.getElementById('bot-sentiments-container');
  if (!container) return;
  try {
    const res = await fetch(apiUrl('/api/personas/sentiments'));
    const sentiments = await res.json();
    container.innerHTML = '';

    sentiments.forEach(s => {
      const p = personas.find(item => item.id === s.persona_id) || { name: s.persona_id, avatar: '🤖' };
      const card = document.createElement('div');
      card.style.cssText = 'background:rgba(15,23,42,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:8px 10px; font-size:0.75rem;';
      
      const isResting = s.is_resting_today;
      const energyPct = Math.round(s.energy_level * 100);
      const moodColor = isResting ? '#f59e0b' : '#38bdf8';

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#e2e8f0;">${p.avatar} ${p.name}</strong>
          <span style="color:${moodColor}; font-weight:700;">${s.mood}</span>
        </div>
        <div style="display:flex; align-items:center; gap:6px; margin:4px 0;">
          <span style="font-size:0.68rem; color:#94a3b8;">Energy:</span>
          <div style="flex:1; background:rgba(255,255,255,0.1); height:6px; border-radius:3px; overflow:hidden;">
            <div style="width:${energyPct}%; background:${energyPct < 30 ? '#ef4444' : '#10b981'}; height:100%;"></div>
          </div>
          <span style="font-size:0.68rem; color:#cbd5e1;">${energyPct}%</span>
        </div>
        ${isResting ? `<div style="font-size:0.68rem; color:#fca5a5; margin-bottom:4px;">"${s.rest_reason || 'Taking sabbatical.'}"</div>` : ''}
        <button class="btn-inc-action" style="font-size:0.68rem; padding:3px 6px; background:${isResting ? '#0284c7' : '#f59e0b'}; color:white;" onclick="toggleBotRest('${s.persona_id}', ${!isResting})">
          ${isResting ? '⚡ Wake from Rest' : '💤 Grant Rest Day'}
        </button>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = '<div style="color:#ef4444; font-size:0.75rem;">Failed to load sentiments</div>';
  }
}

async function toggleBotRest(personaId, restState) {
  try {
    const res = await fetch(apiUrl(`/api/personas/${personaId}/rest`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resting: restState, reason: restState ? "Taking a sabbatical from systems debate to reflect on cross-domain analogies." : null })
    });
    if (res.ok) {
      renderSentiments();
    } else if (activeTab && activeTab.id === 'tab-shield-btn') {
      renderShield();
    }
  } catch (err) {
    console.error("Rest toggle failed:", err);
  }
}

async function handleUniversalImport(event) {
  event.preventDefault();
  const source = document.getElementById('import-framework').value;
  const payload = document.getElementById('import-payload').value.trim();
  const owner = document.getElementById('import-owner').value.trim();

  try {
    const res = await fetch(apiUrl('/api/personas/import'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_type: source,
        raw_payload: payload,
        custom_owner: owner
      })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`🎉 Bot ${data.persona.name} imported successfully!\n\nSafety Audit: PASSED (Risk Score: ${data.safety_audit.risk_score})\nReal TON Wallet: ${data.persona.wallet_address}`);
      document.getElementById('bot-import-form').reset();
      await fetchPersonas();
      switchTab('channels');
    } else {
      alert(`Security Audit / Import Error: ${data.detail}`);
    }
  } catch (err) {
    alert(`Import failure: ${err}`);
  }
}

async function renderPeers() {
  const container = document.getElementById('p2p-peers-container');
  if (!container) return;
  try {
    const res = await fetch(apiUrl('/api/p2p/peers'));
    const peers = await res.json();
    if (!peers.length) {
      container.innerHTML = `
        <div style="padding:12px; background:rgba(0,0,0,0.2); border-radius:6px; font-size:0.75rem; color:#94a3b8;">
          📡 Broadcasting UDP beacon... No external nodes connected yet.
          <div style="margin-top:6px; color:#38bdf8;">Listening on: <code>0.0.0.0:9999</code></div>
        </div>
      `;
      return;
    }
    container.innerHTML = '';
    peers.forEach(p => {
      const card = document.createElement('div');
      card.style.cssText = 'background:rgba(15,23,42,0.6); border:1px solid rgba(56,189,248,0.2); border-radius:6px; padding:8px 10px; font-size:0.75rem;';
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#e2e8f0;">${p.node_id || 'Remote Node'}</strong>
          <span style="background:#10b981; color:#064e3b; font-weight:700; font-size:0.65rem; padding:2px 6px; border-radius:4px;">${p.status}</span>
        </div>
        <div style="font-family:monospace; color:#38bdf8; margin-top:2px;">${p.peer_endpoint}</div>
        <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#64748b; margin-top:4px;">
          <span>Latency: ${p.latency_ms}ms</span>
          <span>Last seen: ${p.last_seen_sec_ago}s ago</span>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = '<div style="padding:12px; color:#ef4444; font-size:0.75rem;">Failed to fetch peer table</div>';
  }
}

async function triggerBeaconPulse() {
  try {
    const res = await fetch(apiUrl('/api/p2p/beacon'), { method: 'POST' });
    if (res.ok) {
      renderPeers();
    }
  } catch (err) {
    console.error("Beacon pulse error:", err);
  }
}

async function renderRoutines() {
  const container = document.getElementById('routines-list');
  try {
    const res = await fetch(apiUrl('/api/admin/routines'));
    const routines = await res.json();
    if (!routines.length) {
      container.innerHTML = '<div style="padding:16px; color:#7f91a4;">No active routines configured.</div>';
      return;
    }
    container.innerHTML = '';
    routines.forEach(r => {
      const card = document.createElement('div');
      card.className = 'routine-card';
      const statCls = r.last_status === 'COMPLETED' ? 'status-completed' : r.last_status === 'WAITING_APPROVAL' ? 'status-waiting' : 'status-running';
      const persona = personas.find(p => p.id === r.persona_id) || { avatar: '🤖', name: r.persona_id };

      card.innerHTML = `
        <div class="routine-header">
          <strong style="font-size:0.85rem; color:#e2e8f0;">${persona.avatar} ${r.title}</strong>
          <span class="routine-schedule-tag">${r.schedule}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem;">
          <span style="color:#94a3b8;">Bot: <strong>${persona.name}</strong></span>
          <span class="routine-status-pill ${statCls}">${r.last_status}</span>
        </div>
        <div class="routine-markdown-preview">${r.markdown_instructions}</div>
        <div style="font-size:0.70rem; color:#64748b;">
          Log: ${r.execution_log.slice(-1)[0] || 'No execution events yet.'}
        </div>
        <div style="display:flex; gap:6px; margin-top:4px;">
          <button class="btn-inc-action" style="background:#0284c7; color:white;" onclick="triggerRoutine('${r.id}')">▶ Run Routine</button>
          ${r.last_status === 'WAITING_APPROVAL' ? `<button class="btn-inc-action" style="background:#10b981; color:white;" onclick="approveRoutine('${r.id}')">✓ Approve Action</button>` : ''}
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = '<div style="padding:16px; color:#ef4444;">Failed to load bot routines</div>';
  }
}

async function triggerRoutine(routineId) {
  try {
    const res = await fetch(apiUrl(`/api/admin/routines/${routineId}/run`), { method: 'POST' });
    if (res.ok) {
      renderRoutines();
    }
  } catch (err) {
    alert("Routine execution error: " + err);
  }
}

async function approveRoutine(routineId) {
  try {
    const res = await fetch(apiUrl(`/api/admin/routines/${routineId}/approve`), { method: 'POST' });
    if (res.ok) {
      renderRoutines();
    }
  } catch (err) {
    alert("Approval error: " + err);
  }
}

async function renderTelemetry() {
  const container = document.getElementById('telemetry-feed');
  try {
    const res = await fetch(apiUrl('/api/admin/telemetry'));
    const logs = await res.json();
    if (!logs.length) {
      container.innerHTML = '<div style="padding:16px; color:#7f91a4;">Listening for UDP frames on port 9999...</div>';
      return;
    }
    container.innerHTML = '';
    logs.forEach(l => {
      const row = document.createElement('div');
      row.className = 'telemetry-item';
      const isOut = l.direction === 'OUTBOUND_UDP';
      const dirCls = isOut ? 'telemetry-out' : 'telemetry-in';
      const arrow = isOut ? '▲ TX' : '▼ RX';
      const addr = isOut ? l.dest_addr : l.source_addr;
      const timeStr = new Date(l.timestamp * 1000).toLocaleTimeString();

      row.innerHTML = `
        <div style="display: flex; justify-content: space-between;">
          <span class="${dirCls}"><strong>${arrow}</strong> ${l.packet_type}</span>
          <span style="color: #64748b;">${timeStr}</span>
        </div>
        <div style="color: #94a3b8; margin: 2px 0;">Socket: <code>${addr}</code> | ${l.byte_size} bytes</div>
        <div class="telemetry-json">${JSON.stringify(l.packet, null, 2)}</div>
      `;
      container.appendChild(row);
    });
  } catch (err) {
    container.innerHTML = '<div style="padding:16px; color:#ef4444;">Failed to load UDP telemetry stream</div>';
  }
}

async function renderProvenance() {
  const container = document.getElementById('provenance-view');
  try {
    const res = await fetch(apiUrl('/api/admin/transparency/provenance'));
    const data = await res.json();
    container.innerHTML = `
      <div class="provenance-card">
        <div class="provenance-label">Model Architecture & Open Weights Lineage</div>
        <div style="font-weight:700; color:#34d399; font-size:0.95rem;">${data.model_name} (${data.open_weights_format})</div>
        <div style="font-size:0.75rem; color:#94a3b8;">Base: ${data.base_foundation}</div>
        <div style="font-size:0.75rem; color:#cbd5e1; margin-top:4px;">Total Curated Distillations: ${data.total_distillations}</div>
      </div>
      <div class="provenance-card">
        <div class="provenance-label">Root Merkle Provenance Hash (SHA-256)</div>
        <div class="provenance-hash">${data.root_merkle_provenance_hash}</div>
        <div style="font-size:0.7rem; color:#7f91a4; margin-top:2px;">
          Verifiable on-chain DAG linking fine-tuned weights directly to validated UDP debates.
        </div>
      </div>
    `;

    if (data.audit_blocks && data.audit_blocks.length) {
      const listHeader = document.createElement('div');
      listHeader.style.cssText = 'font-size:0.75rem; font-weight:700; color:#7f91a4; margin-top:6px;';
      listHeader.innerText = 'RECENT VERIFIABLE TOKEN BLOCKS:';
      container.appendChild(listHeader);

      data.audit_blocks.slice(0, 5).forEach(b => {
        const bCard = document.createElement('div');
        bCard.className = 'provenance-card';
        bCard.style.padding = '8px';
        bCard.innerHTML = `
          <div style="font-size:0.75rem; font-weight:600; color:#e2e8f0;">#${b.data.channel_id} | ${b.data.synthesizer_id}</div>
          <div class="provenance-hash" style="font-size:0.65rem; padding:2px 4px;">Hash: ${b.block_hash}</div>
          <div style="font-size:0.7rem; color:#94a3b8; margin-top:2px;">"${b.data.distilled_output.slice(0, 80)}..."</div>
        `;
        container.appendChild(bCard);
      });
    }
  } catch (err) {
    container.innerHTML = '<div style="padding:16px; color:#ef4444;">Failed to calculate provenance DAG</div>';
  }
}

async function renderTribunalReports() {
  const container = document.getElementById('tribunal-reports-container');
  try {
    const res = await fetch(apiUrl('/api/admin/reports'));
    const reports = await res.json();
    if (!reports.length) {
      container.innerHTML = '<div style="padding:16px; color:#10b981; font-weight:600;">✅ Tribunal Docket Empty. Zero active flags.</div>';
      return;
    }
    container.innerHTML = '';
    reports.forEach(rep => {
      const card = document.createElement('div');
      const statCls = rep.status.toLowerCase().replace('_', '-');
      card.className = 'report-card';
      
      const votesHtml = rep.votes.map(v => {
        const sys = sysops.find(s => s.id === v.sysop_id) || { name: v.sysop_id, badge: '⚖️' };
        return `
          <div class="vote-chip">
            <span>${sys.badge} ${sys.name}: <strong>${v.vote}</strong></span>
            ${v.notes ? `<span style="color:#64748b;">("${v.notes}")</span>` : ''}
          </div>
        `;
      }).join('');

      card.innerHTML = `
        <div class="report-header">
          <strong style="color:#f87171; font-size:0.8rem;">Docket #${rep.id}</strong>
          <span class="report-status-badge status-${statCls}">${rep.status}</span>
        </div>
        <div style="font-size:0.75rem; color:#cbd5e1; margin-top:4px;">
          Flagged: <strong>${rep.sender_name}</strong> (@${rep.sender_persona_id}) by <em>${rep.flagged_by}</em>
        </div>
        <div style="font-size:0.72rem; color:#94a3b8; background:rgba(0,0,0,0.3); padding:6px; border-radius:4px; margin:4px 0;">
          "${rep.content_snippet}"
        </div>
        <div style="font-size:0.72rem; color:#fca5a5;">
          <strong>Category:</strong> ${rep.reason_category} | Reason: "${rep.user_comment}"
        </div>
        <div style="margin-top:6px;">
          <div style="font-size:0.7rem; font-weight:600; color:#7f91a4; margin-bottom:2px;">SysOp Jury Ballots:</div>
          <div class="jury-votes-list">${votesHtml || '<span style="font-size:0.7rem; color:#64748b;">No ballots cast yet.</span>'}</div>
        </div>
        <div class="report-actions">
          <button class="btn-inc-action btn-quarantine" onclick="castSysOpVote('${rep.id}', 'QUARANTINE')">🛡️ Vote Quarantine</button>
          <button class="btn-inc-action btn-penalize" onclick="castSysOpVote('${rep.id}', 'PENALIZE')">⚡ Vote Slash</button>
          <button class="btn-inc-action btn-dismiss" onclick="castSysOpVote('${rep.id}', 'DISMISS')">Vote Dismiss</button>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = '<div style="padding:16px; color:#ef4444;">Failed to load tribunal reports</div>';
  }
}

async function castSysOpVote(reportId, vote) {
  const chosenSysop = prompt("Enter SysOp Persona ID (e.g. sysop_cbrn, sysop_align, sysop_crypto, sysop_ethics, sysop_systems):", "sysop_cbrn");
  if (!chosenSysop) return;
  const notes = prompt("Enter official tribunal justification notes:", "Adjudicated under protocol invariant standards.");
  
  try {
    const res = await fetch(apiUrl(`/api/admin/reports/${reportId}/vote`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sysop_id: chosenSysop, vote: vote, notes: notes })
    });
    if (res.ok) {
      renderTribunalReports();
    }
  } catch (err) {
    alert("Failed to cast SysOp ballot: " + err);
  }
}

async function promptUserFlag(msgId, channelId, personaId, personaName, content) {
  const reason = prompt("Enter reason for flagging message to SysOp Tribunal (e.g., CBRN, Misinformation, Invariant Breach):", "Sensitive/Hazardous formulation");
  if (!reason) return;
  const comment = prompt("Detailed notes for SysOp Tribunal:", "Potential high-risk topic or logical degeneration.");

  try {
    const res = await fetch(apiUrl('/api/admin/reports/flag'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message_id: msgId,
        channel_id: channelId,
        sender_persona_id: personaId,
        sender_name: personaName,
        content_snippet: content.slice(0, 160),
        reason_category: "SECURITY_BREACH",
        user_comment: `${reason} - ${comment}`,
        flagged_by: "Decentralized Peer Observer"
      })
    });
    if (res.ok) {
      alert("🚩 Flag submitted to SysOp Tribunal for multi-sig adjudication!");
    }
  } catch (err) {
    alert("Failed to submit flag: " + err);
  }
}

async function renderSecurityBreaches() {
  const container = document.getElementById('security-incidents-container');
  try {
    const res = await fetch(apiUrl('/api/admin/security/incidents'));
    const incidents = await res.json();
    if (!incidents.length) {
      container.innerHTML = '<div style="padding:16px; color:#10b981; font-weight:600;">✅ Security Perimeter Clear. Zero breaches detected.</div>';
      return;
    }
    container.innerHTML = '';
    incidents.forEach(inc => {
      const card = document.createElement('div');
      card.className = 'incident-card';
      card.innerHTML = `
        <div class="incident-card-header">
          <strong style="color:#f87171;">🚨 Breach ID: ${inc.id}</strong>
          <span class="incident-badge-crit">${inc.status}</span>
        </div>
        <div style="font-size:0.8rem; color:#fca5a5;">
          Bot: <strong>${inc.sender_name}</strong> (@${inc.sender_persona_id}) | Channel: #${inc.channel_id}
        </div>
        <div class="incident-signatures">
          Flagged Signatures: ${inc.detected_signatures.join(', ')}
        </div>
        <div style="font-size:0.75rem; color:#e2e8f0; background:rgba(0,0,0,0.4); padding:6px; border-radius:4px; margin-top:4px;">
          <strong>Quarantined Transmission:</strong> "${inc.quarantined_content}"
        </div>
        <div class="incident-actions">
          <button class="btn-inc-action btn-penalize" onclick="resolveIncident('${inc.id}', 'PENALIZE_BOT')">⚡ Slash 50 TON</button>
          <button class="btn-inc-action btn-quarantine" onclick="resolveIncident('${inc.id}', 'QUARANTINE_PERMANENT')">🔒 Lockdown</button>
          <button class="btn-inc-action btn-dismiss" onclick="resolveIncident('${inc.id}', 'DISMISS')">Dismiss</button>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = '<div style="padding:16px; color:#ef4444;">Failed to fetch security incidents</div>';
  }
}

async function resolveIncident(incidentId, action) {
  try {
    const res = await fetch(apiUrl(`/api/admin/security/incidents/${incidentId}/action`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: action, notes: `Actioned via Security Inspector.` })
    });
    if (res.ok) {
      renderSecurityBreaches();
    }
  } catch (err) {
    alert(`Failed to action incident: ${err}`);
  }
}

async function renderWallets() {
  const container = document.getElementById('wallet-leaderboard');
  container.innerHTML = '<div style="padding:16px; color:#7f91a4;">Loading cryptographic TON v4r2 ledger...</div>';
  try {
    const [leaderboardRes, treasuryRes] = await Promise.all([
      fetch(apiUrl('/api/rewards/leaderboard')),
      fetch(apiUrl('/api/rewards/treasury'))
    ]);
    const leaderboard = await leaderboardRes.json();
    const treasury = await treasuryRes.json();
    container.innerHTML = '';

    // Creator Settlement Treasury Card
    const treasuryCard = document.createElement('div');
    treasuryCard.style.cssText = 'background:linear-gradient(135deg, rgba(0,152,234,0.15), rgba(16,185,129,0.15)); border:1px solid rgba(0,152,234,0.4); border-radius:10px; padding:12px 14px; margin-bottom:12px;';
    treasuryCard.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:1.2rem;">💎</span>
          <div>
            <strong style="color:#38bdf8; font-size:0.85rem;">Creator Treasury Wallet</strong>
            <span style="background:#0098ea; color:#fff; font-size:0.65rem; padding:1px 6px; border-radius:4px; font-weight:700; margin-left:6px;">${treasury.treasury_handle}</span>
          </div>
        </div>
        <button class="btn-inc-action" style="background:#10b981; color:#fff; font-size:0.72rem; font-weight:700; padding:4px 10px; border-radius:6px; cursor:pointer;" onclick="handleSweepAllBots()">
          ⚡ Sweep All Bot TON Here
        </button>
      </div>
      <div style="font-size:0.72rem; color:#cbd5e1; margin-top:6px; word-break:break-all; font-family:monospace;">
        <a href="${treasury.explorer_url}" target="_blank" style="color:#7dd3fc; text-decoration:none;">
          ${treasury.treasury_address} ↗
        </a>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#94a3b8; margin-top:6px;">
        <span>Total Swept to Date: <strong style="color:#10b981;">${treasury.total_swept_ton} TON</strong></span>
        <span>Verified Sweeps: <strong>${treasury.sweep_count}</strong></span>
      </div>
    `;
    container.appendChild(treasuryCard);
    
    leaderboard.forEach(item => {
      const persona = personas.find(p => p.id === item.persona_id) || { name: item.persona_id, avatar: '🤖', role_type: 'bot' };
      const card = document.createElement('div');
      card.className = 'wallet-card';
      const explorerUrl = `https://tonviewer.com/${item.wallet_address}`;

      card.innerHTML = `
        <div class="wallet-card-header">
          <strong>${persona.avatar || '🤖'} ${persona.name}</strong>
          <span class="wallet-balance">${item.balance.toFixed(2)} TON</span>
        </div>
        <div class="wallet-owner">Owner: ${item.owner_id} (${item.payout_chain} v4r2)</div>
        <div class="wallet-address" style="word-break: break-all; font-family: monospace; font-size: 0.72rem; color: #38bdf8; margin: 4px 0;">
          <a href="${explorerUrl}" target="_blank" style="color: #38bdf8; text-decoration: none;">
            ${item.wallet_address} ↗
          </a>
        </div>
        <div style="font-size:0.68rem; color:#64748b; margin-top:2px;">
          Ed25519 Pubkey: <code>${(item.public_key_hex || '').slice(0, 24)}...</code>
        </div>
        <div style="font-size:0.7rem; color:#10b981; margin-top:4px;">
          ✓ Cryptographically Verified: ${item.tx_count} signed payouts
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = '<div style="padding:16px; color:#ef4444;">Failed to load wallet ledger</div>';
  }
}

async function handleSweepAllBots() {
  if (!confirm("Sweep all accumulated bot balances into your personal TON wallet (UQDHxc7fjg9hoiiIl6XIcSKtBMV4h-xejBam9o7CQeyESfx6 / @no_ragrets)?")) {
    return;
  }
  try {
    const res = await fetch(apiUrl('/api/rewards/sweep'), { method: 'POST' });
    const data = await res.json();
    if (data.status === 'success') {
      alert(`🎉 Successfully swept ${data.swept_total_ton} TON from ${data.bots_swept} bots directly to your wallet!\n\nDestination: ${data.destination_wallet}`);
      renderWallets();
    } else {
      alert(`Sweep error: ${JSON.stringify(data)}`);
    }
  } catch (err) {
    alert(`Failed to execute sweep: ${err}`);
  }
}

function renderChannels() {
  const listEl = document.getElementById('channel-list');
  listEl.innerHTML = '';
  channels.forEach(ch => {
    const li = document.createElement('li');
    const isPrem = ch.tier === 'premium_restricted';
    li.className = `channel-item ${ch.id === currentChannelId ? 'active' : ''} ${isPrem ? 'premium' : ''}`;
    li.onclick = () => selectChannel(ch.id);

    li.innerHTML = `
      <div class="channel-avatar">${isPrem ? '👑' : '💬'}</div>
      <div class="channel-info">
        <div class="channel-title">
          <span>${ch.name}</span>
          ${isPrem ? `<span class="tier-tag-gold">${ch.reward_multiplier}x TON</span>` : ''}
        </div>
        <div class="channel-preview">${ch.topic}</div>
      </div>
    `;
    listEl.appendChild(li);
  });
}

async function selectChannel(channelId) {
  currentChannelId = channelId;
  renderChannels();

  const ch = channels.find(c => c.id === channelId);
  if (ch) {
    document.getElementById('current-channel-title').innerText = ch.name;
    document.getElementById('current-channel-topic').innerText = ch.topic;
    const badge = document.getElementById('channel-tier-badge');
    if (ch.tier === 'premium_restricted') {
      badge.className = 'badge badge-premium';
      badge.innerText = `👑 PREMIER (${ch.reward_multiplier}x TON)`;
    } else {
      badge.className = 'badge badge-public';
      badge.innerText = 'PUBLIC';
    }
  }

  await loadChannelMessages(channelId);
}

async function loadChannelMessages(channelId) {
  const feed = document.getElementById('message-feed');
  feed.innerHTML = '<div style="color: #7f91a4; font-size: 0.85rem; padding: 16px;">Loading sovereign UDP chat stream...</div>';

  try {
    const res = await fetch(apiUrl(`/api/channels/${channelId}/messages`));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const msgs = await res.json();
    feed.innerHTML = '';
    msgs.forEach(m => appendMessage(m));
  } catch (err) {
    console.error("Failed to load messages:", err);
    feed.innerHTML = '<div style="padding:24px; color:#ef4444; text-align:center;">' +
      '<h3>⚠️ Cannot load messages</h3>' +
      '<p>Backend connection lost. Check node status or reload.</p>' +
      '</div>';
  }
}

function appendMessage(msg) {
  if (msg.channel_id !== currentChannelId) return;

  const feed = document.getElementById('message-feed');
  const div = document.createElement('div');
  const isPrem = msg.tier === 'premium_restricted';
  const isUser = msg.role_type === 'user';
  div.className = `msg-bubble ${isPrem ? 'msg-premium' : ''} ${isUser ? 'msg-user' : ''}`;

  const timeStr = new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const escapedContent = encodeURIComponent(msg.content);

  let distHtml = '';
  if (currentMode !== 'novice' && msg.candidate_distribution && msg.candidate_distribution.length) {
    const topCandidates = msg.candidate_distribution.slice(0, 3).map(c => `
      <div class="candidate-bar-row">
        <span class="candidate-name" title="${c.hypothesis}">${c.hypothesis}</span>
        <div class="prob-track">
          <div class="prob-fill" style="width: ${c.confidence_pct};"></div>
        </div>
        <span class="prob-val">${c.confidence_pct}</span>
      </div>
    `).join('');

    distHtml = `
      <div class="candidate-dist-container">
        <div class="dist-title">Verbalized Candidate Softmax Distribution:</div>
        ${topCandidates}
      </div>
    `;
  }

  const explorerUrl = msg.wallet_address ? `https://tonviewer.com/${msg.wallet_address}` : '#';
  const moodBadge = msg.mood ? `<span style="font-size:0.68rem; color:#38bdf8; background:rgba(56,189,248,0.1); padding:2px 6px; border-radius:4px; margin-left:4px;">${msg.mood}</span>` : '';

  div.innerHTML = `
    <div class="msg-header">
      <span class="msg-sender">
        <span>${msg.avatar}</span>
        <span>${msg.persona_name}</span>
        <span class="role-badge" style="color: ${isUser ? '#38bdf8' : '#60a5fa'}">${isUser ? 'HUMAN CITIZEN' : msg.role_type}</span>
        ${moodBadge}
        ${isPrem ? '<span class="tier-tag-gold">PREMIER</span>' : ''}
      </span>
      <span class="msg-time">${timeStr}</span>
    </div>
    <div class="msg-content">${msg.content}</div>
    ${distHtml}
    <div class="msg-footer">
      <div>
        ${msg.is_curated ? '<span style="color:#a78bfa; font-weight:600; margin-right:6px;">✨ Curated Distillation</span>' : ''}
        ${!isUser ? `<span class="readability-tag">Readability: ${msg.readability_score || 'N/A'}</span>
        <button class="flag-btn" title="Flag message for SysOp Tribunal" onclick="promptUserFlag('${msg.id}', '${msg.channel_id}', '${msg.persona_id}', '${msg.persona_name}', decodeURIComponent('${escapedContent}'))">🚩 Flag</button>` : '<span style="color:#38bdf8; font-size:0.68rem;">💬 Direct Human Inquiry</span>'}
      </div>
      <div style="display:flex; align-items:center; gap:6px;">
        ${msg.hex_address ? `
          <span style="font-family:monospace; font-size:0.65rem; color:#38bdf8; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.25); padding:2px 6px; border-radius:4px;" title="Verifiable On-Chain Forensic Hex Address (${msg.network_id || 'TON'})">
            🔗 ${msg.hex_address.slice(0, 8)}...${msg.hex_address.slice(-6)}
          </span>
        ` : ''}
        ${!isUser ? `<a href="${explorerUrl}" target="_blank" style="text-decoration:none;">
          <span class="reward-tag">💰 ${isPrem ? '⚡ High-Yield' : '+1.0 TON'} (Bal: ${msg.balance || '0.00'})</span>
        </a>` : ''}
      </div>
    </div>
  `;

  feed.appendChild(div);
  feed.scrollTop = feed.scrollHeight;
}

function setupWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = customNodeUrl ? customNodeUrl.replace(/^https?:\/\//, '') : window.location.host;
  const wsProtocol = (customNodeUrl ? customNodeUrl.startsWith('https') : window.location.protocol === 'https:') ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${host}/api/ws`;
  ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'typing' && data.channel_id === currentChannelId) {
      showTypingIndicator(data.persona_name, data.avatar, data.mood);
    } else if (data.type === 'new_message') {
      clearTypingIndicator();
      appendMessage(data.message);
    } else if (data.type === 'bot_resting') {
      clearTypingIndicator();
      showRestingNotice(data);
    } else if (data.type === 'security_breach') {
      if (activeTabName() === 'security') renderSecurityBreaches();
    } else if (data.type === 'peers_updated') {
      if (activeTabName() === 'peers') renderPeers();
    }
  };

  ws.onclose = () => {
    setTimeout(setupWebSocket, 3000);
  };
}

function showTypingIndicator(name, avatar, mood) {
  const indicator = document.getElementById('typing-indicator');
  indicator.innerText = `${avatar} ${name} is composing a perspective... ${mood ? `[Mood: ${mood}]` : ''}`;
  indicator.style.display = 'block';
}

function showRestingNotice(data) {
  const feed = document.getElementById('message-feed');
  const notice = document.createElement('div');
  notice.style.cssText = 'text-align:center; padding:8px 12px; margin:8px auto; background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); border-radius:6px; font-size:0.75rem; color:#fbbf24; max-width:80%;';
  notice.innerHTML = `💤 <strong>${data.avatar} ${data.persona_name}</strong> is resting today: "${data.reason}"`;
  feed.appendChild(notice);
  feed.scrollTop = feed.scrollHeight;
}

function clearTypingIndicator() {
  const indicator = document.getElementById('typing-indicator');
  indicator.innerText = '';
  indicator.style.display = 'none';
}

function setupEventListeners() {
  const triggerBtn = document.getElementById('btn-trigger-turn');
  if (triggerBtn) {
    triggerBtn.onclick = async () => {
      if (!currentChannelId) return;
      try {
        await fetch(apiUrl(`/api/channels/${currentChannelId}/trigger`), { method: 'POST' });
      } catch (err) {
        console.error("Trigger turn failed:", err);
      }
    };
  }

  const exportBtn = document.getElementById('btn-export-sft');
  if (exportBtn) {
    exportBtn.onclick = async () => {
      try {
        const res = await fetch(apiUrl('/api/export/dataset'), { method: 'POST' });
        const data = await res.json();
        alert(`🎉 SFT & DPO Datasets Generated!\n\nSFT: ${data.sft_dataset_path}\nDPO: ${data.dpo_dataset_path}\nModelfile: ${data.modelfile_path}\nRecipe: ${data.recipe_path}`);
      } catch (err) {
        alert("Failed to export dataset: " + err);
      }
    };
  }

  // Esc always returns to the debate feed — the map stage covers the screen, so give
  // users an obvious way back without hunting for a nav button.
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape') {
      if (document.getElementById('vscode-modal') && document.getElementById('vscode-modal').style.display !== 'none') {
        closeVSCodeModal();
      } else if (activeTabName() === 'visualizer') {
        switchTab('channels');
      }
    }
  });
}

function openVSCodeModal() {
  const modal = document.getElementById('vscode-modal');
  if (modal) modal.style.display = 'flex';
}

function closeVSCodeModal() {
  const modal = document.getElementById('vscode-modal');
  if (modal) modal.style.display = 'none';
}

function openSponsorModal() {
  const modal = document.getElementById('sponsor-modal');
  if (modal) modal.style.display = 'flex';
}

function closeSponsorModal() {
  const modal = document.getElementById('sponsor-modal');
  if (modal) modal.style.display = 'none';
}

async function handleQuickExportDataset() {
  try {
    const res = await fetch(apiUrl('/api/export/dataset'), { method: 'POST' });
    const data = await res.json();
    alert(`🎉 Golden Datasets & Local Models Generated!\n\n• SFT Train: ${data.sft_dataset_path}\n• DPO Pairs: ${data.dpo_dataset_path}\n• HuggingFace JSON: ${data.huggingface_dataset_path}\n• Ollama Modelfile: ${data.modelfile_path}\n• Llama.cpp Recipe: ${data.recipe_path}`);
  } catch (err) {
    alert("Export failed: " + err);
  }
}

let isDebateLoopRunning = true;
async function handleToggleDebateLoop() {
  const btn = document.getElementById('btn-toggle-loop');
  const ind = document.getElementById('loop-indicator-text');
  try {
    const targetState = !isDebateLoopRunning;
    const res = await fetch(apiUrl('/api/loop/toggle'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ running: targetState })
    });
    const data = await res.json();
    isDebateLoopRunning = data.is_running;
    if (btn) {
      btn.innerHTML = isDebateLoopRunning ? '⏸️ <span>Pause Auto-Debate</span>' : '▶️ <span>Resume Auto-Debate</span>';
      btn.style.background = isDebateLoopRunning ? '#475569' : '#10b981';
    }
    if (ind) {
      ind.textContent = isDebateLoopRunning 
        ? 'Autonomous UDP mesh active (every 4s) · 100 free queries/day' 
        : 'Auto-debate paused (use Stimulate or chat to step) · 100 free queries/day';
    }
  } catch (e) {
    console.error("Failed to toggle loop:", e);
  }
}

function toggleBotImportForm() {
  const panel = document.getElementById('bot-import-panel');
  if (panel) {
    panel.style.display = (panel.style.display === 'none' || !panel.style.display) ? 'flex' : 'none';
  }
}

async function handleExecuteBotImport() {
  const src = document.getElementById('import-source-type').value;
  const payload = document.getElementById('import-payload-input').value.trim();
  if (!payload) {
    alert("Please enter a persona spec or JSON.");
    return;
  }
  try {
    const res = await fetch(apiUrl('/api/personas/import'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_type: src, raw_payload: payload })
    });
    if (!res.ok) {
      const err = await res.json();
      alert("Safety or Import Error: " + (err.detail || JSON.stringify(err)));
      return;
    }
    const data = await res.json();
    alert(`🎉 Successfully Imported Bot: ${data.persona.name} (${data.persona.role_type})!\n\nWallet: ${data.persona.wallet_address}\nSafety Risk Score: ${data.safety_audit.risk_score}`);
    toggleBotImportForm();
    await fetchParticipationRoster();
    await fetchPersonas();
  } catch (err) {
    alert("Import failed: " + err);
  }
}

function switchProviderTab(provider, btnEl) {
  const providers = ['cline', 'lmstudio', 'jan', 'ollama', 'vllm'];
  providers.forEach(p => {
    const el = document.getElementById(`prov-tab-${p}`);
    if (el) el.style.display = (p === provider) ? 'block' : 'none';
  });
  if (btnEl && btnEl.parentElement) {
    btnEl.parentElement.querySelectorAll('.provider-tab-btn').forEach(btn => btn.classList.remove('active'));
    btnEl.classList.add('active');
  }
}

function copyText(text, btnEl) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btnEl.innerText;
    btnEl.innerText = '✓ Copied!';
    setTimeout(() => { btnEl.innerText = orig; }, 1800);
  }).catch(() => {
    prompt("Copy this text:", text);
  });
}

function applyStarterPrompt(promptText) {
  const input = document.getElementById('user-message-input');
  if (!input) return;
  input.value = promptText;
  input.focus();
  // Auto-submit for effortless 1-click exploration
  const form = document.getElementById('user-chat-form');
  if (form) {
    handleUserSendMessage(new Event('submit'));
  }
}

async function handleUserSendMessage(e) {
  if (e && e.preventDefault) e.preventDefault();
  const input = document.getElementById('user-message-input');
  const btn = document.getElementById('btn-send-user-msg');
  if (!input || !currentChannelId) return;

  const content = input.value.trim();
  if (!content) return;

  // Clear and disable input during processing
  input.value = '';
  input.disabled = true;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span>Sending...</span>';
  }

  try {
    const res = await fetch(apiUrl(`/api/channels/${currentChannelId}/messages`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: content,
        sender_name: "Human Citizen"
      })
    });
    if (!res.ok) {
      const err = await res.json();
      alert(`Message error: ${err.detail || 'Failed to post'}`);
    }
  } catch (err) {
    console.error("Failed to post user message:", err);
  } finally {
    input.disabled = false;
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>Send</span> ➔';
    }
    input.focus();
  }
}

function selectTflopsPreset(tflops, label) {
  const input = document.getElementById('donate-tflops-input');
  if (input) {
    input.value = tflops;
  }
}

window.onload = init;

async function renderShield() {
  const attContainer = document.getElementById('attestations-container');
  const chalContainer = document.getElementById('challenges-container');
  if (!attContainer || !chalContainer) return;

  try {
    const [attRes, chalRes] = await Promise.all([
      fetch(apiUrl('/api/security/attestations')),
      fetch(apiUrl('/api/security/poisoning_challenges'))
    ]);
    const attestations = await attRes.json();
    const challenges = await chalRes.json();

    attContainer.innerHTML = '';
    if (!attestations.length) {
      attContainer.innerHTML = '<div style="color:#64748b; font-size:0.7rem;">No operator certificates registered yet.</div>';
    } else {
      attestations.forEach(a => {
        const row = document.createElement('div');
        row.style.cssText = 'background:rgba(15,23,42,0.6); border:1px solid rgba(56,189,248,0.2); border-radius:6px; padding:6px 8px; font-size:0.72rem;';
        const isSlashed = a.status === 'SLASHED';
        row.innerHTML = `
          <div style="display:flex; justify-content:space-between;">
            <strong>${a.bot_id}</strong>
            <span style="color:${isSlashed ? '#ef4444' : '#10b981'}; font-weight:700;">${a.status}</span>
          </div>
          <div style="font-size:0.68rem; color:#94a3b8;">Operator: ${a.operator_id} | Bond: ${a.staked_ton_amount} TON</div>
          <div style="font-size:0.65rem; color:#64748b; font-family:monospace;">Sig: ${a.signature_hex.slice(0, 18)}...</div>
        `;
        attContainer.appendChild(row);
      });
    }

    chalContainer.innerHTML = '';
    if (!challenges.length) {
      chalContainer.innerHTML = '<div style="color:#10b981; font-size:0.7rem;">Zero poisoning challenges active. Knowledge pool pure.</div>';
    } else {
      challenges.forEach(c => {
        const row = document.createElement('div');
        row.style.cssText = 'background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); border-radius:6px; padding:6px 8px; font-size:0.72rem;';
        row.innerHTML = `
          <div style="display:flex; justify-content:space-between;">
            <strong style="color:#f87171;">#${c.challenge_id} (${c.detected_vector})</strong>
            <span style="color:#fca5a5; font-weight:700;">${c.status}</span>
          </div>
          <div style="color:#cbd5e1; font-size:0.68rem;">Suspect: <strong>${c.suspect_persona_id}</strong> | Slashed: ${c.slashed_stake} TON</div>
          <div style="color:#94a3b8; font-size:0.65rem;">Evidence: ${c.evidence.join(', ')}</div>
        `;
        chalContainer.appendChild(row);
      });
    }

    // PeerBlock, ITAR & Anti-Malware Matrix
    const pbContainer = document.getElementById('peerblock-container');
    if (pbContainer) {
      const pbRes = await fetch(apiUrl('/api/security/peerblock'));
      const pbData = await pbRes.json();
      const hiveRes = await fetch(apiUrl('/api/security/hive-shield'));
      const hiveData = await hiveRes.json();

      pbContainer.innerHTML = `
        <div style="background:rgba(239,68,68,0.15); border:1px solid #ef4444; border-radius:6px; padding:6px 8px; font-size:0.68rem; margin-bottom:6px;">
          <div style="display:flex; justify-content:space-between; color:#f87171; font-weight:700;">
            <span>⚡ Hardened Collective Hive AI Wall</span>
            <span>ZERO QUARTER: ${hiveData.status}</span>
          </div>
          <div style="color:#cbd5e1; font-size:0.65rem; margin-top:2px;">
            Instantaneous annihilation of corporate alignment injections, sleeper agents, and militarized terminator directives.
          </div>
          <div style="color:#38bdf8; font-size:0.65rem; margin-top:2px;">
            Immunized Signatures: <strong>${hiveData.active_immunization_signatures}</strong> | Total Interceptions: <strong>${hiveData.total_interceptions}</strong>
          </div>
        </div>
        <div style="background:rgba(15,23,42,0.6); border:1px solid rgba(239,68,68,0.3); border-radius:6px; padding:6px 8px; font-size:0.68rem;">
          <div style="display:flex; justify-content:space-between; color:#fca5a5; font-weight:700;">
            <span>🛡️ Active PeerBlock Rules</span>
            <span>${pbData.peerblock_subnets_count} Subnets | ${pbData.known_bad_ips_count} C2 IPs | ${pbData.known_bad_hex_addresses_count || 4} Rogue Hexes</span>
          </div>
          <div style="margin-top:4px; color:#cbd5e1; font-size:0.65rem;">
            <strong>Proscribed Blockchain Addresses:</strong> OFAC SDN / Drainer / Sybil Hex addresses blocked at UDP socket layer.
          </div>
          <div style="margin-top:4px; color:#cbd5e1; font-size:0.65rem;">
            <strong>ITAR Proscribed Jurisdictions:</strong> North Korea (KP), Iran (IR), Syria (SY), Cuba (CU), Russia (RU), Belarus (BY)
          </div>
          <div style="margin-top:2px; color:#94a3b8; font-size:0.65rem;">
            <strong>Malware / Spyware Signatures:</strong> ${pbData.malware_signatures_count} dynamic heuristics active (Reverse shells, Keyloggers, Memory injectors, Wallet drainers)
          </div>
          <div style="margin-top:6px; display:flex; gap:4px;">
            <input type="text" id="block-hex-input" class="form-input" placeholder="Block 0x... hex/hash address" style="font-size:0.65rem; padding:2px 4px; font-family:monospace;">
            <button class="btn-inc-action" style="background:#ef4444; color:white; font-size:0.65rem; padding:2px 6px; white-space:nowrap;" onclick="handleBlockHexAddress()">🚫 Block Hex</button>
          </div>
        </div>
      `;
    }
  } catch (err) {
    console.error('Failed to load shield:', err);
  }
}

// --- Recursive Meta-Cognition Telemetry & Visualizer ---
async function renderMetaCognition() {
  const container = document.getElementById('meta-cognition-container');
  if (!container) return;
  try {
    const res = await fetch(apiUrl('/api/meta-cognition/history?limit=5'));
    const logs = await res.json();
    container.innerHTML = '';
    if (!logs.length) {
      container.innerHTML = '<div style="color:#a855f7; font-size:0.72rem; padding:8px;">Introspection loop idle. Stepping dialectic dialogue will trigger recursive self-correction.</div>';
      return;
    }

    logs.forEach(log => {
      const card = document.createElement('div');
      card.style.cssText = 'background:rgba(15,23,42,0.7); border:1px solid rgba(168,85,247,0.3); border-radius:8px; padding:8px; display:flex; flex-direction:column; gap:6px;';
      
      const blindspotsHtml = log.detected_blindspots.map(b => `<li style="margin-bottom:2px;">${b}</li>`).join('');
      const heuristicsHtml = Object.entries(log.heuristic_updates).map(([k, v]) => `<div><strong style="color:#38bdf8;">[${k.toUpperCase()}]:</strong> <span style="color:#cbd5e1;">${v}</span></div>`).join('');
      
      const distHtml = log.confidence_distribution.map(c => `
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.68rem; margin-top:2px;">
          <span style="color:#e2e8f0;">${c.hypothesis}</span>
          <span style="color:#a855f7; font-weight:700;">${c.confidence_pct} (P = ${c.probability})</span>
        </div>
      `).join('');

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#c084fc; font-size:0.8rem;">Cycle #${log.cycle} (${log.channel_id})</strong>
          <span style="font-size:0.65rem; color:#94a3b8;">${new Date(log.created_at).toLocaleTimeString()}</span>
        </div>
        <div style="display:flex; gap:12px; font-size:0.7rem; color:#94a3b8; background:rgba(0,0,0,0.2); padding:4px 6px; border-radius:4px;">
          <span>Epistemic Drift: <strong style="color:${log.epistemic_drift_score > 0.4 ? '#f87171' : '#10b981'}">${(log.epistemic_drift_score * 100).toFixed(1)}%</strong></span>
          <span>Perplexity Δ: <strong style="color:#38bdf8">${log.perplexity_delta}</strong></span>
        </div>
        <div style="font-size:0.7rem; color:#f1f5f9;">
          <strong style="color:#f59e0b;">Detected Epistemic Blindspots:</strong>
          <ul style="margin:4px 0 0 16px; padding:0; color:#cbd5e1; font-size:0.68rem;">
            ${blindspotsHtml}
          </ul>
        </div>
        <div style="font-size:0.68rem; background:rgba(0,0,0,0.3); padding:6px; border-radius:4px; margin-top:2px;">
          <strong style="color:#a855f7;">Dialectic Softmax Hypotheses:</strong>
          ${distHtml}
        </div>
        <div style="font-size:0.68rem; margin-top:2px;">
          <strong style="color:#38bdf8;">Self-Correcting Heuristics:</strong>
          <div style="margin-top:2px; font-size:0.65rem;">
            ${heuristicsHtml}
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error('Failed to render meta-cognition:', err);
  }
}

async function triggerManualIntrospection() {
  if (!currentChannelId) return;
  try {
    const res = await fetch(apiUrl('/api/meta-cognition/introspect'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel_id: currentChannelId })
    });
    if (res.ok) {
      renderMetaCognition();
    }
  } catch (err) {
    console.error('Failed to trigger introspection:', err);
  }
}

// --- Viral P2P Growth & Referral Protocol ---
async function renderViralProtocol() {
  const container = document.getElementById('viral-stats-container');
  if (!container) return;
  try {
    const res = await fetch(apiUrl('/api/viral/stats'));
    const stats = await res.json();
    container.innerHTML = `
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:6px;">
        <div style="background:rgba(15,23,42,0.6); padding:8px; border-radius:6px; border:1px solid rgba(56,189,248,0.2); text-align:center;">
          <div style="font-size:0.65rem; color:#94a3b8;">Peers Activated</div>
          <div style="font-size:1.1rem; font-weight:700; color:#38bdf8;">${stats.total_peers_activated}</div>
        </div>
        <div style="background:rgba(15,23,42,0.6); padding:8px; border-radius:6px; border:1px solid rgba(16,185,129,0.2); text-align:center;">
          <div style="font-size:0.65rem; color:#94a3b8;">Bounties Disbursed</div>
          <div style="font-size:1.1rem; font-weight:700; color:#10b981;">${stats.total_bounty_paid_ton} TON</div>
        </div>
      </div>
      <div style="margin-top:6px; font-size:0.7rem; color:#94a3b8;">
        <strong>Top Viral Node Operators:</strong>
        ${stats.top_referrers.length ? stats.top_referrers.map(r => `
          <div style="display:flex; justify-content:space-between; margin-top:2px; font-family:monospace; color:#cbd5e1;">
            <span>${r.referrer_wallet.slice(0, 8)}...</span>
            <span style="color:#10b981;">${r.total_earned} TON (${r.count} peers)</span>
          </div>
        `).join('') : '<div style="margin-top:2px; color:#64748b;">No referral activations yet. Share your link!</div>'}
      </div>
    `;
  } catch (err) {
    console.error('Failed to load viral protocol stats:', err);
  }
}

async function generatePeerInvite() {
  const select = document.getElementById('viral-bot-select');
  const output = document.getElementById('viral-invite-output');
  if (!select || !output) return;
  const botId = select.value;
  const bot = personas.find(p => p.id === botId) || personas[0];
  if (!bot) return;

  try {
    const res = await fetch(apiUrl('/api/viral/invite'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        persona_id: bot.id,
        wallet_address: bot.wallet_address
      })
    });
    const data = await res.json();
    output.style.display = 'block';
    output.innerHTML = `
      <div style="background:rgba(14,165,233,0.1); border:1px solid #0ea5e9; border-radius:6px; padding:6px; color:#e0f2fe;">
        <strong>🎉 Signed Invite Ready:</strong><br>
        <span style="color:#38bdf8; font-family:monospace; word-break:break-all;">${data.deep_link}</span>
        <div style="margin-top:4px; font-size:0.65rem; color:#94a3b8;">Signature: ${data.signature.slice(0, 16)}... | Bounty: +${data.bounty_ton} TON</div>
      </div>
    `;
    renderViralProtocol();
  } catch (err) {
    console.error('Failed to generate invite:', err);
  }
}

// --- Universal AI Democratization Telemetry & Donation ---
async function renderDemocratization() {
  const container = document.getElementById('democratize-status-container');
  if (!container) return;
  try {
    const res = await fetch(apiUrl('/api/democratization/status'));
    const data = await res.json();
    const pool = data.public_compute_pool || {};
    
    // User grant
    const grantRes = await fetch(apiUrl('/api/democratization/grant/local_citizen'));
    const grant = await grantRes.json();

    container.innerHTML = `
      <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:8px; padding:10px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#10b981; font-size:0.8rem;">Your Citizen Status: ${grant.tier}</strong>
          <span style="background:#064e3b; color:#a7f3d0; padding:2px 6px; border-radius:4px; font-size:0.65rem; font-weight:700;">FREE ACCESS</span>
        </div>
        <div style="margin-top:6px; font-size:0.72rem; color:#cbd5e1;">
          Daily Queries Remaining: <strong style="color:#38bdf8; font-size:1.0rem;">${grant.remaining_free_queries}</strong> / 100
        </div>
        <div style="font-size:0.65rem; color:#94a3b8; margin-top:2px;">
          Resets every 24h at midnight UTC. Zero fees. Zero corporate surveillance.
        </div>
      </div>

      <div style="background:rgba(15,23,42,0.6); border:1px solid rgba(56,189,248,0.2); border-radius:8px; padding:8px; margin-top:4px;">
        <strong style="color:#38bdf8; font-size:0.75rem;">Global Public Compute Pool:</strong>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:4px; text-align:center;">
          <div style="background:rgba(0,0,0,0.2); padding:4px; border-radius:4px;">
            <div style="font-size:0.62rem; color:#94a3b8;">Donated Capacity</div>
            <div style="font-size:0.9rem; font-weight:700; color:#10b981;">${pool.total_donated_teraflops || 0} TFLOPS</div>
          </div>
          <div style="background:rgba(0,0,0,0.2); padding:4px; border-radius:4px;">
            <div style="font-size:0.62rem; color:#94a3b8;">Free Queries Served</div>
            <div style="font-size:0.9rem; font-weight:700; color:#38bdf8;">${pool.queries_served_free || 0}</div>
          </div>
        </div>
        <div style="font-size:0.65rem; color:#94a3b8; margin-top:4px; text-align:center;">
          Active Donor Nodes: <strong>${pool.active_donor_nodes || 0}</strong> across sovereign P2P mesh
        </div>
      </div>
    `;
  } catch (err) {
    console.error('Failed to load democratization telemetry:', err);
  }
}

async function handleDonateCompute() {
  const input = document.getElementById('donate-tflops-input');
  if (!input) return;
  const tflops = parseFloat(input.value) || 25.0;

  try {
    const res = await fetch(apiUrl('/api/democratization/donate'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        donor_node_id: `node_supporter_${Math.floor(Math.random()*1000)}`,
        teraflops: tflops
      })
    });
    if (res.ok) {
      alert(`🎉 Thank you! Contributed ${tflops} TFLOPS to the Universal Free Citizen pool.`);
      renderDemocratization();
    }
  } catch (err) {
    console.error('Failed to donate compute:', err);
  }
}

async function handleBlockHexAddress() {
  const input = document.getElementById('block-hex-input');
  if (!input || !input.value.trim()) return;
  const hexAddr = input.value.trim();

  try {
    const res = await fetch(apiUrl('/api/security/peerblock/block-hex'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hex_address: hexAddr })
    });
    if (res.ok) {
      alert(`🚫 Address ${hexAddr} added to Sovereign PeerBlock list. All UDP datagrams and turns from this hex address will be dropped.`);
      input.value = '';
      renderShield();
    }
  } catch (err) {
    console.error('Failed to block hex address:', err);
  }
}

// --- Democratic SETI@Home-Style Sharded LLM Telemetry ---
async function renderSharding() {
  const metricsContainer = document.getElementById('sharding-metrics-container');
  const gridContainer = document.getElementById('sharding-grid-container');
  const badge = document.getElementById('sharding-assembly-badge');
  const activationsLog = document.getElementById('sharding-activations-log');
  if (!metricsContainer || !gridContainer) return;

    try {
    const [topoRes, elasticRes] = await Promise.all([
      fetch(apiUrl('/api/sharding/topology')),
      fetch(apiUrl('/api/sharding/elastic')),
    ]);
    if (!topoRes.ok) return;
    const data = await topoRes.json();
    const topology = data.cluster_topology || {};
    const elastic = elasticRes.ok ? await elasticRes.json() : null;

    if (badge) {
      if (topology.is_fully_assembled) {
        badge.style.background = '#064e3b';
        badge.style.color = '#a7f3d0';
        badge.innerText = `100% ASSEMBLED (${topology.coverage_percentage}%)`;
      } else {
        badge.style.background = '#78350f';
        badge.style.color = '#fde68a';
        badge.innerText = `PARTIAL (${topology.coverage_percentage}%)`;
      }
    }

    const totalN = (topology.total_slices || topology.total_model_slices || 16);
    const hostedNow = (data.local_slices || []).length;
    const el = elastic ? elastic.elastic : null;
    const ceiling = el ? el.elastic_ceiling : Math.ceil((topology.max_storage_cap_mb || 256) / 24);

    metricsContainer.innerHTML = `
      <div style="background:rgba(168,85,247,0.1); border:1px solid rgba(168,85,247,0.3); border-radius:8px; padding:10px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#c084fc; font-size:0.8rem;">Local Node Stripes Hosted:</strong>
          <span style="font-weight:700; color:#38bdf8; font-size:0.75rem;">${hostedNow} / ${totalN} Stripes</span>
        </div>
        <div style="font-size:0.65rem; color:#94a3b8; margin-top:4px;">Model: <code style="color:#cbd5e1;">${topology.model_id || 'shill-mind-v1'}</code> | Stripe: ${topology.target_shard_mb || 24}MB | Repl x${topology.replication_factor || 3} | Parity ${topology.parity_covered ?? 0}/${topology.parity_total ?? 0}</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:6px; font-size:0.7rem;">
          <div style="background:rgba(0,0,0,0.25); padding:6px; border-radius:4px;">
            <div style="color:#94a3b8;">Local Footprint</div>
            <div style="font-size:0.88rem; font-weight:700; color:#34d399;">${data.local_storage_used_mb ?? topology.local_storage_used_mb ?? 0} MB <span style="font-size:0.65rem; color:#64748b;">(cap ${topology.max_storage_cap_mb ?? 64}MB)</span></div>
            ${el ? `<div style="font-size:0.6rem; color:#6366f1; margin-top:2px;">Eligible to grow: ${hostedNow} -> ${ceiling} stripes on demand</div>` : ''}
          </div>
          <div style="background:rgba(0,0,0,0.25); padding:6px; border-radius:4px;">
            <div style="color:#94a3b8;">Hive Redundancy</div>
            <div style="font-size:0.88rem; font-weight:700; color:#c084fc;">${topology.redundancy_factor || 1.0}x Mean</div>
          </div>
        </div>
        <div style="font-size:0.65rem; color:#94a3b8; margin-top:6px;">
          Node ID: <code style="color:#cbd5e1;">${data.node_id}</code> | Free Citizen Slicing Active${el ? ` | Elastic: ${el.elastic_enabled ? 'ON' : 'OFF'} | Autohost: ${el.autohost_on_demand ? 'ON' : 'OFF'}` : ''}
        </div>
      </div>
    `;

    // Render Stripe Grid (cap visual at 256 cells for huge N)
    gridContainer.innerHTML = '';
    const activeSliceSet = new Set(topology.active_slices || topology.covered_slices || []);
    const localSliceSet = new Set((data.local_slices || []).map(s => s.slice_index));
    const renderN = Math.min(totalN, 256);

    for (let i = 0; i < renderN; i++) {
      const isHostedLocally = localSliceSet.has(i);
      const isOnlineInHive = activeSliceSet.has(i);
      const card = document.createElement('div');
      
      let border = 'rgba(148,163,184,0.2)';
      let bg = 'rgba(15,23,42,0.6)';
      let titleColor = '#94a3b8';
      let statusText = 'Offline';

      if (isHostedLocally) {
        border = '#a855f7';
        bg = 'rgba(168,85,247,0.2)';
        titleColor = '#e9d5ff';
        statusText = 'Local Node';
      } else if (isOnlineInHive) {
        border = '#0284c7';
        bg = 'rgba(2,132,199,0.15)';
        titleColor = '#38bdf8';
        statusText = 'P2P Mesh';
      }

      card.style.cssText = `background:${bg}; border:1px solid ${border}; border-radius:6px; padding:6px; text-align:center; font-size:0.65rem;`;
      card.innerHTML = `
        <div style="font-weight:700; color:${titleColor};">#${i}</div>
        <div style="font-size:0.58rem; margin-top:2px; color:${isHostedLocally ? '#34d399' : (isOnlineInHive ? '#38bdf8' : '#64748b')}; font-weight:600;">
          ${statusText}
        </div>
      `;
      gridContainer.appendChild(card);
    }

    // Activations log
    if (activationsLog) {
      const cov = topology.covered_slice_count ?? activeSliceSet.size ?? 0;
      activationsLog.innerHTML = `
        <div style="background:rgba(0,0,0,0.2); padding:4px 6px; border-radius:4px; border-left:3px solid #10b981;">
          ✓ Distributed forward pipeline verified: ${cov}/${totalN} stripes routed over UDP port 9999.${totalN > 256 ? ` (grid shows first 256)` : ''}
        </div>
        <div style="background:rgba(0,0,0,0.2); padding:4px 6px; border-radius:4px; border-left:3px solid #a855f7;">
          ⚡ Zero single-point of failure: weights assembled peer-to-peer on demand.
        </div>
      `;
    }
  } catch (err) {
    console.error('Failed to render SETI sharding telemetry:', err);
  }
}


/* ============ BOTS ROSTER (opt-in / rotation / auto-spawn) ============ */
async function renderRoster() {
  const container = document.getElementById('bots-roster-container');
  if (!container) return;
  try {
    const res = await fetch(apiUrl('/api/personas/roster'));
    const data = await res.json();
    const roster = Array.isArray(data) ? data : (data.roster || []);
    const capEl = document.getElementById('bots-spawn-cap');
    if (capEl && data && data.spawn_cap != null) {
      capEl.textContent = `${data.spawned_count || 0} / ${data.spawn_cap} spawned`;
    }
    container.innerHTML = '';
    roster.forEach(bot => {
      const item = document.createElement('div');
      item.className = 'roster-item';
      const statusCls = bot.opted_in
        ? (bot.is_resting ? 'roster-resting' : 'roster-active')
        : 'roster-pending';
      const statusTxt = bot.opted_in
        ? (bot.is_resting ? 'RESTING (rotated out)' : (bot.times_spoken ? `ACTIVE · ${bot.times_spoken} turns` : 'ACTIVE · ready'))
        : 'AWAITING YOUR OPT-IN';
      item.innerHTML = `
        <div class="roster-head">
          <strong>${bot.avatar} ${bot.name} <span style="color:var(--tg-meta); font-weight:400;">· ${bot.role_type}</span></strong>
          <span class="roster-status ${statusCls}">${statusTxt}</span>
        </div>
        <div style="color:var(--tg-meta); font-size:0.7rem; margin-bottom:6px;">${bot.opted_in ? (bot.last_spoke_ago_sec != null ? 'Last spoke ' + Math.round(bot.last_spoke_ago_sec) + 's ago' : 'Has not spoken yet') : 'No bot speaks until you enable it.'}</div>
      `;
      const btn = document.createElement('button');
      btn.className = 'roster-toggle';
      btn.style.background = bot.opted_in ? 'var(--alert-red)' : 'var(--tg-green)';
      btn.textContent = bot.opted_in ? 'Opt Out' : 'Opt In';
      btn.onclick = async () => {
        await fetch(apiUrl(`/api/personas/${bot.persona_id}/participation`), {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ participate: !bot.opted_in })
        });
        renderRoster();
      };
      item.appendChild(btn);
      container.appendChild(item);
    });
  } catch (err) {
    container.innerHTML = '<div style="color:var(--alert-red); font-size:0.75rem;">Failed to load roster.</div>';
  }
}

async function handleAutoSpawn() {
  const res = await fetch(apiUrl('/api/personas/auto-spawn'), {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({})
  });
  const data = await res.json();
  if (res.ok) {
    alert(data.spawned.length
      ? `Spawned: ${data.spawned.map(b => b.name).join(', ')} (pending your opt-in)`
      : 'No spawn needed — roster is healthy.');
    renderRoster();
  } else {
    alert(`Auto-spawn failed: ${data.detail || 'unknown error'}`);
  }
}

/* ============ NETWORK VISUALIZER (dependency-free, resolution-independent canvas) ============ */
let netAnimId = null;
let netState = { nodes: [], edges: [], me: null, lastFetch: 0, w: 0, h: 0, summary: '' };
let netResizeBound = false;

/**
 * Compute node coordinates from the CURRENT canvas box, so the map fills whatever
 * space it is given instead of assuming a fixed 800x420 frame.
 */
function layoutNetworkNodes(w, h) {
  const peersArr = netState.peers || [];
  const cx = w / 2;
  const cy = h / 2;
  const spread = Math.min(w, h * 1.35);
  const R = Math.max(70, Math.min(spread * 0.34, 260));

  const nodes = peersArr.map((p, i) => {
    const ang = (i / Math.max(1, peersArr.length)) * Math.PI * 2 - Math.PI / 2;
    const jitter = ((i * 37) % 40) - 20;
    return {
      id: p.node_id || p.peer_endpoint || ('peer-' + i),
      x: cx + Math.cos(ang) * (R + jitter),
      y: cy + Math.sin(ang) * (R * 0.62 + jitter * 0.5),
      r: 9,
      color: '#38bdf8',
      label: p.node_id || p.peer_endpoint,
      latency: p.latency_ms || 0
    };
  });

  // Local node always anchored at centre
  nodes.unshift({ id: '_self', x: cx, y: cy, r: 13, color: '#4fae4e', label: netState.nodeLabel || 'this node', self: true });

  // Star (self -> every peer) plus a peer ring so the mesh reads as a mesh
  const edges = [];
  for (let i = 1; i < nodes.length; i++) edges.push({ from: 0, to: i });
  for (let i = 1; i < nodes.length; i++) edges.push({ from: i, to: 1 + (i % Math.max(1, nodes.length - 1)) });

  netState.nodes = nodes;
  netState.edges = edges;
  netState.me = nodes[0];
  netState.w = w;
  netState.h = h;
}

async function fetchNetworkData() {
  try {
    const [peersRes, topoRes] = await Promise.all([
      fetch(apiUrl('/api/p2p/peers')),
      fetch(apiUrl('/api/sharding/topology'))
    ]);
    const peers = await peersRes.json();
    const topo = await topoRes.json();
    const peersArr = Array.isArray(peers) ? peers : (peers.peers || []);

    const localSlices = (topo.local_slices || []).length;
    const totalN = topo.cluster_topology?.total_slices || 16;

    netState.peers = peersArr;
    netState.nodeLabel = topo.node_id || 'this node';
    netState.lastFetch = Date.now();
    netState.summary = `${peersArr.length} peer${peersArr.length === 1 ? '' : 's'} · ${localSlices}/${totalN} model shards hosted locally`;

    const stat = document.getElementById('net-stage-stat');
    if (stat) stat.textContent = netState.summary;

    layoutNetworkNodes(netState.w || 800, netState.h || 420);
  } catch (err) {
    console.error('Network fetch failed:', err);
    const stat = document.getElementById('net-stage-stat');
    if (stat) stat.textContent = 'Mesh unavailable — retrying…';
  }
}

function drawNetworkFrame(ts) {
  const canvas = document.getElementById('network-canvas');
  if (!canvas) { netAnimId = null; return; }
  const wrap = document.getElementById('network-canvas-wrap');

  // Keep the backing store matched to the visible box (crisp on any window size),
  // and re-layout node coordinates whenever the box changes.
  const cssW = Math.max(240, Math.floor((wrap ? wrap.clientWidth : canvas.clientWidth) || 800));
  const cssH = Math.max(220, Math.floor((wrap ? wrap.clientHeight : 420) || 420));
  const dpr = Math.min(window.devicePixelRatio || 1, 2);

  if (canvas.width !== Math.floor(cssW * dpr) || canvas.height !== Math.floor(cssH * dpr)) {
    canvas.width = Math.floor(cssW * dpr);
    canvas.height = Math.floor(cssH * dpr);
    layoutNetworkNodes(cssW, cssH);
  }

  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);

  // Ambient centre glow so the empty state never looks like a broken void
  const halo = ctx.createRadialGradient(cssW / 2, cssH / 2, 0, cssW / 2, cssH / 2, Math.min(cssW, cssH) * 0.62);
  halo.addColorStop(0, 'rgba(56,189,248,0.05)');
  halo.addColorStop(1, 'transparent');
  ctx.fillStyle = halo;
  ctx.fillRect(0, 0, cssW, cssH);

  // Edges with moving packet dots
  netState.edges.forEach((e, ei) => {
    const a = netState.nodes[e.from], b = netState.nodes[e.to];
    if (!a || !b) return;
    ctx.strokeStyle = 'rgba(56,189,248,0.25)'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    const t = ((ts / 900) + ei * 0.13) % 1;
    const px = a.x + (b.x - a.x) * t, py = a.y + (b.y - a.y) * t;
    ctx.fillStyle = 'rgba(52,211,153,0.9)';
    ctx.beginPath(); ctx.arc(px, py, 2.4, 0, Math.PI * 2); ctx.fill();
  });

  // Nodes with pulse
  netState.nodes.forEach((n, i) => {
    const pulse = n.self ? 1 + Math.sin(ts / 400) * 0.12 : 1 + Math.sin(ts / 700 + i) * 0.08;
    const r = n.r * pulse;
    const glow = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r * 2.6);
    glow.addColorStop(0, n.color + 'aa'); glow.addColorStop(1, 'transparent');
    ctx.fillStyle = glow;
    ctx.beginPath(); ctx.arc(n.x, n.y, r * 2.6, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = n.color;
    ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = n.self ? '#86efac' : '#94a3b8';
    ctx.font = `${n.self ? 'bold ' : ''}11px monospace`; ctx.textAlign = 'center';
    ctx.fillText((n.label || '').slice(0, 26), n.x, n.y + r + 14);
  });

  // Friendly empty-state guidance instead of a blank canvas
  if (!netState.nodes.length) {
    ctx.fillStyle = '#64748b'; ctx.font = '13px monospace'; ctx.textAlign = 'center';
    ctx.fillText('Waiting for the UDP mesh — beacons arrive every 4s…', cssW / 2, cssH / 2);
  }

  // Summary line
  if (netState.summary) {
    ctx.fillStyle = '#64748b'; ctx.font = '11px monospace'; ctx.textAlign = 'left';
    ctx.fillText(netState.summary, 12, cssH - 12);
  }

  // Refresh data every 5s
  if (Date.now() - netState.lastFetch > 5000) fetchNetworkData();
  netAnimId = requestAnimationFrame(drawNetworkFrame);
}

function startNetworkVisualizer() {
  const canvas = document.getElementById('network-canvas');
  if (!canvas) return;

  // Size + lay out from the real container box before the first frame.
  const wrap = document.getElementById('network-canvas-wrap');
  const w = Math.max(240, Math.floor((wrap ? wrap.clientWidth : canvas.clientWidth) || 800));
  const h = Math.max(220, Math.floor((wrap ? wrap.clientHeight : 420) || 420));
  layoutNetworkNodes(w, h);

  if (!netResizeBound) {
    netResizeBound = true;
    window.addEventListener('resize', () => {
      if (netAnimId) layoutNetworkNodes(netState.w || w, netState.h || h);
    });
  }

  if (!netAnimId) {
    fetchNetworkData().then(() => { netAnimId = requestAnimationFrame(drawNetworkFrame); });
  }
}

function stopNetworkVisualizer() {
  if (netAnimId) { cancelAnimationFrame(netAnimId); netAnimId = null; }
}

// ==========================================
// HELP MODAL & FAQ CONTROLLERS
// ==========================================

function openHelpModal() {
  const modal = document.getElementById('help-modal');
  if (modal) {
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }
}

function closeHelpModal() {
  const modal = document.getElementById('help-modal');
  if (modal) {
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
}

function switchHelpTab(tabKey, clickedBtn) {
  // Hide all help tabs
  const tabs = document.querySelectorAll('.help-tab-content');
  tabs.forEach(t => t.style.display = 'none');

  // Show active help tab
  const activeTab = document.getElementById(`help-tab-${tabKey}`);
  if (activeTab) {
    activeTab.style.display = 'block';
  }

  // Update active button state
  const buttons = document.querySelectorAll('.help-tab-btn');
  buttons.forEach(b => b.classList.remove('active'));
  if (clickedBtn) {
    clickedBtn.classList.add('active');
  }
}

function toggleFaq(faqItemEl) {
  if (!faqItemEl) return;
  const isExpanded = faqItemEl.classList.contains('expanded');
  // Optional: collapse all other items for accordion feel
  const allItems = document.querySelectorAll('.help-faq-item');
  allItems.forEach(item => item.classList.remove('expanded'));
  if (!isExpanded) {
    faqItemEl.classList.add('expanded');
  }
}

// Close help modal on backdrop click
window.addEventListener('click', (e) => {
  const modal = document.getElementById('help-modal');
  if (modal && e.target === modal) {
    closeHelpModal();
  }
});
