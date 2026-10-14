#! /usr/bin/env python3
#
# Cache aerial imagery tiles for the site map, map.php
#
# Fetches standard web map tiles (EPSG:3857, z/x/y, 256 pixels) covering the
# site's map features from an ArcGIS ImageServer or MapServer, one export
# request per tile, so the server's own tiling scheme does not matter.  Tiles
# go to DIR/LAYER/z/x/y.jpg, with DIR/LAYER/layer.json describing the layer for
# mapData.php.  A tile already on disk is kept, so an interrupted or repeated
# run only fetches what is missing; --force refetches everything.
#
# The tiles are served from the Pi, so the map works without the imagery
# server: e.g. Oregon's, whose TLS certificate expired 2026-09-26 (--insecure).
#
# Oct-2026, Pat Welch, pat@mousebrains.com

import argparse
import datetime
import json
import logging
import math
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request

import MyLogger

TILE = 256  # pixels
HALF = 20037508.342789244  # Web Mercator half-width, meters
EARTH = 6378137.0  # Web Mercator sphere radius, meters

OSIP = "https://imagery.oregonexplorer.info/arcgis/rest/services/OSIP_{0}/OSIP_{0}_WM/ImageServer"
PRESETS = {
    "osip2024": {"url": OSIP.format(2024), "label": "Oregon OSIP 2024 (1 ft)",
                 "attribution": "Oregon Statewide Imagery Program (OSIP) 2024"},
    "osip2022": {"url": OSIP.format(2022), "label": "Oregon OSIP 2022 (1 ft)",
                 "attribution": "Oregon Statewide Imagery Program (OSIP) 2022"},
}


def lonLat2tile(lon: float, lat: float, z: int) -> tuple[int, int]:
    """ The z/x/y tile containing lon/lat """
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return (min(max(x, 0), n - 1), min(max(y, 0), n - 1))


def tileBounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """ (xmin, ymin, xmax, ymax) of tile z/x/y in EPSG:3857 meters """
    size = 2 * HALF / 2 ** z
    xmin = -HALF + x * size
    ymax = HALF - y * size
    return (xmin, ymax - size, xmin + size, ymax)


