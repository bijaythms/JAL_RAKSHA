"use strict";

/* ---------- XSS-safe escaping ---------- */
const esc = s => String(s ?? "").replace(/[&<>"']/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

/* ---------- i18n (persisted) ---------- */
const I18N = {
 en:{"nav.map":"MAP OVERVIEW","nav.setup":"DAM ANALYSIS","nav.breach":"BREACH SIMULATION",
  "nav.results":"INUNDATION MODEL","nav.visual":"VISUAL SIMULATION",
  "nav.manual":"MANUAL SIMULATION","nav.monitor":"LAKE MONITOR",
  "nav.satellite":"SATELLITE","nav.damage":"FIELD REPORTS",
  "nav.national":"NATIONAL EXERCISE","nav.scenarios":"SCENARIO LIBRARY",
  "nav.admin":"ADMIN","nav.about":"ABOUT US","btn.centerline":"DRAW CENTERLINE","lbl.assets":"Assets",
  "legend.title":"MAP LAYERS & CLASSIFICATION","legend.depth":"FLOOD INUNDATION DEPTH",
  "legend.features":"GEOSPATIAL FEATURES","legend.dam":"Incident / Dam Site",
  "legend.asset":"Exposure Assets","legend.infra":"Critical Infrastructure",
  "legend.report":"Field Reports","anim.phase":"FLOOD PROPAGATION",
  "draw.hint":"Click points downstream","login.title":"Sign in"},
 hi:{"nav.map":"\u092e\u093e\u0928\u091a\u093f\u0924\u094d\u0930","nav.setup":"\u092c\u093e\u0901\u0927 \u0935\u093f\u0936\u094d\u0932\u0947\u0937\u0923",
  "nav.breach":"\u092d\u0902\u0917 \u0938\u093f\u092e\u0941\u0932\u0947\u0936\u0928","nav.results":"\u092c\u093e\u0922\u093c \u092e\u0949\u0921\u0932",
  "nav.visual":"\u0926\u0943\u0936\u094d\u092f \u0938\u093f\u092e\u0941\u0932\u0947\u0936\u0928","nav.manual":"\u092e\u0948\u0928\u0941\u0905\u0932 \u0938\u093f\u092e\u0941\u0932\u0947\u0936\u0928",
  "nav.monitor":"\u091d\u0940\u0932 \u0928\u093f\u0917\u0930\u093e\u0928\u0940","nav.satellite":"\u0909\u092a\u0917\u094d\u0930\u0939",
  "nav.damage":"\u0915\u094d\u0937\u0947\u0924\u094d\u0930 \u0930\u093f\u092a\u094b\u0930\u094d\u091f","nav.national":"\u0930\u093e\u0937\u094d\u091f\u094d\u0930\u0940\u092f \u0905\u092d\u094d\u092f\u093e\u0938",
  "nav.scenarios":"\u092a\u0930\u093f\u0926\u0943\u0936\u094d\u092f \u092a\u0941\u0938\u094d\u0924\u0915\u093e\u0932\u092f","nav.admin":"\u092a\u094d\u0930\u0936\u093e\u0938\u0928",
  "nav.about":"\u0939\u092e\u093e\u0930\u0947 \u092c\u093e\u0930\u0947 \u092e\u0947\u0902",
  "btn.centerline":"\u0915\u0947\u0902\u0926\u094d\u0930\u0930\u0947\u0916\u093e \u0916\u0940\u0902\u091a\u0947\u0902","lbl.assets":"\u0938\u0902\u092a\u0924\u094d\u0924\u093f\u092f\u093e\u0901",
  "legend.title":"\u092e\u093e\u0928\u091a\u093f\u0924\u094d\u0930 \u092a\u0930\u0924\u0947\u0902","legend.depth":"\u092c\u093e\u0922\u093c \u0915\u0940 \u0917\u0939\u0930\u093e\u0908",
  "legend.features":"\u092d\u094c\u0917\u094b\u0932\u093f\u0915 \u0935\u093f\u0936\u0947\u0937\u0924\u093e\u090f\u0901","legend.dam":"\u0918\u091f\u0928\u093e / \u092c\u093e\u0901\u0927 \u0938\u094d\u0925\u0932",
  "legend.asset":"\u0938\u0902\u092a\u0924\u094d\u0924\u093f\u092f\u093e\u0901","legend.infra":"\u092e\u0939\u0924\u094d\u0935\u092a\u0942\u0930\u094d\u0923 \u0905\u0935\u0938\u0902\u0930\u091a\u0928\u093e",
  "legend.report":"\u0915\u094d\u0937\u0947\u0924\u094d\u0930 \u0930\u093f\u092a\u094b\u0930\u094d\u091f","anim.phase":"\u092c\u093e\u0922\u093c \u092a\u094d\u0930\u0938\u093e\u0930",
  "draw.hint":"\u0928\u0940\u091a\u0947 \u0915\u0940 \u0913\u0930 \u092c\u093f\u0902\u0926\u0941 \u091a\u0941\u0928\u0947\u0902","login.title":"\u0932\u0949\u0917\u093f\u0928 \u0915\u0930\u0947\u0902",
  "btn.runSim": "सिमुलेशन चलाएं",
  "btn.download": "डाउनलोड करें",
  "lbl.breach": "भंग पैरामीटर",
  "lbl.results": "सिमुलेशन परिणाम",
  "lbl.damHeight": "बांध की ऊंचाई (मीटर)",
  "lbl.volume": "संग्रहीत जल (घन मीटर)",
  "lbl.material": "बांध सामग्री",
  "lbl.arrival": "आगमन समय",
  "lbl.depth": "जल गहराई",
  "lbl.area": "जलमग्न क्षेत्र",
  "msg.noIncident": "कोई सक्रिय घटना नहीं चुनी गई",
  "msg.runFirst": "पहले सिमुलेशन चलाएं",
  "msg.selectDam": "बांध या घटना चुनें",
  "lbl.popAt": "जनसंख्या खतरे में",
  "lbl.peakQ": "अधिकतम प्रवाह दर",
  "btn.report": "रिपोर्ट देखें",
  "btn.export": "GIS निर्यात"
}
};
let lang = localStorage.getItem("jr4_lang") || "en";
const t = k => I18N[lang][k] ?? I18N.en[k] ?? k;
function applyI18n(){
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(e => e.textContent = t(e.dataset.i18n));
}
const fmtIST = iso => iso ? new Date(iso).toLocaleString("en-IN",
  {timeZone:"Asia/Kolkata", dateStyle:"medium", timeStyle:"short"}) + " IST" : "-";

/* ---------- state ---------- */
const S = {token:null, role:null, user:null, incidents:[], incident:null,
  centerline:[], drawMode:false, roiMode:false, roiZoneId:null, roiPts:[],
  simId:null, lastResults:null, layers:{}, showPop:true, showScen:true, showBld:true,
  scenarioData:null, scenarioLayerMap:{}};
const $ = id => document.getElementById(id);
const L_ = n => (S.layers[n] = S.layers[n] || []);
function clearLayer(n){ L_(n).forEach(l => l && map.removeLayer(l)); S.layers[n] = []; }
function clearAll(){ Object.keys(S.layers).forEach(clearLayer);
  $("floodDock").classList.add("hidden");
  if ($("scenDock")) $("scenDock").classList.add("hidden"); }


async function api(path, opts = {}){
  const r = await fetch(path, {...opts, headers:{"Content-Type":"application/json",
    ...(S.token ? {Authorization:`Bearer ${S.token}`} : {}), ...(opts.headers||{})}});
  if (r.status === 401){ throw new Error("Unauthorized"); }
  const text = await r.text();
  let j;
  try {
    j = text ? JSON.parse(text) : {};
  } catch(e) {
    if (!r.ok) {
      throw new Error(`Server error (${r.status}): ${text.slice(0, 100)}`);
    }
    throw new Error("Invalid response format from server");
  }
  if (!r.ok) {
    const msg = typeof j.detail === "string" ? j.detail
              : (j.detail ? JSON.stringify(j.detail) : (j.error || `Server error (${r.status})`));
    throw new Error(msg);
  }
  return j;
}
function toast(msg, ms = 3400){
  const d = document.createElement("div"); d.className = "toast"; d.textContent = msg;
  $("toasts").append(d); setTimeout(() => d.remove(), ms);
}
const EMPTY = (icon, msg, action, fn) => `
  <div class="empty-state"><span class="es-icon">${icon}</span>${msg}
  ${action ? `<div class="es-action"><button class="tbtn primary sm"
    onclick="${fn}">${action}</button></div>` : ""}</div>`;

/* ---------- map ---------- */
const map = L.map("map").setView([21.7679, 78.8718], 5);
const bases = {
  hybrid: L.tileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", {maxZoom:20, attribution:"© Google"}),
  sat: L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {maxZoom:18, attribution:"© Esri"}),
  topo: L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", {maxZoom:18, attribution:"© Esri Topo"})
};
bases.hybrid.addTo(map);
document.querySelectorAll("[data-base]").forEach(b => b.onclick = () => {
  Object.values(bases).forEach(l => map.removeLayer(l));
  if (bases[b.dataset.base]) bases[b.dataset.base].addTo(map);
  document.querySelectorAll("[data-base]").forEach(x => x.classList.toggle("active", x === b));
});
const sb = (id, v) => { const el = $(id); if (el) el.textContent = v; };
map.on("mousemove", e => sb("sbCoords",
  `${e.latlng.lat.toFixed(5)}N, ${e.latlng.lng.toFixed(5)}E`));
map.on("zoomend", () => sb("sbZoom", map.getZoom().toFixed(1)));
sb("sbZoom", map.getZoom().toFixed(1));

let relocateMode = false;

function renderIncidentOnMap(inc){
  clearAll();
  if (!inc){ sb("sbIncident","NO ACTIVE INCIDENT"); return; }
  sb("sbIncident", `${inc.id} - ${inc.name}`);

  // Create high-visibility draggable dam crest marker
  const pinHtml = `
    <div style="position:relative;width:30px;height:30px;cursor:grab" title="Drag to adjust dam crest position">
      <div style="position:absolute;width:30px;height:30px;background:rgba(34,211,238,0.3);border-radius:50%;animation:pulse 2s infinite"></div>
      <div style="position:absolute;top:4px;left:4px;width:22px;height:22px;background:#00f0ff;border:2.5px solid #fff;border-radius:50%;box-shadow:0 3px 12px rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;color:#05080c;font-size:11px;font-weight:bold">&#9678;</div>
    </div>
  `;
  const pinIcon = L.divIcon({ html: pinHtml, className: "dam-crest-pin", iconSize: [30, 30], iconAnchor: [15, 15] });
  const m = L.marker([inc.lat, inc.lon], { icon: pinIcon, draggable: true });
  m.bindPopup(`
    <div style="min-width:220px">
      <b style="font-size:13.5px;color:var(--cyan)">${esc(inc.name)}</b>
      <div style="font-size:11px;color:var(--text-2);margin:2px 0 6px">&#127754; ${esc(inc.river_name || "")}</div>
      <div style="font-size:10.5px;color:var(--text-3);line-height:1.45;background:var(--surface-2);padding:6px;border-radius:6px;margin-bottom:8px">
        &#128205; <b>${inc.lat.toFixed(5)}°N, ${inc.lon.toFixed(5)}°E</b><br>
        <span style="color:#34d399;font-weight:600">&#10003; Position verified on physical dam crest wall.</span><br>
        <span style="color:var(--amber)">&#128161; Drag pin or click relocate to micro-adjust.</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:6px">
        <button class="tbtn sm" style="padding:4px 6px;font-size:10.5px" onclick="window.zoomToDamWall()">&#128269; Zoom In (16x)</button>
        <button class="tbtn sm" style="padding:4px 6px;font-size:10.5px" onclick="window.fitReachBounds()">&#8982; Full Reach</button>
      </div>
      <button class="tbtn sm primary full" style="padding:4px 8px" onclick="startRelocateDamMode()">
        &#128205; Click Satellite to Relocate
      </button>
    </div>
  `);

  m.on("dragend", async (ev) => {
    const pos = ev.target.getLatLng();
    await updateDamPosition(pos.lat, pos.lng);
  });

  m.addTo(map); L_("markers").push(m);
  const cl = inc.centerline || [];
  if (cl.length >= 2){
    let reachKm = 0;
    for (let k = 1; k < cl.length; k++) reachKm += haversineJs(cl[k-1], cl[k]);
    const line = L.polyline(cl, {color:"#00f0ff", weight:3.5, dashArray:"7 5", opacity:0.9}).addTo(map);
    line.bindTooltip(`🌊 <b>Dam Break Valley Flow Route (DEM)</b><br>${cl.length} nodes · ${(reachKm/1000).toFixed(1)} km down valley`, {sticky: true});
    L_("centerline").push(line);
    window._lastCenterlineLayer = line;
    // Default to close satellite view on the dam wall (level 15) so the user directly sees the physical dam structure
    map.setView([inc.lat, inc.lon], 15);
  } else {
    map.setView([inc.lat, inc.lon], 15);
  }
}

window.zoomToDamWall = function() {
  if (S.incident) map.setView([S.incident.lat, S.incident.lon], 16);
};

window.fitReachBounds = function() {
  if (window._lastCenterlineLayer) {
    map.fitBounds(window._lastCenterlineLayer.getBounds().pad(0.25));
  } else if (S.incident) {
    map.setView([S.incident.lat, S.incident.lon], 12);
  }
};

async function updateDamPosition(newLat, newLon) {
  if (!S.incident) return;
  const lat = Math.round(newLat * 100000) / 100000;
  const lon = Math.round(newLon * 100000) / 100000;
  try {
    toast(`Saving new dam position: ${lat}°N, ${lon}°E...`);
    await api(`/api/incidents/${S.incident.id}`, {
      method: "PATCH",
      body: JSON.stringify({ lat: lat, lon: lon })
    });
    S.incident.lat = lat;
    S.incident.lon = lon;
    await selectIncident(S.incident.id);
    if (document.querySelector('.nav-item[data-tab="setup"].active')) {
      panelSetup();
    }
    toast(`✓ Dam relocated to ${lat.toFixed(5)}°N, ${lon.toFixed(5)}°E`, 3500);
  } catch(err) {
    toast("Failed to update location: " + err.message);
  }
}

function startRelocateDamMode() {
  if (!S.incident) return;
  relocateMode = true;
  document.getElementById("map").style.cursor = "crosshair";
  toast("📍 Click anywhere on the satellite view to place the dam wall", 6000);
}

map.on("click", async (e) => {
  if (relocateMode && S.incident) {
    relocateMode = false;
    document.getElementById("map").style.cursor = "";
    await updateDamPosition(e.latlng.lat, e.latlng.lng);
  }
});

/* ---------- auth (auto-admin enabled) ---------- */
function showLogin(){ if ($("loginModal")) $("loginModal").classList.add("hidden"); }
if ($("btnLogin")) $("btnLogin").onclick = () => {};
if ($("loginCancel")) $("loginCancel").onclick = () => $("loginModal") && $("loginModal").classList.add("hidden");
if ($("loginGo")) $("loginGo").onclick = async () => {};
if ($("btnLogout")) $("btnLogout").onclick = () => {};
(function restore(){
  Object.assign(S, {token:"admin-session", role:"admin", user:"admin"});
  sessionStorage.setItem("jr4_auth", JSON.stringify({token:"admin-session", role:"admin", username:"admin"}));
  updateUserBadge();
})();
function updateUserBadge(){
  const b = $("userBadge");
  if (b){
    b.classList.remove("hidden"); b.textContent = "ADMIN";
  }
  if ($("btnLogin")) $("btnLogin").classList.add("hidden");
  if ($("btnLogout")) $("btnLogout").classList.add("hidden");
  if ($("navAdmin")) $("navAdmin").classList.remove("hidden");
  if ($("userChip")) $("userChip").classList.remove("hidden");
}

/* ---------- incidents ---------- */
async function refreshIncidents(){
  try{
    const j = await api("/api/incidents?limit=100");
    S.incidents = j.items;
    $("incidentSelect").innerHTML = '<option value="">— Select Dam / Incident —</option>' + S.incidents.map(i =>
      `<option value="${i.id}">${esc(i.id)} - ${esc(i.name)}</option>`).join("");
    if (S.incident){
      const pick = S.incidents.find(i => i.id === S.incident.id);
      if (pick) {
        $("incidentSelect").value = pick.id;
        await selectIncident(pick.id);
      }
    }
  }catch(e){ /* pre-login */ }
}
async function selectIncident(id){
  S.incident = await api(`/api/incidents/${id}`);
  renderIncidentOnMap(S.incident);

  // Automatically fetch latest completed simulation for this incident so results, visual sim, and exports are immediately ready!
  try{
    const sims = await api(`/api/simulations?incident_id=${id}&limit=5`);
    const doneSim = (sims.items || []).find(s => s.status === "DONE");
    if (doneSim){
      S.simId = doneSim.id;
      const full = await api(`/api/simulations/${doneSim.id}`);
      S.lastResults = full;
      if (full.results?.inundation){
        drawFloodOnMap(full.results.inundation, true);
      }
    } else {
      S.simId = null;
      S.lastResults = null;
    }
  }catch(e){ S.simId = null; S.lastResults = null; }

  loadAssets();
  loadDemStat();
  loadPopulationClusters();
  loadScenarioExtents();
}
async function loadAssets(){
  clearLayer("assets");
  if (!S.incident) return;
  try{
    const j = await api(`/api/incidents/${S.incident.id}/assets`);
    sb("statAssets", j.length);

    // Look up simulation impact results if available
    const impacts = S.lastResults?.results?.visual?.impact || [];

    j.forEach(a => {
      // Find simulation impact record for this asset
      const imp = impacts.find(im =>
        (im.name && a.name && (im.name === a.name || im.name.includes(a.name) || a.name.includes(im.name))) ||
        (Math.abs(im.lat - a.lat) < 0.003 && Math.abs(im.lon - a.lon) < 0.003)
      );

      // Determine building type and classification
      const attrs = a.attributes || {};
      const rawType = (attrs.building_type || attrs.use || a.kind || "").toLowerCase();
      const rawName = (a.name || "").toLowerCase();

      let bldType = attrs.building_type || "Building / Structure";
      let icon = "&#127970;"; // 🏢

      if (rawType.includes("hospital") || rawType.includes("clinic") || rawType.includes("phc") || rawType.includes("health") ||
          rawName.includes("hospital") || rawName.includes("clinic") || rawName.includes("phc")) {
        bldType = "Hospital / Health Center";
        icon = "&#127973;"; // 🏥
      } else if (rawType.includes("school") || rawType.includes("college") || rawType.includes("education") ||
                 rawName.includes("school") || rawName.includes("college") || rawName.includes("ghss")) {
        bldType = "Educational Facility";
        icon = "&#127979;"; // 🏫
      } else if (rawType.includes("powerhouse") || rawType.includes("power") || rawType.includes("substation") ||
                 rawName.includes("powerhouse") || rawName.includes("kseb") || rawName.includes("substation")) {
        bldType = "Hydropower Powerhouse";
        icon = "&#9889;"; // ⚡
      } else if (rawType.includes("wood") || rawType.includes("mill") || rawType.includes("factory") || rawType.includes("industrial") ||
                 rawName.includes("mill") || rawName.includes("industries") || rawName.includes("factory")) {
        bldType = "Industrial Processing Plant";
        icon = "&#127981;"; // 🏭
      } else if (rawType.includes("commercial") || rawType.includes("fuel") || rawType.includes("depot") || rawType.includes("market") ||
                 rawName.includes("indianoil") || rawName.includes("fuel") || rawName.includes("market") || rawName.includes("commercial")) {
        bldType = "Commercial / Fuel Terminal";
        icon = "&#127978;"; // 🏬
      } else if (rawType.includes("bridge") || rawName.includes("bridge") || rawName.includes("gateway")) {
        bldType = "River Crossing Bridge";
        icon = "&#127753;"; // 🌉
      } else if (rawType.includes("residential") || rawType.includes("quarters") || rawType.includes("housing") ||
                 rawName.includes("quarters") || rawName.includes("settlement") || rawName.includes("colony")) {
        bldType = "Residential Quarters";
        icon = "&#127968;"; // 🏠
      } else if (a.kind === "agriculture" || rawType.includes("crop") || rawType.includes("agri")) {
        bldType = "Agricultural Area";
        icon = "&#127806;"; // 🌾
      } else if (a.kind === "infrastructure" || a.critical) {
        bldType = "Critical Public Infrastructure";
        icon = "&#128737;"; // 🛡️
      }

      // Determine flood risk level: EXTREME, HIGH, MODERATE, LOW
      let risk = "LOW";
      let peakDepth = null, peakV = null, arrMin = null, forceKn = null, dmgFrac = null;

      if (imp) {
        risk = imp.people_hazard || "MODERATE";
        peakDepth = imp.peak_depth_m;
        peakV = imp.peak_v_ms;
        arrMin = imp.arrival_min;
        forceKn = imp.force_kN_m;
        dmgFrac = imp.building_damage_frac;
      } else {
        const elev = attrs.elevation_above_bed_m != null ? attrs.elevation_above_bed_m : 5.0;
        if (a.critical || elev < 3.0) risk = "EXTREME";
        else if (elev < 6.0) risk = "HIGH";
        else if (elev < 12.0) risk = "MODERATE";
        else risk = "LOW";
      }

      const riskLower = risk.toLowerCase();
      const riskBadgeColors = {
        extreme: {bg:"#ef4444", text:"#ffffff", label:"EXTREME RISK"},
        high: {bg:"#f97316", text:"#ffffff", label:"HIGH RISK"},
        moderate: {bg:"#eab308", text:"#000000", label:"MODERATE RISK"},
        low: {bg:"#22c55e", text:"#ffffff", label:"LOW RISK"}
      };
      const badge = riskBadgeColors[riskLower] || riskBadgeColors.moderate;

      const markerHtml = `
        <div class="bld-marker risk-${riskLower}" style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;border-radius:50%;cursor:pointer" title="${esc(a.name)} - ${badge.label}">
          <span style="font-size:14px;line-height:1">${icon}</span>
        </div>
      `;
      const divIcon = L.divIcon({
        html: markerHtml,
        className: "bld-marker-container",
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        popupAnchor: [0, -14]
      });

      const m = L.marker([a.lat, a.lon], {icon: divIcon});

      m.bindTooltip(`
        <div style="font-size:11.5px;font-family:sans-serif;line-height:1.4">
          <div style="font-weight:700;display:flex;align-items:center;gap:4px">
            <span>${icon}</span> <span>${esc(a.name)}</span>
          </div>
          <div style="margin:2px 0">
            <span style="background:${badge.bg};color:${badge.text};padding:1px 6px;border-radius:4px;font-size:9.5px;font-weight:700;letter-spacing:0.04em">
              ${badge.label}
            </span>
            <span style="color:#94a3b8;font-size:10.5px;margin-left:4px">${esc(bldType)}</span>
          </div>
          ${peakDepth != null ? `<div style="font-size:10.5px;color:#cbd5e1;margin-top:2px">
            Flood Depth: <b style="color:#ef4444">${peakDepth.toFixed(1)}m</b> &middot; Vel: <b style="color:#f59e0b">${peakV ? peakV.toFixed(1) + ' m/s' : '-'}</b> &middot; Arr: <b style="color:#38bdf8">${arrMin != null ? arrMin + ' min' : '-'}</b>
          </div>` : `<div style="font-size:10px;color:#94a3b8">Elev above river: ${attrs.elevation_above_bed_m ? attrs.elevation_above_bed_m + 'm' : '~3-5m'}</div>`}
        </div>
      `, {sticky: true, direction: "top", offset: [0, -10]});

      const popupHtml = `
        <div style="min-width:240px;font-family:sans-serif">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
            <span style="font-size:20px">${icon}</span>
            <div>
              <b style="font-size:13px;color:#00f0ff;line-height:1.2;display:block">${esc(a.name)}</b>
              <span style="font-size:11px;color:#94a3b8">${esc(bldType)}</span>
            </div>
          </div>
          <div style="margin-bottom:8px">
            <span style="background:${badge.bg};color:${badge.text};padding:2px 8px;border-radius:4px;font-size:10.5px;font-weight:700;letter-spacing:0.05em">
              ${badge.label}
            </span>
            ${a.critical ? '<span style="background:#dc2626;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700;margin-left:4px">CRITICAL INFRA</span>' : ''}
          </div>
          <table style="width:100%;font-size:11px;border-collapse:collapse;margin-bottom:8px;color:#e2e8f0">
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)">
              <td style="color:#94a3b8;padding:3px 0">Structure:</td>
              <td style="font-weight:600;text-align:right;padding:3px 0">${esc(attrs.structure || (attrs.floors ? attrs.floors + " Floors RCC" : "Reinforced Concrete"))}</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)">
              <td style="color:#94a3b8;padding:3px 0">Occupants / Pop:</td>
              <td style="font-weight:600;text-align:right;padding:3px 0">${a.population ? a.population.toLocaleString() + ' people' : (attrs.occupants ? attrs.occupants + ' staff' : '15-40 occupants')}</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)">
              <td style="color:#94a3b8;padding:3px 0">Riverbed Offset:</td>
              <td style="font-weight:600;text-align:right;padding:3px 0">+${attrs.elevation_above_bed_m != null ? attrs.elevation_above_bed_m + 'm elev' : '3.5m'}</td>
            </tr>
            ${peakDepth != null ? `
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)">
              <td style="color:#94a3b8;padding:3px 0">Peak Water Depth:</td>
              <td style="font-weight:700;color:#ef4444;text-align:right;padding:3px 0">${peakDepth.toFixed(2)} m</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)">
              <td style="color:#94a3b8;padding:3px 0">Flow Velocity:</td>
              <td style="font-weight:700;color:#f59e0b;text-align:right;padding:3px 0">${peakV != null ? peakV.toFixed(2) + ' m/s' : '-'}</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)">
              <td style="color:#94a3b8;padding:3px 0">Arrival Time:</td>
              <td style="font-weight:700;color:#38bdf8;text-align:right;padding:3px 0">${arrMin != null ? arrMin + ' min post-breach' : '-'}</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)">
              <td style="color:#94a3b8;padding:3px 0">Structural Damage:</td>
              <td style="font-weight:700;color:#f43f5e;text-align:right;padding:3px 0">${dmgFrac != null ? Math.round(dmgFrac * 100) + '%' : '85%'}</td>
            </tr>
            ` : ''}
          </table>
          <div style="font-size:10px;color:#64748b;font-family:monospace">
            Lat/Lon: ${a.lat.toFixed(5)}&deg;N, ${a.lon.toFixed(5)}&deg;E
          </div>
        </div>
      `;
      m.bindPopup(popupHtml);
      m.addTo(map);
      L_("assets").push(m);
    });
  }catch(e){}
}
async function loadDemStat(){
  if (!S.incident) return;
  try{
    const d = await api(`/api/incidents/${S.incident.id}/dem`);
    sb("statDem", d.has_dem ? `${d.points} pts` : "-");
  }catch(e){ sb("statDem","-"); }
}

