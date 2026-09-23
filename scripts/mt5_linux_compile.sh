#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="${GITHUB_WORKSPACE:-$PWD}/mt5_ci_artifact"
mkdir -p "$ARTIFACT_DIR"

export WINEPREFIX="${WINEPREFIX:-${RUNNER_TEMP:-/tmp}/aureon-mt5-wine}"
export WINEARCH="${WINEARCH:-win64}"
export WINEDEBUG="${WINEDEBUG:--all}"
INSTALLER_URL="${MT5_INSTALLER_URL:-https://download.terminal.free/cdn/web/metaquotes.ltd/mt5/mt5setup.exe}"
INSTALLER="${RUNNER_TEMP:-/tmp}/mt5setup.exe"
EA_SOURCE="${EA_SOURCE:-ea/baseline/FVG_Scalper_V2_11_ORIGINAL.mq5}"
EA_FILENAME="$(basename "$EA_SOURCE")"
export EA_FILENAME

cleanup() {
  wineserver -k >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "== Environment =="
uname -a | tee "$ARTIFACT_DIR/uname.txt"
wine --version | tee "$ARTIFACT_DIR/wine-version.txt"

echo "== Initialize Wine prefix =="
mkdir -p "$WINEPREFIX"
set +e
xvfb-run -a timeout 180s wineboot -u >"$ARTIFACT_DIR/wineboot.log" 2>&1
wineboot_rc=$?
set -e
if [[ "$wineboot_rc" != "0" && "$wineboot_rc" != "124" ]]; then
  cat "$ARTIFACT_DIR/wineboot.log"
  echo "wineboot failed with exit code $wineboot_rc"
  exit "$wineboot_rc"
fi
wineserver -w >/dev/null 2>&1 || true
test -d "$WINEPREFIX/drive_c"

echo "== Download official MT5 installer =="
curl --fail --location --retry 5 --retry-delay 3 \
  "$INSTALLER_URL" -o "$INSTALLER"
test -s "$INSTALLER"
sha256sum "$INSTALLER" | tee "$ARTIFACT_DIR/mt5setup.sha256"
file "$INSTALLER" | tee "$ARTIFACT_DIR/mt5setup.file.txt"

echo "== Install MetaTrader 5 =="
set +e
xvfb-run -a timeout 900s wine "$INSTALLER" /auto /path:"C:\\AUREON_MT5" \
  >"$ARTIFACT_DIR/installer.log" 2>&1
installer_rc=$?
set -e
echo "$installer_rc" > "$ARTIFACT_DIR/installer-exit-code.txt"

# The web installer can spawn the terminal or leave helper processes behind.
# Stop them only after installation files have had time to flush.
sleep 5
wineserver -k >/dev/null 2>&1 || true
sleep 2

TERMINAL="$(find "$WINEPREFIX/drive_c" -type f -iname 'terminal64.exe' -print -quit || true)"
METAEDITOR="$(find "$WINEPREFIX/drive_c" -type f -iname 'metaeditor64.exe' -print -quit || true)"

if [[ -z "$TERMINAL" || -z "$METAEDITOR" ]]; then
  echo "MetaTrader installation files were not found." | tee "$ARTIFACT_DIR/failure.txt"
  find "$WINEPREFIX/drive_c" -maxdepth 6 -type f \
    \( -iname 'terminal*.exe' -o -iname 'metaeditor*.exe' \) -print \
    | tee "$ARTIFACT_DIR/discovered-mt5-files.txt" || true
  tail -n 200 "$ARTIFACT_DIR/installer.log" || true
  exit 1
fi

printf 'terminal=%s\nmetaeditor=%s\n' "$TERMINAL" "$METAEDITOR" \
  | tee "$ARTIFACT_DIR/mt5-paths.txt"

echo "== Resolve MT5 MQL5 data root =="
TRADE_MQH="$(find "$WINEPREFIX/drive_c" -type f -ipath '*/MQL5/Include/Trade/Trade.mqh' -print -quit || true)"

if [[ -z "$TRADE_MQH" ]]; then
  echo "Standard Library not materialized yet; launching terminal once in portable mode."
  set +e
  xvfb-run -a timeout 45s wine "$TERMINAL" /portable \
    >"$ARTIFACT_DIR/terminal-first-launch.log" 2>&1
  terminal_launch_rc=$?
  set -e
  echo "$terminal_launch_rc" > "$ARTIFACT_DIR/terminal-first-launch-exit-code.txt"
  wineserver -k >/dev/null 2>&1 || true
  sleep 3
  TRADE_MQH="$(find "$WINEPREFIX/drive_c" -type f -ipath '*/MQL5/Include/Trade/Trade.mqh' -print -quit || true)"
fi

if [[ -z "$TRADE_MQH" ]]; then
  echo "MT5 Standard Library Trade.mqh was not found." | tee "$ARTIFACT_DIR/failure.txt"
  find "$WINEPREFIX/drive_c" -type d -iname 'MQL5' -print | tee "$ARTIFACT_DIR/mql5-roots.txt" || true
  exit 1
fi

MQL5_ROOT="$(dirname "$(dirname "$(dirname "$TRADE_MQH")")")"
printf 'trade_mqh=%s\nmql5_root=%s\n' "$TRADE_MQH" "$MQL5_ROOT" \
  | tee "$ARTIFACT_DIR/mql5-root.txt"

echo "== Stage EA source =="
test -s "$EA_SOURCE"
EXPERT_DIR="$MQL5_ROOT/Experts/AUREON"
mkdir -p "$EXPERT_DIR"
EA_DEST="$EXPERT_DIR/$EA_FILENAME"
cp "$EA_SOURCE" "$EA_DEST"
cmp --silent "$EA_SOURCE" "$EA_DEST"
sha256sum "$EA_SOURCE" | tee "$ARTIFACT_DIR/ea-source.sha256"

echo "== Compile with official MetaEditor =="
EA_WIN="$(winepath -w "$EA_DEST")"
MQL5_WIN="$(winepath -w "$MQL5_ROOT")"
printf '%s\n' "$EA_WIN" > "$ARTIFACT_DIR/ea-windows-path.txt"
printf '%s\n' "$MQL5_WIN" > "$ARTIFACT_DIR/mql5-windows-path.txt"

set +e
xvfb-run -a timeout 480s wine "$METAEDITOR" /compile:"$EA_WIN" /include:"$MQL5_WIN" /log \
  >"$ARTIFACT_DIR/metaeditor-process.log" 2>&1
compile_rc=$?
set -e
echo "$compile_rc" > "$ARTIFACT_DIR/metaeditor-exit-code.txt"

sleep 3
wineserver -k >/dev/null 2>&1 || true

EX5="${EA_DEST%.mq5}.ex5"
RAW_LOG="${EA_DEST%.mq5}.log"

if [[ -f "$RAW_LOG" ]]; then
  python3 - "$RAW_LOG" "$ARTIFACT_DIR/compile.log" <<'PY'
import pathlib
import sys

src = pathlib.Path(sys.argv[1]).read_bytes()
for enc in ("utf-16", "utf-16le", "utf-8-sig", "cp1252"):
    try:
        text = src.decode(enc)
        break
    except UnicodeDecodeError:
        pass
else:
    text = src.decode("utf-8", errors="replace")

pathlib.Path(sys.argv[2]).write_text(text, encoding="utf-8")
print(text)
PY
else
  echo "MetaEditor did not create a compilation log." | tee "$ARTIFACT_DIR/compile.log"
fi

cp "$EA_DEST" "$ARTIFACT_DIR/"
[[ -f "$EX5" ]] && cp "$EX5" "$ARTIFACT_DIR/"

if [[ ! -s "$EX5" ]]; then
  echo "Compilation did not produce EX5." | tee -a "$ARTIFACT_DIR/failure.txt"
  cat "$ARTIFACT_DIR/metaeditor-process.log" || true
  cat "$ARTIFACT_DIR/compile.log" || true
  exit 1
fi

if ! grep -Eiq '(^|[^0-9])0 errors([^0-9]|$)' "$ARTIFACT_DIR/compile.log"; then
  echo "Compiler log does not confirm zero errors." | tee -a "$ARTIFACT_DIR/failure.txt"
  cat "$ARTIFACT_DIR/compile.log" || true
  exit 1
fi

sha256sum "$EX5" | tee "$ARTIFACT_DIR/ex5.sha256"

echo "== Build reproducibility manifest =="
python3 - "$ARTIFACT_DIR/manifest.json" <<'PY'
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys

root = pathlib.Path("mt5_ci_artifact")

def sha(path):
    p = pathlib.Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

try:
    wine_version = subprocess.check_output(["wine", "--version"], text=True).strip()
except Exception:
    wine_version = None

compile_text = (root / "compile.log").read_text(encoding="utf-8", errors="replace") if (root / "compile.log").exists() else ""
import re
m = re.search(r"Result:\s*(\d+)\s*errors,\s*(\d+)\s*warnings", compile_text, re.I)
compile_errors = int(m.group(1)) if m else None
compile_warnings = int(m.group(2)) if m else None
installer_hash_file = root / "mt5setup.sha256"
installer_hash = installer_hash_file.read_text(encoding="utf-8").split()[0] if installer_hash_file.exists() else None

manifest = {
    "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "github_run_id": os.getenv("GITHUB_RUN_ID"),
    "github_sha": os.getenv("GITHUB_SHA"),
    "runner_os": os.getenv("RUNNER_OS"),
    "runner_arch": os.getenv("RUNNER_ARCH"),
    "wine_version": wine_version,
    "mt5_installer_sha256": installer_hash,
    "source_ea_sha256": sha(root / os.environ.get("EA_FILENAME", "FVG_Scalper_V2_11_ORIGINAL.mq5")),
    "compiled_ex5_sha256": sha(root / pathlib.Path(os.environ.get("EA_FILENAME", "FVG_Scalper_V2_11_ORIGINAL.mq5")).with_suffix(".ex5")),
    "compile_errors": compile_errors,
    "compile_warnings": compile_warnings,
    "compile_zero_errors": compile_errors == 0,
    "safety": {
        "credentials_used": False,
        "broker_login_used": False,
        "orders_sent": False,
        "purpose": "compile_smoke_only"
    }
}
pathlib.Path(sys.argv[1]).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(manifest, indent=2))
PY

# Keep a copy of the downloaded installer hash evidence, not the installer itself.
echo "MT5 Linux compile smoke PASSED."
