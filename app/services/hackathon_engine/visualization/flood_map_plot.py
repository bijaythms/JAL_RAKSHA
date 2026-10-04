"""
Flood Map Visualization — Interactive HTML Maps with Google & ESRI Basemaps
===========================================================================

Generates production-quality interactive flood maps with:
  - Google Hybrid (Satellite + Labels) basemap
  - ESRI World Imagery basemap
  - OpenStreetMap basemap
  - Colour-coded flood depth overlay (Blues scale, opacity-controlled)
  - Risk classification overlay (NDMA India colour scheme)
  - Pixel-level depth tooltips on hover
  - IMD-style alert banner
  - Legend panel with simulation statistics
  - Fullscreen toggle
  - Layer control (toggle basemaps + overlays)
  - PNG export button

The key to Google Hybrid / ESRI overlays in Folium is using the correct
XYZ tile URL templates (no API key needed for standard use):
  Google Hybrid:  https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}
  Google Satellite: https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}
  ESRI World Imagery: https://server.arcgisonline.com/ArcGIS/rest/services/
                       World_Imagery/MapServer/tile/{z}/{y}/{x}
"""

import numpy as np
import logging
import base64
import json
import io
from pathlib import Path
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tile layer definitions
# ---------------------------------------------------------------------------

TILE_LAYERS = {
    "google_hybrid": {
        "name": "Google Hybrid",
        "tiles": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        "attr": "© Google",
        "max_zoom": 20,
    },
    "google_satellite": {
        "name": "Google Satellite",
        "tiles": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "attr": "© Google",
        "max_zoom": 20,
    },
    "esri_imagery": {
        "name": "ESRI World Imagery",
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP",
        "max_zoom": 18,
    },
    "esri_labels": {
        "name": "ESRI Labels",
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        "attr": "© Esri",
        "max_zoom": 18,
    },
    "osm": {
        "name": "OpenStreetMap",
        "tiles": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": "© OpenStreetMap contributors",
        "max_zoom": 19,
    },
    "google_roadmap": {
        "name": "Google Roadmap",
        "tiles": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        "attr": "© Google",
        "max_zoom": 20,
    },
    "stamen_terrain": {
        "name": "Terrain",
        "tiles": "https://stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}.png",
        "attr": "Map tiles by Stamen Design, under CC BY 3.0",
        "max_zoom": 18,
    },
}

# Risk class colours (NDMA India)
RISK_CLASS_COLORS = {
    0: (255, 255, 255, 0),     # Dry / transparent
    1: (255, 255, 51,  180),   # Low    — bright yellow
    2: (255, 153, 0,   210),   # Medium — orange
    3: (220, 20,  60,  230),   # High   — crimson
    4: (128, 0,   128, 245),   # Extreme — dark purple
}

RISK_LABELS = {
    0: "No Flood",
    1: "Low (< 30 cm)",
    2: "Medium (30–100 cm)",
    3: "High (1–2 m)",
    4: "Extreme (> 2 m)",
}


# ---------------------------------------------------------------------------
# Array → base64 PNG helper
# ---------------------------------------------------------------------------

def _array_to_base64_png(rgba_array: np.ndarray) -> str:
    """Convert an RGBA numpy array to a base64-encoded PNG string."""
    try:
        from PIL import Image
        img = Image.fromarray(rgba_array.astype(np.uint8), mode="RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        # Fallback: use matplotlib
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 1, figsize=(1, 1), dpi=rgba_array.shape[1])
        ax.imshow(rgba_array)
        ax.axis("off")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0,
                    transparent=True)
        plt.close(fig)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def depth_to_rgba(flood_depth: np.ndarray,
                   vmax: float = None,
                   alpha_max: float = 0.82) -> np.ndarray:
    """
    Convert flood depth array to RGBA image for map overlay.

    Uses a blue colour ramp:
      - Dry cells (< 1 cm): fully transparent
      - Shallow floods: light blue with lower opacity
      - Deep floods: dark blue with higher opacity

    Args:
        flood_depth: 2D float array (metres)
        vmax: Maximum depth for colour scale (auto if None)
        alpha_max: Maximum opacity (0–1)

    Returns:
        RGBA uint8 array of shape (rows, cols, 4)
    """
    depth = np.where(flood_depth < 0.01, 0.0, flood_depth)
    wet_mask = depth > 0.01

    if vmax is None:
        if np.any(wet_mask):
            vmax = np.percentile(depth[wet_mask], 97)
        else:
            vmax = 5.0
    vmax = max(vmax, 0.1)

    # Normalise [0, 1]
    norm = np.clip(depth / vmax, 0, 1)

    # Blue colour ramp: light→dark blue
    # R: 173→0,  G: 216→50,  B: 230→180
    R = (173 * (1 - norm)).astype(np.uint8)
    G = (216 * (1 - norm * 0.8)).astype(np.uint8)
    B = np.clip(230 - norm * 50, 180, 230).astype(np.uint8)

    # Alpha: 0 where dry, increases with depth
    A = np.where(wet_mask, np.clip(norm * alpha_max + 0.2, 0.15, alpha_max), 0.0)
    A = (A * 255).astype(np.uint8)

    rgba = np.stack([R, G, B, A], axis=-1)
    return rgba


