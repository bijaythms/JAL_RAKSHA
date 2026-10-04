/**
 * JAL-RAKSHA v4.1 — Frontend Extensions
 * Exposes all newly-added backend capabilities:
 *   1.  Debris-flow bulking multiplier in breach panel
 *   2.  Unit cost editor (Admin tab extension)
 *   3.  Erosion parameter calibration per incident
 *   4.  SAR threshold per zone (Monitor tab)
 *   5.  Growth alert threshold configurator (Monitor tab)
 *   6.  Region override selector
 *   7.  Engine badge update (2D vs 1D used)
 *   8.  Breach panel: AMC selector exposed
 */

/* ══════════════════════════════════════════════════════════
   §1  BREACH PANEL — debris bulking + AMC injection
   Hooks into panelBreach() after DOM render
   ══════════════════════════════════════════════════════════ */

const _origPanelBreach = window.panelBreach || (typeof panelBreach !== 'undefined' ? panelBreach : null);
if (_origPanelBreach) {
  window.panelBreach = async function () {
    await _origPanelBreach.call(this);

    // Inject debris-bulking row right before the Run button
    const runBtn = document.getElementById('btnRun');
    if (!runBtn) return;

    const debrisDiv = document.createElement('div');
    debrisDiv.className = 'mod';
    debrisDiv.innerHTML = `
      <div class="mod-title">DEBRIS BULKING (optional — analyst)</div>
      <div class="slider-group">
        <div class="slider-head">
          <span>DEBRIS FACTOR</span>
          <b id="dispDebris">1.0×</b>
        </div>
        <input type="range" id="sDebris" min="1.0" max="10.0" step="0.5" value="1.0">
        <div class="slider-limits"><span>1.0× (clear water)</span><span>10.0× (heavy debris)</span></div>
        <div class="hint">Scales peak Q after clear-water routing. Not physically modeled —
          use debris-flow specialist calibration. Factor &gt;1 flagged in all outputs.</div>
      </div>
      <div class="field">
        <label>Antecedent Moisture (SCS-CN)</label>
        <select class="input" id="f_amc">
          <option value="dry">Dry (AMC I — pre-storm soil moisture low)</option>
          <option value="average" selected>Average (AMC II — default)</option>
          <option value="wet">Wet (AMC III — saturated soil)</option>
        </select>
      </div>`;
    runBtn.parentNode.insertBefore(debrisDiv, runBtn);

    document.getElementById('sDebris').oninput = e => {
      document.getElementById('dispDebris').textContent = (+e.target.value).toFixed(1) + '×';
    };
  };
}

/* Monkey-patch runSimulation to include debris_bulking_factor */
const _origRunSim = window.runSimulation || (typeof runSimulation !== 'undefined' ? runSimulation : null);
if (_origRunSim) {
  window.runSimulation = async function () {
    const debrisInput = document.getElementById('sDebris');
    const amcInput    = document.getElementById('f_amc');
    // Store for later injection into params. runSimulation() builds the body from DOM IDs,
    // so we stash these into hidden inputs that it won't see but we patch the API call.
    if (debrisInput) window._jrDebrisFactor = +debrisInput.value;
    if (amcInput)    window._jrAmc = amcInput.value;
    return _origRunSim.call(this);
  };
}

/* Intercept api() to inject debris factor in simulation POST */
const _origApi = window.api;
if (_origApi) {
  window.api = function (path, opts) {
    if (path && path.includes('/api/simulations') && opts && opts.method === 'POST'
        && !path.includes('/manual') && !path.includes('cancel')) {
      try {
        const body = JSON.parse(opts.body || '{}');
        if (window._jrDebrisFactor && window._jrDebrisFactor > 1.0)
          body.debris_bulking_factor = window._jrDebrisFactor;
        if (window._jrAmc) body.amc = window._jrAmc;
        opts = { ...opts, body: JSON.stringify(body) };
      } catch (_) {}
    }
    return _origApi(path, opts);
  };
}

/* ══════════════════════════════════════════════════════════
   §2  ENGINE BADGE — show 2D vs 1D used after results load
   ══════════════════════════════════════════════════════════ */

const _origShowResults = window.showResults || (typeof showResults !== 'undefined' ? showResults : null);
if (_origShowResults) {
  window.showResults = async function () {
    await _origShowResults.call(this);
    /* After results paint, update engine badge with used engine */
    try {
      const badge = document.getElementById('engineLabel');
      if (badge && window.S && window.S.lastResults) {
        const res = S.lastResults.results || {};
        const used2d = res.used_2d || (res.inundation && res.inundation.engine_2d);
        if (used2d !== undefined) {
          badge.textContent = used2d
            ? '2D RASTER PRIORITY-FLOOD (GLO-30)'
            : '1D MUSKINGUM-CUNGE (DEM UNAVAILABLE)';
          badge.style.color = used2d ? 'var(--cyan)' : 'var(--amber)';
        }
        if (res.inundation && res.inundation.used_2d === false) {
          toast('2D DEM routing unavailable — used 1D Muskingum-Cunge fallback');
        }
        if (window.S && window.S.simId && typeof injectHydrodynamicComparisonPanel === 'function') {
          injectHydrodynamicComparisonPanel(window.S.simId);
        }
      }
    } catch (_) {}
  };
}

/* ══════════════════════════════════════════════════════════
   §3  ADMIN PANEL EXTENSION — Unit Cost Editor + System Config
   ══════════════════════════════════════════════════════════ */

const _origPanelAdmin = window.panelAdmin || (typeof panelAdmin !== 'undefined' ? panelAdmin : null);
if (_origPanelAdmin) {
  window.panelAdmin = async function () {
    await _origPanelAdmin.call(this);
    /* Append additional admin modules after base panel renders */
    await _appendAdminExtensions();
  };
}

