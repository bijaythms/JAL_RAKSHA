"""Dam-breach simulation.

EMPIRICAL PEAK-DISCHARGE ENSEMBLE (compiled after Wahl 1998/2004):
  Kirkpatrick (1977): Qp = 1.268 (Hw+0.3)^2.5
  SCS (1981):         Qp = 16.6  Hw^1.85
  USBR (1981):        Qp = 19.1  Hw^1.85
  Froehlich (1995):   Qp = 0.607 Vw^0.295 Hw^1.24
Breach geometry/timing:
  Froehlich (1995):  B = 0.1803 k_o Vw^0.32 Hb^0.04  (k_o 1.4 overtop / 1.0 piping)
  Froehlich (2008):  t_f = 63.2 sqrt(Vw/(g Hb^2))  [s]
  Von Thun & Gillette (1990): t_f[hr] = 0.015 Hb (erodible) / 0.02 Hb + 0.25

PHYSICAL ENGINE (erodible dams):
  level-pool mass balance + broad-crested weir (Q = 1.7 b H^1.5)
  + excess-shear erosion (Hanson & Temple 1997):
      dz/dt = k_d (tau - tau_c),  tau = gamma_w y S_f,  y ~ (2/3) H
  + widening tied to incision via side-slope angle: dW/dt = 2 dz/dt / tan(phi)

NON-ERODIBLE (Concrete/Masonry): different failure paradigm — fixed breach
section, no widening/incision, debris-sluicing opening. Engine label
'v4.1-overtop'.

Muskingum-CUNGE routing coefficients (Cunge 1969):
  K = dx/c,  X = 0.5 (1 - q0/(S0 c B dx))  clamped to [0, 0.5].
"""
import math
import numpy as np
from . import erosion_params

G = 9.81
GAMMA_W = 9810.0

NON_ERODIBLE = {"Concrete", "Masonry"}


def empirical_peak_discharge(Vw, Hw, mode="overtopping"):
    eqs = {
        "Kirkpatrick (1977)": 1.268 * (Hw + 0.3) ** 2.5,
        "SCS (1981)":         16.6 * Hw ** 1.85,
        "USBR (1981)":        19.1 * Hw ** 1.85,
        "Froehlich (1995)":   0.607 * Vw ** 0.295 * Hw ** 1.24,
    }
    vals = list(eqs.values())
    return {
        "equations": {k: round(v, 1) for k, v in eqs.items()},
        "ensemble_median": round(float(np.median(vals)), 1),
        "ensemble_min": round(min(vals), 1),
        "ensemble_max": round(max(vals), 1),
        "spread_ratio": round(max(vals) / max(min(vals), 1.0), 2),
        "caveat": "All four equations were calibrated on EMBANKMENT dams. "
                  "Landslide and glacial dams were excluded from their "
                  "training data - the ensemble is a bracketing guide, not "
                  "a prediction, for natural dams.",
    }


def empirical_breach_geometry(Vw, Hb, mode="overtopping"):
    k_o = 1.4 if mode == "overtopping" else 1.0
    b_avg = 0.1803 * k_o * Vw ** 0.32 * Hb ** 0.04
    t_f = 63.2 * math.sqrt(Vw / (G * Hb ** 2)) / 3600.0
    return {
        "froehlich1995_avg_breach_width_m": round(b_avg, 1),
        "froehlich2008_formation_time_hr": round(t_f, 2),
        "vonthun1990_time_hr_highly_erodible": round(0.015 * Hb, 2),
        "vonthun1990_time_hr_erosion_resistant": round(0.02 * Hb + 0.25, 2),
        "caveat": "Suggested defaults from literature; the actual run uses "
                  "the user's values verbatim.",
    }


def weir_Q(b_m, head_m):
    if b_m <= 0 or head_m <= 0:
        return 0.0
    return 1.7 * b_m * head_m ** 1.5