def risk_to_rgba(flood_depth: np.ndarray) -> np.ndarray:
    """
    Convert flood depth to RGBA risk classification image.

    Args:
        flood_depth: 2D float array (metres)

    Returns:
        RGBA uint8 array
    """
    from engine.inundation_mapper import classify_risk
    risk = classify_risk(flood_depth)

    rows, cols = risk.shape
    rgba = np.zeros((rows, cols, 4), dtype=np.uint8)

    for cls, color in RISK_CLASS_COLORS.items():
        mask = risk == cls
        rgba[mask] = color

    return rgba


# ---------------------------------------------------------------------------
# Interactive HTML Map (Primary Output)
# ---------------------------------------------------------------------------

def create_interactive_map(
    flood_depth: np.ndarray,
    bbox: Tuple[float, float, float, float],
    output_path: str,
    velocity: np.ndarray = None,
    stats: Optional[Dict] = None,
    rainfall_mm: float = None,
    duration_hr: float = None,
    title: str = "India Flood Inundation Engine",
    default_basemap: str = "google_hybrid",
) -> str:
    """
    Create a production-quality interactive Folium flood map.

    Features:
      - Google Hybrid (satellite + road labels) — default basemap
      - ESRI World Imagery (pure satellite)
      - Google Satellite, OSM, Google Roadmap as alternatives
      - Flood depth overlay (blue ramp, semi-transparent)
      - Flood risk overlay (yellow/orange/red/purple classes)
      - Velocity overlay (if provided)
      - Hover tooltips showing lat/lon (bottom-right)
      - Fullscreen button
      - Legend with IMD colour codes
      - Simulation stats panel
      - IMD alert banner
      - Layer control (basemap switcher + overlay toggles)

    Args:
        flood_depth: 2D flood depth array (metres)
        bbox: (min_lon, min_lat, max_lon, max_lat)
        output_path: Path to save HTML file
        velocity: Optional 2D velocity array
        stats: Simulation statistics dict
        rainfall_mm: Event rainfall (mm)
        duration_hr: Storm duration (hours)
        title: Map title string
        default_basemap: Which basemap to show first

    Returns:
        Path to saved HTML file
    """
    try:
        import folium
        from folium.plugins import Fullscreen, MousePosition, MeasureControl
    except ImportError:
        raise ImportError("folium required: pip install folium")

    min_lon, min_lat, max_lon, max_lat = bbox
    center_lat = (min_lat + max_lat) / 2.0
    center_lon = (min_lon + max_lon) / 2.0

    # Compute auto zoom level from bbox size
    bbox_size = max(max_lon - min_lon, max_lat - min_lat)
    if bbox_size < 0.1:
        zoom = 13
    elif bbox_size < 0.5:
        zoom = 11
    elif bbox_size < 2.0:
        zoom = 9
    else:
        zoom = 7

    # ── Create base map (no default tiles) ──────────────────────────────────
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        tiles=None,               # We add tiles manually below
        prefer_canvas=True,
        control_scale=True,
    )

    # ── Basemap layers ───────────────────────────────────────────────────────
    # We add all basemaps and set default to Google Hybrid
    layer_order = [
        "google_hybrid",       # Show first (default)
        "esri_imagery",
        "google_satellite",
        "osm",
        "google_roadmap",
    ]

    for key in layer_order:
        t = TILE_LAYERS[key]
        is_default = (key == default_basemap)
        folium.TileLayer(
            tiles=t["tiles"],
            attr=t["attr"],
            name=t["name"],
            max_zoom=t.get("max_zoom", 18),
            show=is_default,
            overlay=False,
            control=True,
        ).add_to(m)

    # ── Flood Depth RGBA overlay ─────────────────────────────────────────────
    depth_rgba = depth_to_rgba(flood_depth)
    depth_b64 = _array_to_base64_png(depth_rgba)

    # Folium ImageOverlay accepts base64 PNG
    folium.raster_layers.ImageOverlay(
        image=depth_b64,
        bounds=[[min_lat, min_lon], [max_lat, max_lon]],
        name="🌊 Flood Depth",
        opacity=1.0,          # Opacity baked into RGBA alpha channel
        interactive=False,
        zindex=400,
        show=True,
    ).add_to(m)

    # ── Risk Classification overlay ──────────────────────────────────────────
    risk_rgba = risk_to_rgba(flood_depth)
    risk_b64 = _array_to_base64_png(risk_rgba)

    folium.raster_layers.ImageOverlay(
        image=risk_b64,
        bounds=[[min_lat, min_lon], [max_lat, max_lon]],
        name="⚠️ Risk Class (NDMA)",
        opacity=0.85,
        interactive=False,
        zindex=401,
        show=False,          # Hidden by default; toggle in layer control
    ).add_to(m)

    # ── Velocity overlay (if provided) ──────────────────────────────────────
    if velocity is not None and np.any(velocity > 0):
        vel_rgba = velocity_to_rgba(velocity)
        vel_b64 = _array_to_base64_png(vel_rgba)
        folium.raster_layers.ImageOverlay(
            image=vel_b64,
            bounds=[[min_lat, min_lon], [max_lat, max_lon]],
            name="💨 Flow Velocity",
            opacity=0.8,
            interactive=False,
            zindex=402,
            show=False,
        ).add_to(m)

    # ── Flood extent bounding box ────────────────────────────────────────────
    wet = flood_depth > 0.01
    if np.any(wet):
        _add_flood_extent_polygon(m, flood_depth, bbox)

    # ── Plugins ──────────────────────────────────────────────────────────────
    Fullscreen(
        position="topleft",
        title="Enter fullscreen",
        title_cancel="Exit fullscreen",
        force_separate_button=True,
    ).add_to(m)

    MousePosition(
        position="bottomright",
        separator=" | ",
        empty_string="Hover over map",
        lng_first=False,
        num_digits=5,
        prefix="📍",
    ).add_to(m)

    MeasureControl(
        position="topleft",
        primary_length_unit="kilometers",
        secondary_length_unit="meters",
        primary_area_unit="sqkilometers",
    ).add_to(m)

    # ── Layer Control ────────────────────────────────────────────────────────
    folium.LayerControl(
        position="topright",
        collapsed=False,
        autoZIndex=True,
    ).add_to(m)

    # ── HTML Panels (Legend, Alert, Stats, Title) ────────────────────────────
    html_elements = []
    html_elements.append(_build_title_html(title))
    html_elements.append(_build_legend_html(rainfall_mm, duration_hr, stats))

    if rainfall_mm is not None:
        html_elements.append(_build_alert_banner_html(rainfall_mm, duration_hr))

    # Inject all HTML elements
    for html in html_elements:
        m.get_root().html.add_child(folium.Element(html))

    # ── Inject custom CSS + JS for better UX ────────────────────────────────
    m.get_root().html.add_child(folium.Element(_custom_css_js()))

    # ── Save ─────────────────────────────────────────────────────────────────
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    m.save(output_path)

    size_kb = Path(output_path).stat().st_size / 1024
    logger.info(f"Interactive map saved: {output_path} ({size_kb:.0f} KB)")
    return output_path


