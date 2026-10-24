# AUREON Ω — Local Ollama Research Integration

## Purpose
This integration uses the existing Ollama installation as an optional, local research analyst for AUREON. It is deliberately separate from the MT5 execution adapter. It has no order-placement functions, no broker credentials, no web browsing, and no ability to change EA configuration.

## Recommended baseline
- Model: `qwen2.5:3b` via Ollama; chosen as a modest local model for structured analysis on an 8 GB Windows machine. This is a starting benchmark, not a claim that it is optimal on every CPU/GPU.
- API: `http://127.0.0.1:11434`, bound to loopback only.
- Context: 2,048 tokens; one request at a time; temperature 0.1; unload after request (`keep_alive: 0`).
- Output: constrained JSON schema, archived to `reports/ollama_analysis.json` and `research/ollama/`.
- Execution: prohibited. Demo order sending remains disabled by the MT5 adapter; live order sending remains disabled.

## One-click installation
Run `AUREON_ONE_CLICK_FULL_SETUP.cmd` from Windows. It uses the configured project root, creates a project-local Python environment, installs MT5 adapter dependencies, installs the local analyst, checks the existing Ollama CLI/API, downloads `qwen2.5:3b` if absent, and runs non-trading health checks. Internet is needed for Python packages and a first-time model download. The model stays in Ollama's model store; the project reports and scripts stay under the AUREON root.

## Use
1. Start and log into the intended MT5 DEMO terminal.
2. Run `AUREON_MT5_CONTROL_CENTER.cmd` and create the relevant JSON report.
3. Run `AUREON_OLLAMA_CONTROL_CENTER.cmd`.
4. Check the Ollama API/model, then analyse a doctor, broker-intelligence, quote, or other JSON report.
5. Inspect `reports/ollama_analysis.json` and the timestamped copy in `research/ollama/`.

## Research examples
- Diagnose missing broker/symbol/quote data from `reports/mt5_doctor.json`.
- Explain what the current broker-intelligence report can and cannot establish.
- Turn a Strategy Tester report into a list of testable hypotheses. The report must be JSON for this initial integration.
- Review results only after independent calculations have established metrics such as net profit, profit factor, maximum drawdown, sample size, commission, spread and slippage.

## Safety model
- No buy/sell signal or trade authorization is emitted.
- The analyst cannot call MT5, launch Strategy Tester, submit an order, alter config, or access network research.
- AI output is untrusted and must not be used as evidence that a strategy is profitable.
- The model is not placed in the time-critical entry/exit path.
- If the local API/model is unavailable, analysis fails closed; MT5 adapter operations remain separate.
- This does not enable live trading. No passwords are stored by this integration.

## Research references
- Ollama Windows/API: https://github.com/ollama/ollama/blob/main/docs/windows.mdx
- Ollama API and structured output/tool-call documentation: https://github.com/ollama/ollama/blob/main/docs/api.md
- Ollama tool calling: https://github.com/ollama/ollama/blob/main/docs/capabilities/tool-calling.mdx
- Example MT5 + Ollama project (reviewed as an implementation reference, not adopted wholesale): https://github.com/theabrahamaudu/simmer_bot
- Example local XAUUSD research assistant (reviewed; its optional cloud keys and credential configuration are not used here): https://github.com/sensesVoid/XAUUSD-AI-Agent

Public repositories are reference material, not evidence of profitability or security. AUREON uses a smaller, bounded, research-only integration rather than importing third-party trading execution code.
