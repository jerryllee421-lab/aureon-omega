#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="${GITHUB_WORKSPACE:-$PWD}/mt5_tester_artifact"
mkdir -p "$ARTIFACT_DIR"

export WINEPREFIX="${WINEPREFIX:-${RUNNER_TEMP:-/tmp}/aureon-mt5-wine}"
export WINEARCH="${WINEARCH:-win64}"
export WINEDEBUG="${WINEDEBUG:--all}"

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
  find "$MQL5_ROOT/Experts" -maxdepth 4 -type f \( -iname '*.mq5' -o -iname '*.ex5' \) \
    | head -n 200 > "$ARTIFACT_DIR/expert-inventory.txt" || true
  exit 1
fi

echo "== Create Strategy Tester config =="
mkdir -p "$MT5_DIR/reports"
CONFIG="$MT5_DIR/aureon_tester_smoke.ini"
cat > "$CONFIG" <<'INI'
[Tester]
Expert=Examples\MACD\MACD Sample
Symbol=EURUSD
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
Report=reports\mt5_tester_smoke
ReplaceReport=1
ShutdownTerminal=1
INI

cat "$CONFIG" | tee "$ARTIFACT_DIR/tester-config.ini"
CONFIG_WIN="$(winepath -w "$CONFIG")"

echo "== Run headless MT5 Strategy Tester smoke =="
set +e
xvfb-run -a timeout 420s wine "$TERMINAL" /portable /config:"$CONFIG_WIN" \
  >"$ARTIFACT_DIR/terminal-tester-process.log" 2>&1
tester_rc=$?
set -e
echo "$tester_rc" | tee "$ARTIFACT_DIR/tester-exit-code.txt"

wineserver -k >/dev/null 2>&1 || true
sleep 2

echo "== Collect tester evidence =="
find "$MT5_DIR" -maxdepth 5 -type f \( \
    -iname 'mt5_tester_smoke*' -o \
    -path '*/Tester/logs/*' -o \
    -path '*/logs/*' \
  \) -print > "$ARTIFACT_DIR/discovered-output-files.txt" || true

mkdir -p "$ARTIFACT_DIR/logs"
while IFS= read -r f; do
  [[ -f "$f" ]] || continue
  base="$(basename "$f")"
  cp "$f" "$ARTIFACT_DIR/logs/${base}" 2>/dev/null || true
done < "$ARTIFACT_DIR/discovered-output-files.txt"

REPORT="$(find "$MT5_DIR/reports" -maxdepth 2 -type f -iname 'mt5_tester_smoke*' -print -quit || true)"
if [[ -n "$REPORT" && -s "$REPORT" ]]; then
  cp "$REPORT" "$ARTIFACT_DIR/"
  echo "report=$REPORT" | tee "$ARTIFACT_DIR/result.txt"
  echo "MT5 Strategy Tester smoke PASSED."
  exit 0
fi

echo "No Strategy Tester report was produced." | tee "$ARTIFACT_DIR/failure.txt"
tail -n 250 "$ARTIFACT_DIR/terminal-tester-process.log" || true

# Surface any tester journal lines for diagnosis.
for f in "$MT5_DIR"/Tester/logs/* "$MT5_DIR"/logs/*; do
  [[ -f "$f" ]] || continue
  echo "----- $f -----"
  tail -n 120 "$f" || true
done

exit 1