# Detachability / critical shear: Hanson & Temple (1997) class guidance.
# ORDER-OF-MAGNITUDE literature values [VERIFY per site].
KD_BY_MATERIAL = {
    "Earth": 2.0e-6, "Landslide debris": 5.0e-6, "Sediment": 4.0e-6,
    "Ice/debris": 3.0e-6, "Mixed": 3.0e-6, "Unknown": 3.0e-6,
    "Rock": 2.0e-7,
}
TAU_C_BY_MATERIAL = {
    "Earth": 5.0, "Landslide debris": 2.0, "Sediment": 1.5,
    "Ice/debris": 2.0, "Mixed": 3.0, "Unknown": 3.0, "Rock": 100.0,
}


def _reservoir(V0, A0, hypsometry, notes):
    """Depth-below-surface tables (ds ascending, areas, drained)."""
    if hypsometry:
        curve = sorted(hypsometry, key=lambda r: r["elev_m"])
        e = np.array([float(r["elev_m"]) for r in curve])
        a = np.clip(np.array([float(r.get("area_m2", 0)) for r in curve]), 0, None)
        v = np.maximum.accumulate(np.clip(
            np.array([float(r.get("cum_volume_m3", 0)) for r in curve]), 0, None))
        e_max, Vfull = float(e[-1]), float(v[-1])
        Dfull = max(e_max - float(e[0]), 1.0)
        if Vfull <= 0:
            return _reservoir(V0, A0, None, notes)
        k = V0 / Vfull
        if abs(k - 1.0) > 0.05:
            notes.append(f"DEM volume {Vfull:,.0f} m3 differs from input; "
                         f"curve scaled by {k:.2f} to honour the input volume.")
        ds = np.linspace(0.0, Dfull, 200)
        areas = np.clip(np.interp(e_max - ds, e, a), 0.0, None)
        drained = k * (Vfull - np.interp(e_max - ds, e, v))
        drained = np.maximum.accumulate(np.clip(drained, 0.0, V0))
        notes.append(f"Bathymetry from DEM hypsometry ({len(curve)} levels).")
    else:
        pw = 1.5
        Dp = max(V0 * (pw + 1) / max(A0, 1.0), 1.0)
        ds = np.linspace(0.0, Dp, 200)
        areas = A0 * np.clip(1.0 - ds / Dp, 0.0, 1.0) ** pw
        drained = np.zeros_like(ds)
        for i in range(1, len(ds)):
            drained[i] = drained[i-1] + 0.5*(areas[i-1]+areas[i])*(ds[i]-ds[i-1])
        drained = np.minimum(drained, V0)
        notes.append("Parametric bathymetry A(h)=A0(1-d/D)^1.5 (upload a CSV "
                     "DEM or use satellite-derived lake area for measured "
                     "hypsometry).")
    return ds, areas, drained


def simulate_breach(p, dt=5.0, hypsometry=None, cancel=None, progress=None):
    """Dispatch: non-erodible -> overtopping paradigm; else erosion model."""
    mat = p.get("dam_material", "Unknown")
    if mat in NON_ERODIBLE:
        return _simulate_overtopping_only(p, dt, hypsometry, cancel, progress)
    return _simulate_erosion(p, dt, hypsometry, cancel, progress)


