from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

REPO = Path.cwd()
INSTALLER_URL = "https://download.terminal.free/cdn/web/metaquotes.ltd/mt5/mt5setup.exe"
MIRROR_COMMIT = "922f83a60cc574e7395fb27397077288055a1ef6"
DATA_FROM = "2025-08-20"
SPLIT_DATE = "2026-04-20"
DATA_TO = "2026-08-20"


def run(cmd, timeout=None, check=True, env=None):
    print("RUN", " ".join(map(str, cmd)), flush=True)
    return subprocess.run([str(x) for x in cmd], timeout=timeout, check=check, env=env)


def kill_processes():
    for name in ("terminal64.exe", "metatester64.exe", "metaeditor64.exe"):
        subprocess.run(["taskkill", "/F", "/IM", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def read_text_auto(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-16", "utf-8", "cp1252"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8", errors="ignore")


def write_ini(path: Path, lines: list[str]):
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-16")


def build_data():
    run([sys.executable, "research/mirror_m1.py", "--start", DATA_FROM, "--end", DATA_TO,
         "--commit", MIRROR_COMMIT, "--output", "research_data"], timeout=900)
    run([sys.executable, "research/export_mt5_m1.py", "--root", "research_data", "--symbol", "XAUUSD",
         "--point", "0.001", "--output", "mt5_input/ASTRA_XAUUSD_M1.csv"], timeout=300)


def install_mt5(root: Path):
    kill_processes()
    root.mkdir(parents=True, exist_ok=True)
    installer = Path(os.environ.get("RUNNER_TEMP", str(REPO))) / ("mt5setup-" + root.name + ".exe")
    if not installer.exists() or installer.stat().st_size < 100000:
        r = requests.get(INSTALLER_URL, timeout=(20, 180))
        r.raise_for_status()
        installer.write_bytes(r.content)
    # MetaQuotes' installer can return a non-zero process code even when the
    # requested installation completed. Treat the filesystem as authoritative,
    # matching the already-proven PowerShell CI lane.
    run([installer, "/auto", f"/path:{root}"], timeout=600, check=False)
    deadline = time.time() + 180
    while time.time() < deadline and not (root / "metaeditor64.exe").exists():
        time.sleep(2)
    if not (root / "metaeditor64.exe").exists():
        raise RuntimeError("MetaEditor missing after MT5 install")
    p = subprocess.Popen([str(root / "terminal64.exe"), "/portable"])
    time.sleep(8)
    kill_processes()


def compile_mql(root: Path):
    mql5 = root / "MQL5"
    ea_dir = mql5 / "Experts" / "AUREON"
    script_dir = mql5 / "Scripts" / "AUREON"
    ea_dir.mkdir(parents=True, exist_ok=True)
    script_dir.mkdir(parents=True, exist_ok=True)
    ea = ea_dir / "AUREON_ASTRA_GOLD_CAMPAIGN_V1.mq5"
    loader = script_dir / "AUREON_CustomSymbolLoader.mq5"
    shutil.copy2(REPO / "ea/astra/AUREON_ASTRA_GOLD_CAMPAIGN_V1.mq5", ea)
    shutil.copy2(REPO / "ea/astra/tools/AUREON_CustomSymbolLoader.mq5", loader)
    for src, label in ((ea, "EA"), (loader, "loader")):
        run([root / "metaeditor64.exe", f"/compile:{src}", f"/include:{mql5}", "/log"], timeout=180)
        time.sleep(2)
        log = src.with_suffix(".log")
        ex5 = src.with_suffix(".ex5")
        if not log.exists() or not ex5.exists():
            raise RuntimeError(f"{label} compile output missing")
        txt = read_text_auto(log)
        if "0 errors" not in txt or "0 warnings" not in txt:
            raise RuntimeError(f"{label} compile was not clean:\n{txt[-2000:]}")
    return ea, loader


def import_history(root: Path, artifact: Path):
    mql5 = root / "MQL5"
    files = mql5 / "Files"
    files.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "mt5_input/ASTRA_XAUUSD_M1.csv", files / "ASTRA_XAUUSD_M1.csv")
    cfg = root / "loader.ini"
    write_ini(cfg, [
        "[Experts]", "Enabled=1", "AllowLiveTrading=0", "AllowDllImport=0", "",
        "[StartUp]", r"Script=AUREON\AUREON_CustomSymbolLoader", "Symbol=EURUSD", "Period=M1", "ShutdownTerminal=1"
    ])
    kill_processes()
    p = subprocess.Popen([str(root / "terminal64.exe"), "/portable", f"/config:{cfg}"])
    try:
        p.wait(timeout=900)
    except subprocess.TimeoutExpired:
        p.kill()
        kill_processes()
        raise RuntimeError("custom-symbol history import timeout")
    time.sleep(2)
    event_text = ""
    for log_root in (root / "Logs", mql5 / "Logs"):
        if not log_root.exists():
            continue
        for pth in log_root.rglob("*.log"):
            try:
                event_text += read_text_auto(pth) + "\n"
            except Exception:
                pass
    lines = [x for x in event_text.splitlines() if "ASTRA_IMPORT_" in x]
    (artifact / "import.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if "ASTRA_IMPORT_OK" not in event_text:
        raise RuntimeError("history import did not report ASTRA_IMPORT_OK")


def account():
    login = os.environ.get("MT5_DEMO_LOGIN", "").strip()
    password = os.environ.get("MT5_DEMO_PASSWORD", "").strip()
    server = os.environ.get("MT5_DEMO_SERVER", "PXBTTrading-1").strip() or "PXBTTrading-1"
    if not login or not password:
        raise RuntimeError("MT5 demo account secrets are required")
    return login, password, server


def tester_config(root: Path, preset: str, report_name: str, from_date: str, to_date: str) -> Path:
    login, password, server = account()
    cfg = root / f"{report_name}.ini"
    write_ini(cfg, [
        "[Common]", f"Login={login}", f"Password={password}", f"Server={server}",
        "KeepPrivate=0", "NewsEnable=0", "",
        "[Experts]", "Enabled=1", "AllowLiveTrading=0", "AllowDllImport=0", "",
        "[Tester]", r"Expert=AUREON\AUREON_ASTRA_GOLD_CAMPAIGN_V1",
        f"ExpertParameters={preset}", "Symbol=ASTRA_XAUUSD", "Period=M5",
        f"Login={login}", "Deposit=10000", "Currency=USD", "Leverage=1:100",
        "Model=1", "ExecutionMode=0", "Optimization=0",
        f"FromDate={from_date}", f"ToDate={to_date}", "ForwardMode=0",
        f"Report=\\reports\\{report_name}", "ReplaceReport=1", "ShutdownTerminal=1",
        "UseLocal=1", "UseRemote=0", "UseCloud=0", "Visual=0"
    ])
    return cfg


def find_report(root: Path, report_name: str) -> Path:
    candidates = sorted(
        [p for p in root.rglob(f"{report_name}*.htm*") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise RuntimeError(f"report missing for {report_name}")
    return candidates[0]


def run_cases(root: Path, preset_dir: Path, manifest_path: Path, report_dir: Path,
              from_date: str, to_date: str, prefix: str):
    mql5 = root / "MQL5"
    profile = mql5 / "Profiles" / "Tester"
    profile.mkdir(parents=True, exist_ok=True)
    (root / "reports").mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for case in manifest:
        preset = preset_dir / case["preset"]
        shutil.copy2(preset, profile / preset.name)
        report_name = f"{prefix}_{int(case['index']):02d}"
        cfg = tester_config(root, preset.name, report_name, from_date, to_date)
        kill_processes()
        p = subprocess.Popen([str(root / "terminal64.exe"), "/portable", f"/config:{cfg}"])
        try:
            p.wait(timeout=300)
        except subprocess.TimeoutExpired:
            p.kill()
            kill_processes()
            raise RuntimeError(f"{case['name']} tester timeout")
        time.sleep(2)
        report = find_report(root, report_name)
        shutil.copy2(report, report_dir / f"{case['name']}.htm")


def analyze_manifest(manifest_path: Path, report_dir: Path, analysis_dir: Path, min_trades=1, min_pf=0.0, max_dd=100.0):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for case in manifest:
        out = analysis_dir / case["name"]
        out.mkdir(parents=True, exist_ok=True)
        run([sys.executable, "scripts/analyze_mt5_report.py", report_dir / f"{case['name']}.htm",
             "--out", out, "--min-trades", str(min_trades), "--min-pf", str(min_pf), "--max-dd", str(max_dd)],
            timeout=60, check=False)


def copy_event_ledgers(root: Path, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    for p in root.rglob("*.csv"):
        if p.name.startswith(("ASTRA_DOE_", "ASTRA_CROSS_", "OOS_")):
            safe = str(p).replace(":", "_").replace("\\", "_").replace("/", "_")
            try:
                shutil.copy2(p, dest / safe)
            except Exception:
                pass


def common_setup(root: Path, artifact: Path):
    artifact.mkdir(parents=True, exist_ok=True)
    build_data()
    install_mt5(root)
    compile_mql(root)
    import_history(root, artifact)


def screen(args):
    artifact = Path(args.artifact)
    generated = Path("generated") / args.family
    run([sys.executable, "scripts/astra_doe.py", "generate", "--family", args.family,
         "--base", "ea/astra/presets/ASTRA_GOLD_V1_E1_ONLY_OHLC.set",
         "--out", generated, "--magic-base", str(args.magic_base)], timeout=60)
    (artifact / "presets").mkdir(parents=True, exist_ok=True)
    for p in generated.glob("*.set"):
        shutil.copy2(p, artifact / "presets" / p.name)
    shutil.copy2(generated / "manifest.json", artifact / "manifest.json")

    root = Path("C:/AUREON_DOE_" + args.family.upper())
    common_setup(root, artifact)
    run_cases(root, generated, generated / "manifest.json", artifact / "reports",
              "2025.08.20", "2026.04.20", "DOE_" + args.family.upper())
    analyze_manifest(generated / "manifest.json", artifact / "reports", artifact / "analysis")
    run([sys.executable, "scripts/astra_doe.py", "rank", "--analysis", artifact / "analysis",
         "--manifest", generated / "manifest.json", "--out", artifact, "--top", "3"], timeout=60)
    dm = Path("research_data/XAUUSD/download_manifest.json")
    if dm.exists():
        shutil.copy2(dm, artifact / "download_manifest.json")
    copy_event_ledgers(root, artifact / "event_ledgers")
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        (artifact / "source_commit.txt").write_text(commit + "\n")
    except Exception:
        pass


def cross(args):
    artifact = Path(args.artifact)
    artifact.mkdir(parents=True, exist_ok=True)
    cross_presets = Path("cross_presets")
    run([sys.executable, "scripts/astra_doe.py", "cross",
         "--base", "ea/astra/presets/ASTRA_GOLD_V1_E1_ONLY_OHLC.set",
         "--tops", args.tops, "--out", cross_presets, "--per-family", "2",
         "--magic-base", str(args.magic_base)], timeout=60)
    shutil.copytree(cross_presets, artifact / "presets", dirs_exist_ok=True)
    shutil.copytree(args.tops, artifact / "family_screens", dirs_exist_ok=True)

    root = Path("C:/AUREON_DOE_CROSS")
    common_setup(root, artifact)
    run_cases(root, cross_presets, cross_presets / "manifest.json", artifact / "reports",
              "2025.08.20", "2026.04.20", "CROSS")
    analyze_manifest(cross_presets / "manifest.json", artifact / "reports", artifact / "analysis")
    run([sys.executable, "scripts/astra_doe.py", "rank", "--analysis", artifact / "analysis",
         "--manifest", cross_presets / "manifest.json", "--out", artifact, "--top", "6"], timeout=60)

    oos = Path("oos_presets")
    run([sys.executable, "scripts/astra_doe.py", "oos", "--ranking", artifact / "ranking.json",
         "--presets", cross_presets, "--out", oos, "--top", "4", "--min-trades", "10"], timeout=60)
    shutil.copytree(oos, artifact / "oos_presets", dirs_exist_ok=True)
    run_cases(root, oos, oos / "manifest.json", artifact / "oos_reports",
              "2026.04.20", "2026.08.20", "OOS")
    analyze_manifest(oos / "manifest.json", artifact / "oos_reports", artifact / "oos_analysis",
                     min_trades=5, min_pf=1.0, max_dd=10.0)
    run([sys.executable, "scripts/astra_doe.py", "rank", "--analysis", artifact / "oos_analysis",
         "--manifest", oos / "manifest.json", "--out", artifact / "oos_summary", "--top", "4"], timeout=60)

    methodology = [
        "DATA=DUKASCOPY_EXTERNAL_PINNED_MIRROR",
        "MODEL=MT5_1_MINUTE_OHLC",
        "IN_SAMPLE=2025-08-20_to_2026-04-20",
        "OOS=2026-04-20_to_2026-08-20",
        "VOLUME_FILTER=DISABLED_EXTERNAL_DATA_HAS_NO_TRUE_TICK_VOLUME",
        "BROKER_NATIVE_REAL_TICK_CONFIRMATION=REQUIRED_BEFORE_FORWARD_PROMOTION",
        "LIVE_TRADING=DISABLED",
    ]
    (artifact / "methodology.txt").write_text("\n".join(methodology) + "\n")
    dm = Path("research_data/XAUUSD/download_manifest.json")
    if dm.exists():
        shutil.copy2(dm, artifact / "download_manifest.json")
    copy_event_ledgers(root, artifact / "event_ledgers")
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        (artifact / "source_commit.txt").write_text(commit + "\n")
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("screen")
    s.add_argument("--family", required=True, choices=["structure", "trigger", "exit", "session"])
    s.add_argument("--artifact", required=True)
    s.add_argument("--magic-base", type=int, default=26300000)
    s.set_defaults(func=screen)
    c = sub.add_parser("cross")
    c.add_argument("--tops", required=True)
    c.add_argument("--artifact", required=True)
    c.add_argument("--magic-base", type=int, default=26400000)
    c.set_defaults(func=cross)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
