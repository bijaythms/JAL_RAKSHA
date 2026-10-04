"""Copernicus CDSE + USGS Landsat STAC scene search.
CDSE token cached WITH EXPIRY (fix: tokens live ~10 min)."""
import asyncio, io, json, math, time
import httpx
import numpy as np
from ..config import cfg

CDSE_TOKEN_URL = ("https://identity.dataspace.copernicus.eu/auth/realkeys/"
                  "CDSE/protocol/openid-connect/token")
CDSE_TOKEN_URL = ("https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
                  "/protocol/openid-connect/token")
CDSE_STAC = "https://catalogue.dataspace.copernicus.eu/stac/search"
USGS_STAC = "https://landsatlook.usgs.gov/stac-server/search"

BANDS = {
    "copernicus_s2": {"green": "B03", "nir": "B08", "swir": "B11", "res_m": 10.0},
    "usgs_landsat":  {"green": "green", "nir": "nir08", "swir": "swir16", "res_m": 30.0},
}

_token_cache = {"token": None, "exp": 0.0}

async def _cdse_token():
    if _token_cache["token"] and time.time() < _token_cache["exp"] - 60:
        return _token_cache["token"]
    u, p = cfg.CDSE_USERNAME, cfg.CDSE_PASSWORD
    if not u or not p:
        return None
    async with httpx.AsyncClient(timeout=30) as cl:
        r = await cl.post(CDSE_TOKEN_URL, data={
            "grant_type": "password", "username": u, "password": p,
            "client_id": "cdse-public"})
        r.raise_for_status()
        j = r.json()
        _token_cache["token"] = j["access_token"]
        _token_cache["exp"] = time.time() + int(j.get("expires_in", 600))
        return _token_cache["token"]

def _bbox(lat, lon, pad_deg=0.15):
    return [lon - pad_deg, lat - pad_deg, lon + pad_deg, lat + pad_deg]

async def _stac_search(url, body, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=45) as cl:
        try:
            r = await cl.post(url, json=body, headers=headers)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            # Return empty features on bad request / no matches rather than crashing
            return {"features": [], "error": str(e)}
        except Exception as e:
            return {"features": [], "error": str(e)}

def _asset_href(asset):
    """CDSE STAC hrefs can be str or {href: str} - handle both."""
    if asset is None:
        return None
    h = asset.get("href") if isinstance(asset, dict) else asset
    if isinstance(h, dict):
        h = h.get("href")
    return h

async def search_scenes(lat, lon, start, end, source="usgs_landsat",
                        cloud_max=30, limit=10):
    bbox = _bbox(lat, lon)
    # Ensure RFC3339 datetime format required by USGS and Copernicus STAC servers
    dt_start = str(start) if "T" in str(start) else f"{start}T00:00:00Z"
    dt_end = str(end) if "T" in str(end) else f"{end}T23:59:59Z"

    if source == "usgs_landsat":
        body = {"collections": ["landsat-c2l2-sr"], "bbox": bbox,
                "datetime": f"{dt_start}/{dt_end}", "limit": limit,
                "query": {"eo:cloud_cover": {"lte": cloud_max}}}
        data = await _stac_search(USGS_STAC, body)
        items = []
        for it in data.get("features", []):
            assets = it.get("assets", {})
            items.append({
                "scene_id": it["id"],
                "datetime": it["properties"].get("datetime"),
                "cloud_pct": it["properties"].get("eo:cloud_cover"),
                "platform": it["properties"].get("platform"),
                "assets": {b: _asset_href(assets.get(BANDS[source][b]))
                           for b in ("green", "nir", "swir")},
                "thumbnail": _asset_href(assets.get("thumbnail")),
                "source": "USGS Landsat C2 L2 SR"})
    else:
        token = await _cdse_token()
        if not token:
            return {"ok": False, "error":
                    "Copernicus not configured - set CDSE_USERNAME / "
                    "CDSE_PASSWORD (free account at dataspace.copernicus.eu)"}
        body = {"collections": ["SENTINEL-2-L2A"], "bbox": bbox,
                "datetime": f"{dt_start}/{dt_end}", "limit": limit,
                "query": {"eo:cloud_cover": {"lte": cloud_max}}}
        data = await _stac_search(CDSE_STAC, body, token)
        items = []
        for it in data.get("features", []):
            assets = it.get("assets", {})
            items.append({
                "scene_id": it["id"],
                "datetime": it["properties"].get("datetime"),
                "cloud_pct": it["properties"].get("eo:cloud_cover"),
                "platform": "Sentinel-2",
                "assets": {b: _asset_href(assets.get(BANDS[source][b]))
                           for b in ("green", "nir", "swir")},
                "thumbnail": None, "source": "Copernicus S2 L2A"})
    return {"ok": True, "items": items}


def decode(raw):
    try:
        import rasterio
        with rasterio.open(io.BytesIO(raw)) as src:
            return src.read(1)
    except Exception:
        return None


def decode_with_transform(raw):
    """-> (array, transform) - needed for zone cropping."""
    import rasterio, io as _io
    with rasterio.open(_io.BytesIO(raw)) as src:
        return src.read(1), src.transform


async def fetch_band_bytes(url, headers=None, timeout=180):
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as cl:
        r = await cl.get(url, headers=headers or {})
        r.raise_for_status()
        return r.content