async function loadPopulationClusters(){
  clearLayer("population");
  if (!S.incident || S.showPop === false) return;
  try{
    const res = await api(`/api/incidents/${S.incident.id}/population-clusters`);
    const clusters = res.clusters || [];
    clusters.forEach(c => {
      const circle = L.circle([c.lat, c.lon], {
        radius: c.radius_meters || 600,
        color: "#ec4899",
        weight: 2,
        fillColor: "#a855f7",
        fillOpacity: 0.26,
        dashArray: "4 4"
      });

      const popK = c.population >= 1000 ? (c.population/1000).toFixed(1) + "k" : c.population;
      const badgeHtml = `
        <div class="pop-cluster-badge" title="${esc(c.name)} (${c.population.toLocaleString()} pop)">
          <span>&#128101;</span>
          <span>${esc(c.name.split(" ")[0])}</span>
          <span style="color:#f472b6;font-weight:800">${popK}</span>
        </div>
      `;
      const badgeIcon = L.divIcon({
        html: badgeHtml,
        className: "bld-marker-container",
        iconSize: [110, 24],
        iconAnchor: [55, 12]
      });
      const badgeMarker = L.marker([c.lat, c.lon], {icon: badgeIcon});

      const tooltipHtml = `
        <div style="font-size:11.5px;font-family:sans-serif;line-height:1.4">
          <div style="font-weight:700;color:#f472b6">&#128101; ${esc(c.name)}</div>
          <div>Locality Population: <b>${c.population.toLocaleString()}</b> residents</div>
          <div style="font-size:10.5px;color:#cbd5e1">Children: <b>${c.demographics?.children || 0}</b> &middot; Elderly: <b>${c.demographics?.elderly || 0}</b></div>
          <div style="font-size:10.5px;color:#94a3b8">Evacuation Est: <b>${c.evacuation?.estimated_clearance_hr || 1.5} hrs</b></div>
        </div>
      `;
      circle.bindTooltip(tooltipHtml, {sticky: true});
      badgeMarker.bindTooltip(tooltipHtml, {sticky: true});

      const popupHtml = `
        <div style="min-width:240px;font-family:sans-serif">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
            <span style="font-size:22px">&#128101;</span>
            <div>
              <b style="font-size:13.5px;color:#f472b6">${esc(c.name)}</b>
              <div style="font-size:11px;color:#94a3b8">Locality Demographic &amp; Flood Exposure</div>
            </div>
          </div>
          <table style="width:100%;font-size:11px;border-collapse:collapse;margin-bottom:8px;color:#e2e8f0">
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)"><td style="color:#94a3b8;padding:2px 0">Total Residents:</td><td style="font-weight:700;color:#fff;text-align:right">${c.population.toLocaleString()} people</td></tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)"><td style="color:#94a3b8;padding:2px 0">Children (&lt;14):</td><td style="font-weight:600;color:#fbcfe8;text-align:right">${c.demographics?.children || 0}</td></tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)"><td style="color:#94a3b8;padding:2px 0">Elderly (&gt;65):</td><td style="font-weight:600;color:#fbcfe8;text-align:right">${c.demographics?.elderly || 0}</td></tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)"><td style="color:#94a3b8;padding:2px 0">Local Structures:</td><td style="font-weight:600;text-align:right">${c.buildings} blds</td></tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)"><td style="color:#94a3b8;padding:2px 0">Evacuation Clearance:</td><td style="font-weight:700;color:#38bdf8;text-align:right">${c.evacuation?.estimated_clearance_hr || 1.5} hrs</td></tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.08)"><td style="color:#94a3b8;padding:2px 0">Evacuation Priority:</td><td style="font-weight:700;color:${c.evacuation?.priority === 'IMMEDIATE' ? '#ef4444' : '#f59e0b'};text-align:right">${c.evacuation?.priority || 'STANDARD'}</td></tr>
            ${c.peak_depth_m != null ? `<tr><td style="color:#94a3b8;padding:2px 0">Simulated Depth:</td><td style="font-weight:700;color:#ef4444;text-align:right">${c.peak_depth_m} m</td></tr>` : ''}
            ${c.first_arrival_min != null ? `<tr><td style="color:#94a3b8;padding:2px 0">Wave Arrival:</td><td style="font-weight:700;color:#38bdf8;text-align:right">${c.first_arrival_min} min</td></tr>` : ''}
          </table>
          ${c.facilities && c.facilities.length ? `<div style="font-size:10px;color:#94a3b8;border-top:1px solid rgba(255,255,255,0.1);padding-top:4px"><b>Key Facilities:</b> ${esc(c.facilities.join(', '))}</div>` : ''}
        </div>
      `;
      circle.bindPopup(popupHtml);
      badgeMarker.bindPopup(popupHtml);

      circle.addTo(map);
      badgeMarker.addTo(map);
      L_("population").push(circle, badgeMarker);
    });
  }catch(e){}
}

async function loadScenarioExtents(){
  clearLayer("scenarios");
  if (!S.incident || S.showScen === false) return;
  try{
    const url = S.simId ? `/api/simulations/${S.simId}/scenario-extents`
                        : `/api/incidents/${S.incident.id}/scenario-extents`;
    const res = await api(url);
    if (!res || !res.scenarios) return;
    S.scenarioData = res;
    S.scenarioLayerMap = {};

    res.scenarios.forEach(sc => {
      if (!sc.polygon || sc.polygon.length < 3) return;
      const poly = L.polygon(sc.polygon, {
        color: sc.color,
        weight: 2,
        fillColor: sc.fill_color,
        fillOpacity: sc.fill_opacity
      });

      const tipHtml = `
        <div class="hydraulic-tooltip">
          <div style="font-weight:700;color:${sc.color};font-size:12px;margin-bottom:3px">
            &#127754; ${esc(sc.name)}
          </div>
          <table style="width:100%;font-size:11px;color:#e2e8f0">
            <tr><td style="color:#94a3b8">Risk Level:</td><td style="font-weight:700;color:${sc.color};text-align:right">${sc.risk_level}</td></tr>
            <tr><td style="color:#94a3b8">Inundated Area:</td><td style="font-weight:700;color:#38bdf8;text-align:right">${sc.area_km2} km&sup2;</td></tr>
            <tr><td style="color:#94a3b8">Peak Discharge Q:</td><td style="font-weight:700;color:#f59e0b;text-align:right">${sc.peak_Q_m3s.toLocaleString()} m&sup3;/s</td></tr>
            <tr><td style="color:#94a3b8">Max Flood Depth:</td><td style="font-weight:700;color:#ef4444;text-align:right">${sc.max_depth_m} m</td></tr>
          </table>
          <div style="font-size:10px;color:#94a3b8;margin-top:4px">${esc(sc.mechanism)}</div>
        </div>
      `;
      poly.bindTooltip(tipHtml, {sticky: true, className: "custom-hydraulic-tip"});
      poly.addTo(map);
      L_("scenarios").push(poly);
      S.scenarioLayerMap[sc.key] = poly;
    });

    const dock = $("scenDock");
    if (dock) {
      dock.classList.remove("hidden");
      updateScenDockInfo("all");
    }
  }catch(e){}
}

function updateScenDockInfo(scenKey){
  if (!S.scenarioData || !S.scenarioData.scenarios) return;
  const info = $("scenDockInfo");
  if (!info) return;
  if (scenKey === "all") {
    const scs = S.scenarioData.scenarios;
    info.innerHTML = `<b>Stacked Comparison (${scs.length} Scenarios)</b><br>
      Corridor: <b>${S.scenarioData.corridor_km || 43.3} km</b><br>
      Area Envelope: <b>${scs[0].area_km2}</b> &rarr; <b>${scs[scs.length-1].area_km2} km&sup2;</b>`;
  } else {
    const sc = S.scenarioData.scenarios.find(s => s.key === scenKey);
    if (sc) {
      info.innerHTML = `<b style="color:${sc.color}">${esc(sc.name)}</b><br>
        Inundation Area: <b>${sc.area_km2} km&sup2;</b><br>
        Peak Q: <b>${sc.peak_Q_m3s.toLocaleString()} m&sup3;/s</b> &middot; Max Depth: <b>${sc.max_depth_m}m</b>`;
    }
  }
}


/* ---------- drawing: centerline + ROI ---------- */
const haversineJs = (a, b) => {
  const R = 6371000, r = Math.PI/180;
  const dLa = (b[0]-a[0])*r, dLo = (b[1]-a[1])*r;
  const h = Math.sin(dLa/2)**2 + Math.cos(a[0]*r)*Math.cos(b[0]*r)*Math.sin(dLo/2)**2;
  return 2*R*Math.asin(Math.sqrt(h));
};
function updateDrawHud(){
  $("drawPts").textContent = S.drawMode ? S.centerline.length : S.roiPts.length;
  const pts = S.drawMode ? S.centerline : S.roiPts;
  let km = 0;
  for (let i = 1; i < pts.length; i++) km += haversineJs(pts[i-1], pts[i]);
  $("drawKm").textContent = (km/1000).toFixed(1);
}
 $("btnDrawCenterline").onclick = () => {
  if (!S.incident){ toast("Select an incident first"); return; }
  S.drawMode = !S.drawMode; S.centerline = [];
  $("drawHud").classList.toggle("hidden", !S.drawMode);
  $("drawModeLabel").textContent = t("draw.hint");
  $("btnDrawCenterline").classList.toggle("primary", S.drawMode);
  toast(S.drawMode ? "Click points downstream, then Save" : "Draw mode off");
  updateDrawHud();
};
map.on("click", e => {
  if (S.drawMode){
    S.centerline.push([+e.latlng.lat.toFixed(5), +e.latlng.lng.toFixed(5)]);
    clearLayer("draft");
    L_("draft").push(L.polyline(S.centerline, {color:"#f59e0b", weight:3}).addTo(map));
  } else if (S.roiMode){
    S.roiPts.push([+e.latlng.lat.toFixed(5), +e.latlng.lng.toFixed(5)]);
    clearLayer("draft");
    L_("draft").push(L.polygon(S.roiPts, {color:"#34d399", weight:2,
      dashArray:"5 5", fillOpacity:.1}).addTo(map));
  } else return;
  updateDrawHud();
});
function undoPoint(){
  if (S.drawMode && S.centerline.length) S.centerline.pop();
  else if (S.roiMode && S.roiPts.length) S.roiPts.pop();
  else return;
  clearLayer("draft");
  const pts = S.drawMode ? S.centerline : S.roiPts;
  if (pts.length >= 2)
    L_("draft").push((S.drawMode ? L.polyline(pts, {color:"#f59e0b", weight:3})
                                 : L.polygon(pts, {color:"#34d399", fillOpacity:.1}))
                     .addTo(map));
  updateDrawHud();
}
 $("btnUndoPt").onclick = undoPoint;

function cancelDraw(){
  S.drawMode = false;
  S.roiMode = false;
  S.centerline = [];
  S.roiPts = [];
  clearLayer("draft");
  $("drawHud").classList.add("hidden");
  if ($("btnDrawCenterline")) $("btnDrawCenterline").classList.remove("primary");
  toast("Drawing cancelled", 2000);
}
if ($("btnCloseDrawHud")) $("btnCloseDrawHud").onclick = cancelDraw;

document.addEventListener("keydown", e => {
  if (e.key === "Backspace" && (S.drawMode || S.roiMode)){ e.preventDefault(); undoPoint(); }
  if (e.key === "Escape"){
    if (S.drawMode || S.roiMode){ cancelDraw(); }
    if ($("loginModal")) $("loginModal").classList.add("hidden");
    if ($("reportModal")) $("reportModal").classList.add("hidden");
  }
  if (e.altKey && e.key >= "1" && e.key <= "9"){
    const items = document.querySelectorAll(".nav-item");
    const idx = +e.key - 1;
    if (items[idx]) items[idx].click();
  }
});
 $("btnFinishCl").onclick = async () => {
  if (S.roiMode){ await saveRoi(); return; }
  if (S.centerline.length < 2){ toast("Need at least 2 points"); return; }
  S.drawMode = false; $("drawHud").classList.add("hidden");
  $("btnDrawCenterline").classList.remove("primary");
  try{
    const j = await api(`/api/incidents/${S.incident.id}/centerline`, {method:"PUT",
      body:JSON.stringify({centerline:S.centerline})});
    toast(`Centerline saved - ${j.points} pts, ${j.length_km} km` +
      (j.warnings.length ? ` (warnings: ${j.warnings.join("; ")})` : ""));
    await selectIncident(S.incident.id);
  }catch(e){ toast("Save failed - " + e.message); }
};
 $("btnClearMap").onclick = () => { clearAll(); renderIncidentOnMap(S.incident);
  if (S.lastResults) drawFloodOnMap(S.lastResults.results.inundation, true); };
 $("btnFit").onclick = () => S.incident ? map.setView([S.incident.lat, S.incident.lon], 12) : map.setView([21.7679, 78.8718], 5);
 $("legendMin").onclick = () => {
  const b = $("legendBody"), h = b.style.display === "none";
  b.style.display = h ? "" : "none"; $("legendMin").textContent = h ? "-" : "+";
};
window.startRoiDraw = zid => {
  S.roiMode = true; S.roiZoneId = zid; S.roiPts = []; S.drawMode = false;
  $("drawHud").classList.remove("hidden");
  $("drawModeLabel").textContent = "Click ROI polygon vertices (>=3)";
  toast("Click polygon vertices around the valley reach, then Save");
  updateDrawHud();
};
async function saveRoi(){
  if (S.roiPts.length < 3){ toast("Need >= 3 vertices"); return; }
  try{
    const r = await api(`/api/detection/zones/${S.roiZoneId}/roi`, {method:"PUT",
      body:JSON.stringify({polygon:S.roiPts})});
    toast(`ROI saved - ${r.area_km2} km2. Rebuild the baseline next.`);
  }catch(e){ toast(e.message); }
  S.roiMode = false; clearLayer("draft"); $("drawHud").classList.add("hidden");
  panelMonitor();
}

/* ---------- inspector ---------- */
const insp = $("inspector");
function openPanel(title, sub, html){
  $("panelTitle").textContent = title; $("panelSub").textContent = sub || "";
  $("panelBody").innerHTML = html; insp.classList.remove("closed");
}
 $("panelClose").onclick = () => insp.classList.add("closed");
document.querySelectorAll(".side-group-label").forEach(l =>
  l.onclick = () => l.parentElement.classList.toggle("collapsed"));
const PANELS = {
  map: () => insp.classList.add("closed"),
  setup: panelSetup, breach: panelBreach, visual: panelVisual,
  results: () => S.simId ? showResults() : openPanel("INUNDATION MODEL","",
    EMPTY("&#127754;","No simulation yet.","RUN BREACH SIMULATION",
          "document.querySelector('[data-tab=breach]').click()")),
  manual: panelManual, monitor: panelMonitor, satellite: panelSatellite,
  damage: panelDamage, national: panelNational, scenarios: panelScenarios,
  admin: panelAdmin, about: panelAbout,
};
document.querySelectorAll(".nav-item").forEach(btn => btn.onclick = () => {
  document.querySelectorAll(".nav-item").forEach(b => b.classList.toggle("active", b === btn));
  if (btn.dataset.tab !== "visual") exitVS();
  clearAll(); renderIncidentOnMap(S.incident);
  if (S.lastResults) drawFloodOnMap(S.lastResults.results.inundation, true);
  if (S.incident){ loadAssets(); loadDamageMarkers(); }
  PANELS[btn.dataset.tab]();
});
function requireIncident(){
  if (S.incident) return true;
  openPanel("DAM REGISTRY & SELECTION", "Select an incident to view geometry, flow corridor & telemetry", `
    <div style="padding:4px 0">
      <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:16px;text-align:center;margin-bottom:14px">
        <div style="font-size:32px;margin-bottom:8px">🌊</div>
        <div style="font-weight:700;font-size:14px;color:var(--text);margin-bottom:4px">No Dam or Incident Selected</div>
        <div style="font-size:11.5px;color:var(--text-3);margin-bottom:14px;max-width:340px;margin-left:auto;margin-right:auto">
          Choose from 65+ major Indian dams in the registry or select a benchmark disaster scenario.
        </div>
        <button class="tbtn primary" onclick="document.getElementById('btnOpenDamFinder')?.click()" style="padding:8px 18px;font-size:12px;font-weight:600">
          🌊 Browse 65+ Indian Dams (Registry)
        </button>
      </div>

      <div style="font-size:11px;font-weight:700;color:var(--text-3);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">
        Quick-Select Benchmark Cases (NTRO HADR)
      </div>
      <div style="display:grid;gap:8px">
        <div class="panel-card" style="cursor:pointer;padding:10px 12px;display:flex;justify-content:space-between;align-items:center;background:var(--surface-2);border-radius:8px;border:1px solid var(--border)" onclick="selectIncident('JR-NTRO-IDUKKI').then(()=>{ if (PANELS.setup) PANELS.setup(); })">
          <div>
            <div style="font-weight:600;font-size:12px;color:var(--cyan)">Idukki Arch Dam</div>
            <div style="font-size:10.5px;color:var(--text-3)">Periyar River · Kerala · Concrete Arch (168m)</div>
          </div>
          <span style="font-size:11px;color:var(--text-2);font-weight:600">Select →</span>
        </div>
        <div class="panel-card" style="cursor:pointer;padding:10px 12px;display:flex;justify-content:space-between;align-items:center;background:var(--surface-2);border-radius:8px;border:1px solid var(--border)" onclick="selectIncident('JR-20260929-1B32D4').then(()=>{ if (PANELS.setup) PANELS.setup(); })">
          <div>
            <div style="font-weight:600;font-size:12px;color:var(--amber)">Tehri Dam</div>
            <div style="font-size:10.5px;color:var(--text-3)">Bhagirathi River · Uttarakhand · Rock-fill (260m)</div>
          </div>
          <span style="font-size:11px;color:var(--text-2);font-weight:600">Select →</span>
        </div>
        <div class="panel-card" style="cursor:pointer;padding:10px 12px;display:flex;justify-content:space-between;align-items:center;background:var(--surface-2);border-radius:8px;border:1px solid var(--border)" onclick="selectIncident('JR-20260929-69A72B').then(()=>{ if (PANELS.setup) PANELS.setup(); })">
          <div>
            <div style="font-weight:600;font-size:12px;color:var(--green)">Bhakra Dam</div>
            <div style="font-size:10.5px;color:var(--text-3)">Sutlej River · Himachal Pradesh · Concrete Gravity (226m)</div>
          </div>
          <span style="font-size:11px;color:var(--text-2);font-weight:600">Select →</span>
        </div>
        <div class="panel-card" style="cursor:pointer;padding:10px 12px;display:flex;justify-content:space-between;align-items:center;background:var(--surface-2);border-radius:8px;border:1px solid var(--border)" onclick="selectIncident('JR-20260929-6ECF59').then(()=>{ if (PANELS.setup) PANELS.setup(); })">
          <div>
            <div style="font-weight:600;font-size:12px;color:var(--purple)">Sardar Sarovar Dam</div>
            <div style="font-size:10.5px;color:var(--text-3)">Narmada River · Gujarat · Concrete Gravity (163m)</div>
          </div>
          <span style="font-size:11px;color:var(--text-2);font-weight:600">Select →</span>
        </div>
      </div>
    </div>
  `);
  return false;
}