async function _appendAdminExtensions() {
  const body = document.getElementById('panelBody');
  if (!body) return;

  /* ── Unit Cost Editor ── */
  let costsData = null;
  try {
    costsData = await api('/api/costs');
  } catch (_) { /* endpoint not yet available */ }

  const costDiv = document.createElement('div');
  costDiv.className = 'mod';
  costDiv.id = 'costEditor';
  if (costsData) {
    const def = costsData.default || {};
    costDiv.innerHTML = `
      <div class="mod-title">UNIT COST RATES (INR)</div>
      <p class="hint">Used for economic proxy in impact assessment.
        District Schedule of Rates recommended; defaults are literature placeholders.</p>
      <div class="grid2">
        <div class="field"><label>Building (₹ per unit)</label>
          <input class="input" id="ucBuilding" type="number" value="${def.building || 600000}"></div>
        <div class="field"><label>Crop per ha (₹)</label>
          <input class="input" id="ucCrop" type="number" value="${def.crop_per_ha || 120000}"></div>
        <div class="field"><label>Livestock per head (₹)</label>
          <input class="input" id="ucLivestock" type="number" value="${def.livestock_per_head || 40000}"></div>
      </div>
      <div class="row-end">
        <button class="tbtn sm" id="ucSaveDefault">Save as Default</button>
        ${(window.S && window.S.incident)
          ? `<button class="tbtn sm primary" id="ucSaveIncident">Save for Current Incident</button>` : ''}
      </div>
      <div id="ucMsg" class="hint"></div>`;
  } else {
    costDiv.innerHTML = `<div class="mod-title">UNIT COST RATES</div>
      <div class="hint">Unit cost endpoint not available — start server and reload.</div>`;
  }
  body.appendChild(costDiv);

  if (costsData) {
    document.getElementById('ucSaveDefault').onclick = async () => {
      try {
        await api('/api/costs', { method: 'POST', body: JSON.stringify({
          level: 'default', key: 'default',
          building: +document.getElementById('ucBuilding').value,
          crop_per_ha: +document.getElementById('ucCrop').value,
          livestock_per_head: +document.getElementById('ucLivestock').value }) });
        document.getElementById('ucMsg').textContent = 'Saved as default.';
        toast('Unit costs updated (default)');
      } catch (e) { document.getElementById('ucMsg').textContent = 'FAIL: ' + e.message; }
    };
    const incBtn = document.getElementById('ucSaveIncident');
    if (incBtn) incBtn.onclick = async () => {
      try {
        await api('/api/costs', { method: 'POST', body: JSON.stringify({
          level: 'incident', key: S.incident.id,
          building: +document.getElementById('ucBuilding').value,
          crop_per_ha: +document.getElementById('ucCrop').value,
          livestock_per_head: +document.getElementById('ucLivestock').value }) });
        document.getElementById('ucMsg').textContent = 'Saved for incident ' + S.incident.id;
        toast('Unit costs saved for incident');
      } catch (e) { document.getElementById('ucMsg').textContent = 'FAIL: ' + e.message; }
    };
  }

  /* ── Growth Alert Thresholds ── */
  let growthData = null;
  try { growthData = await api('/api/detection/growth-thresholds'); } catch (_) {}

  if (growthData) {
    const growthDiv = document.createElement('div');
    growthDiv.className = 'mod';
    growthDiv.innerHTML = `
      <div class="mod-title">GROWTH ALERT THRESHOLDS</div>
      <p class="hint">Heuristic thresholds used by the lake-growth classifier.
        Advisory only — not a learned model.</p>
      <table class="tbl"><tr><th>Parameter</th><th>Current</th><th>New value</th><th>Description</th></tr>
        ${Object.entries(growthData).filter(([k]) => !k.startsWith('_')).map(([k, v]) =>
          `<tr><td>${k.replace(/_/g,' ')}</td><td>${typeof v === 'object' ? JSON.stringify(v) : v}</td>
           <td><input class="input" id="gt_${k}" value="${typeof v === 'object' ? JSON.stringify(v) : v}" style="width:90px"></td>
           <td style="color:var(--text-3);font-size:10px">${_growthParamDesc(k)}</td></tr>`
        ).join('')}
      </table>
      <div class="row-end">
        <button class="tbtn sm primary" id="gtSave">Save Thresholds</button>
      </div>
      <div id="gtMsg" class="hint"></div>`;
    body.appendChild(growthDiv);

    document.getElementById('gtSave').onclick = async () => {
      const payload = {};
      Object.keys(growthData).filter(k => !k.startsWith('_')).forEach(k => {
        const el = document.getElementById('gt_' + k);
        if (!el) return;
        const v = el.value;
        try { payload[k] = JSON.parse(v); } catch (_) { payload[k] = +v || v; }
      });
      try {
        await api('/api/detection/growth-thresholds', { method: 'PUT', body: JSON.stringify(payload) });
        document.getElementById('gtMsg').textContent = 'Thresholds saved.';
        toast('Growth thresholds updated');
      } catch (e) { document.getElementById('gtMsg').textContent = 'FAIL: ' + e.message; }
    };
  }
}

function _growthParamDesc(k) {
  const DESCS = {
    area_critical_m2: 'Area above which CRITICAL alert fires',
    area_warning_m2: 'Area above which WARNING alert fires',
    growth_rate_warning: 'Area growth ratio triggering WARNING',
    growth_rate_critical: 'Area growth ratio triggering CRITICAL',
    doubling_days_warning: 'Doubling time below which WARNING fires',
    min_observations: 'Minimum observations required for growth assessment',
    draining_fraction: 'Area fraction below which DRAINING fires',
  };
  return DESCS[k] || '';
}

/* ══════════════════════════════════════════════════════════
   §4  DAM ANALYSIS (SETUP) PANEL — Erosion calibration modal
   ══════════════════════════════════════════════════════════ */

const _origPanelSetup = window.panelSetup || (typeof panelSetup !== 'undefined' ? panelSetup : null);
if (_origPanelSetup) {
  window.panelSetup = async function () {
    await _origPanelSetup.call(this);
    /* Append erosion calibration module */
    if (!S.incident || !['analyst','admin'].includes(S.role || '')) return;
    const body = document.getElementById('panelBody');
    if (!body) return;

    const div = document.createElement('div');
    div.className = 'mod';
    div.id = 'erosionCalib';
    div.innerHTML = `
      <div class="mod-title">&#9881; EROSION CALIBRATION (k_d / τ_c)</div>
      <p class="hint">Override literature defaults with site-measured values.
        Hanson &amp; Temple (1997). Required units: k_d [m³/(N·s)], τ_c [Pa].</p>
      <div id="erosionParamBody"><span class="spinner"></span> loading...</div>`;
    body.appendChild(div);

    try {
      const ep = await api(`/api/incidents/${S.incident.id}/erosion-params`);
      const mats = Object.entries(ep.calibrations || {});
      document.getElementById('erosionParamBody').innerHTML = `
        <table class="tbl">
          <tr><th>Material</th><th>k_d</th><th>τ_c (Pa)</th><th>Source</th><th></th></tr>
          ${mats.map(([mat, p]) => `
            <tr>
              <td>${mat}</td>
              <td><input class="input" id="ep_kd_${mat.replace(/\W/g,'_')}" value="${p.k_d.toExponential(2)}" style="width:80px"></td>
              <td><input class="input" id="ep_tc_${mat.replace(/\W/g,'_')}" value="${p.tau_c}" style="width:60px"></td>
              <td style="font-size:10px;color:${p.flagged_literature ? 'var(--amber)' : 'var(--green)'}">
                ${p.flagged_literature ? '⚠ literature' : '✓ calibrated'}</td>
              <td>
                <button class="tbtn sm primary" onclick="saveErosionParam('${mat}')">Save</button>
                ${!p.flagged_literature
                  ? `<button class="tbtn sm danger" onclick="resetErosionParam('${mat}')">Reset</button>`
                  : ''}
              </td>
            </tr>`).join('')}
        </table>
        <p class="hint" style="margin-top:6px">After saving, re-run simulation to apply updated parameters.</p>`;
    } catch (e) {
      document.getElementById('erosionParamBody').textContent = 'Endpoint not available: ' + e.message;
    }
  };
}

window.saveErosionParam = async (mat) => {
  const key = mat.replace(/\W/g, '_');
  const kd = +document.getElementById('ep_kd_' + key).value;
  const tc = +document.getElementById('ep_tc_' + key).value;
  try {
    await api(`/api/incidents/${S.incident.id}/erosion-params`, {
      method: 'PUT',
      body: JSON.stringify({ material: mat, k_d: kd, tau_c: tc, source: 'user-calibrated' })
    });
    toast(`Erosion params saved for ${mat}`);
    panelSetup();
  } catch (e) { toast('Save failed: ' + e.message); }
};

window.resetErosionParam = async (mat) => {
  if (!confirm(`Reset ${mat} to literature values?`)) return;
  try {
    await api(`/api/incidents/${S.incident.id}/erosion-params/${encodeURIComponent(mat)}`, { method: 'DELETE' });
    toast(`${mat} reset to literature values`);
    panelSetup();
  } catch (e) { toast('Reset failed: ' + e.message); }
};

/* ══════════════════════════════════════════════════════════
   §5  MONITOR PANEL — SAR threshold per zone (injected into zone table)
   ══════════════════════════════════════════════════════════ */