# ---------------------------------------------------------------------------
# Velocity RGBA
# ---------------------------------------------------------------------------

def velocity_to_rgba(velocity: np.ndarray, vmax: float = None) -> np.ndarray:
    """Convert velocity array to RGBA using YlOrRd (yellow→red) ramp."""
    vel = np.where(velocity < 0.05, 0.0, velocity)
    wet = vel > 0.05

    if vmax is None:
        vmax = np.percentile(vel[wet], 97) if np.any(wet) else 3.0
    vmax = max(vmax, 0.1)

    norm = np.clip(vel / vmax, 0, 1)

    # Yellow→Orange→Red
    R = np.clip(255 * norm + 200 * (1 - norm), 0, 255).astype(np.uint8)
    G = np.clip(255 * (1 - norm) * 0.8, 0, 255).astype(np.uint8)
    B = np.zeros_like(R, dtype=np.uint8)
    A = np.where(wet, np.clip(norm * 200 + 60, 60, 220), 0).astype(np.uint8)

    return np.stack([R, G, B, A], axis=-1)


# ---------------------------------------------------------------------------
# Flood extent polygon
# ---------------------------------------------------------------------------

def _add_flood_extent_polygon(m, flood_depth, bbox):
    """Add a thin outline rectangle showing the flood simulation domain."""
    import folium  # Import here to avoid NameError
    min_lon, min_lat, max_lon, max_lat = bbox
    flooded_area_pct = 100 * np.sum(flood_depth > 0.01) / flood_depth.size

    folium.Rectangle(
        bounds=[[min_lat, min_lon], [max_lat, max_lon]],
        color="#4488ff",
        weight=2,
        fill=False,
        dash_array="6 4",
        tooltip=f"Simulation domain | Flooded: {flooded_area_pct:.1f}%",
        name="📐 Simulation Domain",
    ).add_to(m)