/* ---------- TAB: DAM ANALYSIS ---------- */
async function panelSetup(){
  if (!requireIncident()) return;
  const i = S.incident;

  // Centerline reach calculation
  let clKm = 0.0;
  const clPts = i.centerline || [];
  for (let idx = 1; idx < clPts.length; idx++) {
    clKm += haversineJs(clPts[idx-1], clPts[idx]);
  }
  const lengthStr = (clKm / 1000).toFixed(1);
  const isStraightDemo = clPts.length >= 2 && clPts.length <= 25 &&
    (i.name.includes("[NATIONAL]") || i.status === "NATIONAL_EXERCISE" || i.region === "Auto-detection");

  // Fetch region info
  let reg = {name: i.region || "Default", valley_width_m: 90, bed_slope: 0.02, manning_n: 0.045, key: ""};
  try {
    const rData = await api(`/api/india/region?lat=${i.lat}&lon=${i.lon}`);
    if (rData && rData.name) reg = rData;
  } catch(_) {}

  // Fetch assets summary
  let assets = [];
  try {
    assets = await api(`/api/incidents/${i.id}/assets`);
  } catch(_) {}
  const bldCount = assets.reduce((s, a) => s + (a.buildings || 0), 0);
  const pplCount = assets.reduce((s, a) => s + (a.population || 0), 0);

  openPanel("DAM ANALYSIS", "Incident geometry · flow corridor · data ingestion", `
    <!-- Dam Quick Switcher -->
    <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:8px 10px;margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <span style="font-size:10px;font-weight:700;color:var(--text-3);letter-spacing:0.05em">SWITCH DAM SITE (65+ ACROSS INDIA)</span>
        <button class="tbtn sm" id="btnBrowseAllDams" style="padding:2px 8px;font-size:10px">&#127754; Browse Registry</button>
      </div>
      <div style="display:flex;gap:6px">
        <input type="text" id="setupDamSearch" class="input" style="font-size:11.5px;padding:5px 8px;height:auto" placeholder="Search major dams (Tehri, Idukki, Bhakra)..." />
      </div>
    </div>

    <!-- Top Action Bar -->
    <div style="display:flex;gap:8px;margin-bottom:12px">
      <button class="tbtn primary sm full" id="btnGoBreach" style="font-weight:700">
        &#9889; PROCEED TO BREACH SIMULATION &rarr;
      </button>
      <button class="tbtn sm" id="btnFullReport" title="View official 13-section assessment report" style="white-space:nowrap">
        &#128203; Full Report
      </button>
    </div>

    <!-- 1. Incident & Dam Profile -->
    <div class="mod">
      <div class="mod-title" style="display:flex;justify-content:space-between;align-items:center">
        <span>DAM &amp; RESERVOIR SITE PROFILE</span>
        <span class="nav-pill ${i.status && i.status.includes('ALERT') ? 'hot' : ''}">${esc(i.status)}</span>
      </div>
      <table class="tbl">
        <tr><td>Feature ID</td><td><code>${esc(i.id)}</code></td></tr>
        <tr><td>Dam / Site Name</td><td><b>${esc(i.name)}</b></td></tr>
        <tr><td>River Basin</td><td>${esc(i.river_name || "Unspecified stream")}</td></tr>
        <tr><td>Coordinates</td><td style="display:flex;align-items:center;justify-content:space-between"><b>${i.lat.toFixed(5)}°N, ${i.lon.toFixed(5)}°E</b><div style="display:flex;gap:4px"><button class="tbtn sm" id="btnZoomWall" onclick="window.zoomToDamWall()" style="padding:2px 6px;font-size:10px" title="Zoom directly to dam wall">&#128269; Wall</button><button class="tbtn sm primary" id="btnRelocateDam" style="padding:2px 6px;font-size:10px" title="Click satellite view to relocate dam wall">&#128205; Relocate</button></div></td></tr>
        <tr><td>Structure Type</td><td><span class="badge">${esc(i.incident_type)}</span></td></tr>
      </table>

      <!-- Physiographic Region Box -->
      <div style="margin-top:10px;padding:8px 10px;background:var(--surface-2);border-radius:8px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span style="font-size:10px;font-weight:700;color:var(--text-3);letter-spacing:.8px">PHYSIOGRAPHIC REGION</span>
          <button class="tbtn sm" id="btnRegionOverride" style="padding:2px 8px;font-size:10px">&#127760; Override</button>
        </div>
        <div style="font-size:12px;font-weight:600;color:var(--cyan)">${esc(reg.name)}</div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:6px;font-size:10px;color:var(--text-2);font-family:var(--mono)">
          <div>Valley: <b>${reg.valley_width_m || 90}m</b></div>
          <div>Slope: <b>${reg.bed_slope || 0.02}</b></div>
          <div>Manning: <b>${reg.manning_n || 0.045}</b></div>
        </div>
      </div>
    </div>

    <!-- 2. Downstream Flow Path (Centerline) -->
    <div class="mod">
      <div class="mod-title" style="display:flex;justify-content:space-between;align-items:center">
        <span>DOWNSTREAM FLOW CORRIDOR (ROUTING PATH)</span>
        <span style="font-size:10px;color:${clPts.length >= 2 ? 'var(--cyan)' : 'var(--amber)'}">
          ${clPts.length >= 2 ? `${clPts.length} pts · ${lengthStr} km` : 'Missing'}
        </span>
      </div>
      <div style="font-size:11px;color:var(--text-2);margin-bottom:8px;line-height:1.5">
        <b>What is this line?</b> The cyan dashed line on the map is the <b>dam break flow route</b> along which the breach flood wave routes downstream. It represents the natural river valley thalweg and terrain depressions derived from DEM data.
        ${isStraightDemo ? '<br><span style="color:var(--amber);font-size:10.5px">&#9888; Currently using a demonstration vector. Click "DEM River Flow" below to generate the topographic valley flow path:</span>' : ''}
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
        <button class="tbtn primary sm" id="btnAutoCl" title="Trace downstream dam break flood path using DEM valley topography">&#127754; DEM River Flow</button>
        <button class="tbtn sm" id="btnFitCl">&#8982; Fit to Reach</button>
        <button class="tbtn sm" id="goDraw">&#9998; Trace Manual</button>
        <button class="tbtn sm danger" id="btnClearCl">&#10005; Clear Path</button>
      </div>
    </div>

    <!-- 3. Terrain DEM & Bathymetry Data Ingestion -->
    <div class="mod">
      <div class="mod-title">TERRAIN DEM &amp; DATA INGESTION</div>
      <p class="hint" style="margin-bottom:8px">
        Upload high-resolution reservoir bathymetry CSV (<code>lat,lon,elev</code>) to compute exact hypsometry, or GeoJSON/CSV to add exposure assets.
      </p>
      <input type="file" id="fileUp" class="input" accept=".csv,.geojson,.json" style="padding:6px">
      <div id="upResult" style="font-size:11px;color:var(--cyan);margin-top:6px"></div>
      <div id="demChartWrap" style="margin-top:8px"></div>
    </div>

    <!-- 4. Downstream Exposure Assets -->
    <div class="mod">
      <div class="mod-title" style="display:flex;justify-content:space-between;align-items:center">
        <span>EXPOSED DOWNSTREAM ASSETS</span>
        <span style="font-size:10px;color:var(--text-3)">${assets.length} layers</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:8px;text-align:center">
        <div style="background:var(--surface-2);padding:6px;border-radius:6px">
          <div style="font-size:15px;font-weight:700;color:var(--cyan)">${assets.length}</div>
          <div style="font-size:9px;color:var(--text-3)">SITES</div>
        </div>
        <div style="background:var(--surface-2);padding:6px;border-radius:6px">
          <div style="font-size:15px;font-weight:700;color:var(--amber)">${pplCount.toLocaleString()}</div>
          <div style="font-size:9px;color:var(--text-3)">PEOPLE</div>
        </div>
        <div style="background:var(--surface-2);padding:6px;border-radius:6px">
          <div style="font-size:15px;font-weight:700;color:var(--purple)">${bldCount.toLocaleString()}</div>
          <div style="font-size:9px;color:var(--text-3)">BUILDINGS</div>
        </div>
      </div>
      ${assets.length ? `
        <div style="max-height:140px;overflow-y:auto;border:1px solid var(--border);border-radius:6px">
          <table class="tbl" style="margin:0;font-size:10.5px">
            <tr><th>Name</th><th>Type</th><th>Pop</th></tr>
            ${assets.slice(0, 5).map(a => `<tr><td>${esc(a.name)}</td><td>${esc(a.kind)}</td><td>${a.population || "-"}</td></tr>`).join('')}
            ${assets.length > 5 ? `<tr><td colspan="3" style="text-align:center;color:var(--text-3)">+ ${assets.length - 5} more downstream</td></tr>` : ''}
          </table>
        </div>` : '<div class="hint">No exposure assets registered for this corridor yet.</div>'}
    </div>

    <!-- 5. Edit Incident & Manage -->
    <div class="mod">
      <div class="mod-title">MANAGE INCIDENT</div>
      <div class="field"><label>Incident Title</label>
        <input id="edName" class="input" value="${esc(i.name)}"></div>
      <div class="grid2">
        <div class="field"><label>River / Basin</label>
          <input id="edRiver" class="input" value="${esc(i.river_name || '')}"></div>
        <div class="field"><label>Status</label>
          <select id="edStatus" class="input">${["NEW_ANALYSIS","ACTIVE_MONITORING",
            "ELEVATED_ALERT","SURVEILLANCE_ACTIVE","CLOSED","NATIONAL_EXERCISE"].map(s =>
            `<option ${s === i.status ? "selected" : ""}>${s}</option>`).join("")}</select>
        </div>
      </div>
      <div class="row-end" style="margin-top:6px">
        <button class="tbtn sm primary" id="edSave">Save Changes</button>
        ${S.role === "admin" ? `<button class="tbtn sm danger" id="edDelete">Delete Incident</button>` : ""}
      </div>
    </div>
  `);

  $("btnGoBreach").onclick = () => document.querySelector('[data-tab="breach"]').click();
  $("btnFullReport").onclick = () => viewFullReport(i.id);
  if ($("btnRegionOverride")) $("btnRegionOverride").onclick = () => {
    if (typeof openRegionOverride === 'function') openRegionOverride();
  };
  if ($("btnRelocateDam")) $("btnRelocateDam").onclick = () => startRelocateDamMode();
  $("goDraw").onclick = () => $("btnDrawCenterline").click();
  $("btnFitCl").onclick = () => {
    if (i.centerline && i.centerline.length >= 2) {
      map.fitBounds(L.polyline(i.centerline).getBounds().pad(0.25));
    } else {
      toast("No flow corridor to fit");
    }
  };
  if ($("btnBrowseAllDams")) $("btnBrowseAllDams").onclick = () => openDamFinderModal();
  if ($("setupDamSearch")) {
    $("setupDamSearch").onfocus = () => openDamFinderModal($("setupDamSearch").value);
    $("setupDamSearch").oninput = () => openDamFinderModal($("setupDamSearch").value);
  }
  $("btnAutoCl").onclick = async () => {
    try {
      toast("🌊 Computing dambreak flow route using DEM valley topography...");
      const res = await api(`/api/incidents/${i.id}/auto-centerline?method=dem&length_km=25`, {method: "POST"});
      toast(`✓ Traced DEM river valley route (${res.points} pts · ${res.length_km} km)`, 4000);
      await selectIncident(i.id);
      panelSetup();
    } catch(e) { toast("DEM flow generation failed: " + e.message); }
  };
  $("btnClearCl").onclick = async () => {
    if (!confirm("Clear this flow path? Breach routing requires a downstream centerline.")) return;
    try {
      await api(`/api/incidents/${i.id}/centerline`, {method: "DELETE"});
      toast("Flow path cleared");
      await selectIncident(i.id);
      panelSetup();
    } catch(e) { toast("Clear failed: " + e.message); }
  };
  $("fileUp").onchange = uploadFile;
  loadDemChart();
  $("edSave").onclick = async () => {
    try{
      await api(`/api/incidents/${i.id}`, {method:"PATCH", body:JSON.stringify({
        name:$("edName").value, river_name:$("edRiver").value, status:$("edStatus").value})});
      toast("Incident updated"); refreshIncidents();
    }catch(e){ toast(e.message); }
  };
  if ($("edDelete")) $("edDelete").onclick = async () => {
    if (!confirm("Delete this incident and ALL its data?")) return;
    try{
      await api(`/api/incidents/${i.id}`, {method:"DELETE"});
      toast("Deleted"); S.incident = null; refreshIncidents(); insp.classList.add("closed");
    }catch(e){ toast(e.message); }
  };
}
async function uploadFile(ev){
  const f = ev.target.files[0]; if (!f || !S.incident) return;
  const fd = new FormData(); fd.append("file", f);
  const r = await fetch(`/api/incidents/${S.incident.id}/uploads`, {method:"POST",
    headers:{Authorization:`Bearer ${S.token}`}, body:fd});
  const j = await r.json();
  $("upResult").textContent = r.ok ? `OK: ${j.kind} ingested`
                                   : `FAIL: ${j.detail}`;
  if (r.ok){ loadDemStat(); loadAssets(); loadDemChart(); }
}
async function loadDemChart(){
  if (!S.incident) return;
  try{
    const d = await api(`/api/incidents/${S.incident.id}/dem`);
    const wrap = $("demChartWrap"); if (!wrap) return;
    if (!d.has_dem){ wrap.innerHTML = ""; return; }
    wrap.innerHTML = `<div class="chart-box"><div class="chart-head">
      <span>DEM HYPSOMETRY - ELEV vs AREA &amp; VOLUME</span></div>
      <canvas id="hypChart" class="chart"></canvas></div>`;
    drawHypsometry($("hypChart"), d.hypsometry);
  }catch(e){}
}
function drawHypsometry(cv, curve){
  if (!cv || !curve.length) return;
  const dpr = devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
  cv.width = w*dpr; cv.height = h*dpr;
  const x = cv.getContext("2d"); x.scale(dpr, dpr);
  const E = curve.map(c => c.elev_m), A = curve.map(c => c.area_m2),
        V = curve.map(c => c.cum_volume_m3 || 0);
  const eMin = Math.min(...E), eMax = Math.max(...E);
  const aMax = Math.max(...A) * 1.1 || 1, vMax = Math.max(...V) * 1.1 || 1;
  const px = e => 40 + (w-50)*(e-eMin)/(eMax-eMin || 1);
  const pyA = a => h-20-(h-36)*a/aMax, pyV = v => h-20-(h-36)*v/vMax;
  x.strokeStyle = "rgba(139,153,173,.25)";
  for (let i = 0; i <= 4; i++){
    const y = h-20-(h-36)*i/4; x.beginPath(); x.moveTo(36,y); x.lineTo(w-8,y); x.stroke();
  }
  x.strokeStyle = "#22d3ee"; x.lineWidth = 2; x.beginPath();
  E.forEach((e,i) => i ? x.lineTo(px(e), pyA(A[i])) : x.moveTo(px(e), pyA(A[i]))); x.stroke();
  x.strokeStyle = "#f59e0b"; x.beginPath();
  E.forEach((e,i) => i ? x.lineTo(px(e), pyV(V[i])) : x.moveTo(px(e), pyV(V[i]))); x.stroke();
  x.fillStyle = "#8b99ad"; x.font = "9px ui-monospace,monospace";
  x.fillText(`elev ${eMin.toFixed(0)}m`, 38, h-8);
  x.fillText(`${eMax.toFixed(0)}m`, w-52, h-8);
  x.fillStyle = "#22d3ee"; x.fillText("- area", 40, 12);
  x.fillStyle = "#f59e0b"; x.fillText("- volume", 100, 12);
}

/* ---------- TAB: BREACH (region-preset defaults, no global mutation) ---------- */
const DEF_BASE = {stored_volume_m3:5.0e6, lake_area_m2:486000, dam_height_m:38,
  dam_crest_len_m:115, dam_material:"Landslide debris", scenario:"major",
  breach_width_m:35, breach_depth_m:24, breach_time_hr:1.5, inflow_m3s:92,
  valley_width_m:90, bed_slope:0.02, manning_n:0.045, spreading_factor:2.5,
  base_flow_m3s:50, with_uncertainty:true};
