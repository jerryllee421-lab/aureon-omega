#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="${GITHUB_WORKSPACE:-$PWD}/mt5_tester_artifact"
mkdir -p "$ARTIFACT_DIR"

export WINEPREFIX="${WINEPREFIX:-${RUNNER_TEMP:-/tmp}/aureon-mt5-wine}"
export WINEARCH="${WINEARCH:-win64}"
export WINEDEBUG="${WINEDEBUG:--all}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-mscoree,mshtml=;winemenubuilder.exe=d}"

cleanup() {
  wineserver -k >/dev/null 2>&1 || true
}
trap cleanup EXIT

TERMINAL="$(find "$WINEPREFIX/drive_c" -type f -iname 'terminal64.exe' -print -quit || true)"
METAEDITOR="$(find "$WINEPREFIX/drive_c" -type f -iname 'metaeditor64.exe' -print -quit || true)"
TRADE_MQH="$(find "$WINEPREFIX/drive_c" -type f -ipath '*/MQL5/Include/Trade/Trade.mqh' -print -quit || true)"

if [[ -z "$TERMINAL" || -z "$METAEDITOR" || -z "$TRADE_MQH" ]]; then
  echo "MT5 compile prerequisite is missing." | tee "$ARTIFACT_DIR/failure.txt"
  exit 1
fi

MT5_DIR="$(dirname "$TERMINAL")"
MQL5_ROOT="$(dirname "$(dirname "$(dirname "$TRADE_MQH")")")"
MQL5_WIN="$(winepath -w "$MQL5_ROOT")"

printf 'terminal=%s\nmetaeditor=%s\nmql5_root=%s\n' "$TERMINAL" "$METAEDITOR" "$MQL5_ROOT" \
  | tee "$ARTIFACT_DIR/paths.txt"

echo "== Resolve built-in MACD sample EA =="
MACD_MQ5="$(find "$MQL5_ROOT/Experts" -type f -iname 'MACD Sample.mq5' -print -quit || true)"
MACD_EX5="$(find "$MQL5_ROOT/Experts" -type f -iname 'MACD Sample.ex5' -print -quit || true)"

if [[ -n "$MACD_MQ5" && -z "$MACD_EX5" ]]; then
  MACD_WIN="$(winepath -w "$MACD_MQ5")"
  set +e
  xvfb-run -a timeout 300s wine "$METAEDITOR" /compile:"$MACD_WIN" /include:"$MQL5_WIN" /log \
    >"$ARTIFACT_DIR/macd-compile-process.log" 2>&1
  rc=$?
  set -e
  echo "$rc" > "$ARTIFACT_DIR/macd-compile-exit-code.txt"
  wineserver -k >/dev/null 2>&1 || true
  MACD_EX5="${MACD_MQ5%.mq5}.ex5"
fi

if [[ -z "$MACD_EX5" || ! -s "$MACD_EX5" ]]; then
  echo "Built-in MACD Sample EX5 was not found." | tee "$ARTIFACT_DIR/failure.txt"
  exit 1
fi

echo "== Build pinned offline XAUUSD M1 smoke dataset =="
MIRROR_COMMIT="922f83a60cc574e7395fb27397077288055a1ef6"
MIRROR_ROOT="https://raw.githubusercontent.com/kevingtlin/Market-Data-Lab/$MIRROR_COMMIT"
BID_URL="$MIRROR_ROOT/xauusd/bid/m1/xauusd_bid_m1_2026_08.csv"
ASK_URL="$MIRROR_ROOT/xauusd/ask/m1/xauusd_ask_m1_2026_08.csv"
BID_CSV="$RUNNER_TEMP/xauusd_bid_m1_2026_08.csv"
ASK_CSV="$RUNNER_TEMP/xauusd_ask_m1_2026_08.csv"

curl --fail --location --retry 5 "$BID_URL" -o "$BID_CSV"
curl --fail --location --retry 5 "$ASK_URL" -o "$ASK_CSV"
sha256sum "$BID_CSV" "$ASK_CSV" | tee "$ARTIFACT_DIR/source-csv.sha256"

mkdir -p "$MQL5_ROOT/Files"
CUSTOM_CSV="$MQL5_ROOT/Files/AUREON_XAUUSD_M1.csv"

python3 - "$BID_CSV" "$ASK_CSV" "$CUSTOM_CSV" "$ARTIFACT_DIR/dataset-manifest.json" <<'PY'
import csv
import datetime as dt
import hashlib
import json
import pathlib
import sys