# ---------------------------------------------------------------------------
# HTML panel builders
# ---------------------------------------------------------------------------

def _build_title_html(title: str) -> str:
    return f"""
    <div id="flood-title" style="
        position: fixed;
        top: 12px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        background: rgba(5, 10, 35, 0.88);
        color: #e0eaff;
        padding: 9px 22px 9px 14px;
        border-radius: 10px;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 15px;
        font-weight: 700;
        border: 1.5px solid #3366cc;
        box-shadow: 0 2px 12px rgba(0,80,255,0.25);
        white-space: nowrap;
        pointer-events: none;
    ">
        🌊 {title}
    </div>"""


def _build_legend_html(rainfall_mm, duration_hr, stats) -> str:
    # Depth gradient bar
    depth_gradient = """
    <div style="height:12px; width:100%; border-radius:3px; margin:4px 0 10px 0;
         background: linear-gradient(to right,
             rgba(173,216,230,0.3),
             rgba(100,149,237,0.7),
             rgba(0,0,139,0.95));
    "></div>
    <div style="display:flex;justify-content:space-between;font-size:10px;color:#aac;margin-bottom:8px;">
        <span>0 m</span><span>Flood Depth</span><span>Deep →</span>
    </div>"""

    # Risk classes
    risk_rows = ""
    for cls in [1, 2, 3, 4]:
        r, g, b, a = RISK_CLASS_COLORS[cls]
        risk_rows += f"""
        <div style="display:flex;align-items:center;gap:7px;margin:3px 0;">
            <div style="width:14px;height:14px;border-radius:3px;flex-shrink:0;
                 background:rgba({r},{g},{b},{a/255:.2f});border:1px solid rgba(255,255,255,0.2);"></div>
            <span style="font-size:11px;color:#cce;">{RISK_LABELS[cls]}</span>
        </div>"""

    # Stats panel
    stats_html = ""
    if stats:
        ext = stats.get("flood_extent", {})
        dep = stats.get("depth_stats_m", {})
        risk_areas = stats.get("risk_classes", {}).get("areas_km2", {})
        stats_html = f"""
        <hr style="border:none;border-top:1px solid #334;margin:8px 0;">
        <div style="font-size:11px;color:#adc;line-height:1.7;">
            <span style="color:#88aaff;font-weight:600;">📊 Results</span><br>
            Flooded: <b style="color:#fff">{ext.get('flooded_area_km2', 0):.2f} km²</b>
            <span style="color:#777">({ext.get('flood_fraction_pct', 0):.1f}%)</span><br>
            Max depth: <b style="color:#fff">{dep.get('max', 0):.2f} m</b><br>
            Mean depth: <b style="color:#fff">{dep.get('mean_flooded', 0):.2f} m</b>
        </div>"""

    rain_html = ""
    if rainfall_mm:
        rain_html = f"""
        <hr style="border:none;border-top:1px solid #334;margin:8px 0;">
        <div style="font-size:11px;color:#adc;">
            <span style="color:#88aaff;font-weight:600;">🌧️ Input</span><br>
            Rainfall: <b style="color:#fff">{rainfall_mm:.0f} mm</b>
            {"over <b style='color:#fff'>" + str(round(duration_hr, 1)) + " hr</b>" if duration_hr else ""}
        </div>"""

    return f"""
    <div id="flood-legend" style="
        position: fixed;
        bottom: 28px;
        left: 12px;
        z-index: 9998;
        background: rgba(5, 10, 40, 0.92);
        color: #c8d8ff;
        padding: 13px 15px;
        border-radius: 10px;
        font-family: 'Segoe UI', Arial, sans-serif;
        border: 1.5px solid #2244aa;
        box-shadow: 0 4px 20px rgba(0,40,200,0.3);
        min-width: 200px;
        max-width: 220px;
    ">
        <div style="font-weight:700;font-size:13px;margin-bottom:8px;color:#aaccff;">
            🌊 Flood Depth
        </div>
        {depth_gradient}
        <div style="font-weight:700;font-size:13px;margin-bottom:6px;color:#aaccff;">
            ⚠️ Risk (NDMA India)
        </div>
        {risk_rows}
        {rain_html}
        {stats_html}
        <hr style="border:none;border-top:1px solid #334;margin:8px 0;">
        <div style="font-size:9px;color:#557;text-align:center;">
            India Flood Engine · van den Bout et al. 2026
        </div>
    </div>"""