def _simulate_erosion(p, dt, hypsometry, cancel, progress):
    V0 = p["stored_volume_m3"]
    A0 = max(p["lake_area_m2"], 1000.0)
    Hdam = p["dam_height_m"]
    Bdam = p["dam_crest_len_m"]
    mat = p.get("dam_material", "Unknown")
    _ep = erosion_params.get_params(p.get("incident_id"), mat)
    k_d = _ep["k_d"]; tau_c = _ep["tau_c"]
    phi = 45.0
    S_f = 0.08
    W_max = 3.0 * Bdam
    d_max = min(p["breach_depth_m"], Hdam)

    _lit_flag = " [LITERATURE — VERIFY per site]" if _ep["flagged_literature"] else ""
    notes = [f"Erosion: Hanson & Temple (1997) excess-shear detachment, "
             f"k_d={k_d:.1e} m3/(N.s), tau_c={tau_c} Pa for '{mat}'. "
             f"Source: {_ep['source']}{_lit_flag}"]
    ds, areas, drained = _reservoir(V0, A0, hypsometry, notes)
    A_surf = max(float(areas[0]), 100.0)

    def stage_of_volume(V):
        if V >= V0:
            return (V - V0) / A_surf
        return -float(np.interp(V0 - V, drained, ds))

    V, s = V0, 0.0
    W = max(p["breach_width_m"] * 0.10, 1.0)
    depth_ero = 0.0
    t = 0.0
    t_end = max(p["breach_time_hr"] * 4, 3 * 3600.0, 6 * 3600.0)
    ts, qs = [0.0], [0.0]
    Qp, tp, Vout = 0.0, 0.0, 0.0
    Qin = p["inflow_m3s"]

    while t <= t_end:
        if cancel and cancel():
            from ..jobs import JobCancelled
            raise JobCancelled()
        invert = -depth_ero
        Q = weir_Q(W, s - invert)
        if s > 0:
            Q += weir_Q(max(Bdam - W, 0.0), s)
        H_local = s - invert
        if H_local > 0 and depth_ero < d_max:
            y = (2.0 / 3.0) * H_local
            tau = GAMMA_W * y * S_f
            if tau > tau_c:
                dz = k_d * (tau - tau_c) * dt
                depth_ero = min(depth_ero + dz, d_max)
                W = min(W + 2.0 * dz / math.tan(math.radians(phi)), W_max)
        Vout += Q * dt
        V = max(V + (Qin - Q) * dt, 0.0)
        s = stage_of_volume(V)
        t += dt
        ts.append(t / 60.0); qs.append(Q)
        if Q > Qp:
            Qp, tp = Q, t
        if depth_ero >= d_max * 0.999 and Q < max(Qin, 1.0) * 1.05:
            break
        if progress and int(t) % 600 == 0:
            progress(min(t / t_end, 0.95))

    closure = abs(V - (V0 + Qin * t - Vout)) / max(V0, 1.0) * 100.0

    if len(ts) > 400:
        idx = np.unique(np.linspace(0, len(ts) - 1, 400).astype(int))
        ts = [ts[i] for i in idx]; qs = [round(qs[i], 2) for i in idx]

    return {
        "time_min": [round(x, 2) for x in ts],
        "Q_m3s": qs,
        "drained_volume_m3": round(V0 - V, 0),
        "peak_Q_m3s": round(Qp, 1),
        "time_to_peak_min": round(tp / 60.0, 1),
        "final_breach_width_m": round(W, 1),
        "final_incision_m": round(depth_ero, 2),
        "mass_balance_closure_err_pct": round(closure, 3),
        "reservoir_notes": notes,
        "engine": "v4.1-erosion",
        "method": ("Level-pool routing + broad-crested weir + Hanson & Temple "
                   "(1997) excess-shear erosion; widening via side-slope "
                   "kinematics"),
        "limitations": [
            "k_d and tau_c are literature order-of-magnitude values for the "
            "material class - real detachability needs lab testing.",
            "Empirical ensembles were trained on embankment dams; "
            "natural-dam transferability is unverified.",
            "Clear-water model: no sediment bulking or debris-flow "
            "transformation.",
            "Single-section breach: no 2D flow field, no headcut migration."],
    }