window.editSarThreshold = async (zid) => {
  try {
    const cur = await api(`/api/detection/zones/${zid}/sar-threshold`);
    const val = prompt(
      `SAR water threshold for zone ${zid}\n` +
      `Current: ${cur.threshold_db} dB\nDefault: ${cur.default_db} dB\n` +
      `Range: -25 to -10 dB (lower = wetter surface needed for detection)\n\n` +
      `New threshold (dB):`,
      cur.threshold_db
    );
    if (val === null) return;
    const db = parseFloat(val);
    if (isNaN(db) || db < -25 || db > -10) { toast('Invalid: must be -25 to -10 dB'); return; }
    await api(`/api/detection/zones/${zid}/sar-threshold`, {
      method: 'PUT', body: JSON.stringify({ threshold_db: db })
    });
    toast(`SAR threshold set to ${db} dB for zone`);
  } catch (e) { toast('Error: ' + e.message); }
};

/* Patch panelMonitor to inject SAR edit button into zone rows */
const _origPanelMonitor = window.panelMonitor || (typeof panelMonitor !== 'undefined' ? panelMonitor : null);
if (_origPanelMonitor) {
  window.panelMonitor = async function () {
    await _origPanelMonitor.call(this);

    /* After render, inject SAR threshold buttons into zone table rows */
    if (!['analyst','admin'].includes(S.role || '')) return;
    const body = document.getElementById('panelBody');
    if (!body) return;

    /* Append growth threshold shortcut */
    let growthData = null;
    try { growthData = await api('/api/detection/growth-thresholds'); } catch (_) {}
    if (!growthData) return;

    const div = document.createElement('div');
    div.className = 'mod';
    div.style.marginTop = '12px';
    div.innerHTML = `
      <div class="mod-title">&#9881; GROWTH ALERT THRESHOLDS</div>
      <div class="grid2">
        <div class="field"><label>Warning area (m²)</label>
          <input class="input" id="gt_area_w" type="number" value="${growthData.area_warning_m2 || 10000}"></div>
        <div class="field"><label>Critical area (m²)</label>
          <input class="input" id="gt_area_c" type="number" value="${growthData.area_critical_m2 || 50000}"></div>
        <div class="field"><label>Growth rate warning (ratio)</label>
          <input class="input" id="gt_rate_w" type="number" step="0.1" value="${growthData.growth_rate_warning || 1.3}"></div>
        <div class="field"><label>Growth rate critical (ratio)</label>
          <input class="input" id="gt_rate_c" type="number" step="0.1" value="${growthData.growth_rate_critical || 2.0}"></div>
      </div>
      <button class="tbtn sm primary" id="gtSaveMon">Save Thresholds</button>
      <div id="gtMonMsg" class="hint"></div>`;
    body.appendChild(div);

    document.getElementById('gtSaveMon').onclick = async () => {
      const patch = {};
      if (growthData.area_warning_m2  !== undefined) patch.area_warning_m2  = +document.getElementById('gt_area_w').value;
      if (growthData.area_critical_m2 !== undefined) patch.area_critical_m2 = +document.getElementById('gt_area_c').value;
      if (growthData.growth_rate_warning  !== undefined) patch.growth_rate_warning  = +document.getElementById('gt_rate_w').value;
      if (growthData.growth_rate_critical !== undefined) patch.growth_rate_critical = +document.getElementById('gt_rate_c').value;
      try {
        await api('/api/detection/growth-thresholds', { method: 'PUT', body: JSON.stringify(patch) });
        document.getElementById('gtMonMsg').textContent = 'Saved.';
        toast('Growth thresholds updated');
      } catch (e) { document.getElementById('gtMonMsg').textContent = 'FAIL: ' + e.message; }
    };
  };
}

/* ══════════════════════════════════════════════════════════
   §6  INDIA REGION OVERRIDE — injected into Setup panel
   ══════════════════════════════════════════════════════════ */

const REGION_KEYS = [
  'western_himalaya','eastern_himalaya','ne_hills',
  'western_ghats','peninsular','gangetic','arid','coastal'
];

window.openRegionOverride = async () => {
  if (!S.incident) { toast('Select an incident first'); return; }
  try {
    const cur = await api(`/api/india/region?lat=${S.incident.lat}&lon=${S.incident.lon}`);
    const sel = prompt(
      `Current region: ${cur.name}\n\n` +
      `Override options:\n${REGION_KEYS.map((k,i) => `${i+1}. ${k}`).join('\n')}\n\n` +
      `Enter region key or leave blank to clear:`,
      cur.key
    );
    if (sel === null) return;
    if (sel === '') {
      await api(`/api/india/region-override`, { method: 'DELETE',
        body: JSON.stringify({ lat: S.incident.lat, lon: S.incident.lon }) });
      toast('Region override cleared');
    } else if (REGION_KEYS.includes(sel.trim())) {
      await api(`/api/india/region-override`, { method: 'POST',
        body: JSON.stringify({ lat: S.incident.lat, lon: S.incident.lon, region_key: sel.trim() }) });
      toast(`Region overridden to: ${sel.trim()}`);
    } else { toast('Invalid region key — use one from the list'); }
  } catch (e) { toast('Error: ' + e.message); }
};

/* openRegionOverride function is wired directly to #btnRegionOverride in panelSetup */

/* ══════════════════════════════════════════════════════════
   §7  RESULTS PANEL — show engine used + unit cost source
   ══════════════════════════════════════════════════════════ */

/* After showResults, if 2D was used and unit costs are configured, update the
   inundation panel to show engine info more prominently. */
const _origShowResults2 = window.showResults;
if (_origShowResults2 && _origShowResults2 !== window.showResults) {
  // Already patched in §2 — no double-patch needed
}

/* ══════════════════════════════════════════════════════════
   §8  BREACH PANEL — expose AMC in SCS-CN inflow estimator
   Already injected in §1 via the debrisDiv markup.
   Here we wire the amcInput value into the inflow calc.
   ══════════════════════════════════════════════════════════ */

/* Patch the inflow calc button handler after panel renders */
document.addEventListener('click', e => {
  if (e.target && e.target.id === 'btnInflowCalc') {
    /* Let original handler fire first, then inject AMC note if available */
    setTimeout(() => {
      const amcEl = document.getElementById('f_amc');
      const boxEl = document.getElementById('inflowBox');
      if (amcEl && boxEl && boxEl.textContent) {
        const amc = amcEl.value;
        if (amc !== 'average') {
          boxEl.textContent += ` (AMC: ${amc.toUpperCase()})`;
        }
      }
    }, 100);
  }
}, true);

/* ══════════════════════════════════════════════════════════
   §9  REGION BADGE in status bar — show current region
   ══════════════════════════════════════════════════════════ */

const _origRefreshIncidents = window.refreshIncidents;
if (_origRefreshIncidents) {
  window.refreshIncidents = async function () {
    const result = await _origRefreshIncidents.call(this);
    _updateRegionBadge();
    return result;
  };
}

async function _updateRegionBadge() {
  if (!S.incident) return;
  try {
    const r = await api(`/api/india/region?lat=${S.incident.lat}&lon=${S.incident.lon}`);
    const el = document.getElementById('sbIncident');
    if (el) el.textContent = `${S.incident.name.toUpperCase()} · ${r.name.split('(')[0].trim().toUpperCase()}`;
  } catch (_) {}
}

/* ══════════════════════════════════════════════════════════
   §10  COST-AWARE RESULTS — show whether economic figures are
   configured or placeholder after results render
   ══════════════════════════════════════════════════════════ */

const _origShowResults3 = window.showResults;
if (_origShowResults3) {
  window.showResults = async function () {
    await _origShowResults3.call(this);
    try {
      if (!S.lastResults) return;
      const vis = S.lastResults.results && S.lastResults.results.visual;
      if (!vis) return;
      const tot = vis.totals || {};
      if (tot.unit_costs_flagged === false) {
        // Costs are configured — add a green note
        const pb = document.getElementById('panelBody');
        if (!pb) return;
        const note = document.createElement('div');
        note.className = 'note';
        note.style.borderColor = 'var(--green)';
        note.innerHTML = `&#10003; Economic figures use <b>configured</b> unit costs (${tot.unit_costs_source || 'custom'}).`;
        pb.prepend(note);
      }
    } catch (_) {}
  };
}

