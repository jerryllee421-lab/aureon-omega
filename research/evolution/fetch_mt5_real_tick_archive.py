#!/usr/bin/env python3
"""Fetch the latest validated public AUREON MT5 XAUUSD real-tick release.

Downloads are kept outside Git history and every monthly ZIP is SHA-256 verified
against the release manifest before it can be consumed by a research pipeline.
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
from pathlib import Path

DEFAULT_REPO = "jerryllee421-lab/aureon-omega"
TAG_PREFIX = "xauusd-real-ticks-"
USER_AGENT = "AUREON-RealTick-Archive/1.0"

def request_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"})
    try:
        with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as out:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                out.write(block)
        tmp.replace(target)
    finally:
        if tmp.exists():
            tmp.unlink()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO, help="Public GitHub owner/repository")
    ap.add_argument("--out", default="data/mt5_real_ticks", help="Destination outside Git history")
    ap.add_argument("--tag", default="", help="Pin an exact xauusd-real-ticks-* release tag")
    args = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        ap.error("--repo must be owner/repository")
    out = Path(args.out).resolve()
    api = f"https://api.github.com/repos/{args.repo}/releases"
    releases = request_json(api + "?per_page=100")
    release = next((r for r in releases if r.get("tag_name", "").startswith(TAG_PREFIX)
                    and not r.get("draft") and not r.get("prerelease")
                    and (not args.tag or r.get("tag_name") == args.tag)), None)
    if release is None:
        raise SystemExit("No matching published real-tick release found. Do not substitute OHLC/proxy data.")
    assets = {a["name"]: a for a in release.get("assets", [])}
    manifest_name = "xauusd_mt5_real_ticks_manifest.json"
    if manifest_name not in assets:
        raise SystemExit(f"Release {release['tag_name']} is missing {manifest_name}.")
    manifest_path = out / manifest_name
    download(assets[manifest_name]["browser_download_url"], manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset") != "AUREON_XAUUSD_MT5_REAL_TICKS":
        raise SystemExit("Manifest dataset identifier mismatch.")
    if manifest.get("symbol") != "XAUUSD" or manifest.get("source") != "MT5 CopyTicksRange(COPY_TICKS_ALL)":
        raise SystemExit("Manifest source/symbol does not prove MT5 real-tick provenance.")
    if manifest.get("broker_server") != "PXBTTrading-1" or manifest.get("account_mode_required") != "DEMO":
        raise SystemExit("Manifest server/account-mode policy mismatch.")
    if not manifest.get("validation", {}).get("minimum_coverage_days_passed"):
        raise SystemExit("Manifest does not confirm minimum coverage.")
    if float(manifest.get("coverage_days", 0)) < 730:
        raise SystemExit("Manifest has less than 730 days of coverage.")
    if not manifest.get("archives"):
        raise SystemExit("Manifest contains no monthly archives.")
    for item in manifest["archives"]:
        name = item.get("file", "")
        expected = item.get("sha256", "")
        if not re.fullmatch(r"xauusd_mt5_real_ticks_\d{6}\.zip", name) or not re.fullmatch(r"[a-f0-9]{64}", expected):
            raise SystemExit(f"Unsafe or invalid archive manifest entry: {name!r}")
        if name not in assets:
            raise SystemExit(f"Release is missing monthly asset: {name}")
        target = out / name
        if not target.is_file() or sha256(target) != expected:
            download(assets[name]["browser_download_url"], target)
        actual = sha256(target)
        if actual != expected:
            target.unlink(missing_ok=True)
            raise SystemExit(f"SHA-256 mismatch for {name}; deleted invalid download.")
        print(f"[AUREON] verified {name} ({target.stat().st_size:,} bytes)")
    for optional in ("xauusd_mt5_real_ticks_daily.csv", "mt5_tick_daily_manifest.csv", "mt5_tick_coverage_status.txt", "SHA256SUMS.txt"):
        if optional in assets:
            target = out / optional
            if not target.exists():
                download(assets[optional]["browser_download_url"], target)
    pinned = {
        "release_tag": release["tag_name"],
        "release_url": release["html_url"],
        "repo": args.repo,
        "manifest_sha256": sha256(manifest_path),
        "coverage_start_utc": manifest["coverage_start_utc"],
        "coverage_end_utc": manifest["coverage_end_utc"],
        "coverage_days": manifest["coverage_days"],
        "tick_count": manifest["tick_count"],
        "verified_archives": [x["file"] for x in manifest["archives"]],
        "research_only": True,
        "live_trading_allowed": False,
    }
    (out / "PINNED_SOURCE.json").write_text(json.dumps(pinned, indent=2), encoding="utf-8")
    print(json.dumps(pinned, indent=2))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