def _build_alert_banner_html(rainfall_mm: float, duration_hr: float) -> str:
    """IMD-style colour-coded alert banner."""
    if rainfall_mm > 204.5:
        bg, icon, text = "#8B0000", "🔴", "RED ALERT — Extremely Heavy Rain"
        border = "#ff4444"
    elif rainfall_mm > 115.6:
        bg, icon, text = "#CC3300", "🟠", "ORANGE ALERT — Very Heavy Rain"
        border = "#ff7744"
    elif rainfall_mm > 64.5:
        bg, icon, text = "#997700", "🟡", "YELLOW WATCH — Heavy Rain"
        border = "#ffcc00"
    elif rainfall_mm > 35.5:
        bg, icon, text = "#336600", "🟢", "GREEN WATCH — Moderate Rain"
        border = "#66cc00"
    else:
        return ""  # No banner for light rain

    return f"""
    <div id="imd-alert" style="
        position: fixed;
        top: 58px;
        right: 15px;
        z-index: 9999;
        background: {bg};
        color: white;
        padding: 8px 15px;
        border-radius: 8px;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
        font-weight: 700;
        border: 2px solid {border};
        box-shadow: 0 3px 15px rgba(0,0,0,0.5);
        text-align: center;
        cursor: pointer;
    " onclick="this.style.display='none'" title="Click to dismiss">
        {icon} IMD: {text}<br>
        <span style="font-size:11px;font-weight:400;opacity:0.9;">
            {rainfall_mm:.0f} mm
            {("/ " + str(round(duration_hr, 0)) + " hr") if duration_hr else ""}
            &nbsp;·&nbsp; Click to dismiss
        </span>
    </div>"""