bid_path, ask_path, out_path, manifest_path = map(pathlib.Path, sys.argv[1:])
start = dt.datetime(2026, 8, 3, tzinfo=dt.timezone.utc)
end = dt.datetime(2026, 8, 8, tzinfo=dt.timezone.utc)
point = 0.001

def load(path):
    rows = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            ts = int(row["timestamp"])
            when = dt.datetime.fromtimestamp(ts / 1000, tz=dt.timezone.utc)
            if start <= when < end:
                rows[ts] = row
    return rows

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

bid = load(bid_path)
ask = load(ask_path)
common = sorted(set(bid) & set(ask))
if not common:
    raise SystemExit("No common bid/ask rows in pinned range")

out_path.parent.mkdir(parents=True, exist_ok=True)
with out_path.open("w", newline="", encoding="ascii") as f:
    w = csv.writer(f)
    w.writerow(["time","open","high","low","close","tick_volume","spread","real_volume"])
    for ts in common:
        b = bid[ts]
        a = ask[ts]
        when = dt.datetime.fromtimestamp(ts / 1000, tz=dt.timezone.utc)
        spread = max(0, round((float(a["close"]) - float(b["close"])) / point))
        # The mirror contains OHLC but no tick-volume field. A constant technical
        # tick-volume proxy is used ONLY to let MT5 construct tester bars; it is
        # explicitly excluded from strategy evidence and recorded in the manifest.
        w.writerow([
            when.strftime("%Y.%m.%d %H:%M:%S"),
            b["open"], b["high"], b["low"], b["close"],
            1, spread, 0
        ])

manifest = {
    "source": "DUKASCOPY_EXTERNAL_PINNED_GITHUB_MIRROR",
    "mirror_commit": "922f83a60cc574e7395fb27397077288055a1ef6",
    "period_utc": {"from": start.isoformat(), "to_exclusive": end.isoformat()},
    "rows": len(common),
    "bid_sha256": sha(bid_path),
    "ask_sha256": sha(ask_path),
    "output_sha256": sha(out_path),
    "price_side": "BID_OHLC",
    "spread": "ASK_CLOSE_MINUS_BID_CLOSE converted to 0.001 points",
    "tick_volume": "TECHNICAL_PROXY_1_NOT_RESEARCH_EVIDENCE",
    "real_volume": 0,
    "purpose": "MT5_OFFLINE_STRATEGY_TESTER_SMOKE_ONLY"
}
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(manifest, indent=2))
PY

cp "$CUSTOM_CSV" "$ARTIFACT_DIR/AUREON_XAUUSD_M1.csv"

echo "== Compile custom Gold importer =="
IMPORTER_SRC="ea/tools/AUREON_CustomGoldImporter.mq5"
IMPORTER_DIR="$MQL5_ROOT/Scripts/AUREON"
mkdir -p "$IMPORTER_DIR"
IMPORTER_DEST="$IMPORTER_DIR/AUREON_CustomGoldImporter.mq5"
cp "$IMPORTER_SRC" "$IMPORTER_DEST"
IMPORTER_WIN="$(winepath -w "$IMPORTER_DEST")"

set +e
xvfb-run -a timeout 300s wine "$METAEDITOR" /compile:"$IMPORTER_WIN" /include:"$MQL5_WIN" /log \
  >"$ARTIFACT_DIR/importer-compile-process.log" 2>&1
importer_compile_rc=$?
set -e
echo "$importer_compile_rc" > "$ARTIFACT_DIR/importer-compile-exit-code.txt"
wineserver -k >/dev/null 2>&1 || true
sleep 2

IMPORTER_EX5="${IMPORTER_DEST%.mq5}.ex5"
IMPORTER_LOG="${IMPORTER_DEST%.mq5}.log"
if [[ -f "$IMPORTER_LOG" ]]; then
  python3 - "$IMPORTER_LOG" "$ARTIFACT_DIR/importer-compile.log" <<'PY'
import pathlib, sys
b = pathlib.Path(sys.argv[1]).read_bytes()
for enc in ("utf-16", "utf-16le", "utf-8-sig", "cp1252"):
    try:
        t = b.decode(enc)
        break
    except UnicodeDecodeError:
        pass
else:
    t = b.decode("utf-8", errors="replace")
pathlib.Path(sys.argv[2]).write_text(t, encoding="utf-8")
print(t)
PY
fi

if [[ ! -s "$IMPORTER_EX5" ]]; then
  echo "Custom Gold importer did not compile." | tee "$ARTIFACT_DIR/failure.txt"
  cat "$ARTIFACT_DIR/importer-compile.log" 2>/dev/null || true
  exit 1