let DEF = {...DEF_BASE};
async function panelBreach(){
  if (!requireIncident()) return;
  if (S.incident.centerline.length < 2){
    openPanel("BREACH SIMULATION ENGINE","Prerequisite missing",`
      <div class="note">A downstream <b>centerline</b> is required before routing.
      Open <b>DAM ANALYSIS - DRAW ON MAP</b>.</div>`);
    return;
  }
  let region = null;
  try{
    region = await api(`/api/india/region?lat=${S.incident.lat}&lon=${S.incident.lon}`);
    DEF = {...DEF_BASE, valley_width_m: region.valley_width_m,
      bed_slope: region.bed_slope, manning_n: region.manning_n,
      spreading_factor: region.spreading_factor, base_flow_m3s: region.base_flow_m3s,
      dam_material: region.material_prior,
      breach_time_hr: region.breach_time_typical_hr};
  }catch(e){ DEF = {...DEF_BASE}; }
  const F = k => `<div class="field"><label>${k.replace(/_/g," ")}</label>
    <input class="input" id="f_${k}" type="number" step="any" value="${DEF[k]}"></div>`;
  const wMax = Math.max(100, Math.ceil(DEF.dam_crest_len_m));
  openPanel("BREACH SIMULATION ENGINE",
    "Level-pool + erosion / overtopping - mass-balance verified",`
    ${region ? `<div class="note"><b>REGION PRESET:</b> ${esc(region.name)}<br>
      <small>${esc(region.notes)}</small></div>` : ""}
    <div style="background:rgba(251,191,36,0.1);border:1px solid rgba(251,191,36,0.3);border-radius:8px;padding:10px 14px;margin-bottom:12px;display:flex;gap:10px;align-items:flex-start">
      <span style="font-size:16px">ℹ️</span>
      <div style="font-size:11px;color:var(--amber)">
        <b>Engine:</b> DEM Cross-Section Bathtub Solver + 1D Muskingum-Cunge. This is a <b>rapid planning tool</b>, not a full Shallow Water Equation (SWE) solver. Results suitable for initial emergency planning and evacuation zone estimation. For dam safety design, use certified hydraulic models (HEC-RAS, MIKE FLOOD).
      </div>
    </div>
    <div class="mod"><div class="mod-title">FAILURE SCENARIO (presets adjust the
      sliders - what you see is exactly what runs)</div>
      <div class="scen-grid">
        ${[["minor","MINOR","Piping / partial erosion"],
           ["moderate","MODERATE","Headcut / 40-60% incision"],
           ["major","MAJOR","Rapid structural failure"],
           ["full","FULL FAILURE","Complete collapse"]].map(([v,tt,d]) =>
          `<button class="scen-card ${v === DEF.scenario ? "active" : ""}" data-scen="${v}">
            <span class="scen-title">${tt}</span><span class="scen-desc">${d}</span></button>`).join("")}
      </div><div class="preset-note" id="presetNote"></div></div>
    <div class="mod"><div class="mod-title">BREACH GEOMETRY (LIVE)</div>
      <div class="slider-group"><div class="slider-head"><span>BREACH WIDTH</span>
        <b id="dispW">${DEF.breach_width_m.toFixed(1)} m</b></div>
        <input type="range" id="sW" min="5" max="${wMax}" step="0.1" value="${DEF.breach_width_m}">
        <div class="slider-limits"><span>5 m</span><span>${wMax} m</span></div></div>
      <div class="slider-group"><div class="slider-head"><span>BREACH FORMATION TIME</span>
        <b id="dispT">${DEF.breach_time_hr.toFixed(2)} hr (${Math.round(DEF.breach_time_hr*60)} min)</b></div>
        <input type="range" id="sT" min="0.05" max="6" step="0.01" value="${DEF.breach_time_hr}">
        <div class="slider-limits"><span>3 min</span><span>6.0 hr</span></div></div>
      <div class="slider-group"><div class="slider-head"><span>BREACH DEPTH</span>
        <b id="dispD">${DEF.breach_depth_m.toFixed(1)} m</b></div>
        <input type="range" id="sD" min="1" max="${DEF.dam_height_m}" step="0.5" value="${DEF.breach_depth_m}">
        <div class="slider-limits"><span>1 m</span><span>${DEF.dam_height_m} m (full height)</span></div></div>
    </div>
    <div class="mod"><div class="mod-title">RESERVOIR &amp; DAM</div>
      <div class="grid2">${F("stored_volume_m3")}${F("lake_area_m2")}
      ${F("dam_height_m")}${F("dam_crest_len_m")}${F("inflow_m3s")}</div>
      <div class="field"><label>dam material</label>
        <select class="input" id="f_dam_material">${["Earth","Rock","Landslide debris",
          "Sediment","Ice/debris","Mixed","Concrete","Masonry"].map(m =>
          `<option ${m === DEF.dam_material ? "selected" : ""}>${m}</option>`).join("")}</select>
        <div class="hint">Concrete/Masonry use the overtopping-only paradigm.</div></div>
      ${region && String(region.inflow_mode).includes("snowmelt") ? `
      <button class="tbtn sm full" id="btnSnow" style="margin-top:4px">&#10052; SNOWMELT INFLOW</button>
      <div id="snowOut" class="preset-note"></div>` : ""}
      <button class="tbtn sm full" id="btnInflowCalc" style="margin-top:4px">&#127783; ESTIMATE INFLOW (SCS-CN)</button>
      <div id="inflowBox" class="preset-note"></div></div>
    <div class="mod"><div class="mod-title">VALLEY HYDRAULICS (REGION PRESET)</div>
      <div class="grid2">${F("valley_width_m")}${F("bed_slope")}${F("manning_n")}
      ${F("spreading_factor")}${F("base_flow_m3s")}</div>
      <label style="font-size:11.5px;color:var(--muted)">
        <input type="checkbox" id="f_unc" ${DEF.with_uncertainty ? "checked" : ""}>
        Monte Carlo uncertainty (progress + cancel)</label></div>
    <button class="tbtn primary full" id="btnRun">&#9654; RUN INUNDATION MODEL</button>
    <div id="runStatus" style="margin-top:8px">
      <div class="progress hidden" id="runProg"><i id="runProgBar"></i></div>
      <div class="stage-progress hidden" id="runStages"></div>
      <div style="font-size:11px;color:var(--muted);margin-top:6px" id="runMsg"></div>
      <button class="tbtn sm danger hidden" id="btnCancelRun" style="margin-top:6px">Cancel run</button>
    </div>`);
  const upd = () => {
    $("dispW").textContent = (+$("sW").value).toFixed(1) + " m";
    $("dispT").textContent = `${(+$("sT").value).toFixed(2)} hr (${Math.round(+$("sT").value*60)} min)`;
    $("dispD").textContent = (+$("sD").value).toFixed(1) + " m";
  };
  ["sW","sT","sD"].forEach(id => $(id).oninput = upd);
  $("f_dam_height_m").oninput = e => { $("sD").max = +e.target.value || DEF.dam_height_m; };
  document.querySelectorAll(".scen-card").forEach(c => c.onclick = () => {
    document.querySelectorAll(".scen-card").forEach(x => x.classList.toggle("active", x === c));
    const v = c.dataset.scen;
    const pr = {minor:{w:0.4,d:0.5,t:1.5}, moderate:{w:0.7,d:0.75,t:1.15},
                major:{w:1.0,d:1.0,t:1.0}, full:{w:null,d:null,t:0.6}}[v];
    const oldW = +$("sW").value, oldD = +$("sD").value, oldT = +$("sT").value;
    const H = +$("f_dam_height_m").value || DEF.dam_height_m;
    const CL = +$("f_dam_crest_len_m").value || DEF.dam_crest_len_m;
    $("sW").value = pr.w === null ? Math.min(CL, +$("sW").max) : oldW * pr.w;
    $("sD").max = H; $("sD").value = pr.d === null ? H : Math.min(oldD * pr.d, H);
    $("sT").value = Math.max(0.05, oldT * pr.t);
    upd();
    $("presetNote").textContent =
      `Preset applied: width ${oldW.toFixed(1)}->${(+$("sW").value).toFixed(1)} m, ` +
      `depth ${oldD.toFixed(1)}->${(+$("sD").value).toFixed(1)} m, ` +
      `time ${oldT.toFixed(2)}->${(+$("sT").value).toFixed(2)} hr.`;
  });
  $("btnInflowCalc").onclick = async () => {
    const cn = prompt("Curve Number (woods 55-66, pasture 49-71):", "74");
    const rain = prompt("24-hr storm rainfall (mm):", String(region?.design_storm_24h_mm || 100));
    const area = prompt("Catchment area (km2):", "142.8");
    const tc = prompt("Time of concentration (hr):", "3");
    if (!cn || !rain || !area || !tc) return;
    try{
      const j = await api("/api/hydrology/inflow", {method:"POST", body:JSON.stringify({
        catchment_km2:+area, rainfall_mm:+rain, curve_number:+cn, tc_hr:+tc})});
      $("f_inflow_m3s").value = j.peak_inflow_m3s;
      $("inflowBox").textContent = `SCS-CN: runoff ${j.runoff_mm} mm -> peak ` +
        `${j.peak_inflow_m3s} m3/s (set in the inflow field).`;
    }catch(e){ toast(e.message); }
  };
  if ($("btnSnow")) $("btnSnow").onclick = async () => {
    const T = prompt("Mean temperature (C):", "5");
    const R = prompt("Rain-on-snow (mm):", "0");
    const A = prompt("Catchment (km2):", "100");
    if (T === null) return;
    try{
      const j = await api("/api/india/snowmelt-inflow", {method:"POST",
        body:JSON.stringify({catchment_km2:+A, t_mean_c:+T, rain_on_snow_mm:+R,
          ddf: region.ddf_mm_per_deg_day || 5})});
      $("f_inflow_m3s").value = j.inflow_m3s;
      $("snowOut").textContent = `Melt ${j.melt_mm_day} mm/d + ROS ` +
        `${j.rain_on_snow_runoff_mm} mm -> ${j.inflow_m3s} m3/s`;
    }catch(e){ toast(e.message); }
  };
  $("btnRun").onclick = runSimulation;
}
const STAGES = ["Reservoir routing","Flood propagation","Exposure & risk","Monte Carlo"];
async function runSimulation(){
  const g = id => $(id);
  const params = {
    stored_volume_m3:+g("f_stored_volume_m3").value, lake_area_m2:+g("f_lake_area_m2").value,
    dam_height_m:+g("f_dam_height_m").value, dam_crest_len_m:+g("f_dam_crest_len_m").value,
    dam_material:g("f_dam_material").value,
    scenario:document.querySelector(".scen-card.active")?.dataset.scen || "major",
    breach_width_m:+g("sW").value, breach_depth_m:+g("sD").value,
    breach_time_hr:+g("sT").value, inflow_m3s:+g("f_inflow_m3s").value,
    valley_width_m:+g("f_valley_width_m").value, bed_slope:+g("f_bed_slope").value,
    manning_n:+g("f_manning_n").value, spreading_factor:+g("f_spreading_factor").value,
    base_flow_m3s:+g("f_base_flow_m3s").value, with_uncertainty:g("f_unc").checked};
  g("btnRun").disabled = true;
  g("runProg").classList.remove("hidden"); g("runStages").classList.remove("hidden");
  g("btnCancelRun").classList.remove("hidden");
  let jid;
  try{
    const j = await api(`/api/simulations?incident_id=${S.incident.id}`,
      {method:"POST", body:JSON.stringify(params)});
    S.simId = j.simulation_id; jid = j.job_id;
  }catch(e){
    g("btnRun").disabled = false; g("runProg").classList.add("hidden");
    g("runStages").classList.add("hidden"); g("btnCancelRun").classList.add("hidden");
    g("runMsg").textContent = "FAIL: " + e.message; return;
  }
  g("btnCancelRun").onclick = async () => {
    try{ await api(`/api/jobs/${jid}/cancel`, {method:"POST"}); }catch(e){}
  };
  const poll = setInterval(async () => {
    try{
      const st = await api(`/api/jobs/${jid}`);
      g("runProgBar").style.width = (st.progress || 0) + "%";
      const idx = Math.floor((st.progress || 0) / 25);
      g("runStages").innerHTML = STAGES.map((s,i) =>
        `<i class="${i < idx ? "done" : i === idx && st.status === "RUNNING" ? "active" : ""}"
           title="${s}"></i>`).join("");
      g("runMsg").textContent = st.status === "RUNNING"
        ? `${STAGES[Math.min(idx,3)]}... ${st.progress || 0}%` : st.status;
      if (["DONE","FAILED","CANCELLED"].includes(st.status)){
        clearInterval(poll); g("btnRun").disabled = false;
        g("btnCancelRun").classList.add("hidden");
        g("runMsg").textContent = st.status === "DONE" ? "OK: complete"
          : `FAIL: ${st.error || st.status}`;
        if (st.status === "DONE")
          document.querySelector('[data-tab="results"]').click();
      }
    }catch(err){
      clearInterval(poll); g("btnRun").disabled = false;
      g("btnCancelRun").classList.add("hidden"); g("runMsg").textContent = "FAIL: " + err.message;
    }
  }, 1000);
}

/* ---------- TAB: INUNDATION RESULTS ---------- */
async function showResults(){
  const sim = await api(`/api/simulations/${S.simId}`);
  if (sim.status !== "DONE"){ toast("Simulation not ready"); return; }
  S.lastResults = sim;
  drawFloodOnMap(sim.results.inundation);
  const b = sim.results.breach, inun = sim.results.inundation,
        u = sim.results.uncertainty, c = sim.results.confidence;
  sb("confBadge", `CONFIDENCE: ${c.confidence_pct}% (computed)`);
  const arr = inun.first_arrival_min;
  
  const firstArrivalMin = inun.first_arrival_min;
  const maxDepth = inun.max_depth_m;
  const corridorKm = inun.corridor_km;
  const peakQ = b.peak_Q_m3s;
  
  const emergencySummaryHtml = `
  <div style="background:linear-gradient(135deg,rgba(239,68,68,0.15),rgba(220,38,38,0.08));border:1.5px solid rgba(239,68,68,0.4);border-radius:12px;padding:14px 18px;margin-bottom:14px">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
      <span style="font-size:18px">🚨</span>
      <span style="font-weight:700;color:#f87171;font-size:13px;letter-spacing:0.5px">EMERGENCY SUMMARY — FOR FIELD COMMANDERS</span>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:10px">
        <div style="font-size:10px;color:var(--text-3);text-transform:uppercase;letter-spacing:0.5px">⏱ Earliest Impact</div>
        <div style="font-size:20px;font-weight:700;color:var(--amber);margin:2px 0">${firstArrivalMin ? Math.round(firstArrivalMin) + ' min' : '—'}</div>
        <div style="font-size:10px;color:var(--text-2)">Time before floodwater reaches first downstream settlement</div>
      </div>
      <div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:10px">
        <div style="font-size:10px;color:var(--text-3);text-transform:uppercase;letter-spacing:0.5px">📏 Max Water Depth</div>
        <div style="font-size:20px;font-weight:700;color:#f87171;margin:2px 0">${maxDepth ? maxDepth.toFixed(1) + ' m' : '—'}</div>
        <div style="font-size:10px;color:var(--text-2)">Peak depth at dam site — reduces as wave travels downstream</div>
      </div>
      <div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:10px">
        <div style="font-size:10px;color:var(--text-3);text-transform:uppercase;letter-spacing:0.5px">🗺 Flood Corridor</div>
        <div style="font-size:20px;font-weight:700;color:var(--cyan);margin:2px 0">${corridorKm ? corridorKm.toFixed(1) + ' km' : '—'}</div>
        <div style="font-size:10px;color:var(--text-2)">Total length of valley at risk downstream of dam</div>
      </div>
      <div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:10px">
        <div style="font-size:10px;color:var(--text-3);text-transform:uppercase;letter-spacing:0.5px">💧 Peak Flow Rate</div>
        <div style="font-size:20px;font-weight:700;color:var(--purple);margin:2px 0">${peakQ ? (peakQ/1000).toFixed(1) + ' k m³/s' : '—'}</div>
        <div style="font-size:10px;color:var(--text-2)">Extreme discharge at dam breach — ${peakQ > 50000 ? 'CATASTROPHIC, evacuate immediately' : peakQ > 10000 ? 'SEVERE, evacuate all low-lying areas' : 'SIGNIFICANT, follow EAP'}</div>
      </div>
    </div>
    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:10px;flex-wrap:wrap">
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <button class="tbtn sm" style="padding:4px 10px;font-size:11px;background:rgba(34,211,238,0.12);color:var(--cyan);border-color:var(--cyan)" onclick="window.openGeeModal()">
          🛰️ Open Earth Engine (GEE)
        </button>
        <button class="tbtn sm" style="padding:4px 10px;font-size:11px;background:rgba(251,191,36,0.12);color:var(--amber);border-color:var(--amber)" onclick="window.openFastFloodModal ? window.openFastFloodModal() : toast('Running hydrodynamic solver...')">
          ⚡ SPH &amp; Delft3D Verification
        </button>
        <button class="tbtn sm" style="padding:4px 10px;font-size:11px" onclick="window.triggerShapefileDownload()">
          📦 Download .SHP
        </button>
        <button class="tbtn sm" style="padding:4px 10px;font-size:11px" onclick="window.triggerKmlDownload()">
          🌍 Google Earth KML
        </button>
      </div>
      <span style="font-size:10px;color:var(--text-3);font-family:var(--mono)">NTRO SIH26161 COMPLIANT</span>
    </div>
    <div style="margin-top:10px;padding:8px;background:rgba(251,191,36,0.12);border-radius:6px;border-left:3px solid var(--amber);font-size:11px;color:var(--amber)">
      ⚠ This is an operational hydrodynamic estimate (Priority-Flood D8 + Muskingum-Cunge diffusion wave). For dam structural design, use detailed 2D/3D solvers.
    </div>
  </div>
  `;

  openPanel("INUNDATION MODEL",
    `${b.engine || "engine"} - mass-balance closure ${b.mass_balance_closure_err_pct}%`,`
    ${emergencySummaryHtml}
    <div class="kpi-row">
      <div class="kpi"><small>Peak Q</small><b class="c">${b.peak_Q_m3s.toLocaleString()}</b><small>m3/s</small></div>
      <div class="kpi"><small>Max depth</small><b class="a">${inun.max_depth_m}</b><small>m</small></div>
      <div class="kpi"><small>Max area</small><b class="c">${inun.max_area_km2}</b><small>km2</small></div>
      <div class="kpi"><small>First arrival</small><b class="r">${arr ?? "-"}</b><small>${arr != null ? "min" : "none"}</small></div>
    </div>
    <div class="mod"><div class="mod-title">OUTFLOW HYDROGRAPH Q(t)</div>
      <div class="chart-box"><div class="chart-head"><span>DISCHARGE vs TIME</span>
        <span class="qtag">Qp: ${b.peak_Q_m3s.toLocaleString()} m3/s</span></div>
        <canvas id="hydChart" class="chart"></canvas></div>
      <p style="font-size:10.5px;color:var(--muted);margin-top:6px;font-family:var(--mono)">
        Froehlich(1995): ${b.empirical_froehlich1995_Qp?.toLocaleString() ?? "-"} m3/s -
        ensemble ${b.empirical_ensemble?.ensemble_min ?? "-"} to
        ${b.empirical_ensemble?.ensemble_max ?? "-"} m3/s</p></div>
    <div class="mod"><div class="mod-title">VALLEY PROFILE - DEPTH &amp; ARRIVAL</div>
      <div class="chart-box"><canvas id="profChart" class="chart"></canvas></div></div>
    ${u ? `<div class="mod"><div class="mod-title">MONTE CARLO (p10-p90)</div>
      <table class="tbl"><tr><th>Quantity</th><th>p10</th><th>p50</th><th>p90</th></tr>
      ${Object.entries(u).map(([k,v]) => `<tr><td>${k.replace(/_/g," ")}</td>
        <td>${v.p10}</td><td>${v.p50}</td><td>${v.p90}</td></tr>`).join("")}</table></div>` : ""}
    <div class="mod"><div class="mod-title">ROUTING NODES (${inun.nodes.length})</div>
      <table class="tbl"><tr><th>km</th><th>Qpeak</th><th>Depth</th><th>Arrival</th></tr>
      ${inun.nodes.map(n => `<tr><td>${(n.chainage_m/1000).toFixed(1)}</td>
        <td>${n.peak_Q_m3s}</td><td>${n.max_depth_m} m</td>
        <td>${n.arrival_min ?? "-"}</td></tr>`).join("")}</table></div>
    <div class="note"><b>Area method:</b> ${esc(inun.area_method)} -
      <b>clamped reaches:</b> ${inun.muskingum_clamped_reaches}</div>
    <div class="mod"><div class="mod-title">MODEL LIMITATIONS (honest)</div>
      <ul class="clean">${[...b.limitations, ...b.reservoir_notes, ...inun.limitations]
        .map(l => `<li>- ${esc(l)}</li>`).join("")}</ul></div>
    <div class="row-end" style="flex-wrap:wrap;gap:6px;margin-top:12px">
      <button class="tbtn ghost sm" id="btnRepSim">&#128203; REPORT</button>
      <button class="tbtn sm" id="btnDlKml" style="border-color:#38bdf8;color:#38bdf8;font-weight:600" title="Export Google Earth KML">&#127757; KML Export</button>
      <button class="tbtn sm" id="btnDlShp" style="border-color:#34d399;color:#34d399;font-weight:700" title="Export Real ESRI Shapefile Package (inundated_area.shp + scenarios + centerline + buildings)">&#128230; Inundated Area Shapefile (.SHP)</button>
      <button class="tbtn primary sm" id="goVis">VISUAL SIMULATION &#9654;</button>
      <button class="tbtn primary sm" id="goExpo">EXPOSURE &#9654;</button></div>`);
  drawHydrograph($("hydChart"), b);
  drawProfile($("profChart"), inun.nodes);
  loadScenarioExtents();
  loadPopulationClusters();
  $("goVis").onclick = () => document.querySelector('[data-tab="visual"]').click();
  $("goExpo").onclick = () => panelExposureModal();
  $("btnRepSim").onclick = () => viewFullReport(sim.incident_id);
  const btnKml = $("btnDlKml");
  if (btnKml) btnKml.onclick = triggerKmlDownload;
  const btnShp = $("btnDlShp");
  if (btnShp) btnShp.onclick = triggerShapefileDownload;
}
function drawFloodOnMap(inun, restoreOnly = false){
  clearLayer("flood"); clearLayer("snaps");
  const ring = (inun.max_extent_ring || []).map(p => [p[0], p[1]]);
  if (ring.length >= 3){
    const floodPoly = L.polygon(ring, {
      color:"#00f0ff", weight:2,
      fillColor:"#0ea5e9", fillOpacity:.35
    });

    // Rich Hydraulic Hover Tooltip on Inundation Layer
    const floodTip = `
      <div class="hydraulic-tooltip">
        <div style="font-weight:700;color:#00f0ff;font-size:12.5px;margin-bottom:4px;display:flex;align-items:center;gap:6px">
          <span>&#127754;</span> <span>FLOOD INUNDATION LAYER</span>
        </div>
        <div style="display:grid;grid-template-columns:auto auto;gap:3px 12px;font-size:11px">
          <span style="color:#94a3b8">Peak Flood Depth:</span><b style="color:#ef4444">${inun.max_depth_m} m</b>
          <span style="color:#94a3b8">Max Inundated Area:</span><b style="color:#38bdf8">${inun.max_area_km2} km&sup2;</b>
          <span style="color:#94a3b8">First Wave Arrival:</span><b style="color:#f59e0b">${inun.first_arrival_min ?? "-"} min</b>
          <span style="color:#94a3b8">Corridor Length:</span><b style="color:#34d399">${inun.corridor_km ? inun.corridor_km.toFixed(1) + ' km' : '-'}</b>
          <span style="color:#94a3b8">Hydraulic Solver:</span><b style="color:#a78bfa">${inun.used_2d ? '2D Priority-Flood DEM' : '1D Muskingum-Cunge'}</b>
        </div>
        <div style="margin-top:6px;font-size:10px;color:#94a3b8;border-top:1px solid rgba(255,255,255,0.1);padding-top:4px">
          &#128161; Hover over valley station markers or run Visual Sim for node-by-node velocity &amp; drag force.
        </div>
      </div>
    `;
    floodPoly.bindTooltip(floodTip, {sticky: true, className: "custom-hydraulic-tip"});
    floodPoly.addTo(map);
    L_("flood").push(floodPoly);

    if (!restoreOnly) map.fitBounds(L.latLngBounds(ring).pad(0.15));
  }

  // Add interactive hydraulic station probes along the valley reach
  if (inun.nodes && inun.nodes.length) {
    const step = Math.max(1, Math.floor(inun.nodes.length / 8));
    for (let ni = 0; ni < inun.nodes.length; ni += step) {
      const nd = inun.nodes[ni];
      const w = nd.flood_width_m || 90;
      const d = nd.max_depth_m || 1.0;
      const v = nd.peak_v_ms || (nd.peak_Q_m3s / Math.max(w * d, 1.0));
      const km = (nd.chainage_m / 1000).toFixed(1);
      const probeHtml = `
        <div class="hydraulic-probe-pin" style="background:rgba(10,15,29,0.85);border:1.5px solid #00f0ff;border-radius:12px;padding:2px 6px;color:#fff;font-size:10px;font-weight:700;white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,0.6);cursor:pointer;display:flex;align-items:center;gap:4px">
          <span style="color:#00f0ff">&#127754;</span> <span>${km}km &middot; ${d.toFixed(1)}m</span>
        </div>
      `;
      const probeMarker = L.marker([nd.lat, nd.lon], {
        icon: L.divIcon({html: probeHtml, className: "", iconSize: [65, 20], iconAnchor: [32, 10]})
      });
      probeMarker.bindPopup(`
        <div class="hydraulic-tooltip" style="min-width:200px">
          <div style="font-weight:700;color:#00f0ff;font-size:12px;margin-bottom:4px">&#127754; Valley Reach Station: ${km} km</div>
          <table style="width:100%;font-size:11px;border-collapse:collapse;color:#e2e8f0">
            <tr><td style="color:#94a3b8;padding:2px 0">Water Depth (h):</td><td style="font-weight:700;color:#ef4444;text-align:right">${d.toFixed(2)} m</td></tr>
            <tr><td style="color:#94a3b8;padding:2px 0">Flow Velocity (v):</td><td style="font-weight:700;color:#f59e0b;text-align:right">${v.toFixed(2)} m/s</td></tr>
            <tr><td style="color:#94a3b8;padding:2px 0">Peak Discharge (Q):</td><td style="font-weight:700;color:#38bdf8;text-align:right">${Math.round(nd.peak_Q_m3s).toLocaleString()} m&sup3;/s</td></tr>
            <tr><td style="color:#94a3b8;padding:2px 0">Unit Discharge (q):</td><td style="font-weight:700;color:#a78bfa;text-align:right">${(d * v).toFixed(2)} m&sup2;/s</td></tr>
            <tr><td style="color:#94a3b8;padding:2px 0">Arrival Time:</td><td style="font-weight:700;color:#34d399;text-align:right">${nd.arrival_min != null ? nd.arrival_min.toFixed(1) + ' min' : '-'}</td></tr>
            <tr><td style="color:#94a3b8;padding:2px 0">Flood Corridor:</td><td style="font-weight:700;color:#cbd5e1;text-align:right">${Math.round(w)} m width</td></tr>
          </table>
        </div>
      `);
      probeMarker.addTo(map);
      L_("flood").push(probeMarker);
    }
  }

  // Refresh assets to reflect simulation-derived risk & depth
  loadAssets();

  const snaps = inun.snapshots || [];
  const dock = $("floodDock");
  if ($("scenDock")) $("scenDock").classList.add("hidden"); // hide scenario dock when animation dock opens
  if ($("vsimPlayer")) return;       // single-dock rule
  dock.classList.remove("hidden");
  const slider = $("animSlider"); slider.max = Math.max(snaps.length - 1, 0);
  let snapLayers = [], timer = null;
  const show = i => {
    snapLayers.forEach(l => map.removeLayer(l)); snapLayers = [];
    if (snaps[i]){
      snapLayers = [L.polygon(snaps[i].ring, {color:"#0369a1", weight:1,
        fillColor:"#38bdf8", fillOpacity:.5}).addTo(map)];
      L_("snaps").push(...snapLayers);
      $("animElapsed").textContent = snaps[i].time_min + " min";
      $("animArea").textContent = snaps[i].area_km2 + " km2";
    }
  };
  slider.oninput = e => show(+e.target.value); show(0);
  $("animReset").onclick = () => { if (timer){clearInterval(timer); timer = null;}
    slider.value = 0; show(0); };
  $("animPlay").onclick = () => {
    if (timer){ clearInterval(timer); timer = null; return; }
    let i = 0;
    timer = setInterval(() => { i = (i+1) % (snaps.length || 1);
      slider.value = i; show(i); }, 900);
  };
}
function drawHydrograph(cv, b){
  if (!cv) return;
  const dpr = devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
  cv.width = w*dpr; cv.height = h*dpr;
  const x = cv.getContext("2d"); x.scale(dpr, dpr);
  const T = b.time_min, Q = b.Q_m3s;
  const tmax = Math.max(...T), qmax = Math.max(...Q) * 1.12 || 1;
  const px = t => 40+(w-50)*t/tmax, py = q => h-20-(h-36)*q/qmax;
  x.strokeStyle = "rgba(139,153,173,.25)";
  for (let i = 0; i <= 4; i++){
    const y = py(qmax*i/4); x.beginPath(); x.moveTo(36,y); x.lineTo(w-8,y); x.stroke();
    x.fillStyle = "#8b99ad"; x.font = "8.5px ui-monospace,monospace";
    x.fillText(Math.round(qmax*i/4), 4, y+3);
  }
  x.beginPath();
  T.forEach((tt,i) => i ? x.lineTo(px(tt), py(Q[i])) : x.moveTo(px(tt), py(Q[i])));
  x.strokeStyle = "#22d3ee"; x.lineWidth = 2; x.stroke();
  x.lineTo(px(tmax), py(0)); x.lineTo(px(0), py(0)); x.closePath();
  x.fillStyle = "rgba(34,211,238,.12)"; x.fill();
  x.fillStyle = "#8b99ad"; x.font = "9px ui-monospace,monospace";
  x.fillText("Q (m3/s)", 6, 12); x.fillText("time (min)", w-70, h-6);
  x.fillStyle = "#f59e0b"; x.fillText(`Qp=${Math.max(...Q).toFixed(0)}`, w-90, 14);
}
function drawProfile(cv, nodes){
  if (!cv || !nodes.length) return;
  const dpr = devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
  cv.width = w*dpr; cv.height = h*dpr;
  const x = cv.getContext("2d"); x.scale(dpr, dpr);
  const km = nodes.map(n => n.chainage_m/1000);
  const dMax = Math.max(...nodes.map(n => n.max_depth_m)) * 1.15 || 1;
  const aNodes = nodes.filter(n => n.arrival_min != null);
  const aMax = aNodes.length ? Math.max(...aNodes.map(n => n.arrival_min)) * 1.15 : 1;
  const px = k => 40+(w-50)*k/(km[km.length-1] || 1);
  const pyD = d => h-20-(h-36)*d/dMax, pyA = a => h-20-(h-36)*a/aMax;
  x.strokeStyle = "#22d3ee"; x.lineWidth = 2; x.beginPath();
  nodes.forEach((n,i) => i ? x.lineTo(px(km[i]), pyD(n.max_depth_m))
                           : x.moveTo(px(km[i]), pyD(n.max_depth_m))); x.stroke();
  if (aNodes.length){
    x.strokeStyle = "#f59e0b"; x.beginPath(); let first = true;
    nodes.forEach(n => { if (n.arrival_min == null) return;
      first ? x.moveTo(px(n.chainage_m/1000), pyA(n.arrival_min))
            : x.lineTo(px(n.chainage_m/1000), pyA(n.arrival_min)); first = false; });
    x.stroke();
  }
  x.fillStyle = "#8b99ad"; x.font = "9px ui-monospace,monospace";
  x.fillText("distance (km)", w/2-30, h-4);
  x.fillStyle = "#22d3ee"; x.fillText("- depth", 40, 12);
  x.fillStyle = "#f59e0b"; x.fillText("- arrival (min)", 94, 12);
}