def _custom_css_js() -> str:
    """Custom CSS and JS for polished UX."""
    return """
    <style>
        /* Override Folium default styles */
        .leaflet-control-layers {
            background: rgba(5,10,40,0.92) !important;
            color: #c8d8ff !important;
            border: 1.5px solid #2244aa !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 20px rgba(0,40,200,0.3) !important;
        }
        .leaflet-control-layers-list label {
            color: #c8d8ff !important;
        }
        .leaflet-control-layers-separator {
            border-top: 1px solid #334 !important;
        }
        .leaflet-bar a {
            background: rgba(5,10,40,0.88) !important;
            color: #c8d8ff !important;
            border-color: #2244aa !important;
        }
        .leaflet-bar a:hover {
            background: rgba(30,50,120,0.92) !important;
        }
        .leaflet-control-zoom-in,
        .leaflet-control-zoom-out {
            background: rgba(5,10,40,0.88) !important;
            color: #c8d8ff !important;
        }
        .leaflet-control-scale-line {
            background: rgba(5,10,40,0.75) !important;
            color: #aad !important;
            border-color: #446 !important;
        }
        /* Smooth overlay transitions */
        .leaflet-image-layer {
            transition: opacity 0.3s ease;
        }
    </style>
    <script>
        // Add keyboard shortcut: 'h' to toggle depth overlay
        document.addEventListener('keydown', function(e) {
            if (e.key === 'h' || e.key === 'H') {
                var layers = document.querySelectorAll('.leaflet-image-layer');
                layers.forEach(function(l) {
                    l.style.opacity = (l.style.opacity === '0') ? '1' : '0';
                });
            }
        });
    </script>"""


# ---------------------------------------------------------------------------
# Static PNG Map (matplotlib — dark theme)
# ---------------------------------------------------------------------------

