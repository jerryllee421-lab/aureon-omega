#!/usr/bin/env bash
set -euo pipefail

export WINEPREFIX="${WINEPREFIX:-${RUNNER_TEMP:-/tmp}/aureon-mt5-wine}"
export WINEARCH="${WINEARCH:-win64}"
export WINEDEBUG="${WINEDEBUG:--all}"

ARTIFACT_DIR="${GITHUB_WORKSPACE:-$PWD}/mt5_tester_artifact"
COMPILE_ARTIFACT="${GITHUB_WORKSPACE:-$PWD}/mt5_ci_artifact"
DATA_DIR="${GITHUB_WORKSPACE:-$PWD}/mt5_ci_data"
mkdir -p "$ARTIFACT_DIR" "$DATA_DIR"

cleanup() {
  wineserver -k >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "== Build MT5 + baseline EA =="
bash scripts/mt5_linux_compile.sh

source "$COMPILE_ARTIFACT/mt5-paths.txt"
source "$COMPILE_ARTIFACT/mql5-root.txt"
MQL5_ROOT="$mql5_root"

MT5_DIR="$(dirname "$terminal")"
mkdir -p "$MQL5_ROOT/Scripts/AUREON" "$MQL5_ROOT/Files" "$MT5_DIR/reports"

echo "== Prepare pinned external Gold M1 data =="
python3 scripts/prepare_mt5_custom_gold.py \
  --year 2026 --month 8 \
  --output "$DATA_DIR/aureon_gold_m1.csv" \
  --manifest "$DATA_DIR/source_manifest.json"
cp "$DATA_DIR/aureon_gold_m1.csv" "$MQL5_ROOT/Files/aureon_gold_m1.csv"
cp "$DATA_DIR/source_manifest.json" "$ARTIFACT_DIR/source_manifest.json"

echo "== Compile custom-symbol loader =="
LOADER_SRC="$MQL5_ROOT/Scripts/AUREON/AUREON_LoadCustomGold.mq5"
cp mt5/AUREON_LoadCustomGold.mq5 "$LOADER_SRC"
LOADER_WIN="$(winepath -w "$LOADER_SRC")"
MQL5_WIN="$(winepath -w "$MQL5_ROOT")"

set +e
xvfb-run -a timeout 240s wine "$metaeditor" /compile:"$LOADER_WIN" /include:"$MQL5_WIN" /log \
  >"$ARTIFACT_DIR/loader-metaeditor-process.log" 2>&1
loader_compile_rc=$?
set -e
echo "$loader_compile_rc" > "$ARTIFACT_DIR/loader-metaeditor-exit-code.txt"
sleep 2
wineserver -k >/dev/null 2>&1 || true

LOADER_EX5="${LOADER_SRC%.mq5}.ex5"
LOADER_LOG="${LOADER_SRC%.mq5}.log"
if [[ -f "$LOADER_LOG" ]]; then
  iconv -f UTF-16LE -t UTF-8 "$LOADER_LOG" > "$ARTIFACT_DIR/loader-compile.log" 2>/dev/null || \
    cp "$LOADER_LOG" "$ARTIFACT_DIR/loader-compile.log"
fi
cp mt5/AUREON_LoadCustomGold.mq5 "$ARTIFACT_DIR/"

if [[ ! -s "$LOADER_EX5" ]]; then
  echo "Custom Gold loader compilation failed." | tee "$ARTIFACT_DIR/failure.txt"
  cat "$ARTIFACT_DIR/loader-compile.log" 2>/dev/null || true
  exit 1
fi

if ! grep -aEiq '(^|[^0-9])0 errors([^0-9]|$)' "$ARTIFACT_DIR/loader-compile.log"; then
  echo "Loader compiler log does not confirm zero errors." | tee -a "$ARTIFACT_DIR/failure.txt"
  cat "$ARTIFACT_DIR/loader-compile.log" || true
  exit 1
fi

echo "== Run custom-symbol loader inside MT5 =="
LOAD_INI="$MT5_DIR/aureon-load-custom-gold.ini"
cat > "$LOAD_INI" <<'EOF'
[Common]
NewsEnable=0
CertInstall=0

[StartUp]
Symbol=EURUSD
Period=M1
Script=AUREON\AUREON_LoadCustomGold
ShutdownTerminal=1
EOF

LOAD_INI_WIN="$(winepath -w "$LOAD_INI")"
set +e
xvfb-run -a timeout 180s wine "$terminal" /portable "/config:$LOAD_INI_WIN" \
  >"$ARTIFACT_DIR/load-terminal-process.log" 2>&1
load_rc=$?
set -e
echo "$load_rc" > "$ARTIFACT_DIR/load-terminal-exit-code.txt"
wineserver -k >/dev/null 2>&1 || true
sleep 2

LOAD_RESULT="$MQL5_ROOT/Files/aureon_custom_gold_result.txt"
if [[ ! -s "$LOAD_RESULT" ]]; then
  echo "Custom Gold loader did not produce its result marker." | tee "$ARTIFACT_DIR/failure.txt"
  find "$MT5_DIR" "$MQL5_ROOT" -type f \( -iname '*.log' -o -iname '*journal*' \) -mmin -10 -print \
    | tee "$ARTIFACT_DIR/recent-mt5-logs.txt" || true
  while IFS= read -r log; do
    [[ -f "$log" ]] || continue
    safe="$(echo "$log" | sed 's#[/ ]#_#g')"
    cp "$log" "$ARTIFACT_DIR/${safe##*_AUREON_MT5_}" 2>/dev/null || true
  done < "$ARTIFACT_DIR/recent-mt5-logs.txt"
  exit 1
fi
cp "$LOAD_RESULT" "$ARTIFACT_DIR/"
cat "$LOAD_RESULT"
grep -q '^PASS|' "$LOAD_RESULT"

echo "== Run credential-free MT5 Strategy Tester smoke =="
TEST_INI="$MT5_DIR/aureon-tester-smoke.ini"
cat > "$TEST_INI" <<'EOF'
[Common]
NewsEnable=0
CertInstall=0

[Tester]
Expert=AUREON\FVG_Scalper_V2_11_ORIGINAL
Symbol=AUREON_XAUUSD
Period=M1
Deposit=10000
Leverage=1:100
Model=1
ExecutionMode=0
Optimization=0
FromDate=2026.08.05
ToDate=2026.08.19
ForwardMode=0
Report=reports\aureon_fvg_smoke
ReplaceReport=1
ShutdownTerminal=1
EOF

TEST_INI_WIN="$(winepath -w "$TEST_INI")"
set +e
xvfb-run -a timeout 600s wine "$terminal" /portable "/config:$TEST_INI_WIN" \
  >"$ARTIFACT_DIR/tester-terminal-process.log" 2>&1
tester_rc=$?
set -e
echo "$tester_rc" > "$ARTIFACT_DIR/tester-terminal-exit-code.txt"
wineserver -k >/dev/null 2>&1 || true
sleep 3

REPORT="$MT5_DIR/reports/aureon_fvg_smoke.htm"
if [[ ! -s "$REPORT" ]]; then
  alt="$(find "$MT5_DIR" -type f -iname 'aureon_fvg_smoke*.htm' -print -quit || true)"
  if [[ -n "$alt" ]]; then REPORT="$alt"; fi
fi

if [[ ! -s "$REPORT" ]]; then
  echo "Strategy Tester did not produce an HTML report." | tee "$ARTIFACT_DIR/failure.txt"
  find "$WINEPREFIX/drive_c" -type f -path '*/Tester/logs/*' -o -path '*/tester/logs/*' \
    | tail -n 20 | tee "$ARTIFACT_DIR/recent-tester-logs.txt" || true
  exit 1
fi

cp "$REPORT" "$ARTIFACT_DIR/aureon_fvg_smoke.htm"

# Preserve relevant recent terminal/tester logs for audit.
find "$WINEPREFIX/drive_c" -type f \( -path '*/logs/*.log' -o -path '*/Logs/*.log' \) -mmin -20 -print0 \
  | while IFS= read -r -d '' log; do
      safe="$(echo "$log" | sed 's#[/ ]#_#g')"
      cp "$log" "$ARTIFACT_DIR/${safe##*_temp_}" 2>/dev/null || true
    done

echo "== Build tester manifest =="
python3 - "$ARTIFACT_DIR/tester_manifest.json" "$REPORT" <<'PY'
import datetime
import hashlib
import json
import pathlib
import sys

report = pathlib.Path(sys.argv[2])
source_manifest = json.loads(pathlib.Path("mt5_tester_artifact/source_manifest.json").read_text(encoding="utf-8"))

def sha(path):
    p = pathlib.Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

manifest = {
    "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "symbol": "AUREON_XAUUSD",
    "expert": "FVG_Scalper_V2_11_ORIGINAL",
    "period": "M1",
    "from_date": "2026.08.05",
    "to_date": "2026.08.19",
    "model": "1_MINUTE_OHLC",
    "execution_mode": "NORMAL",
    "deposit": 10000,
    "leverage": "1:100",
    "broker_login_used": False,
    "broker_credentials_used": False,
    "real_ticks": False,
    "data_source": source_manifest["source"],
    "data_transport": source_manifest["transport"],
    "data_commit": source_manifest["commit"],
    "source_rows": source_manifest["rows"],
    "report_sha256": sha(report),
    "limitations": [
        "credential-free custom-symbol smoke test",
        "1-minute OHLC model; not real-tick verification",
        "source provides bid/ask M1 OHLC but no source tick volume",
        "tick_volume=4 is a modeling count, not market volume"
    ]
}
pathlib.Path(sys.argv[1]).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(manifest, indent=2))
PY

echo "MT5 Strategy Tester cloud smoke PASSED."