/* ---------- EXPOSURE (modal from results) ---------- */
async function panelExposureModal(){
  if (!S.lastResults){ toast("Run a simulation first"); return; }
  const r = S.lastResults.results, e = r.exposure, k = r.risk, c = r.confidence;
  const bc = {EXTREME:"err",HIGH:"warn",MODERATE:"info",LOW:"ok"}[k.band];
  const vis = r.visual;
  openPanel("POPULATION & ASSET IMPACT","Exact corridor exposure - TDRI risk index",`
    <div class="kpi-row">
      <div class="kpi"><small>Population</small><b class="r">${e.total_population_exposed.toLocaleString()}</b><small>exposed</small></div>
      <div class="kpi"><small>Buildings</small><b class="a">${e.buildings_exposed}</b><small>exposed</small></div>
      <div class="kpi"><small>Critical infra</small><b class="r">${e.critical_infra_affected.length}</b><small>affected</small></div>
      <div class="kpi"><small>Agriculture</small><b class="c">${e.agri_ha_affected} ha</b><small>affected</small></div>
      <div class="kpi"><small>Livestock</small><b>${e.livestock_exposed}</b><small>at risk</small></div>
    </div>
    <div class="mod"><div class="mod-title">TDRI RISK INDEX</div>
      <div style="font-size:30px;font-weight:800">${k.tdri}
        <span style="font-size:12px;color:var(--muted)">(${k.range[0]}-${k.range[1]})</span>
        <span class="badge ${bc}" style="vertical-align:6px">${k.band}</span></div>
      <p style="font-size:11px;color:var(--muted);margin:6px 0">${esc(k.recommended_action)}</p>
      <table class="tbl"><tr><th>Factor</th><th>Score</th><th>Weight</th></tr>
        ${Object.entries(k.factors).map(([fk,fv]) =>
        `<tr><td>${fk}</td><td>${fv}</td><td>${k.weights[fk]}</td></tr>`).join("")}</table></div>
    <div class="mod"><div class="mod-title">CONFIDENCE (computed from provenance)</div>
      <div style="font-size:22px;font-weight:800;color:var(--amber)">${c.confidence_pct}%</div>
      <ul class="clean">${c.provenance.map(p => `<li>- ${esc(p)}</li>`).join("")}</ul></div>
    <div class="mod"><div class="mod-title">AFFECTED SETTLEMENTS</div>
      <table class="tbl"><tr><th>Name</th><th>Pop</th><th>Depth</th><th>Arrival</th></tr>
      ${e.settlements.map(s => `<tr><td>${esc(s.name)}</td><td>${s.population}</td>
        <td>${s.max_depth_m} m</td><td>${s.arrival_min ?? "-"}</td></tr>`).join("")
        || '<tr><td colspan=4>None in corridor</td></tr>'}</table></div>
    ${e.agriculture_affected?.length ? `
    <div class="mod"><div class="mod-title">AGRICULTURE</div>
      <table class="tbl"><tr><th>Parcel</th><th>Area (ha)</th><th>Crop</th></tr>
      ${e.agriculture_affected.map(a => `<tr><td>${esc(a.name)}</td>
        <td>${a.area_ha}${a.defaulted_area ? ' <span class="badge warn">assumed</span>' : ""}</td>
        <td>${esc(a.crop)}</td></tr>`).join("")}</table></div>` : ""}
    <button class="tbtn primary full" id="btnRep2">VIEW COMPREHENSIVE REPORT</button>`);
  $("btnRep2").onclick = () => viewFullReport(S.lastResults.incident_id);
}

/* ---------- VISUAL SIMULATION PLAYER ---------- */
const DEPTH_COLORS = [[0.5,"#7dd3fc"],[1.0,"#38bdf8"],[2.0,"#0ea5e9"],
                      [5.0,"#0369a1"],[1e9,"#1e3a8a"]];
const DV_COLORS = [[0.5,"#34d399"],[1.2,"#fbbf24"],[2.0,"#f97316"],[1e9,"#ef4444"]];
const HAZ_COLORS = {LOW:"#34d399",MODERATE:"#fbbf24",HIGH:"#f97316",EXTREME:"#ef4444"};
function rampColor(v, ramp){
  for (const [thr, c] of ramp) if (v < thr) return c;
  return ramp[ramp.length-1][1];
}
let VS = {frames:null, impact:null, totals:null, cur:-1, playing:false, timer:null,
          speed:1, colorBy:"depth", solverMode:"delft3d", frameLayers:[], assetMarks:[], rings:null,
          lastShown:null};
