"""fetchMapTiles.py: tile math, export requests, and resuming."""

import argparse
import json
import logging
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import fetchMapTiles as fmt  # noqa: E402

LON, LAT = -0.0014700, 51.4779300  # a valve box


def toMercator(lon, lat):
    return (math.radians(lon) * fmt.EARTH,
            math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * fmt.EARTH)


def test_point_lies_in_its_tile():
    (mx, my) = toMercator(LON, LAT)
    for z in (0, 10, 15, 20, 22):
        (x, y) = fmt.lonLat2tile(LON, LAT, z)
        (xmin, ymin, xmax, ymax) = fmt.tileBounds(z, x, y)
        assert xmin <= mx < xmax and ymin < my <= ymax


def test_known_tile():
    # z1: the northwest quadrant is tile 0/0; the whole world is tile 0 at z0
    assert fmt.lonLat2tile(-90, 45, 1) == (0, 0)
    assert fmt.lonLat2tile(LON, LAT, 0) == (0, 0)
    assert fmt.tileBounds(0, 0, 0) == pytest.approx((-fmt.HALF, -fmt.HALF, fmt.HALF, fmt.HALF))


def test_tiles_cover_the_box():
    box = fmt.padBox([(LON, LAT)], 100)
    tiles = fmt.tilesFor(box, 18)
    (w, s, e, n) = box
    for (lon, lat) in ((w, s), (w, n), (e, s), (e, n), (LON, LAT)):
        assert (18, *fmt.lonLat2tile(lon, lat, 18)) in tiles
    xs = {t[1] for t in tiles}
    ys = {t[2] for t in tiles}
    assert len(tiles) == len(xs) * len(ys)  # a full rectangle


def test_pad_box_is_margin_meters():
    (w, s, e, n) = fmt.padBox([(LON, LAT), (LON + 0.001, LAT + 0.001)], 150)
    meters = math.radians(1) * fmt.EARTH  # per degree of latitude
    assert (LAT - s) * meters == pytest.approx(150)
    assert (n - LAT - 0.001) * meters == pytest.approx(150)
    assert (LON - w) * meters * math.cos(math.radians(LAT + 0.0005)) == pytest.approx(150)


def test_export_urls():
    b = fmt.tileBounds(20, 1, 2)
    img = fmt.exportURL(fmt.PRESETS["osip2024"]["url"], b)
    assert "/OSIP_2024_WM/ImageServer/exportImage?" in img
    assert "bboxSR=3857" in img and "size=256%2C256" in img and "f=image" in img
    assert "compressionQuality=85" in img
    ms = fmt.exportURL("https://example.org/arcgis/rest/services/X/MapServer/", b)
    assert "/MapServer/export?" in ms and "compressionQuality" not in ms


def mkArgs(tmp_path, **kw):
    args = dict(bbox=[LON - 0.0005, LAT - 0.0005, LON + 0.0005, LAT + 0.0005], db="x", margin=150,
                zmin=18, zmax=19, dir=str(tmp_path), layer="test", url="https://example.org/ImageServer",
                label="Test", attribution="Example", insecure=False, force=False, dry_run=False,
                delay=0, timeout=5)
    args.update(kw)
    return argparse.Namespace(**args)


def test_run_fetches_then_resumes(tmp_path):
    calls = []

    def getter(url, context, timeout):
        calls.append(url)
        return b"\xff\xd8jpeg"

    log = logging.getLogger("test")
    args = mkArgs(tmp_path)
    assert fmt.run(args, log, getter) == 0
    n = len(calls)
    assert n == sum(len(fmt.tilesFor(args.bbox, z)) for z in (18, 19))
    meta = json.loads((tmp_path / "test" / "layer.json").read_text())
    assert meta["maxNativeZoom"] == 19 and meta["label"] == "Test"
    assert meta["bounds"] == [[args.bbox[1], args.bbox[0]], [args.bbox[3], args.bbox[2]]]
    (z, x, y) = fmt.tilesFor(args.bbox, 19)[0]
    assert (tmp_path / "test" / str(z) / str(x) / f"{y}.jpg").read_bytes() == b"\xff\xd8jpeg"
    assert not list(tmp_path.rglob("*.tmp"))

    assert fmt.run(args, log, getter) == 0  # everything is on disk: nothing fetched
    assert len(calls) == n
    assert fmt.run(mkArgs(tmp_path, force=True), log, getter) == 0
    assert len(calls) == 2 * n


def test_failed_tiles_are_counted_and_retried(tmp_path):
    def broken(url, context, timeout):
        raise ValueError("not an image")

    log = logging.getLogger("test")
    args = mkArgs(tmp_path, zmin=19, zmax=19)
    n = len(fmt.tilesFor(args.bbox, 19))
    assert fmt.run(args, log, broken) == n
    assert not list((tmp_path / "test").rglob("*.jpg"))
    assert fmt.run(args, log, lambda u, c, t: b"jpeg") == 0  # the rerun fetches them


def test_dry_run_writes_nothing(tmp_path):
    def never(url, context, timeout):
        raise AssertionError("dry run fetched")

    assert fmt.run(mkArgs(tmp_path, dry_run=True), logging.getLogger("test"), never) == 0
    assert not list(tmp_path.iterdir())


def test_non_image_reply_is_an_error(monkeypatch):
    class Reply:
        headers = {"Content-Type": "application/json"}

        def read(self):
            return b'{"error":{"code":400}}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(fmt.urllib.request, "urlopen", lambda url, context, timeout: Reply())
    with pytest.raises(ValueError, match="not an image"):
        fmt.fetch("https://example.org/x", None, 5)