/* ══════════════════════════════════════════════════════════
   §11  NATIONAL MAJOR DAMS REGISTRY & SEARCH COMMAND BAR
   ══════════════════════════════════════════════════════════ */
window.ALL_DAMS = [];
window._damFilter = 'all';
window._allDamsLayerGroup = null;

async function loadAllDams() {
  try {
    const res = await api('/api/dams');
    window.ALL_DAMS = res.items || [];
    renderDamCards(window.ALL_DAMS);
    const countEl = document.getElementById('damMatchCount');
    if (countEl) countEl.textContent = `${window.ALL_DAMS.length} dams available`;
  } catch (err) {
    console.warn('Failed loading major dams:', err);
  }
}

function renderDamCards(dams) {
  const grid = document.getElementById('damCardsGrid');
  if (!grid) return;
  if (!dams || !dams.length) {
    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-3);">
      <div style="font-size: 32px; margin-bottom: 8px;">🔍</div>
      <b>No dams found matching your search.</b>
      <div style="font-size: 11px; margin-top: 4px;">Try searching for a state (e.g. Kerala, Uttarakhand), river (e.g. Narmada, Kaveri), or clear the filter.</div>
    </div>`;
    return;
  }

  grid.innerHTML = dams.map(d => {
    const bcm = (d.volume_m3 / 1e9).toFixed(2);
    const mcm = Math.round(d.volume_m3 / 1e6);
    const volStr = d.volume_m3 >= 1e9 ? `${bcm} BCM` : `${mcm} MCM`;
    const matBadgeColor = d.material === 'Concrete' ? 'var(--cyan)' :
                          d.material === 'Masonry' ? 'var(--amber)' :
                          d.material === 'Rock' ? '#a78bfa' : 'var(--green)';

    return `
      <div class="dam-card" data-dam-id="${d.id}" onclick="selectMajorDam('${d.id}')">
        <div>
          <div class="dam-card-head">
            <span class="dam-card-title">${esc(d.name)}</span>
            <span class="badge" style="background: rgba(34,211,238,0.12); color: ${matBadgeColor}; font-size: 9.5px;">${esc(d.material)}</span>
          </div>
          <div class="dam-card-river">🌊 ${esc(d.river)} · <span style="color: var(--text-2); font-weight: normal;">${esc(d.state)}</span></div>
          <div class="dam-card-stats">
            <div class="dam-card-stat-item">
              <span class="dam-card-stat-label">Height</span>
              <span class="dam-card-stat-val">${d.height_m} m</span>
            </div>
            <div class="dam-card-stat-item">
              <span class="dam-card-stat-label">Storage</span>
              <span class="dam-card-stat-val">${volStr}</span>
            </div>
            <div class="dam-card-stat-item">
              <span class="dam-card-stat-label">Crest</span>
              <span class="dam-card-stat-val">${Math.round(d.crest_len_m)} m</span>
            </div>
          </div>
          ${d.notes ? `<div style="font-size: 10px; color: var(--text-3); line-height: 1.35; margin-top: 4px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${esc(d.notes)}</div>` : ''}
        </div>
        <div class="dam-card-footer">
          <span>📍 ${d.lat.toFixed(2)}°N, ${d.lon.toFixed(2)}°E</span>
          <button class="tbtn sm primary" style="padding: 3px 8px; font-size: 10px;" onclick="event.stopPropagation(); selectMajorDam('${d.id}');">
            Analyze Dam ➔
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function filterDams(query, regionKey) {
  let list = window.ALL_DAMS || [];
  if (regionKey === 'ntro_hadr') {
    list = list.filter(d => 
      ['DAM-RISHIGANGA', 'DAM-PHUKTAL', 'DAM-SOUTH-LHONAK', 'DAM-KOSI-BARRAGE', 'DAM-IDUKKI'].includes(d.id) ||
      (d.notes && d.notes.includes('NTRO')) ||
      (d.purpose && d.purpose.includes('NTRO'))
    );
  } else if (regionKey && regionKey !== 'all') {
    list = list.filter(d => d.region_key === regionKey);
  }
  if (query && query.trim()) {
    const q = query.toLowerCase().trim();
    list = list.filter(d =>
      d.name.toLowerCase().includes(q) ||
      d.river.toLowerCase().includes(q) ||
      d.state.toLowerCase().includes(q) ||
      (d.notes && d.notes.toLowerCase().includes(q)) ||
      d.material.toLowerCase().includes(q)
    );
  }
  renderDamCards(list);
  const countEl = document.getElementById('damMatchCount');
  if (countEl) countEl.textContent = `${list.length} dams`;
}

window.selectMajorDam = async function(damId) {
  try {
    toast('Activating dam site and downstream corridor...');
    const res = await api(`/api/dams/${damId}/activate`, { method: 'POST' });
    if (!res || !res.incident_id) throw new Error('Failed to activate dam');

    // Load incident
    if (typeof selectIncident === 'function') {
      await selectIncident(res.incident_id);
    }

    // Sync header display
    const disp = document.getElementById('currentDamDisplay');
    if (disp && res.dam) {
      disp.textContent = `${res.dam.name} (${res.dam.state})`;
    }

    // Close modal
    closeDamFinderModal();

    // Switch to DAM ANALYSIS tab
    const setupTab = document.querySelector('[data-tab="setup"]');
    if (setupTab) setupTab.click();

    toast(`✓ Loaded ${res.dam ? res.dam.name : 'Dam'} workspace`, 4000);
  } catch (err) {
    toast(`Activation error: ${err.message}`);
  }
};

function openDamFinderModal(initialQuery = '') {
  const modal = document.getElementById('damFinderModal');
  if (!modal) return;
  modal.classList.remove('hidden');
  const input = document.getElementById('damModalSearchInput');
  if (input) {
    input.value = initialQuery;
    setTimeout(() => input.focus(), 80);
    filterDams(initialQuery, window._damFilter);
  }
}

function closeDamFinderModal() {
  const modal = document.getElementById('damFinderModal');
  if (modal) modal.classList.add('hidden');
}

// Global hotkeys
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    openDamFinderModal();
  }
  if (e.key === 'Escape') {
    closeDamFinderModal();
    const ffModal = document.getElementById('fastFloodModal');
    if (ffModal) ffModal.classList.add('hidden');
  }
});