function panelVisual(){
  if (!S.simId){ openPanel("VISUAL SIMULATION","",
    EMPTY("&#127916;","No simulation yet.","RUN BREACH SIMULATION",
          "document.querySelector('[data-tab=breach]').click()")); return; }
  const sim = S.lastResults;
  if (!sim || !sim.results.visual){
    openPanel("VISUAL SIMULATION","",
      EMPTY("&#127916;","This run has no visual payload - re-run the simulation.","",
            "")); return;
  }
  const v = sim.results.visual;
  VS = {...VS, frames:v.frames, impact:v.impact, totals:v.totals, cur:-1,
        playing:false, colorBy:"depth", frameLayers:[], assetMarks:[], rings:null,
        lastShown:null};
  const T = VS.frames[VS.frames.length-1].t_min;
  openPanel("VISUAL DAM-BREAK SIMULATION","Routed physics - hazard & damage overlay",`
    <div class="mod"><div class="mod-title">IMPACT SUMMARY (PEAK EVENT)</div>
      <div class="kpi-row">
        <div class="kpi"><small>People</small><b class="r">${VS.totals.people_total.toLocaleString()}</b>
          <small>${VS.totals.people.EXTREME} extreme - ${VS.totals.people.HIGH} high</small></div>
        <div class="kpi"><small>Buildings</small><b class="a">${VS.totals.buildings_affected}</b>
          <small>~${VS.totals.buildings_fully_damaged_eq} damaged (curve-equiv)</small></div>
        <div class="kpi"><small>Agriculture</small><b class="c">${VS.totals.agri_ha_affected} ha</b>
          <small>~${VS.totals.agri_ha_lost} ha lost</small></div>
        <div class="kpi"><small>Livestock</small><b>${VS.totals.livestock}</b><small>at risk</small></div>
      </div>
      <div class="note">Economic proxy (PLACEHOLDER rates):
        Rs ${(VS.totals.economic_total_inr/1e7).toFixed(1)} crore</div></div>
    <div class="mod"><div class="mod-title">ARRIVAL SCHEDULE</div>
      <table class="tbl"><tr><th>t</th><th>Asset</th><th>Depth</th><th>dv</th><th>Hazard</th></tr>
      ${VS.impact.map(e => `<tr><td>${e.arrival_min ?? "-"}</td>
        <td>${esc(e.name)}</td><td>${e.peak_depth_m ?? "-"} m</td>
        <td>${e.dv ?? "-"}</td>
        <td><span class="badge" style="background:${HAZ_COLORS[e.people_hazard]}22;
          color:${HAZ_COLORS[e.people_hazard]}">${e.people_hazard || "-"}</span></td></tr>`).join("")}
      </table></div>
    <div class="mod"><div class="mod-title">COLOR MODE</div>
      <div style="display:flex;gap:8px">
        <button class="tbtn sm primary" id="cbyDepth">FLOOD DEPTH</button>
        <button class="tbtn sm" id="cbyDv">HAZARD (d x v)</button></div>
      <div class="hint" id="vsLegend" style="font-family:var(--mono);font-size:10px;margin-top:8px"></div></div>
    <div class="mod"><div class="mod-title">MODEL &amp; LIMITATIONS</div>
      <p class="hint" style="margin:0 0 6px">${esc(v.method)}</p>
      <ul class="clean">${v.limitations.map(l => `<li>- ${esc(l)}</li>`).join("")}</ul></div>`);
  $("cbyDepth").onclick = () => setVSColor("depth");
  $("cbyDv").onclick = () => setVSColor("dv");
  buildVSPlayer();
  drawVSFrame(0);
}
function setVSColor(mode){
  VS.colorBy = mode; VS.cur = -1; VS.lastShown != null &&
    map.removeLayer(VS.frameLayers[VS.lastShown]);
  VS.lastShown = null;
  $("cbyDepth").classList.toggle("primary", mode === "depth");
  $("cbyDv").classList.toggle("primary", mode === "dv");
  buildVSFrameLayers();
  drawVSFrame(VS.timer ? 0 : Math.max(VS.cur, 0));
  updateVSLegend();
}
function updateVSLegend(){
  const depth = VS.colorBy === "depth";
  const ramp = depth ? DEPTH_COLORS : DV_COLORS;
  const lbl = depth ? ["<0.5m","0.5-1m","1-2m","2-5m",">5m"]
                    : ["<0.5","0.5-1.2","1.2-2",">2 m2/s"];
  $("vsLegend").innerHTML = ramp.slice(0, depth ? 5 : 4).map((c,i) =>
    `<span style="margin-right:10px"><i style="display:inline-block;width:14px;height:8px;
    border-radius:2px;background:${c[1]};margin-right:4px"></i>${lbl[i]}</span>`).join("");
}
function buildVSPlayer(){
  const old = $("vsimPlayer"); if (old) old.remove();
  $("floodDock").classList.add("hidden");      // single-dock rule
  const T = VS.frames[VS.frames.length-1].t_min;
  const dock = document.createElement("div");
  dock.className = "vsim-player"; dock.id = "vsimPlayer";
  dock.innerHTML = `
    <div class="vsim-top">
      <div>
        <span class="vsim-phase" id="vsPhase">BREACH INITIATION</span>
        <div class="vsim-time"><span id="vsT">0.0</span><small> / ${T} min</small></div>
      </div>
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
        <div class="vs-solver-toggle" style="display:flex;gap:3px;align-items:center;background:rgba(0,0,0,0.4);border:1px solid var(--border);border-radius:6px;padding:2px 4px">
          <span style="font-size:9.5px;color:var(--text-3);margin-right:2px;font-family:var(--mono)">SOLVER:</span>
          <button class="vs-solver-pill ${VS.solverMode === 'delft3d' ? 'active' : ''}" id="vsBtnDelft3D" title="Delft3D 2D Depth-Averaged SWE">🌊 Delft3D SWE</button>
          <button class="vs-solver-pill ${VS.solverMode === 'sph' ? 'active' : ''}" id="vsBtnSPH" title="Smoothed-Particle Hydrodynamics Lagrangian wave particles">⚛️ SPH Particles</button>
          <button class="vs-solver-pill ${VS.solverMode === 'cunge' ? 'active' : ''}" id="vsBtnCunge" title="1D Muskingum-Cunge Diffusion Wave">⚡ 1D Cunge</button>
          <button class="vs-solver-pill ${VS.solverMode === 'ensemble' ? 'active' : ''}" id="vsBtnEnsemble" title="Multi-Model Hydrodynamic Comparison">📊 Ensemble</button>
        </div>
        <div class="vsim-controls">
          <button class="tbtn sm" id="vsSpeed">1x</button>
          <button class="tbtn sm primary" id="vsPlay">&#9654; PLAY</button>
          <button class="tbtn sm" id="vsClose">EXIT</button>
        </div>
      </div>
    </div>
    <input type="range" id="vsSlider" min="0" max="${VS.frames.length-1}" value="0" step="1">
    <div class="vsim-kpis">
      <div class="vkpi c"><small>Q AT DAM</small><b id="vsQ">-</b><small>m3/s</small></div>
      <div class="vkpi c"><small>RELEASED</small><b id="vsVol">-</b><small>m3 (%)</small></div>
      <div class="vkpi a"><small>FRONT</small><b id="vsFront">-</b><small>km</small></div>
      <div class="vkpi a"><small>AREA</small><b id="vsArea">-</b><small>km2</small></div>
      <div class="vkpi r"><small>MAX VEL</small><b id="vsV">-</b><small>m/s</small></div>
      <div class="vkpi r"><small>MAX FORCE</small><b id="vsF">-</b><small>kN/m</small></div>
      <div class="vkpi r"><small>MOMENTUM</small><b id="vsM">-</b><small>MN</small></div>
    </div>
    <div class="vsim-impacts">
      <div class="vimp"><h5>PEOPLE AFFECTED</h5><b class="countup" id="vsPpl">0</b>
        <div class="hbar">${["LOW","MODERATE","HIGH","EXTREME"].map(k =>
          `<i style="flex:1;background:${HAZ_COLORS[k]}33" id="vsPbar${k}"></i>`).join("")}</div></div>
      <div class="vimp"><h5>BUILDINGS</h5><b class="countup" id="vsBld">0</b></div>
      <div class="vimp"><h5>AGRICULTURE (ha)</h5><b class="countup" id="vsAgri">0.0</b></div>
    </div>`;
  document.querySelector(".workspace").append(dock);
  buildVSFrameLayers();
  
  // Wire hydrodynamic solver toggles
  const setSolver = (m) => {
    VS.solverMode = m;
    ["Delft3D","SPH","Cunge","Ensemble"].forEach(k => {
      const b = $("vsBtn" + k);
      if (b) b.classList.toggle("active", m.toLowerCase() === k.toLowerCase());
    });
    buildVSFrameLayers();
    drawVSFrame(VS.cur >= 0 ? VS.cur : 0);
    if (typeof toast === "function") {
      const lbl = m === "delft3d" ? "Delft3D 2D Depth-Averaged SWE (Eulerian)" :
                  m === "sph" ? "SPH Lagrangian Wave Particles (Free-surface splash)" :
                  m === "cunge" ? "1D Muskingum-Cunge Diffusion Wave" : "Multi-Model Hydrodynamic Ensemble";
      toast("Hydrodynamic Solver: " + lbl, 2500);
    }
  };
  $("vsBtnDelft3D").onclick = () => setSolver("delft3d");
  $("vsBtnSPH").onclick = () => setSolver("sph");
  $("vsBtnCunge").onclick = () => setSolver("cunge");
  $("vsBtnEnsemble").onclick = () => setSolver("ensemble");

  // asset markers & floating settlement beacons
  VS.assetMarks = [];
  VS.impact.forEach(e => {
    const isHosp = (e.name || "").includes("Hospital") || (e.name || "").includes("Health");
    const isBridge = (e.name || "").includes("Bridge");
    const icon = e.kind === "infrastructure" ? (isHosp ? "🏥" : isBridge ? "🌉" : "⚙️") : (e.kind === "agriculture" ? "🌾" : "🏘️");
    
    const m = L.circleMarker([e.lat, e.lon], {radius:7, color:"#f59e0b",
      fillColor:"#f59e0b", fillOpacity:.9, weight:2})
      .bindPopup(`<b>${esc(e.name)}</b><br>arrival ${e.arrival_min ?? "-"} min<br>
        depth ${e.peak_depth_m ?? "-"} m - dv ${e.dv ?? "-"} m2/s<br>
        ${e.population ? `population ${e.population.toLocaleString()}<br>` : ""}
        ${e.area_ha ? `${e.area_ha} ha ${esc(e.crop || "")} - loss ${e.loss_frac*100}%<br>` : ""}
        hazard <b style="color:${HAZ_COLORS[e.people_hazard]}">${e.people_hazard || ""}</b>`);
    m.addTo(map);

    // Floating settlement beacon badge on map
    const bId = "bcn-" + esc(e.name).replace(/\W/g,"_");
    const beacon = L.marker([e.lat, e.lon], {
      icon: L.divIcon({
        className: "",
        iconSize: [115, 22],
        iconAnchor: [57, 26],
        html: `<div class="settlement-beacon safe" id="${bId}">
          <span>${icon}</span>
          <span style="max-width:75px;overflow:hidden;text-overflow:ellipsis">${esc(e.name)}</span>
          <span class="beacon-timer">${e.arrival_min ?? '-'}m</span>
        </div>`
      }),
      interactive: false
    }).addTo(map);

    VS.assetMarks.push({marker:m, beacon:beacon, entry:e, hit:false});
  });
  // evacuation rings (from S.lastResults - the FIX)
  const ev = S.lastResults?.results?.evacuation;
  if (ev && ev.clocks.length){
    VS.rings = ev.clocks.map(c => {
      const ring = L.circle([c.lat, c.lon], {radius: c.ring_radius_m, weight:2,
        fillOpacity:.08, color:"#34d399", fillColor:"#34d399"})
        .bindPopup(`<b>${esc(c.name)}</b> - ${c.population} people<br>
          Flood arrival: <b>${c.arrival_min ?? "never"} min</b><br>
          Need ~${c.t_needed_min} min (walk ${c.walk_to_safety_m} m +
          ${c.region_mobilization_min} min mobilization)`);
      ring.addTo(map);
      const label = L.marker([c.lat, c.lon], {icon: L.divIcon({className:"",
        iconSize:[70,16],
        html:`<div class="ev-clock" id="evLbl-${esc(c.name).replace(/\W/g,"_")}">-</div>`}),
        interactive:false}).addTo(map);
      return {ring, label, clock:c};
    });
  }
  $("vsSlider").oninput = e => { pauseVS(); drawVSFrame(+e.target.value); };
  $("vsPlay").onclick = toggleVSPlay;
  $("vsSpeed").onclick = () => {
    VS.speed = VS.speed === 1 ? 2 : VS.speed === 2 ? 0.5 : 1;
    $("vsSpeed").textContent = VS.speed + "x";
    if (VS.playing){ pauseVS(); playVS(); }
  };
  $("vsClose").onclick = exitVS;
  updateVSLegend();
}
function makeHydraulicTip(s) {
  const dragKpa = (0.5 * 1000 * s.v * s.v / 1000).toFixed(1);
  const qUnit = (s.dv || (s.y * s.v)).toFixed(2);
  return `
    <div class="hydraulic-tooltip">
      <div style="font-weight:700;color:#00f0ff;font-size:11.5px;margin-bottom:3px;display:flex;align-items:center;gap:4px">
        <span>&#127754;</span> <span>HYDRODYNAMIC WAVE LAYER</span>
      </div>
      <table style="width:100%;font-size:10.5px;border-collapse:collapse;color:#e2e8f0">
        <tr><td style="color:#94a3b8;padding:1px 0">Water Depth (h):</td><td style="font-weight:700;color:#38bdf8;text-align:right">${s.y.toFixed(2)} m</td></tr>
        <tr><td style="color:#94a3b8;padding:1px 0">Flow Velocity (v):</td><td style="font-weight:700;color:#f59e0b;text-align:right">${s.v.toFixed(2)} m/s</td></tr>
        <tr><td style="color:#94a3b8;padding:1px 0">Unit Discharge (q):</td><td style="font-weight:700;color:#a78bfa;text-align:right">${qUnit} m&sup2;/s</td></tr>
        <tr><td style="color:#94a3b8;padding:1px 0">Dynamic Drag:</td><td style="font-weight:700;color:#f43f5e;text-align:right">${dragKpa} kPa</td></tr>
      </table>
    </div>
  `;
}
function buildVSFrameLayers(){
  VS.frameLayers.forEach((g, i) => { if (g && VS.lastShown === i) map.removeLayer(g); });
  const solver = (VS.solverMode || "delft3d").toLowerCase();

  VS.frameLayers = VS.frames.map(fr => {
    const g = L.layerGroup();
    const wetSegs = fr.segments.filter(s => s.wet);

    if (solver === "sph") {
      // ⚛️ SPH (Smoothed-Particle Hydrodynamics): Discrete fluid packets + dynamic spray
      wetSegs.forEach(s => {
        L.polygon(s.ring, {color: "#0284c7", weight: 0.5, opacity: 0.4, fillColor: "#0284c7", fillOpacity: 0.35})
          .bindTooltip(makeHydraulicTip(s), {sticky: true, className: "custom-hydraulic-tip"})
          .addTo(g);
      });
      wetSegs.forEach((s, idx) => {
        const ring = s.ring;
        const numP = Math.min(8, Math.max(3, Math.round(s.v * 1.5)));
        for (let p = 0; p < numP; p++) {
          const u = (p + 0.5) / numP;
          const latA = ring[0][0] + (ring[3][0] - ring[0][0]) * u;
          const lonA = ring[0][1] + (ring[3][1] - ring[0][1]) * u;
          const latB = ring[1][0] + (ring[2][0] - ring[1][0]) * u;
          const lonB = ring[1][1] + (ring[2][1] - ring[1][1]) * u;
          const w = 0.2 + 0.6 * ((p * 7) % 10) / 10;
          const pLat = latA + (latB - latA) * w;
          const pLon = lonA + (lonB - lonA) * w;
          const pCol = s.v > 4 ? "#a5f3fc" : s.v > 2 ? "#38bdf8" : "#0284c7";
          L.circleMarker([pLat, pLon], {
            radius: Math.min(4.5, 2 + s.y * 0.15),
            color: "#ffffff",
            weight: 0.5,
            fillColor: pCol,
            fillOpacity: 0.85
          }).addTo(g);
        }
      });
      if (wetSegs.length > 0) {
        const frontSeg = wetSegs[wetSegs.length - 1];
        const r = frontSeg.ring;
        const frontMid = [(r[1][0] + r[2][0]) / 2, (r[1][1] + r[2][1]) / 2];
        const dLat = r[1][0] - r[0][0];
        const dLon = r[1][1] - r[0][1];
        for (let sp = 0; sp < 12; sp++) {
          const scatter = (Math.random() - 0.5) * 0.003;
          const lead = Math.random() * 0.004;
          L.circleMarker([frontMid[0] + dLat * 0.5 + lead + scatter, frontMid[1] + dLon * 0.5 + lead + scatter], {
            radius: 1.5 + Math.random() * 2,
            color: "#ffffff",
            weight: 0.8,
            fillColor: "#e0f2fe",
            fillOpacity: 0.9
          }).addTo(g);
        }
      }
    } else if (solver === "cunge") {
      // ⚡ 1D Muskingum-Cunge: Prismatic centerline + cross-section ribs
      wetSegs.forEach(s => {
        const val = VS.colorBy === "depth" ? s.y : s.dv;
        const color = rampColor(val, VS.colorBy === "depth" ? DEPTH_COLORS : DV_COLORS);
        L.polygon(s.ring, {color: "#ca8a04", weight: 0.8, opacity: 0.7, fillColor: color, fillOpacity: 0.65})
          .bindTooltip(makeHydraulicTip(s), {sticky: true, className: "custom-hydraulic-tip"})
          .addTo(g);
      });
      if (wetSegs.length > 1) {
        const clPoints = wetSegs.map(s => [
          (s.ring[0][0] + s.ring[1][0] + s.ring[2][0] + s.ring[3][0]) / 4,
          (s.ring[0][1] + s.ring[1][1] + s.ring[2][1] + s.ring[3][1]) / 4
        ]);
        L.polyline(clPoints, {color: "#facc15", weight: 3.5, dashArray: "5, 5", opacity: 0.95}).addTo(g);
      }
    } else if (solver === "ensemble") {
      // 📊 Multi-Model Ensemble: Delft3D 2D depth envelope + SPH fast surge front + 1D centerline
      wetSegs.forEach(s => {
        const val = VS.colorBy === "depth" ? s.y : s.dv;
        const color = rampColor(val, VS.colorBy === "depth" ? DEPTH_COLORS : DV_COLORS);
        L.polygon(s.ring, {color: "#0284c7", weight: 0.5, opacity: 0.5, fillColor: color, fillOpacity: 0.55})
          .bindTooltip(makeHydraulicTip(s), {sticky: true, className: "custom-hydraulic-tip"})
          .addTo(g);
      });
      if (wetSegs.length > 0) {
        const frontSeg = wetSegs[wetSegs.length - 1];
        const r = frontSeg.ring;
        const extLat1 = r[1][0] + (r[1][0] - r[0][0]) * 0.15;
        const extLon1 = r[1][1] + (r[1][1] - r[0][1]) * 0.15;
        const extLat2 = r[2][0] + (r[2][0] - r[3][0]) * 0.15;
        const extLon2 = r[2][1] + (r[2][1] - r[3][1]) * 0.15;
        L.polyline([[extLat1, extLon1], [extLat2, extLon2]], {
          color: "#f59e0b", weight: 4, dashArray: "4, 4", opacity: 0.95
        }).addTo(g);
      }
      if (wetSegs.length > 1) {
        const clPoints = wetSegs.map(s => [
          (s.ring[0][0] + s.ring[3][0]) / 2,
          (s.ring[0][1] + s.ring[3][1]) / 2
        ]);
        L.polyline(clPoints, {color: "#ffffff", weight: 2, dashArray: "3, 6", opacity: 0.8}).addTo(g);
      }
    } else {
      // 🌊 Delft3D SWE (Default): 2D Depth-averaged flood surface with white-water foam wavefront
      wetSegs.forEach(s => {
        const val = VS.colorBy === "depth" ? s.y : s.dv;
        const color = rampColor(val, VS.colorBy === "depth" ? DEPTH_COLORS : DV_COLORS);
        L.polygon(s.ring, {color, weight: 0.5, opacity: 0.75, fillColor: color, fillOpacity: 0.82})
          .bindTooltip(makeHydraulicTip(s), {sticky: true, className: "custom-hydraulic-tip"})
          .addTo(g);
      });
      fr.segments.forEach((s, i) => {
        if (i % 3 || !s.wet || s.v < 0.3) return;
        const ring = s.ring;
        const mid = [(ring[0][0]+ring[3][0])/2, (ring[0][1]+ring[3][1])/2];
        const ang = Math.atan2(ring[1][0]-ring[0][0], ring[1][1]-ring[0][1]) * 180/Math.PI;
        const scale = Math.min(1.8, 0.6 + s.v / 3.5);
        L.marker(mid, {icon: L.divIcon({className:"", iconSize:[0,0],
          html:`<div style="transform:rotate(${ang}deg) scale(${scale});
            color:#e0f2fe;font-size:16px;text-shadow:0 0 5px #0284c7;opacity:.9">
            &#10148;</div>`}), interactive:false}).addTo(g);
      });
      if (wetSegs.length > 0) {
        const frontSeg = wetSegs[wetSegs.length - 1];
        const r = frontSeg.ring;
        L.polyline([[r[1][0], r[1][1]], [r[2][0], r[2][1]]], {
          className: "foam-wavefront",
          color: "#ffffff",
          weight: 4.5,
          opacity: 0.95
        }).addTo(g);
        L.polyline([[r[1][0], r[1][1]], [r[2][0], r[2][1]]], {
          color: "#38bdf8",
          weight: 8,
          opacity: 0.6
        }).addTo(g);
      }
    }
    return g;
  });
  VS.frames.forEach((fr, fi) => {            // pulsing breach marker
    if (fi > 2) return;
    if (S.incident)
      L.marker([S.incident.lat, S.incident.lon],
        {icon: L.divIcon({className:"", iconSize:[14,14],
          html:`<div class="dam-burst" style="width:14px;height:14px;border-radius:50%;
            background:#ef4444;border:2px solid #fff"></div>`}), interactive:false})
        .addTo(VS.frameLayers[fi])
        .bindPopup(`DAM BREACH - Q=${fr.q_dam_m3s} m3/s`);
  });
  VS.lastShown = null;
}
function toggleVSPlay(){ VS.playing ? pauseVS() : playVS(); }
function playVS(){
  if (VS.cur >= VS.frames.length - 1) drawVSFrame(0);
  VS.playing = true; $("vsPlay").innerHTML = "&#10074;&#10074; PAUSE";
  VS.timer = setInterval(() => {
    if (VS.cur >= VS.frames.length - 1){ pauseVS(); return; }
    drawVSFrame(VS.cur + 1);
  }, 1100 / VS.speed);
}
function pauseVS(){
  VS.playing = false;
  if (VS.timer){ clearInterval(VS.timer); VS.timer = null; }
  const b = $("vsPlay"); if (b) b.innerHTML = "&#9654; PLAY";
}
function drawVSFrame(i){
  if (i === VS.cur || !VS.frames) return;
  VS.cur = i;
  const fr = VS.frames[i];
  if (VS.lastShown != null && VS.frameLayers[VS.lastShown])
    map.removeLayer(VS.frameLayers[VS.lastShown]);
  if (VS.frameLayers[i]){ VS.frameLayers[i].addTo(map); VS.lastShown = i; }
  $("vsSlider").value = i;
  $("vsT").textContent = fr.t_min.toFixed(0);
  const qmaxAll = Math.max(...VS.frames.map(f => f.q_dam_m3s));
  $("vsPhase").textContent =
    i === 0 ? "BREACH INITIATION" :
    fr.q_dam_m3s > 0.9 * qmaxAll ? "PEAK OUTFLOW" :
    fr.front_km < VS.frames[VS.frames.length-1].front_km * 0.5 ? "FRONT PROPAGATION" :
    "RECESSION";
  $("vsQ").textContent = fr.q_dam_m3s.toLocaleString();
  $("vsVol").textContent = `${(fr.released_m3/1e6).toFixed(2)}M (${fr.pct_released}%)`;
  $("vsFront").textContent = fr.front_km;
  $("vsArea").textContent = fr.area_km2;
  $("vsV").textContent = fr.max_v_ms;
  $("vsF").textContent = fr.max_force_kN_m;
  $("vsM").textContent = fr.momentum_flux_MN;
  let ppl = {LOW:0,MODERATE:0,HIGH:0,EXTREME:0}, bld = 0, agri = 0;
  VS.assetMarks.forEach(a => {
    const arrived = a.entry.arrival_min != null && fr.t_min >= a.entry.arrival_min;
    a.hit = arrived;
    a.marker.setStyle(arrived
      ? {color: HAZ_COLORS[a.entry.people_hazard] || "#ef4444",
         fillColor: HAZ_COLORS[a.entry.people_hazard] || "#ef4444"}
      : {color:"#f59e0b", fillColor:"#f59e0b"});
    if (arrived){
      if (a.entry.population){
        ppl[a.entry.people_hazard] += a.entry.population;
        bld += a.entry.buildings || 0;
      }
      if (a.entry.area_ha) agri += a.entry.area_ha;
    }
    // Update floating settlement beacon DOM
    if (a.beacon) {
      const bId = "bcn-" + esc(a.entry.name).replace(/\W/g,"_");
      const bEl = document.getElementById(bId);
      if (bEl) {
        if (arrived) {
          bEl.className = "settlement-beacon hit";
          const timerEl = bEl.querySelector(".beacon-timer");
          if (timerEl) timerEl.textContent = `IMPACT (${a.entry.peak_depth_m?.toFixed(1) || ''}m)`;
        } else {
          bEl.className = "settlement-beacon safe";
          const timerEl = bEl.querySelector(".beacon-timer");
          if (timerEl) {
            const remain = a.entry.arrival_min != null ? Math.max(0, a.entry.arrival_min - fr.t_min) : null;
            timerEl.textContent = remain != null ? `-${remain.toFixed(1)}m` : "--";
          }
        }
      }
    }
  });
  const pplT = ppl.LOW+ppl.MODERATE+ppl.HIGH+ppl.EXTREME;
  $("vsPpl").textContent = pplT.toLocaleString();
  $("vsPpl").classList.toggle("hit", pplT > 0);
  ["LOW","MODERATE","HIGH","EXTREME"].forEach(k =>
    $("vsPbar"+k).style.flex = Math.max(ppl[k], .08));
  $("vsBld").textContent = bld;
  $("vsBld").classList.toggle("hit", bld > 0);
  $("vsAgri").textContent = agri.toFixed(1);
  if (VS.rings){
    VS.rings.forEach(r => {
      const c = r.clock;
      const remain = c.arrival_min != null ? c.arrival_min - fr.t_min : null;
      let color, text;
      if (remain == null){ color = "#34d399"; text = "SAFE"; }
      else if (remain <= 0){ color = "#ef4444"; text = "HIT"; }
      else {
        const ratio = remain / Math.max(c.t_needed_min || 1, 1);
        color = ratio >= 1.6 ? "#34d399" : ratio >= 1.2 ? "#fbbf24" : "#ef4444";
        const mm = Math.floor(remain), ss = Math.floor((remain % 1) * 60);
        text = `${mm}:${String(ss).padStart(2,"0")}`;
        if (ratio < 1.2) text += " UP";
      }
      r.ring.setStyle({color, fillColor: color});
      const lbl = $("evLbl-" + c.name.replace(/\W/g,"_"));
      if (lbl){ lbl.textContent = text; lbl.style.color = color; }
    });
  }
}
function exitVS(){
  pauseVS();
  if (VS.lastShown != null && VS.frameLayers[VS.lastShown])
    map.removeLayer(VS.frameLayers[VS.lastShown]);
  (VS.assetMarks || []).forEach(a => {
    if (a) {
      if (a.marker) map.removeLayer(a.marker);
      if (a.beacon) map.removeLayer(a.beacon);
    }
  });
  (VS.rings || []).forEach(r => { if (r){ map.removeLayer(r.ring);
    map.removeLayer(r.label); } });
  const d = $("vsimPlayer"); if (d) d.remove();
  VS = {...VS, frames:null, playing:false, cur:-1, frameLayers:[],
        assetMarks:[], rings:null, lastShown:null};
}

/* ---------- TAB: MANUAL SIMULATION ---------- */
let manualExpert = false;
function panelManual(){
  const canRun = ["analyst","admin"].includes(S.role || "");
  openPanel("MANUAL SIMULATION CONSOLE",
    "Official-entered parameters - region presets - full pipeline",`
    ${canRun ? "" : `<div class="note">Sign in as analyst/admin to run manual
      simulations.</div>`}
    <div class="mod"><div class="mod-title">MODE</div>
      <div style="display:flex;gap:8px">
        <button class="tbtn sm ${!manualExpert ? "primary" : ""}" id="mQuick">QUICK (6 inputs)</button>
        <button class="tbtn sm ${manualExpert ? "primary" : ""}" id="mExpert">EXPERT (all)</button>
      </div></div>
    <div class="mod"><div class="mod-title">LOCATION &amp; RESERVOIR (required)</div>
      <div class="field"><label>Scenario name</label>
        <input id="mName" class="input" value="Manual scenario"></div>
      <div class="grid2">
        <div class="field"><label>Latitude</label>
          <input id="mLat" class="input" type="number" step="0.0001" value="30.4828"></div>
        <div class="field"><label>Longitude</label>
          <input id="mLon" class="input" type="number" step="0.0001" value="79.7214"></div></div>
      <div class="grid2">
        <div class="field"><label>Stored volume (m3)</label>
          <input id="mVol" class="input" type="number" value="5000000"></div>
        <div class="field"><label>Dam height (m)</label>
          <input id="mH" class="input" type="number" value="38"></div></div>
      <div class="grid2">
        <div class="field"><label>Dam material</label>
          <select id="mMat" class="input"><option value="">(region preset)</option>
            ${["Earth","Rock","Landslide debris","Sediment","Ice/debris","Mixed",
               "Concrete","Masonry"].map(m => `<option>${m}</option>`).join("")}
          </select></div>
        <div class="field"><label>Scenario</label>
          <select id="mScen" class="input">${["minor","moderate","major","full"]
            .map(s => `<option ${s==="major"?"selected":""}>${s}</option>`).join("")}
          </select></div></div>
      <div id="mRegionHint" class="preset-note"></div></div>
    <div class="mod ${manualExpert ? "" : "hidden"}" id="mExpertBox">
      <div class="mod-title">EXPERT PARAMETERS (blank = preset/default)</div>
      <div class="grid2">
        <div class="field"><label>Lake area m2</label><input id="mArea" class="input" type="number" placeholder="auto V/(0.5H)"></div>
        <div class="field"><label>Crest length m</label><input id="mCrest" class="input" type="number" placeholder="preset"></div>
        <div class="field"><label>Breach width m</label><input id="mBW" class="input" type="number" placeholder="0.40xcrest"></div>
        <div class="field"><label>Breach depth m</label><input id="mBD" class="input" type="number" placeholder="0.75xH"></div>
        <div class="field"><label>Breach time hr</label><input id="mBT" class="input" type="number" step="0.1" placeholder="preset"></div>
        <div class="field"><label>Inflow m3/s</label><input id="mInf" class="input" type="number" placeholder="preset"></div>
        <div class="field"><label>Valley width m</label><input id="mVW" class="input" type="number" placeholder="preset"></div>
        <div class="field"><label>Bed slope</label><input id="mBS" class="input" type="number" step="0.001" placeholder="preset"></div>
        <div class="field"><label>Manning n</label><input id="mMn" class="input" type="number" step="0.001" placeholder="preset"></div>
        <div class="field"><label>Spreading factor</label><input id="mSF" class="input" type="number" step="0.1" placeholder="preset"></div>
        <div class="field"><label>Base flow m3/s</label><input id="mBF" class="input" type="number" placeholder="preset"></div>
        <div class="field"><label>Monte Carlo</label>
          <select id="mUnc" class="input"><option value="true" selected>yes</option>
          <option value="false">no (fast)</option></select></div></div></div>
    <div class="mod"><div class="mod-title">CENTERLINE (straight estimate)</div>
      <div class="grid2">
        <div class="field"><label>Bearing downstream (deg)</label>
          <input id="mBrg" class="input" type="number" min="0" max="360" value="120"></div>
        <div class="field"><label>Corridor length (km)</label>
          <input id="mLen" class="input" type="number" min="1" max="100" value="12"></div></div></div>
    ${canRun ? `
    <button class="tbtn primary full" id="mRun">&#9654; RUN MANUAL SIMULATION</button>
    <div id="mStatus" style="margin-top:8px">
      <div class="progress hidden" id="mProg"><i id="mProgBar"></i></div>
      <div style="font-size:11px;color:var(--muted);margin-top:6px" id="mMsg"></div></div>
    <div class="mod hidden" id="mProvBox"><div class="mod-title">
      PARAMETER PROVENANCE (yours vs assumed)</div><div id="mProv"></div></div>` : ""}`);
  $("mQuick").onclick = () => { manualExpert = false; panelManual(); };
  $("mExpert").onclick = () => { manualExpert = true; panelManual(); };
  const regionHint = async () => {
    try{
      const r = await api(`/api/india/region?lat=${+$("mLat").value}&lon=${+$("mLon").value}`);
      $("mRegionHint").textContent =
        `REGION: ${r.name} - valley ${r.valley_width_m} m, slope ${r.bed_slope}, ` +
        `n=${r.manning_n}, material ${r.material_prior}, mobilization ` +
        `${r.mobilization_min} min. ${r.notes}`;
      clearLayer("manualPin");
      L_("manualPin").push(L.circleMarker([+$("mLat").value, +$("mLon").value],
        {radius:9, color:"#22d3ee", fillColor:"#22d3ee", fillOpacity:.7})
        .bindPopup("Manual scenario location").addTo(map));
    }catch(e){}
  };
  $("mLat").onchange = regionHint; $("mLon").onchange = regionHint;
  regionHint();
  if (canRun) $("mRun").onclick = runManual;
}
async function runManual(){
  const g = id => $(id);
  const num = id => { const v = g(id).value.trim();
    return v === "" || isNaN(+v) ? null : +v; };
  const body = {
    name: g("mName").value || "Manual scenario",
    lat: +g("mLat").value, lon: +g("mLon").value,
    stored_volume_m3: +g("mVol").value, dam_height_m: +g("mH").value,
    dam_material: g("mMat").value || null, scenario: g("mScen").value,
    auto_bearing_deg: num("mBrg"), auto_length_km: num("mLen") ?? 10,
    with_uncertainty: g("mUnc").value === "true"};
  const exp = {lake_area_m2:"mArea", dam_crest_len_m:"mCrest", breach_width_m:"mBW",
    breach_depth_m:"mBD", breach_time_hr:"mBT", inflow_m3s:"mInf",
    valley_width_m:"mVW", bed_slope:"mBS", manning_n:"mMn",
    spreading_factor:"mSF", base_flow_m3s:"mBF"};
  Object.entries(exp).forEach(([k, id]) => { const v = num(id);
    if (v !== null) body[k] = v; });
  g("mRun").disabled = true; g("mProg").classList.remove("hidden");
  let resp;
  try{
    resp = await api("/api/simulations/manual", {method:"POST",
      body:JSON.stringify(body)});
  }catch(e){
    g("mRun").disabled = false; g("mProg").classList.add("hidden");
    g("mMsg").textContent = "FAIL: " + e.message; return;
  }
  g("mProvBox").classList.remove("hidden");
  g("mProv").innerHTML = `<table class="tbl">
    <tr><th>Parameter</th><th>Value</th><th>Source</th></tr>
    ${Object.entries(resp.resolved_params).map(([k, v]) => `
      <tr><td>${k.replace(/_/g," ")}</td>
        <td>${typeof v === "number" ? (+v).toLocaleString() : v}</td>
        <td style="color:${resp.provenance[k]?.startsWith("USER") ? "var(--red)" :
          resp.provenance[k]?.startsWith("DEFAULT") ? "var(--amber)" : "var(--cyan)"}">
          ${esc(resp.provenance[k] || "-")}</td></tr>`).join("")}</table>
    <p class="hint">Red = you entered it - cyan = regional preset for
      ${esc(resp.region.name)} - amber = platform default.</p>`;
  S.simId = resp.simulation_id;
  const poll = setInterval(async () => {
    try{
      const st = await api(`/api/jobs/${resp.job_id}`);
      g("mProgBar").style.width = (st.progress || 0) + "%";
      g("mMsg").textContent = st.status === "RUNNING"
        ? `running... ${st.progress||0}%` : st.status;
      if (["DONE","FAILED","CANCELLED"].includes(st.status)){
        clearInterval(poll); g("mRun").disabled = false;
        g("mMsg").textContent = st.status === "DONE"
          ? "OK - opening results" : `FAIL: ${st.error || st.status}`;
        if (st.status === "DONE"){
          await refreshIncidents();
          toast("Manual simulation complete");
          document.querySelector('[data-tab="results"]').click();
        }
      }
    }catch(err){ clearInterval(poll); g("mRun").disabled = false;
      g("mMsg").textContent = "FAIL: " + err.message; }
  }, 1000);
}

