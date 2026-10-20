#!/usr/bin/env python3
"""Fetch and verify a published AUREON third-party XAUUSD tick archive.

This dataset is sourced from Dukascopy, not the PXBTTrading-1 broker feed.
Only extracts Parquet members from verified monthly ZIPs; never executes files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

API = "https://api.github.com/repos/jerryllee421-lab/aureon-omega/releases"
PREFIX = "xauusd-dukascopy-ticks-"


def get_json(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "AUREON-tick-archive-fetcher/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)


def download(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "AUREON-tick-archive-fetcher/1.0", "Accept": "application/octet-stream"})
    h = hashlib.sha256()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
                out.write(chunk)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/dukascopy_xauusd_ticks", help="Destination directory")
    ap.add_argument("--tag", help="Exact release tag; defaults to latest matching release")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    releases = get_json(API + "?per_page=100")
    release = next((r for r in releases if r.get("tag_name", "").startswith(PREFIX) and not r.get("draft") and not r.get("prerelease")), None) if not args.tag else next((r for r in releases if r.get("tag_name") == args.tag), None)
    if not release or not release.get("tag_name", "").startswith(PREFIX):
        raise SystemExit("No matching published Dukascopy XAUUSD tick archive release found.")
    assets = {a["name"]: a for a in release.get("assets", [])}
    if "manifest.json" not in assets:
        raise SystemExit("Release has no manifest.json; refusing unverified download.")
    manifest_path = out / "manifest.json"
    download(assets["manifest.json"]["browser_download_url"], manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_id") != "AUREON_XAUUSD_DUKASCOPY_HISTORICAL_TICKS" or manifest.get("symbol") != "XAUUSD":
        raise SystemExit("Manifest dataset or symbol mismatch.")
    if "NOT PXBTTrading-1 broker ticks" not in manifest.get("source_type", ""):
        raise SystemExit("Manifest provenance is missing the third-party feed disclaimer.")
    if int(manifest.get("requested_calendar_span_days", 0)) < 730:
        raise SystemExit("Manifest calendar span is under 730 days.")
    archives = manifest.get("archives")
    if not isinstance(archives, list) or not archives:
        raise SystemExit("Manifest has no archives.")
    downloaded = []
    for item in archives:
        name = item.get("file", "")
        if not re.fullmatch(r"xauusd-ticks-\d{4}-\d{2}\.zip", name):
            raise SystemExit(f"Unexpected archive name: {name!r}")
        if name not in assets:
            raise SystemExit(f"Archive listed in manifest is missing from release assets: {name}")
        archive = out / "archives" / name
        actual = download(assets[name]["browser_download_url"], archive)
        if actual.lower() != str(item.get("sha256", "")).lower():
            raise SystemExit(f"SHA-256 mismatch for {name}")
        with zipfile.ZipFile(archive) as zf:
            bad = zf.testzip()
            if bad:
                raise SystemExit(f"ZIP integrity failure in {name}: {bad}")
            for member in zf.infolist():
                pp = PurePosixPath(member.filename)
                if pp.is_absolute() or ".." in pp.parts or not member.filename.endswith(".parquet"):
                    raise SystemExit(f"Unsafe or unexpected ZIP member: {member.filename}")
                zf.extract(member, out / "parquet")
        downloaded.append({"file": name, "sha256": actual, "bytes": archive.stat().st_size})
        print(f"Verified {name}: {archive.stat().st_size:,} bytes")
    receipt = {
        "dataset_id": manifest["dataset_id"],
        "source_type": manifest["source_type"],
        "release_tag": release["tag_name"],
        "verified_archives": downloaded,
        "archive_count": len(downloaded),
        "note": "Third-party historical ticks; not PXBTTrading-1 broker history and not automatically an MT5 Strategy Tester import."
    }
    (out / "VERIFICATION_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(downloaded)} archive(s). Extracted Parquet files: {out / 'parquet'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (urllib.error.URLError, TimeoutError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