fi

echo "== Create AUREON_XAUUSD custom symbol and import M1 bars =="
IMPORT_CONFIG="$MT5_DIR/aureon_custom_import.ini"
cat > "$IMPORT_CONFIG" <<'INI'
[Experts]
AllowLiveTrading=0
AllowDllImport=0
Enabled=1
Account=0
Profile=0

[StartUp]
Script=AUREON\AUREON_CustomGoldImporter
Symbol=EURUSD
Period=M1
ShutdownTerminal=1
INI

cat "$IMPORT_CONFIG" | tee "$ARTIFACT_DIR/import-config.ini"
IMPORT_CONFIG_WIN="$(winepath -w "$IMPORT_CONFIG")"

set +e
xvfb-run -a timeout 180s wine "$TERMINAL" /portable /config:"$IMPORT_CONFIG_WIN" \
  >"$ARTIFACT_DIR/terminal-import-process.log" 2>&1
import_rc=$?
set -e
echo "$import_rc" > "$ARTIFACT_DIR/import-terminal-exit-code.txt"
wineserver -k >/dev/null 2>&1 || true
sleep 2

MARKER="$MQL5_ROOT/Files/AUREON_CUSTOM_IMPORT_RESULT.txt"
if [[ ! -s "$MARKER" ]]; then
  echo "Offline custom-symbol importer did not produce its marker." | tee "$ARTIFACT_DIR/failure.txt"
  find "$MT5_DIR/logs" -type f -maxdepth 2 -print > "$ARTIFACT_DIR/import-log-files.txt" || true
  exit 1
fi
cp "$MARKER" "$ARTIFACT_DIR/"
cat "$MARKER" | tee "$ARTIFACT_DIR/import-result.txt"
if ! grep -q '^OK' "$MARKER"; then
  echo "Offline custom-symbol importer reported failure." | tee "$ARTIFACT_DIR/failure.txt"
  exit 1
fi

echo "== Create offline Strategy Tester config =="
CONFIG="$MT5_DIR/aureon_tester_smoke.ini"
cat > "$CONFIG" <<'INI'
[Tester]
Expert=Examples\MACD\MACD Sample
Symbol=AUREON_XAUUSD
Period=M5
Login=123456
Deposit=10000
Currency=USD
Leverage=1:100
Model=1
ExecutionMode=0
Optimization=0
FromDate=2026.08.03
ToDate=2026.08.07
ForwardMode=0
Report=mt5_tester_smoke
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
INI

cat "$CONFIG" | tee "$ARTIFACT_DIR/tester-config.ini"
CONFIG_WIN="$(winepath -w "$CONFIG")"

echo "== Run offline headless MT5 Strategy Tester smoke =="
set +e
xvfb-run -a timeout 420s wine "$TERMINAL" /portable /config:"$CONFIG_WIN" \
  >"$ARTIFACT_DIR/terminal-tester-process.log" 2>&1
tester_rc=$?
set -e
echo "$tester_rc" | tee "$ARTIFACT_DIR/tester-exit-code.txt"

wineserver -k >/dev/null 2>&1 || true
sleep 2

echo "== Collect tester evidence =="
find "$MT5_DIR" -maxdepth 7 -type f \( \
    -iname 'mt5_tester_smoke*' -o \
    -path '*/Tester/logs/*' -o \
    -path '*/logs/*' \
  \) -print > "$ARTIFACT_DIR/discovered-output-files.txt" || true

mkdir -p "$ARTIFACT_DIR/logs"
while IFS= read -r file; do
  [[ -f "$file" ]] || continue
  safe_name="$(echo "$file" | sed 's#/#__#g')"
  cp "$file" "$ARTIFACT_DIR/logs/$safe_name" 2>/dev/null || true
done < "$ARTIFACT_DIR/discovered-output-files.txt"

REPORT="$(find "$MT5_DIR" -maxdepth 2 -type f -iname 'mt5_tester_smoke*' -print -quit || true)"
if [[ -n "$REPORT" && -s "$REPORT" ]]; then
  cp "$REPORT" "$ARTIFACT_DIR/"
  sha256sum "$REPORT" | tee "$ARTIFACT_DIR/report.sha256"
  echo "report=$REPORT" | tee "$ARTIFACT_DIR/result.txt"
  echo "MT5 offline Strategy Tester smoke PASSED."
  exit 0
fi

echo "No Strategy Tester report was produced." | tee "$ARTIFACT_DIR/failure.txt"
exit 1