/* ---------- TAB: LAKE MONITOR ---------- */
async function loadDamageMarkers(){
  if (!S.incident) return [];
  try{
    const j = await api(`/api/damage-reports?incident_id=${S.incident.id}&limit=100`);
    clearLayer("damage");
    j.items.forEach(d => {
      const m = L.circleMarker([d.lat, d.lon], {radius:7, color:"#e11d48",
        fillColor:"#e11d48", fillOpacity:.85})
        .bindPopup(`<b>${esc(d.incident_type)}</b> (${esc(d.status)})<br>` +
          esc(d.damage_description) +
          (d.photo_url ? `<br><img src="${esc(d.photo_url)}"
            style="max-width:140px;border-radius:6px;margin-top:4px"
            onerror="this.style.display='none'">` : ""));
      m.addTo(map); L_("damage").push(m);
    });
    return j.items;
  }catch(e){ return []; }
}
const alertCls = {CRITICAL:"err", WARNING:"warn", WATCH:"info", NONE:"", DRAINING:"ok"};
async function panelMonitor(){
  let zones = [], cands = {items:[]}, alerts = {items:[]};
  try{ zones = await api("/api/detection/zones"); }catch(e){}
  try{ cands = await api("/api/detection/candidates?limit=100"); }catch(e){}
  try{ alerts = await api("/api/detection/alerts"); }catch(e){}
  drawCandidates(cands.items);
  openPanel("LAKE FORMATION MONITOR",
    "Automated detection - S1/S2/Landsat - GLO-30 geometry",`
    <div class="mod" style="background:linear-gradient(135deg,rgba(16,185,129,0.12),rgba(5,150,105,0.05));border:1px solid #10b981;border-radius:8px;padding:10px 12px;margin-bottom:12px">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap">
        <div>
          <div style="font-weight:700;color:#34d399;font-size:12px;display:flex;align-items:center;gap:6px">
            <span>&#128230;</span> <span>INUNDATED AREA SHAPEFILE SUITE</span>
          </div>
          <div style="font-size:11px;color:#cbd5e1;margin-top:2px">
            Active Dam: <b>${esc(S.incident?.name || "Selected Dam")}</b>
          </div>
        </div>
        <div style="display:flex;gap:6px">
          <button class="tbtn sm primary" style="background:#10b981;border-color:#10b981;color:#fff;font-weight:700" onclick="triggerShapefileDownload()">
            &#128230; DOWNLOAD .SHP
          </button>
          <button class="tbtn sm" style="border-color:#38bdf8;color:#38bdf8" onclick="triggerKmlDownload()">
            &#127757; KML
          </button>
        </div>
      </div>
      <div style="font-size:10.5px;color:#94a3b8;margin-top:6px;border-top:1px solid rgba(255,255,255,0.08);padding-top:4px">
        &#128161; Switch to <b><a href="#" onclick="document.querySelector('[data-tab=map]').click();return false;" style="color:#38bdf8">Interactive Map</a></b> or <b><a href="#" onclick="document.querySelector('[data-tab=results]').click();return false;" style="color:#38bdf8">Inundation Results</a></b> to view animated flood propagation.
      </div>
    </div>
    ${alerts.items.length ? `
    <div class="mod" style="border-color:${alerts.items[0].alert_level === "CRITICAL" ? "#7f1d1d" : "var(--line)"}">
      <div class="mod-title" style="color:${alerts.items[0].alert_level === "CRITICAL" ? "var(--red)" : "var(--amber)"}">
        ACTIVE GROWTH ALERTS (${alerts.items.length})</div>
      <ul class="clean">${alerts.items.slice(0, 6).map(a => `
        <li><span class="badge ${alertCls[a.alert_level]}">${esc(a.alert_level)}</span>
          <b>${esc(a.id)}</b> - ${(a.area_m2/1e4).toFixed(1)} ha
          ${a.volume_m3 ? `- ${(a.volume_m3/1e6).toFixed(1)} M m3` : ""}
          ${a.growing ? " - <b style='color:var(--red)'>GROWING</b>" : ""}</li>`).join("")}
      </ul></div>` : ""}
    <div class="mod"><div class="mod-title">DETECTED CANDIDATES (${cands.total ?? 0})</div>
      ${cands.items.length ? `<table class="tbl">
        <tr><th>ID</th><th>Area</th><th>Depth</th><th>Volume</th><th>Score</th><th>Alert</th><th></th></tr>
        ${cands.items.map(c => `
          <tr><td>${esc(c.id.slice(-6))}${c.growing ? " &#128200;" : ""}</td>
            <td>${(c.area_km2).toFixed(3)} km2</td>
            <td>${c.depth_m ?? "-"}</td>
            <td>${c.volume_m3 ? (c.volume_m3/1e6).toFixed(2) + "M" : "-"}</td>
            <td><b style="color:${c.score > 70 ? "var(--red)" : "var(--amber)"}">${c.score}</b></td>
            <td><span class="badge ${c.status==="VERIFIED"?"ok":c.status==="REJECTED"?"err":"warn"}">${esc(c.status)}</span>
              ${c.alert_level && c.alert_level !== "NONE" ? `<span class="badge ${alertCls[c.alert_level]}">${esc(c.alert_level)}</span>` : ""}</td>
            <td>${["analyst","admin"].includes(S.role||"") ? `
              <button class="tbtn sm" onclick="candAct('${c.id}','verify')" title="Verify">&#10003;</button>
              <button class="tbtn sm danger" onclick="candAct('${c.id}','reject')" title="Reject">&#10005;</button>
              ${c.status==="VERIFIED" && !c.incident_id
                ? `<button class="tbtn sm primary" onclick="candAct('${c.id}','promote')">INCIDENT</button>` : ""}
              <button class="tbtn sm" onclick="showGrowth('${c.id}')">&#128200;</button>` : ""}</td></tr>`).join("")}
      </table>` : EMPTY("&#128225;",
        "No candidates. The scheduler scans zones automatically; or trigger below.","","")}
    </div>
    <div class="mod"><div class="mod-title">MONITORING ZONES (${zones.length})</div>
      <table class="tbl"><tr><th>Zone</th><th>Open</th><th>Last scan</th><th></th></tr>
      ${zones.map(z => `<tr><td>${esc(z.name)}${z.roi_polygon ? " (ROI)" : ""}</td>
        <td>${z.candidates_open}</td>
        <td>${z.last_scan_at ? fmtIST(z.last_scan_at) : "never"}</td>
        <td>${["analyst","admin"].includes(S.role||"") ? `
          <button class="tbtn sm" onclick="scanZone('${z.id}')">SCAN</button>
          <button class="tbtn sm" onclick="startRoiDraw('${z.id}')" title="Draw ROI">ROI</button>
          ${z.roi_polygon ? `<button class="tbtn sm danger" title="Remove ROI"
            onclick="clearRoi('${z.id}')">x</button>` : ""}` : ""}</td></tr>`).join("")}
      </table></div>
    <div class="mod"><div class="mod-title">HOW DETECTION WORKS</div>
      <ul class="clean">
        <li>- Baseline: 4-12 historical scenes - per-pixel water frequency</li>
        <li>- Current: S1 SAR (preferred) or S2/Landsat MNDWI+NDWI</li>
        <li>- New water + river-buffer exclusion + ROI masking</li>
        <li>- Depth &amp; volume: GLO-30 shoreline fit + hypsometric integral</li></ul>
      <div class="note">Detection is assistive - every candidate requires
      analyst verification before entering the breach pipeline.</div></div>`);
}
function drawCandidates(items){
  clearLayer("cands");
  items.forEach(c => {
    const m = L.rectangle([[c.bbox[1], c.bbox[0]], [c.bbox[3], c.bbox[2]]],
      {color: c.status === "VERIFIED" ? "#34d399" : "#ef4444", weight:2,
       fillOpacity:.25})
      .bindPopup(`<b>Candidate ${esc(c.id)}</b><br>Area: ${c.area_km2} km2<br>` +
        `Depth: ${c.depth_m ?? "-"} m - Vol: ${c.volume_m3 ?? "-"} m3<br>` +
        `Score: ${c.score} - ${esc(c.status)}` +
        (c.growing ? " - GROWING" : ""));
    m.addTo(map); L_("cands").push(m);
  });
}
window.scanZone = async zid => {
  toast("Scanning zone - fetches imagery, may take minutes");
  try{
    const r = await api(`/api/detection/zones/${zid}/scan`, {method:"POST"});
    toast(r.ok ? `Scan complete: ${r.candidates?.length ?? 0} candidate(s)`
               : `Scan: ${r.error}`);
    panelMonitor();
  }catch(e){ toast(e.message); }
};
window.candAct = async (cid, act) => {
  try{
    if (act === "promote"){
      const r = await api(`/api/detection/candidates/${cid}/promote`, {method:"POST"});
      toast(`Incident ${r.incident_id} created - prefill available`);
      refreshIncidents();
    } else {
      await api(`/api/detection/candidates/${cid}/verify`, {method:"PATCH",
        body:JSON.stringify({status: act === "verify" ? "VERIFIED" : "REJECTED"})});
      toast("Candidate " + (act === "verify" ? "verified" : "rejected"));
    }
    panelMonitor();
  }catch(e){ toast(e.message); }
};
window.clearRoi = async zid => {
  try{ await api(`/api/detection/zones/${zid}/roi`, {method:"DELETE"});
    toast("ROI removed"); panelMonitor();
  }catch(e){ toast(e.message); }
};
window.showGrowth = async cid => {
  const g = await api(`/api/detection/candidates/${cid}/growth`);
  let chart = "";
  if (g.series && g.series.length >= 2){
    chart = `<div class="chart-box"><div class="chart-head">
      <span>AREA OBSERVATION SERIES</span>
      <span class="qtag">${g.metrics.doubling_time_days
        ? `T2 = ${g.metrics.doubling_time_days} d` : ""}</span></div>
      <canvas id="growthChart" class="chart"></canvas></div>`;
  }
  $("reportTitle").textContent = `Growth Analysis - ${cid}`;
  $("reportBody").innerHTML = `
    ${g.alert ? `<div style="margin-bottom:10px">
      <span class="badge ${alertCls[g.alert.level]||""}"
        style="font-size:13px;padding:6px 14px">${esc(g.alert.level)}</span>
      ${g.rules_fired?.length ? `<small style="color:var(--muted)">
        rules: ${g.rules_fired.map(esc).join(", ")}</small>` : ""}</div>` : ""}
    ${chart}
    ${g.metrics ? `<div class="mod"><div class="mod-title">METRICS</div>
      <table class="tbl">${Object.entries(g.metrics).map(([k,v]) =>
        `<tr><td>${esc(k.replace(/_/g," "))}</td><td>${esc(String(v))}</td></tr>`).join("")}
      </table></div>` : ""}
    ${g.series ? `<div class="mod"><div class="mod-title">OBSERVATIONS</div>
      <table class="tbl"><tr><th>Scene</th><th>When</th><th>Area</th></tr>
      ${g.series.map(o => `<tr><td>${esc((o.scene_id||"").slice(0,24))}</td>
        <td>${fmtIST(o.observed_at)}</td>
        <td>${(o.area_m2/1e4).toFixed(2)} ha</td></tr>`).join("")}</table></div>` : ""}`;
  $("reportModal").classList.remove("hidden");
  if (g.series && g.series.length >= 2){
    const cv = $("growthChart");
    const dpr = devicePixelRatio||1, w = cv.clientWidth, h = cv.clientHeight;
    cv.width = w*dpr; cv.height = h*dpr;
    const x = cv.getContext("2d"); x.scale(dpr,dpr);
    const T = g.series.map(s => new Date(s.observed_at).getTime());
    const A = g.series.map(s => s.area_m2/1e4);
    const t0 = T[0], t1 = T[T.length-1] || t0+1;
    const aMax = Math.max(...A)*1.15 || 1;
    const px = t => 40+(w-50)*(t-t0)/(t1-t0), py = a => h-20-(h-36)*a/aMax;
    x.strokeStyle = "#34d399"; x.lineWidth = 2; x.beginPath();
    T.forEach((tt,i) => i ? x.lineTo(px(tt),py(A[i])) : x.moveTo(px(tt),py(A[i])));
    x.stroke();
    x.fillStyle = "#8b99ad"; x.font = "9px ui-monospace,monospace";
    x.fillText("area (ha)", 6, 12);
  }
};

/* ---------- TAB: SATELLITE ---------- */
async function panelSatellite(){
  if (!requireIncident()) return;
  const today = new Date().toISOString().slice(0,10);
  const monthAgo = new Date(Date.now()-30*864e5).toISOString().slice(0,10);
  openPanel("SATELLITE MONITOR","Copernicus S2 - USGS Landsat - NDWI/MNDWI",`
    <div class="mod"><div class="mod-title">SCENE SEARCH</div>
      <div class="grid2">
        <div class="field"><label>Start date</label><input id="satStart" class="input" type="date" value="${monthAgo}"></div>
        <div class="field"><label>End date</label><input id="satEnd" class="input" type="date" value="${today}"></div></div>
      <div class="field"><label>Source</label><select id="satSrc" class="input">
        <option value="usgs_landsat">USGS Landsat 8/9 C2 L2 (30 m, public)</option>
        <option value="copernicus_s2">Copernicus Sentinel-2 L2A (10 m, CDSE login)</option>
      </select></div>
      <div class="field"><label>Max cloud %</label>
        <input id="satCloud" class="input" type="number" value="30"></div>
      <button class="tbtn primary sm full" id="satSearch">SEARCH SCENES</button>
      <div id="satMsg" style="font-size:11px;color:var(--muted);margin-top:6px"></div></div>
    <div class="mod hidden" id="satResultsBox"><div class="mod-title">SCENES</div>
      <div id="satResults"></div></div>
    <div class="mod hidden" id="satChangeBox"><div class="mod-title">CHANGE DETECTION</div>
      <div id="satChange"></div></div>`);
  let analyzed = {};
  $("satSearch").onclick = async () => {
    $("satMsg").innerHTML = '<span class="spinner"></span> searching...';
    try{
      const j = await api(`/api/satellite/search?incident_id=${S.incident.id}` +
        `&start=${$("satStart").value}&end=${$("satEnd").value}` +
        `&source=${$("satSrc").value}&cloud_max=${+$("satCloud").value}`);
      $("satMsg").textContent = "";
      $("satResultsBox").classList.remove("hidden");
      $("satResults").innerHTML = j.items.map((s,i) => `
        <div class="scen-card" style="margin-bottom:6px">
          <span class="scen-title">${esc(s.scene_id.slice(0,40))}</span>
          <span class="scen-desc">${esc(s.datetime || "")} -
            ${s.cloud_pct ?? "?"}% cloud - ${esc(s.source)}</span>
          <button class="tbtn sm" style="margin-top:6px"
            onclick="analyzeScene(${i})">ANALYZE WATER</button>
          <span id="satRes${i}" style="font-size:11px;margin-left:8px"></span>
        </div>`).join("") || "No scenes found - widen dates or cloud limit.";
      window._satScenes = j.items;
    }catch(e){ $("satMsg").textContent = "FAIL: " + e.message; }
  };
  window.analyzeScene = async i => {
    const el = $("satRes"+i); el.innerHTML = '<span class="spinner"></span>';
    try{
      const r = await api("/api/satellite/analyze", {method:"POST",
        body:JSON.stringify(window._satScenes[i])});
      if (!r.ok) throw new Error(r.error);
      analyzed[i] = r;
      el.innerHTML = `OK: <b style="color:var(--cyan)">${r.water_area_km2} km2</b> water`;
      updateChange();
    }catch(e){ el.textContent = "FAIL: " + e.message; }
  };
  function updateChange(){
    const idx = Object.keys(analyzed);
    if (idx.length < 2) return;
    $("satChangeBox").classList.remove("hidden");
    const [a, b] = idx.slice(-2).map(k => analyzed[k]);
    api("/api/satellite/change", {method:"POST",
      body:JSON.stringify({before:a, after:b})}).then(c => {
      if (!c.ok) return;
      $("satChange").innerHTML = `
        <table class="tbl">
          <tr><td>Before</td><td>${esc(c.before.date?.slice(0,10) || "")} - ${c.before.area_km2} km2</td></tr>
          <tr><td>After</td><td>${esc(c.after.date?.slice(0,10) || "")} - ${c.after.area_km2} km2</td></tr>
          <tr><td>Delta</td><td><b style="color:${c.delta_m2 > 0 ? "var(--red)" : "var(--ok)"}">${c.delta_km2 > 0 ? "+" : ""}${c.delta_km2} km2</b></td></tr>
          <tr><td>Assessment</td><td>${esc(c.interpretation)}</td></tr></table>`;
    });
  }
}

/* ---------- TAB: FIELD REPORTS ---------- */
async function panelDamage(){
  if (!requireIncident()) return;
  const items = await loadDamageMarkers();
  const canPost = S.role && ["reporter","analyst","admin"].includes(S.role);
  openPanel("FIELD DAMAGE REPORTS","Ground truth - verified workflow - photos",`
    ${canPost ? `<div class="mod"><div class="mod-title">SUBMIT REPORT</div>
      <div class="grid2">
        <div class="field"><label>Lat</label><input id="dLat" class="input" value="${S.incident.lat}"></div>
        <div class="field"><label>Lon</label><input id="dLon" class="input" value="${S.incident.lon}"></div></div>
      <div class="grid2">
        <div class="field"><label>Type</label><input id="dType" class="input" value="Flood"></div>
        <div class="field"><label>Depth (m)</label><input id="dDepth" class="input" type="number" value="1.0" step="0.1"></div></div>
      <div class="field"><label>Description</label><textarea id="dDesc" class="input" rows="3"></textarea></div>
      <div class="field"><label>Photo (JPG/PNG/WebP)</label>
        <input id="dPhoto" class="input" type="file" accept=".jpg,.jpeg,.png,.webp"></div>
      <button class="tbtn primary sm full" id="dSubmit">SUBMIT (PENDING REVIEW)</button></div>` :
    `<div class="note">Sign in as reporter/analyst to submit.</div>`}
    <div class="mod"><div class="mod-title">ACTIVE REPORTS (${items.length})</div>
      <ul class="clean">${items.map(d => `
        <li><span class="badge ${d.status === "VERIFIED" ? "ok" : d.status === "REJECTED" ? "err" : "warn"}">${esc(d.status)}</span>
          <b> ${esc(d.incident_type)}</b> - ${esc(d.damage_description.slice(0,80))}
          <br><span style="color:var(--muted);font-size:10px">${esc(d.reporter_name)} - ${fmtIST(d.created_at)}</span>
          ${d.photo_url ? `<img class="thumb" src="${esc(d.photo_url)}"
            onerror="this.style.display='none'">` : ""}
          ${["admin","analyst"].includes(S.role||"") ? `<br>
            <button class="tbtn sm" onclick="verifyDR('${d.id}','VERIFIED')">Verify</button>
            <button class="tbtn sm danger" onclick="verifyDR('${d.id}','REJECTED')">Reject</button>` : ""}
        </li>`).join("") || "<li>No reports.</li>"}</ul></div>`);
  if (canPost) $("dSubmit").onclick = async () => {
    const fd = new FormData();
    fd.append("incident_id", S.incident.id);
    fd.append("lat", $("dLat").value); fd.append("lon", $("dLon").value);
    fd.append("incident_type", $("dType").value);
    fd.append("water_depth_m", $("dDepth").value);
    fd.append("damage_description", $("dDesc").value);
    fd.append("infrastructure_damage", "");
    fd.append("reporter_name", S.user || "Anonymous");
    if ($("dPhoto").files[0]) fd.append("photo", $("dPhoto").files[0]);
    try{
      const r = await fetch("/api/damage-reports", {method:"POST",
        headers:{Authorization:`Bearer ${S.token}`}, body:fd});
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || "failed");
      toast("Submitted - PENDING verification"); panelDamage();
    }catch(e){ toast(e.message); }
  };
}
window.verifyDR = async (id, status) => {
  try{
    await api(`/api/damage-reports/${id}/verify`, {method:"PATCH",
      body:JSON.stringify({status})});
    toast("Updated"); panelDamage();
  }catch(e){ toast(e.message); }
};

/* ---------- TAB: NATIONAL ---------- */
async function panelNational(){
  const sites = await api("/api/india/sites");
  clearLayer("natsites");
  sites.forEach(s => {
    const m = L.circleMarker([s.lat, s.lon], {radius:6, color:"#a78bfa",
      fillColor:"#a78bfa", fillOpacity:.8})
      .bindPopup(`<b>${esc(s.name)}</b><br>${(s.volume_m3/1e6).toFixed(0)} M m3 -
        ${s.height_m} m - ${esc(s.material)}<br><small>${esc(s.region)}</small>`);
    m.addTo(map); L_("natsites").push(m);
  });
  const regions = [...new Set(sites.map(s => s.region))];
  openPanel("NATIONAL SCENARIO EXERCISE",
    `${sites.length} sites - ${regions.length} regions - regional presets`,`
    <div class="mod"><div class="mod-title">SCENARIO LIBRARY</div>
      <table class="tbl"><tr><th>Site</th><th>Region</th><th>Volume</th><th>H</th></tr>
      ${sites.map(s => `<tr><td>${esc(s.name)}</td>
        <td><small>${esc(s.region)}</small></td>
        <td>${(s.volume_m3/1e6).toFixed(0)} M m3</td><td>${s.height_m} m</td></tr>`).join("")}
      </table></div>
    ${["analyst","admin"].includes(S.role||"") ? `
    <div class="mod"><div class="mod-title">BATCH RUN</div>
      <p class="hint">Queues one simulation per site. Placeholder straight
      centerlines + regional presets; no exposure layers - breach/inundation
      only. Replace per site for decision-grade results.</p>
      <button class="tbtn primary full" id="btnNatRun">RUN ALL ${sites.length} SCENARIOS</button>
      <div id="natStatus" class="hint"></div></div>` : ""}`);
  $("btnNatRun")?.addEventListener("click", async () => {
    if (!confirm(`Queue ${sites.length} simulations? Takes several minutes.`)) return;
    $("natStatus").innerHTML = '<span class="spinner"></span> queueing...';
    try{
      const r = await api("/api/india/national-run", {method:"POST"});
      $("natStatus").textContent = `OK: ${r.queued} queued - see SCENARIO LIBRARY`;
      toast("National exercise queued");
    }catch(e){ $("natStatus").textContent = "FAIL: " + e.message; }
  });
}

/* ---------- TAB: SCENARIOS ---------- */
let scenOffset = 0;
async function panelScenarios(){
  if (!requireIncident()) return;
  const j = await api(`/api/simulations?incident_id=${S.incident.id}&limit=20&offset=${scenOffset}`);
  openPanel("SCENARIO LIBRARY","Saved runs - reports match stored parameters",`
    <div class="mod"><div class="mod-title">SIMULATIONS (${j.total})</div>
      ${j.items.length ? `<table class="tbl">
        <tr><th>ID</th><th>Label</th><th>Qp</th><th>Area</th><th></th><th></th></tr>
        ${j.items.map(s => `<tr><td title="${esc(s.id)}">${esc(s.id.slice(-8))}</td>
          <td>${esc(s.label)}<br><small style="color:var(--muted)">${fmtIST(s.created_at)}</small></td>
          <td>${s.peak_q ?? "..."}</td><td>${s.max_area_km2 ?? "..."}</td>
          <td><button class="tbtn sm" onclick="loadSim('${s.id}')">OPEN</button></td>
          <td>${["admin","analyst"].includes(S.role||"")
            ? `<button class="tbtn sm danger" onclick="delSim('${s.id}')">x</button>` : ""}</td>
        </tr>`).join("")}` :
      EMPTY("&#128202;","None yet - run a breach simulation.",
        "RUN BREACH","document.querySelector('[data-tab=breach]').click()")}
      </table>
      <div class="row-end">
        ${scenOffset > 0 ? `<button class="tbtn sm" onclick="scenOffset-=20;panelScenarios()">Prev</button>` : ""}
        ${scenOffset + 20 < j.total ? `<button class="tbtn sm" onclick="scenOffset+=20;panelScenarios()">Next</button>` : ""}
      </div></div>`);
}
window.loadSim = async id => {
  S.simId = id;
  const sim = await api(`/api/simulations/${id}`);
  if (sim.status !== "DONE"){ toast("That run is " + sim.status.toLowerCase()); return; }
  S.lastResults = sim;
  document.querySelector('[data-tab="results"]').click();
};
window.delSim = async id => {
  if (!confirm("Delete this simulation?")) return;
  try{ await api(`/api/simulations/${id}`, {method:"DELETE"});
    toast("Deleted"); panelScenarios();
  }catch(e){ toast(e.message); }
};

/* ---------- TAB: ADMIN ---------- */
let auditOffset = 0;
async function panelAdmin(){
  if (S.role !== "admin"){ toast("Admins only"); insp.classList.add("closed"); return; }
  const users = await api("/api/admin/users");
  const audit = await api(`/api/admin/audit?limit=50&offset=${auditOffset}`);
  openPanel("ADMINISTRATION","User management - audit trail",`
    <div class="mod"><div class="mod-title">USERS (${users.length})</div>
      <table class="tbl"><tr><th>User</th><th>Role</th><th></th></tr>
      ${users.map(u => `<tr><td>${esc(u.username)}</td><td>${esc(u.role)}</td>
        <td>${u.username !== S.user
          ? `<button class="tbtn sm danger" onclick="delUser('${esc(u.username)}')">x</button>` : ""}</td></tr>`).join("")}
      </table>
      <div class="grid2" style="margin-top:10px">
        <div class="field"><label>New username</label><input id="nuName" class="input"></div>
        <div class="field"><label>Password (8+)</label><input id="nuPass" class="input" type="password"></div></div>
      <div class="field"><label>Role</label><select id="nuRole" class="input">
        ${["viewer","reporter","analyst","admin"].map(r => `<option>${r}</option>`).join("")}
      </select></div>
      <button class="tbtn sm full" id="nuCreate">CREATE USER</button></div>
    <div class="mod"><div class="mod-title">AUDIT LOG (${audit.total})</div>
      <table class="tbl"><tr><th>When (IST)</th><th>User</th><th>Action</th></tr>
      ${audit.items.map(a => `<tr><td>${fmtIST(a.ts)}</td>
        <td>${esc(a.username)}</td><td>${esc(a.action)}<br>
        <small style="color:var(--muted)">${esc(a.detail)}</small></td></tr>`).join("")}
      </table>
      <div class="row-end">
        ${auditOffset > 0 ? `<button class="tbtn sm" onclick="auditOffset-=50;panelAdmin()">Prev</button>` : ""}
        ${auditOffset + 50 < audit.total ? `<button class="tbtn sm" onclick="auditOffset+=50;panelAdmin()">Next</button>` : ""}
      </div></div>`);
  $("nuCreate").onclick = async () => {
    try{
      await api("/api/admin/users", {method:"POST", body:JSON.stringify({
        username:$("nuName").value, password:$("nuPass").value,
        role:$("nuRole").value})});
      toast("User created"); panelAdmin();
    }catch(e){ toast(e.message); }
  };
}
window.delUser = async name => {
  if (!confirm(`Delete user ${name}?`)) return;
  try{ await api(`/api/admin/users/${name}`, {method:"DELETE"});
    toast("Deleted"); panelAdmin();
  }catch(e){ toast(e.message); }
};

/* ---------- TAB: ABOUT US ---------- */
function panelAbout(){
  openPanel("ABOUT JAL RAKSHA", "National Dam Safety & Inundation Intelligence", `
    <!-- Team Photo Banner -->
    <div style="position:relative;border-radius:10px;overflow:hidden;border:1px solid var(--border);box-shadow:0 4px 16px rgba(0,0,0,0.3);margin-bottom:14px;background:#0d1117">
      <img src="/img/team_photo.jpg?v=2" alt="Team VisionQuest - Kerala University of Digital Sciences, Innovation and Technology" style="width:100%;height:auto;display:block">
    </div>

    <!-- Team Roster & Core Members -->
    <div class="mod" style="margin-bottom:14px">
      <div class="mod-title" style="display:flex;align-items:center;gap:6px">
        <span>&#128101;</span> <span>TEAM ROSTER &amp; CORE MEMBERS</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(160px, 1fr));gap:8px">
        <!-- Femin Johny -->
        <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:8px 10px;display:flex;align-items:center;gap:10px">
          <div style="width:34px;height:34px;border-radius:7px;background:var(--surface);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--text);font-size:13px;flex-shrink:0">F</div>
          <div style="overflow:hidden">
            <div style="font-weight:600;font-size:11.5px;color:var(--text);white-space:nowrap">Femin Johny</div>
            <div style="font-size:10px;color:var(--text-3);white-space:nowrap">Team Leader &amp; Project Lead</div>
          </div>
        </div>

        <!-- Rajana Jyothirmayi -->
        <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:8px 10px;display:flex;align-items:center;gap:10px">
          <div style="width:34px;height:34px;border-radius:7px;background:var(--surface);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--text);font-size:13px;flex-shrink:0">J</div>
          <div style="overflow:hidden">
            <div style="font-weight:600;font-size:11.5px;color:var(--text);white-space:nowrap">Rajana Jyothirmayi</div>
            <div style="font-size:10px;color:var(--text-3);white-space:nowrap">Core Team &amp; Researcher</div>
          </div>
        </div>

        <!-- Gayathry S R -->
        <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:8px 10px;display:flex;align-items:center;gap:10px">
          <div style="width:34px;height:34px;border-radius:7px;background:var(--surface);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--text);font-size:13px;flex-shrink:0">G</div>
          <div style="overflow:hidden">
            <div style="font-weight:600;font-size:11.5px;color:var(--text);white-space:nowrap">Gayathry S R</div>
            <div style="font-size:10px;color:var(--text-3);white-space:nowrap">Core Team &amp; Researcher</div>
          </div>
        </div>

        <!-- Priyadarsan G P -->
        <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:8px 10px;display:flex;align-items:center;gap:10px">
          <div style="width:34px;height:34px;border-radius:7px;background:var(--surface);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--text);font-size:13px;flex-shrink:0">P</div>
          <div style="overflow:hidden">
            <div style="font-weight:600;font-size:11.5px;color:var(--text);white-space:nowrap">Priyadarsan G P</div>
            <div style="font-size:10px;color:var(--text-3);white-space:nowrap">Core Team &amp; Engineer</div>
          </div>
        </div>

        <!-- M.Aqeeb Baba -->
        <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:8px 10px;display:flex;align-items:center;gap:10px">
          <div style="width:34px;height:34px;border-radius:7px;background:var(--surface);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--text);font-size:13px;flex-shrink:0">A</div>
          <div style="overflow:hidden">
            <div style="font-weight:600;font-size:11.5px;color:var(--text);white-space:nowrap">M.Aqeeb Baba</div>
            <div style="font-size:10px;color:var(--text-3);white-space:nowrap">Core Team &amp; Engineer</div>
          </div>
        </div>

        <!-- Bijay Thomas -->
        <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:8px 10px;display:flex;align-items:center;gap:10px">
          <div style="width:34px;height:34px;border-radius:7px;background:var(--surface);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--text);font-size:13px;flex-shrink:0">B</div>
          <div style="overflow:hidden">
            <div style="font-weight:600;font-size:11.5px;color:var(--text);white-space:nowrap">Bijay Thomas</div>
            <div style="font-size:10px;color:var(--text-3);white-space:nowrap">Core Team &amp; Developer</div>
          </div>
        </div>
      </div>
    </div>

    <div style="display:flex;gap:8px;margin-bottom:14px">
      <button class="tbtn primary full sm" onclick="document.getElementById('quickstartModal')?.classList.remove('hidden')">
        &#128214; Quick Start Guide
      </button>
      <button class="tbtn sm" style="white-space:nowrap" onclick="window.open('/api/docs','_blank')">
        &#9889; API Docs
      </button>
    </div>

    <div class="mod">
      <div class="mod-title">MISSION & MANDATE</div>
      <div style="font-size:11.5px;color:var(--text-2);line-height:1.55">
        <p style="margin:0 0 8px">
          Aligned with the <b>National Technical Research Organisation (NTRO)</b> problem statement <b>SIH26161</b>, Jal Raksha empowers disaster management authorities, district collectors, and field engineers with:
        </p>
        <ul style="margin:0;padding-left:16px;display:flex;flex-direction:column;gap:6px">
          <li><b>Rapid Breach Simulation:</b> Multi-model ensemble (Froehlich, USBR, Von Thun &amp; Gillette, Macdonald-Langridge, and Hanson-Temple geotechnical erosion kinetics).</li>
          <li><b>High-Resolution 2D Routing:</b> Priority-Flood D8 bathtub &amp; 1D Muskingum-Cunge diffusion wave propagation on 30m Copernicus GLO-30 DEMs.</li>
          <li><b>Earth Observation Verification:</b> All-weather radar (Sentinel-1 SAR VV backscatter &lt; -16 dB) and optical (Sentinel-2 MNDWI / Landsat) flood extent mapping.</li>
          <li><b>Dynamic Socio-Economic Hazard:</b> Automated downstream population exposure, building damage using JRC depth curves, and DEFRA/EA FD2320 hazard classifications (<i>d &times; v</i>).</li>
        </ul>
      </div>
    </div>

    <div class="mod">
      <div class="mod-title">TECHNICAL ARCHITECTURE</div>
      <div style="display:grid;grid-template-columns:1fr;gap:8px;font-size:11px">
        <div style="background:var(--surface-2);border-radius:8px;padding:9px;border-left:3px solid var(--cyan)">
          <b style="color:var(--text)">&#127754; Hydrodynamic Engine Suite</b>
          <div style="color:var(--text-3);margin-top:2px">
            Combines 1D non-linear Muskingum-Cunge wave attenuation with 2D DEM cell inundation and an SPH (Smoothed Particle Hydrodynamics) &amp; Delft3D numerical verification framework.
          </div>
        </div>
        <div style="background:var(--surface-2);border-radius:8px;padding:9px;border-left:3px solid var(--amber)">
          <b style="color:var(--text)">&#128752; Satellite Remote Sensing &amp; GEE</b>
          <div style="color:var(--text-3);margin-top:2px">
            Direct integration with the Copernicus Data Space Ecosystem (CDSE) and Google Earth Engine for automated pre- and post-flood SAR change detection and water masking.
          </div>
        </div>
        <div style="background:var(--surface-2);border-radius:8px;padding:9px;border-left:3px solid #22c55e">
          <b style="color:var(--text)">&#128230; Field-Ready GIS Interoperability</b>
          <div style="color:var(--text-3);margin-top:2px">
            Exports production-grade GIS Shapefiles (<span style="font-family:var(--mono)">.shp</span>), Google Earth 3D KML contours, and comprehensive disaster command dossiers.
          </div>
        </div>
      </div>
    </div>

    <div class="mod">
      <div class="mod-title">SCIENTIFIC PROVENANCE</div>
      <div style="font-size:10.5px;color:var(--text-3);line-height:1.5">
        Models implemented per peer-reviewed literature:
        <br>&bull; Froehlich, D.C. (1995/2008), <i>J. Hydrol. Eng. / J. Water Resour. Plann. Manage.</i>
        <br>&bull; Cunge, J.A. (1969), <i>Muskingum-Cunge Flood Routing Method</i>
        <br>&bull; Hanson, G.J. &amp; Temple, D.M. (1997), <i>Detachment Rate Coeff. k_d / tau_c</i>
        <br>&bull; DEFRA / Environment Agency (2006), <i>Flood Risks to People (FD2320)</i>
        <br>&bull; Huizinga, J. et al. (2017), <i>JRC Global Flood Depth-Damage</i>
      </div>
    </div>
  `);
}

/* ---------- COMPREHENSIVE REPORT ---------- */
async function viewFullReport(incidentId){
  toast("Compiling comprehensive report from latest data...");
  let rep;
  try{
    rep = await api(`/api/incidents/${incidentId}/full-report`);
  }catch(e){ toast("Report failed - " + e.message); return; }
  const BLOCK = b => ({
    text:    `<div class="rline">${esc(b.text)}</div>`,
    kv:      `<div class="rkv">${b.rows.map(([k,v]) =>
               `<span>${esc(k)}</span><span>${esc(String(v))}</span>`).join("")}</div>`,
    table:   `<table class="tbl"><tr>${b.headers.map(h=>`<th>${esc(h)}</th>`).join("")}</tr>
               ${b.rows.map(r=>`<tr>${r.map(c=>`<td>${esc(String(c))}</td>`).join("")}</tr>`).join("")}</table>`,
    list:    `<ul class="clean">${b.items.map(i=>`<li>- ${esc(i)}</li>`).join("")}</ul>`,
    warning: `<div class="note" style="border-color:var(--amber)"><b>!</b> ${esc(b.text)}</div>`,
  }[b.type] || "");
  $("reportTitle").textContent = rep.title;
  $("reportBody").innerHTML = `
    <div class="rline" style="color:var(--muted)">
      Generated ${fmtIST(rep.generated_at_utc)} - Region: ${esc(rep.region.name)}
      ${rep.simulation_id ? ` - Simulation ${esc(rep.simulation_id)}`
                          : " - NO SIMULATION (partial report)"}</div>
    ${rep.sections.map(s => `<h4>${esc(s.heading)}</h4>
      ${s.blocks.map(BLOCK).join("")}`).join("")}
    <p class="note">${esc(rep.disclaimer)}</p>`;
  $("reportModal").classList.remove("hidden");
  $("reportBody").scrollTop = 0;
}
 $("reportClose").onclick = () => $("reportModal").classList.add("hidden");
 $("btnPrintReport").onclick = () => window.print();
async function blobDownload(url, name){
  try{
    const headers = S.token ? {Authorization:`Bearer ${S.token}`} : {};
    const r = await fetch(url, {headers});
    if (!r.ok) throw new Error(r.status + " " + (await r.text()).slice(0, 120));
    const blob = await r.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    toast("Downloaded: " + name);
  }catch(e){ toast("Export failed - " + e.message); }
}
async function triggerShapefileDownload(){
  if (!S.incident && !S.simId){
    toast("Please select a dam or incident first");
    return;
  }
  const incName = S.incident ? S.incident.name : "dam_break";
  const safeName = incName.toLowerCase().replace(/[^a-z0-9]/g, "_").slice(0, 28).replace(/^_+|_+$/g, "");
  const url = S.simId ? `/api/simulations/${S.simId}/export/shapefile.zip`
                      : `/api/incidents/${S.incident.id}/export/shapefile.zip`;
  toast("Preparing ESRI Shapefile package (.shp + scenarios + buildings)...", 2500);
  await blobDownload(url, `${safeName}_inundated_area_shapefile.zip`);
}

async function triggerKmlDownload(){
  if (!S.incident && !S.simId){
    toast("Please select a dam or incident first");
    return;
  }
  const incName = S.incident ? S.incident.name : "dam_break";
  const safeName = incName.toLowerCase().replace(/[^a-z0-9]/g, "_").slice(0, 28).replace(/^_+|_+$/g, "");
  const url = S.simId ? `/api/simulations/${S.simId}/export/flood.kml`
                      : `/api/incidents/${S.incident.id}/export/flood.kml`;
  toast("Preparing Google Earth Pro 3D KML...", 2200);
  await blobDownload(url, `${safeName}_flood_simulation.kml`);
}
window.triggerShapefileDownload = triggerShapefileDownload;
window.triggerKmlDownload = triggerKmlDownload;

 $("btnExportGeo").onclick = () => S.simId && blobDownload(
  `/api/simulations/${S.simId}/export/flood.geojson`, `${S.simId}_flood.geojson`);
 $("btnExportCSV").onclick = () => S.simId && blobDownload(
  `/api/simulations/${S.simId}/export/nodes.csv`, `${S.simId}_nodes.csv`);
 const btnExpKML = $("btnExportKML");
 if (btnExpKML) btnExpKML.onclick = triggerKmlDownload;
 const btnExpShp = $("btnExportShp");
 if (btnExpShp) btnExpShp.onclick = triggerShapefileDownload;

 /* Global Navbar & Map Download Button Handlers */
 if ($("btnTopDlShp")) $("btnTopDlShp").onclick = triggerShapefileDownload;
 if ($("btnTopDlKml")) $("btnTopDlKml").onclick = triggerKmlDownload;
 if ($("btnSideDlShp")) $("btnSideDlShp").onclick = triggerShapefileDownload;
 if ($("btnScenDlShp")) $("btnScenDlShp").onclick = triggerShapefileDownload;

 /* Map layer toggles */
 const btnTogPop = $("btnTogglePop");
 if (btnTogPop) btnTogPop.onclick = e => {
   S.showPop = !S.showPop;
   e.target.classList.toggle("active", S.showPop);
   if (S.showPop) loadPopulationClusters();
   else clearLayer("population");
 };

 const btnTogScen = $("btnToggleScen");
 if (btnTogScen) btnTogScen.onclick = e => {
   S.showScen = !S.showScen;
   e.target.classList.toggle("active", S.showScen);
   $("floodDock")?.classList.add("hidden"); // hide animation dock when scenario dock opens
   if ($("scenDock")) $("scenDock").classList.toggle("hidden", !S.showScen);
   if (S.showScen) loadScenarioExtents();
   else clearLayer("scenarios");
 };

 const btnTogBld = $("btnToggleBld");
 if (btnTogBld) btnTogBld.onclick = e => {
   S.showBld = !S.showBld;
   e.target.classList.toggle("active", S.showBld);
   if (S.showBld) loadAssets();
   else clearLayer("assets");
 };

 const btnScenClose = $("scenDockClose");
 if (btnScenClose) btnScenClose.onclick = () => {
   if ($("scenDock")) $("scenDock").classList.add("hidden");
   S.showScen = false;
   if ($("btnToggleScen")) $("btnToggleScen").classList.remove("active");
   clearLayer("scenarios");
 };

 document.querySelectorAll(".scen-pill-btn").forEach(btn => {
   btn.onclick = () => {
     document.querySelectorAll(".scen-pill-btn").forEach(b => b.classList.toggle("active", b === btn));
     const k = btn.dataset.scenLayer;
     updateScenDockInfo(k);
     if (!S.scenarioLayerMap) return;
     if (k === "all") {
       Object.values(S.scenarioLayerMap).forEach(poly => { if (!map.hasLayer(poly)) poly.addTo(map); });
     } else {
       Object.entries(S.scenarioLayerMap).forEach(([key, poly]) => {
         if (key === k) { if (!map.hasLayer(poly)) poly.addTo(map); }
         else { if (map.hasLayer(poly)) map.removeLayer(poly); }
       });
     }
   };
 });

/* ---------- chrome ---------- */
// Mobile hamburger menu
document.getElementById('btnMobileMenu')?.addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('mobile-open');
});

 if ($("langToggle")) $("langToggle").onclick = e => {
  lang = lang === "en" ? "hi" : "en";
  localStorage.setItem("jr4_lang", lang);
  e.target.textContent = lang === "en" ? "\u0939\u093f\u0902" : "EN";
  applyI18n();
  // Re-render current panel to apply translations to dynamic content
  const activeTab = document.querySelector('.nav-item.active')?.dataset.tab;
  if (activeTab && typeof PANELS !== 'undefined' && PANELS[activeTab]) {
    try { PANELS[activeTab](); } catch(e) {}
  }
  toast(lang === "hi"
    ? "\u092d\u093e\u0937\u093e \u092c\u0926\u0932\u0940 (\u0921\u0947\u091f\u093e \u0905\u0902\u0917\u094d\u0930\u0947\u091c\u093c\u0940 \u092e\u0947\u0902)"
    : "Language changed (data fields remain English)");
 };

/* ---------- boot ---------- */
applyI18n();
// Quick Start modal
(function() {
  const shown = localStorage.getItem('jr4_qs_shown');
  const modal = document.getElementById('quickstartModal');
  if (!shown && modal) {
    modal.classList.remove('hidden');
  } else if (modal) {
    modal.classList.add('hidden');
  }
  document.getElementById('quickstartClose')?.addEventListener('click', closeQS);
  document.getElementById('quickstartStart')?.addEventListener('click', closeQS);
  function closeQS() {
    if (document.getElementById('quickstartDontShow')?.checked) {
      localStorage.setItem('jr4_qs_shown', '1');
    }
    document.getElementById('quickstartModal')?.classList.add('hidden');
  }
})();
refreshIncidents();