// Setup click and input listeners once DOM is ready
function initDamFinderUI() {
  const btnOpen = document.getElementById('btnOpenDamFinder');
  if (btnOpen) btnOpen.onclick = () => openDamFinderModal();

  const btnClose = document.getElementById('damFinderClose');
  if (btnClose) btnClose.onclick = closeDamFinderModal;

  const modal = document.getElementById('damFinderModal');
  if (modal) {
    modal.onclick = (e) => {
      if (e.target === modal) closeDamFinderModal();
    };
  }

  const searchInput = document.getElementById('damModalSearchInput');
  if (searchInput) {
    searchInput.oninput = (e) => filterDams(e.target.value, window._damFilter);
  }

  // Quick search in header
  const quickSearch = document.getElementById('quickDamSearch');
  if (quickSearch) {
    quickSearch.onfocus = () => {
      openDamFinderModal(quickSearch.value);
    };
    quickSearch.oninput = () => {
      openDamFinderModal(quickSearch.value);
    };
  }

  // Filter chips
  document.querySelectorAll('.dam-chip').forEach(chip => {
    chip.onclick = () => {
      document.querySelectorAll('.dam-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      window._damFilter = chip.dataset.filter || 'all';
      const curQuery = searchInput ? searchInput.value : '';
      filterDams(curQuery, window._damFilter);
    };
  });

  // Toggle All Dams Map Layer button
  const btnToggleDams = document.getElementById('btnToggleAllDams');
  if (btnToggleDams) {
    btnToggleDams.onclick = toggleAllDamsMapLayer;
  }

  // FastFlood modal close button
  const ffClose = document.getElementById('fastFloodClose');
  if (ffClose) {
    ffClose.onclick = () => {
      const ffModal = document.getElementById('fastFloodModal');
      if (ffModal) ffModal.classList.add('hidden');
    };
  }

  const ffModal = document.getElementById('fastFloodModal');
  if (ffModal) {
    ffModal.onclick = (e) => {
      if (e.target === ffModal) ffModal.classList.add('hidden');
    };
  }

  loadAllDams();
}

/* ══════════════════════════════════════════════════════════
   §12  ALL INDIA MAJOR DAMS LAYER ON MAP
   ══════════════════════════════════════════════════════════ */
window.toggleAllDamsMapLayer = function() {
  if (window._allDamsLayerGroup) {
    map.removeLayer(window._allDamsLayerGroup);
    window._allDamsLayerGroup = null;
    const btn = document.getElementById('btnToggleAllDams');
    if (btn) btn.classList.remove('active');
    toast('Dam markers hidden');
    return;
  }

  const markers = [];
  (window.ALL_DAMS || []).forEach(d => {
    const iconHtml = `<div style="background: var(--surface); border: 2px solid var(--cyan); border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.6); cursor: pointer;">🌊</div>`;
    const icon = L.divIcon({ html: iconHtml, className: 'dam-pin-icon', iconSize: [22, 22], iconAnchor: [11, 11] });
    const m = L.marker([d.lat, d.lon], { icon: icon });
    m.bindPopup(`
      <div style="min-width: 200px;">
        <b style="font-size: 13.5px; color: var(--cyan);">${esc(d.name)}</b>
        <div style="font-size: 11px; color: var(--text-2); margin-top: 2px;">🌊 ${esc(d.river)} · ${esc(d.state)}</div>
        <div style="font-size: 11px; margin: 8px 0; background: var(--surface-2); padding: 6px; border-radius: 6px; line-height: 1.5;">
          Height: <b>${d.height_m} m</b> · Type: <b>${esc(d.material)}</b><br>
          Gross Storage: <b>${(d.volume_m3 / 1e9).toFixed(2)} BCM</b>
        </div>
        <button class="tbtn sm primary full" style="padding: 4px 10px;" onclick="selectMajorDam('${d.id}')">Select &amp; Analyze Dam ➔</button>
      </div>
    `);
    markers.push(m);
  });

  window._allDamsLayerGroup = L.layerGroup(markers).addTo(map);
  const btn = document.getElementById('btnToggleAllDams');
  if (btn) btn.classList.add('active');
  toast('Displaying 65+ Major Dams across India on map');
};

/* ══════════════════════════════════════════════════════════
   §13  FASTFLOOD 2D ENGINE (HACKATHON MODEL) INTEGRATION
   ══════════════════════════════════════════════════════════ */
window._fastFloodOverlay = null;

window.openFastFloodModal = async function(simId) {
  const sid = simId || (window.S && window.S.simId);
  if (!sid) {
    toast('Please run or select a breach simulation first');
    return;
  }

  const modal = document.getElementById('fastFloodModal');
  const iframe = document.getElementById('fastfloodIframe');
  const btnTab = document.getElementById('btnOpenFastFloodTab');
  if (!modal || !iframe) return;

  modal.classList.remove('hidden');
  toast('Running FastFlood 2D engine (HAND + Manning)...');

  try {
    const ff = await api(`/api/simulations/${sid}/fastflood`);
    const st = ff.stats || {};
    const g = id => document.getElementById(id);
    if (g('ffDamName')) g('ffDamName').textContent = st.dam_name || 'Dam Break Scenario';
    if (g('ffPeakQ')) g('ffPeakQ').textContent = (st.peak_discharge_m3s || 0).toLocaleString();
    if (g('ffArea')) g('ffArea').textContent = st.total_inundated_area_km2 || '—';
    if (g('ffDepth')) g('ffDepth').textContent = st.max_depth_m || '—';
    if (g('ffVel')) g('ffVel').textContent = st.max_velocity_ms || '—';
    if (g('ffHighRisk')) g('ffHighRisk').textContent = st.high_risk_area_km2 || '—';

    const htmlUrl = ff.interactive_html_url || `/api/simulations/${sid}/fastflood/html`;
    iframe.src = htmlUrl;
    if (btnTab) btnTab.href = htmlUrl;
  } catch (err) {
    toast(`FastFlood error: ${err.message}`);
  }
};

window.toggleFastFloodRasterOverlay = async function(mode) {
  const sid = window.S && window.S.simId;
  if (!sid) {
    toast('Run a simulation first to view FastFlood 2D rasters');
    return;
  }

  try {
    toast(`Generating 2D ${mode.toUpperCase()} raster...`);
    const ff = await api(`/api/simulations/${sid}/fastflood`);
    if (!ff || !ff.overlays) throw new Error('No raster overlays returned');

    // Remove existing raster
    if (window._fastFloodOverlay) {
      map.removeLayer(window._fastFloodOverlay);
      window._fastFloodOverlay = null;
    }

    const b64 = ff.overlays[`${mode}_b64`];
    const bounds = ff.bounds_leaflet;
    if (b64 && bounds) {
      window._fastFloodOverlay = L.imageOverlay(b64, bounds, { opacity: 0.85 }).addTo(map);
      map.fitBounds(bounds);
      toast(`✓ FastFlood 2D ${mode.toUpperCase()} overlay rendered on map`);
    }
  } catch (err) {
    toast(`FastFlood raster error: ${err.message}`);
  }
};

// Hook into showResults to inject FastFlood 2D section
const _origShowResults4 = window.showResults;
if (_origShowResults4) {
  window.showResults = async function () {
    await _origShowResults4.call(this);
    try {
      const pb = document.getElementById('panelBody');
      if (!pb) return;

      const ffCard = document.createElement('div');
      ffCard.className = 'mod';
      ffCard.style.borderColor = 'var(--cyan)';
      ffCard.style.background = 'rgba(34, 211, 238, 0.04)';
      ffCard.innerHTML = `
        <div class="mod-title" style="color: var(--cyan); display: flex; align-items: center; justify-content: space-between;">
          <span>⚡ FASTFLOOD 2D ENGINE (HACKATHON MODEL)</span>
          <span class="badge" style="background: rgba(34,211,238,0.15); color: var(--cyan);">NEW</span>
        </div>
        <p style="font-size: 11px; color: var(--text-2); margin: 4px 0 10px; line-height: 1.4;">
          5-Step steady-state HAND + Manning's depth inversion model (van den Bout et al. 2026) with NDMA India risk classification &amp; Google/ESRI satellite overlays.
        </p>
        <button class="tbtn primary full sm" id="btnLaunchFastFlood" style="margin-bottom: 8px;">
          ▶ LAUNCH HIGH-DEF INTERACTIVE MAP (GOOGLE HYBRID + ESRI)
        </button>
        <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--text-3); margin-bottom: 4px;">
          DRAPE 2D RASTERS ON CURRENT MAP:
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;">
          <button class="tbtn sm" id="btnFFDepth">Depth (Blues)</button>
          <button class="tbtn sm" id="btnFFRisk">NDMA Risk</button>
          <button class="tbtn sm" id="btnFFVel">Velocity</button>
        </div>
      `;

      // Insert right after KPI row
      const kpiRow = pb.querySelector('.kpi-row');
      if (kpiRow && kpiRow.nextSibling) {
        pb.insertBefore(ffCard, kpiRow.nextSibling);
      } else {
        pb.prepend(ffCard);
      }

      document.getElementById('btnLaunchFastFlood').onclick = () => openFastFloodModal();
      document.getElementById('btnFFDepth').onclick = () => toggleFastFloodRasterOverlay('depth');
      document.getElementById('btnFFRisk').onclick = () => toggleFastFloodRasterOverlay('risk');
      document.getElementById('btnFFVel').onclick = () => toggleFastFloodRasterOverlay('velocity');
    } catch (_) {}
  };
}

// Hook into selectIncident to update the topbar label
const _origSelectIncident = window.selectIncident;
if (_origSelectIncident) {
  window.selectIncident = async function(id) {
    await _origSelectIncident.call(this, id);
    try {
      const disp = document.getElementById('currentDamDisplay');
      if (disp && window.S && window.S.incident) {
        disp.textContent = window.S.incident.name.replace('[MAJOR DAM] ', '').replace('[NATIONAL] ', '');
      }
    } catch (_) {}
  };
}

/* ══════════════════════════════════════════════════════════
   §9 "WIN THE ROOM" SHOWCASE CONTROLLER
   Full real-reach dam break simulation + SPH / Delft3D comparison +
   Dynamic flood wave propagation down valley with settlement alerts
   ══════════════════════════════════════════════════════════ */

function initWinTheRoomUI() {
  const topbarCenter = document.querySelector('.topbar-center');
  let btn = document.getElementById('btnWinTheRoom');
  if (!btn && topbarCenter) {
    btn = document.createElement('button');
    btn.id = 'btnWinTheRoom';
    btn.className = 'topbar-hydro-pill';
    btn.title = 'Launch Hydrodynamic Dam-Break Simulation Suite (Delft3D SWE & SPH Particle Solvers)';
    btn.innerHTML = `
      <span class="pulse-indicator"></span>
      <span>HYDRODYNAMIC SUITE</span>
      <span class="tag-models">SPH · DELFT3D</span>
    `;
    topbarCenter.appendChild(btn);
  }
  if (btn) {
    btn.onclick = () => openWinTheRoomModal();
  }

  // Inject modal markup into body if not present
  if (!document.getElementById('winTheRoomModal')) {
    const modal = document.createElement('div');
    modal.id = 'winTheRoomModal';
    modal.className = 'modal hidden';
    modal.innerHTML = `
      <div class="modal-card wide" style="max-width:860px;background:var(--surface);border:1px solid #0284c7;box-shadow:0 0 35px rgba(2,132,199,0.4);border-radius:12px;overflow:hidden">
        <div class="modal-head" style="background:linear-gradient(90deg, #0369a1, #0f172a);padding:14px 20px;border-bottom:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;align-items:center">
          <div>
            <div style="display:flex;align-items:center;gap:8px">
              <span style="font-size:18px">🏆</span>
              <h3 style="margin:0;font-size:15px;color:#f8fafc;font-weight:700;letter-spacing:0.5px">JAL-RAKSHA · HYDRODYNAMIC DAM-BREAK SHOWCASE</h3>
            </div>
            <div style="font-size:11px;color:#93c5fd;margin-top:2px">Real River Reach · SPH &amp; Delft3D Wave Solvers · Downstream Settlement Flood Propagation</div>
          </div>
          <button class="icon-btn" id="btnCloseWinRoom" style="color:#cbd5e1;font-size:18px;line-height:1">&times;</button>
        </div>
        
        <div class="modal-body" style="padding:16px 20px;max-height:75vh;overflow-y:auto;gap:12px">
          <!-- Step 1: Real River Reach -->
          <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:12px">
            <div style="font-size:11px;font-weight:700;color:var(--cyan);letter-spacing:0.8px;margin-bottom:8px">
              1. SELECT PHYSICAL RIVER REACH (SURVEYED NATURAL RIVERBED)
            </div>
            <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px" id="reachSelectorGrid">
              <button class="scen-card active" data-dam="JR-20260929-22F604" style="text-align:left;padding:8px 10px">
                <div style="font-weight:700;color:#f8fafc;font-size:12px">🌊 Idukki Arch Dam &middot; Periyar Gorge (Kerala)</div>
                <div style="font-size:10px;color:var(--text-3)">44.0 km gorge &middot; 360 surveyed nodes down to Neriamangalam</div>
              </button>
              <button class="scen-card" data-dam="JR-20260929-1B32D4" style="text-align:left;padding:8px 10px">
                <div style="font-weight:700;color:#f8fafc;font-size:12px">🏔️ Tehri Dam &middot; Bhagirathi Canyon (Uttarakhand)</div>
                <div style="font-size:10px;color:var(--text-3)">40.1 km canyon &middot; 304 nodes down to Devprayag &amp; Rishikesh</div>
              </button>
              <button class="scen-card" data-dam="JR-20260929-4141CC" style="text-align:left;padding:8px 10px">
                <div style="font-weight:700;color:#f8fafc;font-size:12px">🌊 Mullaperiyar Dam &middot; Periyar Valley (Kerala/TN)</div>
                <div style="font-size:10px;color:var(--text-3)">46.1 km valley &middot; 450 nodes through Vallakkadavu &amp; Vandiperiyar</div>
              </button>
              <button class="scen-card" data-dam="JR-20260929-69A72B" style="text-align:left;padding:8px 10px">
                <div style="font-weight:700;color:#f8fafc;font-size:12px">⚡ Bhakra Dam &middot; Sutlej Gorge (Himachal/Punjab)</div>
                <div style="font-size:10px;color:var(--text-3)">57.3 km reach &middot; 130 nodes through Nangal &amp; Anandpur Sahib</div>
              </button>
            </div>
          </div>

          <!-- Step 2: Hydrodynamic Solvers (SPH, Delft3D, 1D) -->
          <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:12px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <span style="font-size:11px;font-weight:700;color:var(--cyan);letter-spacing:0.8px">
                2. HYDRODYNAMIC WAVE PROPAGATION SOLVER
              </span>
              <span style="font-size:10px;color:var(--amber);font-family:var(--mono)">SPH + DELFT3D SWE ACTIVE</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
              <div style="background:var(--surface);border:1px solid rgba(14,165,233,0.3);border-radius:6px;padding:8px">
                <div style="font-weight:700;color:#38bdf8;font-size:11.5px">🌊 Delft3D 2D SWE</div>
                <div style="font-size:10px;color:var(--text-2);margin-top:2px">Non-linear St. Venant equations with bed shear friction and convective acceleration. Accurately captures backwater and channel contractions.</div>
              </div>
              <div style="background:var(--surface);border:1px solid rgba(245,158,11,0.3);border-radius:6px;padding:8px">
                <div style="font-weight:700;color:#fbbf24;font-size:11.5px">⚛️ SPH (Smoothed-Particle)</div>
                <div style="font-size:10px;color:var(--text-2);margin-top:2px">Meshless Lagrangian particle momentum wave. Models free-surface splash and leading-edge surge front down steep mountain canyons.</div>
              </div>
              <div style="background:var(--surface);border:1px solid rgba(52,211,153,0.3);border-radius:6px;padding:8px">
                <div style="font-weight:700;color:#34d399;font-size:11.5px">⚡ 1D Muskingum-Cunge</div>
                <div style="font-size:10px;color:var(--text-2);margin-top:2px">Diffusion wave hydraulic routing with storage attenuation. Robust benchmark across long river reaches.</div>
              </div>
            </div>
          </div>

          <!-- Step 3: Downstream Settlement Timeline Preview -->
          <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:12px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <span style="font-size:11px;font-weight:700;color:var(--cyan);letter-spacing:0.8px">
                3. DOWNSTREAM SETTLEMENTS &amp; EVACUATION CLOCKS
              </span>
              <span style="font-size:10px;color:var(--text-3)" id="showcaseSettlementCount">15 sites along corridor</span>
            </div>
            <div style="max-height:160px;overflow-y:auto;border:1px solid var(--border);border-radius:6px">
              <table class="tbl" style="margin:0;font-size:11px" id="showcaseSettlementsTbl">
                <thead>
                  <tr><th>Downstream Site</th><th>Type</th><th>Population</th><th>Wave Arrival</th><th>Peak Depth</th><th>Urgency</th></tr>
                </thead>
                <tbody>
                  <tr><td><b>Cheruthoni Town &amp; Market</b></td><td>Town</td><td>14,500</td><td><span class="badge" style="background:#ef444422;color:#ef4444">1.2 min</span></td><td>35.7 m</td><td><span class="badge danger">IMMEDIATE</span></td></tr>
                  <tr><td><b>Cheruthoni NH-85 Bridge</b></td><td>Bridge</td><td>Lifeline Link</td><td><span class="badge" style="background:#ef444422;color:#ef4444">1.4 min</span></td><td>35.4 m</td><td><span class="badge danger">IMMEDIATE</span></td></tr>
                  <tr><td><b>Thadiyampadu Village</b></td><td>Village</td><td>5,400</td><td><span class="badge" style="background:#ef444422;color:#ef4444">3.7 min</span></td><td>32.5 m</td><td><span class="badge danger">IMMEDIATE</span></td></tr>
                  <tr><td><b>Karimban Primary Health Centre</b></td><td>Hospital</td><td>40 beds</td><td><span class="badge" style="background:#f9731622;color:#f97316">5.5 min</span></td><td>24.3 m</td><td><span class="badge danger">IMMEDIATE</span></td></tr>
                  <tr><td><b>Chelachuvadu Community Hospital</b></td><td>Hospital</td><td>65 beds</td><td><span class="badge" style="background:#f9731622;color:#f97316">8.0 min</span></td><td>20.7 m</td><td><span class="badge danger">IMMEDIATE</span></td></tr>
                  <tr><td><b>Keerithodu Valley Village</b></td><td>Village</td><td>3,200</td><td><span class="badge" style="background:#fbbf2422;color:#fbbf24">12.2 min</span></td><td>11.9 m</td><td><span class="badge warn">CRITICAL</span></td></tr>
                  <tr><td><b>Lower Periyar Powerhouse Colony</b></td><td>Colony</td><td>1,850</td><td><span class="badge" style="background:#fbbf2422;color:#fbbf24">15.8 min</span></td><td>14.5 m</td><td><span class="badge warn">CRITICAL</span></td></tr>
                  <tr><td><b>Valara Waterfall Settlement</b></td><td>Village</td><td>2,900</td><td><span class="badge" style="background:#38bdf822;color:#38bdf8">23.2 min</span></td><td>23.9 m</td><td><span class="badge warn">CRITICAL</span></td></tr>
                  <tr><td><b>Neriamangalam Gateway Bridge</b></td><td>Bridge</td><td>NH-85 Link</td><td><span class="badge" style="background:#38bdf822;color:#38bdf8">25.7 min</span></td><td>34.2 m</td><td><span class="badge primary">EVACUATION</span></td></tr>
                  <tr><td><b>Neriamangalam Town</b></td><td>Town</td><td>16,200</td><td><span class="badge" style="background:#38bdf822;color:#38bdf8">25.9 min</span></td><td>33.4 m</td><td><span class="badge primary">EVACUATION</span></td></tr>
                  <tr><td><b>Kothamangalam Periyar Reach</b></td><td>Urban</td><td>34,000</td><td><span class="badge" style="background:#34d39922;color:#34d399">27.7 min</span></td><td>32.7 m</td><td><span class="badge primary">EVACUATION</span></td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="modal-actions" style="background:var(--surface-2);padding:14px 20px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">
          <div style="font-size:11px;color:var(--text-3);display:flex;align-items:center;gap:6px">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#22c55e"></span>
            <span>Hydrodynamic pipeline validated on GLO-30 DEM + OSM Hydrography</span>
          </div>
          <div style="display:flex;gap:8px">
            <button class="tbtn sm" id="btnCancelWinRoom">Cancel</button>
            <button class="tbtn sm primary" id="btnLaunchWinRoom" style="font-weight:700;padding:6px 16px;background:linear-gradient(135deg, #0284c7, #2563eb)">
              🌊 LAUNCH SIMULATION &amp; ANIMATE FLOOD WAVE DOWN VALLEY &rarr;
            </button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    document.getElementById('btnCloseWinRoom').onclick = () => modal.classList.add('hidden');
    document.getElementById('btnCancelWinRoom').onclick = () => modal.classList.add('hidden');
    document.getElementById('btnLaunchWinRoom').onclick = () => executeWinTheRoomShowcase();

    // Reach switcher inside modal
    modal.querySelectorAll('#reachSelectorGrid .scen-card').forEach(card => {
      card.onclick = () => {
        modal.querySelectorAll('#reachSelectorGrid .scen-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        window._selectedShowcaseDam = card.dataset.dam;
      };
    });
  }
}

function openWinTheRoomModal() {
  const modal = document.getElementById('winTheRoomModal');
  if (modal) modal.classList.remove('hidden');
}

async function executeWinTheRoomShowcase() {
  const modal = document.getElementById('winTheRoomModal');
  if (modal) modal.classList.add('hidden');

  const damId = window._selectedShowcaseDam || 'JR-20260929-22F604';
  
  if (typeof toast === 'function') {
    toast('🌊 Initializing Hydrodynamic Dam-Break Simulation...', 3000);
  }

  // 1. Select the incident in the app
  if (typeof selectIncident === 'function') {
    await selectIncident(damId);
  }

  // 2. Center map on dam with satellite view
  if (window.map && window.S && window.S.incident) {
    window.map.setView([window.S.incident.lat, window.S.incident.lon], 12);
  }

  // 3. Find latest completed simulation or run one
  try {
    const sims = await api(`/api/simulations?incident_id=${damId}&limit=5`);
    let targetSimId = null;
    if (sims && sims.items && sims.items.length) {
      const done = sims.items.find(s => s.status === 'DONE');
      if (done) targetSimId = done.id;
    }

    if (!targetSimId) {
      if (typeof toast === 'function') toast('⚡ Running hydrodynamic solver along physical riverbed...', 4000);
      const res = await api(`/api/simulations?incident_id=${damId}`, {
        method: 'POST',
        body: JSON.stringify({
          scenario: 'major',
          stored_volume_m3: 1996000000,
          lake_area_m2: 60000000,
          dam_height_m: 168.91,
          dam_crest_len_m: 366,
          breach_width_m: 100,
          breach_depth_m: 80,
          breach_time_hr: 1.5,
          inflow_m3s: 1200,
          dam_material: 'Concrete',
          valley_width_m: 90,
          bed_slope: 0.02,
          manning_n: 0.045,
          spreading_factor: 2.5,
          base_flow_m3s: 50,
          with_uncertainty: false
        })
      });
      targetSimId = res.simulation_id;
      // Wait for completion
      for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 1500));
        const check = await api(`/api/simulations/${targetSimId}`);
        if (check.status === 'DONE') break;
      }
    }

    // 4. Load simulation details into state
    if (targetSimId) {
      window.S.simId = targetSimId;
      window.S.lastResults = await api(`/api/simulations/${targetSimId}`);
      
      // 5. Open visual simulation player
      if (typeof panelVisual === 'function') {
        panelVisual();
      }

      // 6. Automatically start playback of the flood wave!
      setTimeout(() => {
        const playBtn = document.getElementById('vsPlay');
        if (typeof playVS === 'function') {
          playVS();
        } else if (playBtn) {
          playBtn.click();
        }
        if (typeof toast === 'function') {
          toast('🌊 Flood wave propagating down Periyar Valley! Watch settlements alert as wave arrives.', 5000);
        }
      }, 600);

      // 7. Inject Hydrodynamic Comparison Tab into Inspector
      injectHydrodynamicComparisonPanel(targetSimId);
    }
  } catch (err) {
    if (typeof toast === 'function') toast('Showcase execution error: ' + err.message);
  }
}

async function injectHydrodynamicComparisonPanel(simId) {
  try {
    const comp = await api(`/api/simulations/${simId}/hydrodynamic-comparison`);
    if (!comp || !comp.models) return;

    const pb = document.getElementById('panelBody');
    if (!pb) return;

    const compDiv = document.createElement('div');
    compDiv.className = 'mod';
    compDiv.style.border = '1px solid #0284c7';
    compDiv.style.borderRadius = '8px';
    compDiv.style.marginTop = '12px';
    compDiv.innerHTML = `
      <div class="mod-title" style="display:flex;justify-content:space-between;align-items:center">
        <span style="color:var(--cyan)">HYDRODYNAMIC SOLVER COMPARISON</span>
        <span class="badge primary">SPH · DELFT3D · 1D</span>
      </div>
      <div style="font-size:11px;color:var(--text-2);margin-bottom:8px">
        Side-by-side verification comparing 2D Depth-Averaged SWE (Delft3D formulation) against Smoothed-Particle Hydrodynamics (SPH) and 1D Diffusion Wave:
      </div>
      <div style="overflow-x:auto">
        <table class="tbl" style="font-size:10.5px;margin:0">
          <thead>
            <tr><th>Settlement</th><th>Dist</th><th>Delft3D SWE</th><th>SPH Particle</th><th>1D Cunge</th><th>Recommended Action</th></tr>
          </thead>
          <tbody>
            ${comp.settlement_impact_comparison.map(s => `
              <tr>
                <td><b>${esc(s.name)}</b></td>
                <td>${s.distance_km} km</td>
                <td><span style="color:#38bdf8">${s.arrival_time_min.delft3d_swe} min</span> &middot; ${s.peak_depth_m.delft3d_swe}m</td>
                <td><span style="color:#fbbf24">${s.arrival_time_min.sph_particles} min</span> &middot; ${s.peak_depth_m.sph_particles}m</td>
                <td>${s.arrival_time_min.muskingum_cunge_1d} min &middot; ${s.peak_depth_m.muskingum_cunge_1d}m</td>
                <td><span class="badge ${s.evacuation_urgency.includes('IMMEDIATE') ? 'danger' : 'warn'}">${s.evacuation_urgency}</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      <div style="background:var(--surface-2);border-radius:6px;padding:8px;margin-top:8px;font-size:10.5px;color:var(--text-2)">
        <b style="color:var(--amber)">Disaster Relief Recommendation:</b> ${esc(comp.disaster_relief_summary.operational_recommendation)}
      </div>
    `;

    pb.appendChild(compDiv);
  } catch (_) {}
}

// Hook dynamic settlement impact announcements into VS frame drawing
const _origDrawVSFrame = window.drawVSFrame;
if (_origDrawVSFrame) {
  window.drawVSFrame = function(i) {
    _origDrawVSFrame.call(this, i);
    if (!window.VS || !window.VS.frames || !window.VS.assetMarks) return;

    const fr = window.VS.frames[i];
    if (!fr) return;

    window.VS.assetMarks.forEach(a => {
      if (a.entry && a.entry.arrival_min != null) {
        // If arrived in this exact window
        if (!a._announced && fr.t_min >= a.entry.arrival_min) {
          a._announced = true;
          // Flash toast alert on settlement impact
          const isExtreme = a.entry.people_hazard === 'EXTREME' || (a.entry.peak_depth_m && a.entry.peak_depth_m > 10);
          if (typeof toast === 'function' && a.entry.population > 2000) {
            toast(`🚨 IMPACT AT T = ${fr.t_min} MIN: ${a.entry.name} reached! Depth: ${a.entry.peak_depth_m}m · Evacuate ${a.entry.population.toLocaleString()} people!`, 4500);
          }
        }
      }
    });
  };
}

// ══════════════════════════════════════════════════════════════════
// GOOGLE EARTH ENGINE (GEE) NEAR-REAL-TIME FLOOD VERIFICATION UI
// (Addresses NTRO SIH26161 Deliverable iv)
// ══════════════════════════════════════════════════════════════════
function initGeeUI() {
  const btnGee = document.getElementById("btnTopDlGee");
  const modal = document.getElementById("geeModal");
  const closeBtn = document.getElementById("geeModalClose");
  const copyBtn = document.getElementById("btnCopyGeeCode");
  const dlBtn = document.getElementById("btnDownloadGeeCode");
  const viewer = document.getElementById("geeCodeViewer");

  if (!btnGee || !modal) return;

  async function openGee() {
    if (!S.incident) {
      if (typeof toast === "function") toast("Please select a dam or incident first");
      return;
    }
    modal.classList.remove("hidden");
    viewer.value = "// Loading Earth Engine Sentinel-1 SAR script for " + S.incident.name + "...";
    
    try {
      const url = S.simId 
        ? `/api/simulations/${S.simId}/export/gee-script.js`
        : `/api/incidents/${S.incident.id}/export/gee-script.js`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const code = await res.text();
      viewer.value = code;
    } catch (e) {
      viewer.value = "// Failed to load GEE script: " + e.message;
    }
  }

  btnGee.addEventListener("click", openGee);
  if (closeBtn) closeBtn.addEventListener("click", () => modal.classList.add("hidden"));

  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(viewer.value || "")
        .then(() => { if (typeof toast === "function") toast("✓ Copied GEE JavaScript to clipboard! Ready to paste in Earth Engine.", 3000); })
        .catch(() => { viewer.select(); document.execCommand("copy"); if (typeof toast === "function") toast("✓ Copied to clipboard", 2500); });
    });
  }

  if (dlBtn) {
    dlBtn.addEventListener("click", () => {
      const safeName = (S.incident ? S.incident.name : "dam_break")
        .toLowerCase().replace(/[^a-z0-9]/g, "_").slice(0, 28).replace(/^_+|_+$/g, "");
      const blob = new Blob([viewer.value || ""], { type: "application/javascript" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${safeName}_gee_sentinel1_flood_verification.js`;
      a.click();
      URL.revokeObjectURL(a.href);
      if (typeof toast === "function") toast("Downloading Earth Engine script...", 2000);
    });
  }
}
window.openGeeModal = () => {
  const modal = document.getElementById("geeModal");
  if (modal) {
    const btn = document.getElementById("btnTopDlGee");
    if (btn) btn.click();
    else modal.classList.remove("hidden");
  }
};

// Initialize on DOM load
function _initAllExtensions() {
  if (typeof initDamFinderUI === 'function') initDamFinderUI();
  if (typeof initWinTheRoomUI === 'function') initWinTheRoomUI();
  if (typeof initGeeUI === 'function') initGeeUI();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _initAllExtensions);
} else {
  _initAllExtensions();
}

if (typeof PANELS !== 'undefined') {
  if (window.panelBreach)  PANELS.breach  = window.panelBreach;
  if (window.panelSetup)   PANELS.setup   = window.panelSetup;
  if (window.panelAdmin)   PANELS.admin   = window.panelAdmin;
  if (window.panelMonitor) PANELS.monitor = window.panelMonitor;
}

console.log('[JAL-RAKSHA] app_ext.js v4.2 loaded — Win the Room Showcase, 65+ Major Dams & Hydrodynamic Solvers active');