def tilesFor(bbox: tuple[float, float, float, float], z: int) -> list[tuple[int, int, int]]:
    """ Every z/x/y tile touching bbox = (west, south, east, north) degrees """
    (w, s, e, n) = bbox
    (x0, y0) = lonLat2tile(w, n, z)
    (x1, y1) = lonLat2tile(e, s, z)
    return [(z, x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def padBox(points: list[tuple[float, float]], margin: float) -> tuple[float, float, float, float]:
    """ (west, south, east, north) around lon/lat points, padded by margin meters """
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    lat = math.radians((min(lats) + max(lats)) / 2)
    dLat = math.degrees(margin / EARTH)
    dLon = dLat / max(math.cos(lat), 1e-6)
    return (min(lons) - dLon, min(lats) - dLat, max(lons) + dLon, max(lats) + dLat)


def exportURL(url: str, bounds: tuple[float, float, float, float]) -> str:
    """ The export request for one tile from an ArcGIS ImageServer or MapServer """
    base = url.rstrip("/")
    op = "exportImage" if base.endswith("ImageServer") else "export"
    query = {"bbox": ",".join(f"{v:.6f}" for v in bounds), "bboxSR": 3857, "imageSR": 3857,
             "size": f"{TILE},{TILE}", "format": "jpg", "f": "image"}
    if op == "exportImage":
        query["compressionQuality"] = 85
    return f"{base}/{op}?{urllib.parse.urlencode(query)}"


def siteBox(db: str, margin: float, logger: logging.Logger) -> tuple[float, float, float, float]:
    """ The map features, or failing that the site, padded by margin meters """
    import psycopg  # only needed when --bbox is not given
    with psycopg.connect(dbname=db) as conn:
        points = conn.execute("SELECT longitude, latitude FROM mapFeature;").fetchall()
        if not points:
            logger.info("No map features yet; using the site's location")
            points = conn.execute("SELECT longitude, latitude FROM site"
                                  " WHERE latitude IS NOT NULL AND longitude IS NOT NULL;").fetchall()
    if not points:
        raise SystemExit("No map features or site location in the database; give --bbox")
    return padBox(points, margin)


def fetch(url: str, context: ssl.SSLContext | None, timeout: float) -> bytes:
    """ One image; raises if the server sent anything else, e.g. an ArcGIS JSON error """
    with urllib.request.urlopen(url, context=context, timeout=timeout) as reply:
        body: bytes = reply.read()
        ctype = reply.headers.get("Content-Type", "")
    if not ctype.startswith("image/"):
        raise ValueError(f"not an image ({ctype}): {body[:200]!r}")
    return body


def save(path: str, body: bytes) -> None:
    """ Write atomically, so an interrupted run never leaves a partial tile """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as fp:
        fp.write(body)
    os.replace(tmp, path)


def run(args: argparse.Namespace, logger: logging.Logger, getter=fetch) -> int:
    """ Fetch the missing tiles; returns how many failed """
    bbox = tuple(args.bbox) if args.bbox else siteBox(args.db, args.margin, logger)
    tiles = [t for z in range(args.zmin, args.zmax + 1) for t in tilesFor(bbox, z)]
    layerDir = os.path.join(args.dir, args.layer)
    logger.info("%s: %d tiles, zoom %d-%d, bbox %s, from %s",
                args.layer, len(tiles), args.zmin, args.zmax,
                ",".join(f"{v:.6f}" for v in bbox), args.url)
    if args.dry_run:
        return 0
    # Only on request, for public imagery behind an expired certificate
    context = ssl._create_unverified_context() if args.insecure else None  # nosec B323
    (got, kept, failed) = (0, 0, 0)
    for (z, x, y) in tiles:
        path = os.path.join(layerDir, str(z), str(x), f"{y}.jpg")
        if not args.force and os.path.exists(path):
            kept += 1
            continue
        try:
            save(path, getter(exportURL(args.url, tileBounds(z, x, y)), context, args.timeout))
            got += 1
        except Exception as e:
            failed += 1
            logger.warning("Tile %d/%d/%d failed: %s", z, x, y, e)
        if args.delay > 0:
            time.sleep(args.delay)  # be gentle with a public server
    meta = {"id": args.layer, "label": args.label, "attribution": args.attribution,
            "bounds": [[bbox[1], bbox[0]], [bbox[3], bbox[2]]],  # Leaflet [[south, west], [north, east]]
            "minZoom": args.zmin, "maxNativeZoom": args.zmax, "source": args.url,
            "fetched": datetime.date.today().isoformat()}
    save(os.path.join(layerDir, "layer.json"), json.dumps(meta, indent=1).encode())
    logger.info("%s: fetched %d, kept %d, failed %d", args.layer, got, kept, failed)
    return failed


def main() -> None:
    parser = argparse.ArgumentParser(description="Cache aerial imagery tiles for map.php")
    parser.add_argument("--db", type=str, default="irrigation",
                        help="Database whose map features (or site) set the area")
    parser.add_argument("--dir", type=str, default=os.path.expanduser("~/tiles"),
                        help="Tile directory, ./config --tileDir")
    parser.add_argument("--preset", choices=sorted(PRESETS), help="Known imagery source")
    parser.add_argument("--layer", type=str, help="Layer id, a directory name; default the preset")
    parser.add_argument("--url", type=str, help="ArcGIS ImageServer or MapServer URL")
    parser.add_argument("--label", type=str, help="Name shown in the map's layer control")
    parser.add_argument("--attribution", type=str, help="Credit shown on the map")
    parser.add_argument("--bbox", type=float, nargs=4, metavar=("W", "S", "E", "N"),
                        help="Area in degrees, instead of the map features")
    parser.add_argument("--margin", type=float, default=150,
                        help="Meters around the map features")
    parser.add_argument("--zmin", type=int, default=15, help="Coarsest zoom")
    parser.add_argument("--zmax", type=int, default=20,
                        help="Finest zoom; 20 is about 0.1 m at 45 degrees, finer than 1-ft imagery")
    parser.add_argument("--delay", type=float, default=0.1, help="Seconds between requests")
    parser.add_argument("--timeout", type=float, default=60, help="Seconds per request")
    parser.add_argument("--insecure", action="store_true",
                        help="Do not verify the server's TLS certificate (public imagery only)")
    parser.add_argument("--force", action="store_true", help="Refetch tiles already on disk")
    parser.add_argument("--dry-run", action="store_true", help="Only report what would be fetched")
    MyLogger.addArgs(parser)
    args = parser.parse_args()

    preset = PRESETS.get(args.preset or "", {})
    args.layer = args.layer or args.preset
    args.url = args.url or preset.get("url")
    args.label = args.label or preset.get("label") or args.layer
    args.attribution = args.attribution or preset.get("attribution") or ""
    if not args.layer or not args.url:
        parser.error("give --preset, or --layer and --url")
    if not args.layer.replace("_", "").replace("-", "").isalnum():
        parser.error("--layer must be letters, digits, - and _")
    if not 0 <= args.zmin <= args.zmax <= 22:
        parser.error("need 0 <= --zmin <= --zmax <= 22")

    logger = MyLogger.mkLogger(args, __name__, fmt="%(asctime)s: %(levelname)s: %(message)s")
    sys.exit(1 if run(args, logger) else 0)


if __name__ == "__main__":
    main()