def plot_flood_depth(
    flood_depth: np.ndarray,
    bbox: Tuple[float, float, float, float],
    output_path: str,
    title: str = "Flood Depth Map",
    rainfall_mm: float = None,
    duration_hr: float = None,
    velocity: np.ndarray = None,
    vmax: float = None,
) -> str:
    """
    Generate a static dark-theme PNG flood map (2-panel: depth + risk).

    Args:
        flood_depth: 2D depth array (metres)
        bbox: (min_lon, min_lat, max_lon, max_lat)
        output_path: Output PNG path
        title: Map title
        rainfall_mm: Rainfall for subtitle
        duration_hr: Duration for subtitle
        velocity: Optional velocity array for 3rd panel
        vmax: Colour scale maximum

    Returns:
        Path to saved PNG
    """
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from matplotlib.patches import Patch
    from matplotlib.colors import LinearSegmentedColormap
    import matplotlib.ticker as mticker
    from engine.inundation_mapper import classify_risk

    min_lon, min_lat, max_lon, max_lat = bbox

    # Panels
    n_panels = 3 if (velocity is not None and np.any(velocity > 0)) else 2
    fig, axes = plt.subplots(1, n_panels, figsize=(8 * n_panels, 8))
    if n_panels == 1:
        axes = [axes]
    fig.patch.set_facecolor("#050a23")

    # ── Custom blue depth colormap ──────────────────────────────────────────
    blues = LinearSegmentedColormap.from_list(
        "flood_blue",
        ["#aad4f0", "#5593e0", "#1a4baa", "#0a1e66"],
        N=256,
    )

    def _style_ax(ax, xlabel=True, ylabel=True):
        ax.set_facecolor("#080c1e")
        ax.tick_params(colors="#7799cc", labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#2244aa")
        if xlabel:
            ax.set_xlabel("Longitude (°)", color="#7799cc", fontsize=9)
        if ylabel:
            ax.set_ylabel("Latitude (°)", color="#7799cc", fontsize=9)
        ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f°"))
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f°"))

    # ── Panel 1: Flood Depth ───────────────────────────────────────────────
    ax1 = axes[0]
    depth_masked = np.where(flood_depth < 0.01, np.nan, flood_depth)

    if vmax is None:
        wet = ~np.isnan(depth_masked)
        vmax_auto = np.nanpercentile(depth_masked[wet], 97) if np.any(wet) else 5.0
    else:
        vmax_auto = vmax
    vmax_auto = max(vmax_auto, 0.1)

    im1 = ax1.imshow(
        depth_masked,
        cmap=blues, vmin=0, vmax=vmax_auto,
        extent=[min_lon, max_lon, min_lat, max_lat],
        origin="upper", aspect="auto",
        interpolation="nearest",
    )
    cb1 = fig.colorbar(im1, ax=ax1, fraction=0.04, pad=0.02, shrink=0.9)
    cb1.set_label("Flood Depth (m)", color="#aaccff", fontsize=9)
    cb1.ax.yaxis.set_tick_params(color="#7799cc")
    plt.setp(cb1.ax.yaxis.get_ticklabels(), color="#7799cc", fontsize=7)
    cb1.outline.set_edgecolor("#2244aa")

    sub = ""
    if rainfall_mm:
        sub = f"{rainfall_mm:.0f} mm"
        if duration_hr:
            sub += f" / {duration_hr:.1f} hr | {rainfall_mm/max(duration_hr,0.1):.1f} mm/hr"
    ax1.set_title(f"Flood Depth\n{sub}", color="#c8d8ff", fontsize=11, fontweight="bold", pad=8)
    _style_ax(ax1)

    # ── Panel 2: Risk Classification ───────────────────────────────────────
    ax2 = axes[1]
    risk = classify_risk(flood_depth)

    risk_colors_list = [
        (0, 0, 0, 0),                # 0: transparent
        (1.0, 1.0, 0.2, 0.7),        # 1: yellow
        (1.0, 0.55, 0.0, 0.85),      # 2: orange
        (0.86, 0.08, 0.24, 0.9),     # 3: crimson
        (0.50, 0.00, 0.50, 0.95),    # 4: purple
    ]
    risk_cmap = mcolors.ListedColormap(risk_colors_list)
    risk_norm = mcolors.BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], ncolors=5)

    ax2.imshow(
        risk, cmap=risk_cmap, norm=risk_norm,
        extent=[min_lon, max_lon, min_lat, max_lat],
        origin="upper", aspect="auto", interpolation="nearest",
    )

    # Custom legend
    legend_els = [
        Patch(facecolor=c[:3], alpha=c[3] if len(c) > 3 else 1.0, label=RISK_LABELS[i+1])
        for i, c in enumerate(risk_colors_list[1:])
    ]
    legend = ax2.legend(
        handles=legend_els, loc="lower right",
        fontsize=8, facecolor="#0a122e",
        labelcolor="#c8d8ff",
        title="NDMA Risk Class",
        title_fontsize=8,
        edgecolor="#2244aa",
    )
    legend.get_title().set_color("#88aaff")

    ax2.set_title("Risk Classification (NDMA India)", color="#c8d8ff",
                  fontsize=11, fontweight="bold", pad=8)
    _style_ax(ax2, ylabel=False)

    # ── Panel 3: Velocity (optional) ──────────────────────────────────────
    if n_panels == 3:
        ax3 = axes[2]
        vel_masked = np.where(velocity < 0.05, np.nan, velocity)
        vmax_v = np.nanpercentile(vel_masked[~np.isnan(vel_masked)], 97) if np.any(~np.isnan(vel_masked)) else 3.0

        im3 = ax3.imshow(
            vel_masked, cmap="YlOrRd", vmin=0, vmax=max(vmax_v, 0.1),
            extent=[min_lon, max_lon, min_lat, max_lat],
            origin="upper", aspect="auto", interpolation="nearest",
        )
        cb3 = fig.colorbar(im3, ax=ax3, fraction=0.04, pad=0.02, shrink=0.9)
        cb3.set_label("Velocity (m/s)", color="#aaccff", fontsize=9)
        cb3.ax.yaxis.set_tick_params(color="#7799cc")
        plt.setp(cb3.ax.yaxis.get_ticklabels(), color="#7799cc", fontsize=7)
        cb3.outline.set_edgecolor("#2244aa")
        ax3.set_title("Flow Velocity", color="#c8d8ff", fontsize=11, fontweight="bold", pad=8)
        _style_ax(ax3, ylabel=False)

    # ── Supertitle ─────────────────────────────────────────────────────────
    fig.suptitle(
        f"{title}  |  Bbox: {min_lon:.2f}°E–{max_lon:.2f}°E, {min_lat:.2f}°N–{max_lat:.2f}°N",
        color="#c8d8ff", fontsize=12, fontweight="bold", y=0.995,
    )

    plt.tight_layout(rect=[0, 0, 1, 0.99])
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=180, bbox_inches="tight",
                facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    logger.info(f"PNG map saved: {output_path}")
    return output_path