def _simulate_overtopping_only(p, dt, hypsometry, cancel, progress):
    """Concrete/masonry: fixed breach section, no erosion. Peak Q dominated
    by sudden head. Monolith stability NOT modeled - upper-bound envelope."""
    V0 = p["stored_volume_m3"]
    A0 = max(p["lake_area_m2"], 1000.0)
    Hdam = p["dam_height_m"]
    Bdam = p["dam_crest_len_m"]
    bf_w = p["breach_width_m"]
    bf_d = min(p["breach_depth_m"], Hdam)
    tf = max(p["breach_time_hr"] * 3600, 60.0)
    Qin = p["inflow_m3s"]

    notes = ["Non-erodible (concrete/masonry) paradigm: fixed breach section, "
             "no lateral widening, no incision. Real failures depend on "
             "monolith stability analysis (not modeled) - treat Qp as an "
             "upper-bound envelope for a sudden partial-section failure."]
    ds, areas, drained = _reservoir(V0, A0, hypsometry, notes)
    A_surf = max(float(areas[0]), 100.0)

    def stage_of_volume(V):
        if V >= V0:
            return (V - V0) / A_surf
        return -float(np.interp(V0 - V, drained, ds))

    V, s, t = V0, 0.0, 0.0
    t_end = max(tf * 4, 3 * 3600.0)
    ts, qs = [0.0], [0.0]
    Qp, tp, Vout = 0.0, 0.0, 0.0
    while t <= t_end:
        if cancel and cancel():
            from ..jobs import JobCancelled
            raise JobCancelled()
        frac = min(t / tf, 1.0)
        w = bf_w * frac
        invert = -bf_d
        Q = weir_Q(w, s - invert)
        if s > 0:
            Q += weir_Q(max(Bdam - w, 0.0), s)
        Vout += Q * dt
        V = max(V + (Qin - Q) * dt, 0.0)
        s = stage_of_volume(V)
        t += dt
        ts.append(t / 60.0); qs.append(Q)
        if Q > Qp:
            Qp, tp = Q, t
        if frac >= 1.0 and Q < max(Qin, 1.0) * 1.05:
            break
        if progress and int(t) % 600 == 0:
            progress(min(t / t_end, 0.95))

    closure = abs(V - (V0 + Qin * t - Vout)) / max(V0, 1.0) * 100.0
    if len(ts) > 400:
        idx = np.unique(np.linspace(0, len(ts) - 1, 400).astype(int))
        ts = [ts[i] for i in idx]; qs = [round(qs[i], 2) for i in idx]

    return {
        "time_min": [round(x, 2) for x in ts],
        "Q_m3s": qs,
        "drained_volume_m3": round(V0 - V, 0),
        "peak_Q_m3s": round(Qp, 1),
        "time_to_peak_min": round(tp / 60.0, 1),
        "final_breach_width_m": round(bf_w, 1),
        "final_incision_m": 0.0,
        "mass_balance_closure_err_pct": round(closure, 3),
        "reservoir_notes": notes,
        "engine": "v4.1-overtop",
        "method": ("Level-pool routing + weir through a fixed non-erodible "
                   "breach section (debris-sluicing opening over t_f)"),
        "limitations": [
            "Monolith stability, foundation scour and puncture mechanisms "
            "not modeled; consult the dam's own PMF/EAP studies for "
            "engineered concrete structures.",
            "This paradigm produces a FASTER, higher peak than an eroding "
            "earth dam of equal size - intentional and flagged.",
            "Clear-water model: no debris from the failed monoliths."],
    }


# ------------------------------------------------- Muskingum-Cunge -----------
def _normal_depth(Q, B, n, S):
    return (Q * n / (max(B, 5.0) * math.sqrt(max(S, 1e-4)))) ** 0.6


def muskingum_cunge(qin, dt, dx, c, S0, B, q0=None):
    """Cunge (1969): K = dx/c, X = 0.5(1 - q0/(S0 c B dx)), clamped [0, 0.5].
    Returns (routed, clamped_flag, X)."""
    K = dx / c
    if q0 is None:
        q0 = float(np.mean(qin)) or 1.0
    X = 0.5 * (1.0 - q0 / (S0 * c * max(B, 1.0) * dx))
    X = max(0.0, min(0.5, X))
    clamped = (K < dt * X * 1.05) or (K > dt * (1 - X) * 2 / 1.05)
    if K < dt * X * 1.05:
        K = dt * X * 1.05
    if K > dt * (1 - X) * 2 / 1.05:
        K = dt * (1 - X) * 2 / 1.05
    den = 2 * K * (1 - X) + dt
    C0 = (dt - 2 * K * X) / den
    C1 = (dt + 2 * K * X) / den
    C2 = (2 * K * (1 - X) - dt) / den
    out = np.empty_like(qin); out[0] = qin[0]
    for i in range(1, len(qin)):
        out[i] = max(0.0, C0 * qin[i] + C1 * qin[i-1] + C2 * out[i-1])
    return out, clamped, round(X, 3)
