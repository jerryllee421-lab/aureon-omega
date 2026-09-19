import {
  ChangeEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BrainCircuit,
  Check,
  CheckCircle2,
  ChevronDown,
  Circle,
  Clock3,
  Crosshair,
  Gauge,
  Image as ImageIcon,
  Layers3,
  LoaderCircle,
  Plus,
  Radar,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Target,
  UploadCloud,
  Wifi,
  X,
  XCircle,
} from 'lucide-react';
import { api } from './api';

type Authority = 'OBSERVED' | 'USER_SUPPLIED' | 'INFERRED' | 'UNKNOWN';

type AuthorityField = {
  value: string | number | null;
  authority: Authority;
};

type SpecialistRole =
  | 'STRUCTURE ANALYST'
  | 'OPPORTUNITY ANALYST'
  | 'RISK CRITIC';

type CouncilMember = {
  role: string;
  model: string;
  stance: string;
  summary: string;
  latencyMs?: number | null;
};

type Opportunity = {
  direction: 'BUY' | 'SELL' | 'NEUTRAL';
  status: string;
  setupType: string;
  timeframe: string;
  thesis: string;
  trigger: string | null;
  entryZone: string | null;
  stopLoss: string | null;
  tp1: string | null;
  tp2: string | null;
  tp3: string | null;
  rr1: string | null;
  rr2: string | null;
  rr3: string | null;
  invalidation: string | null;
  nextRequiredEvent: string | null;
  evidence: string[];
  contradictions: string[];
  gates: {
    structure: string;
    trigger: string;
    invalidation: string;
    target: string;
    mtf: string;
    contradiction: string;
  };
  readinessScore: number;
  executable: boolean;
};

type ScanResult = {
  scanId: string;
  generatedAt: string;
  architecture: string;
  reasoningEffort: string;
  leadModel: string;
  chartCount: number;
  strategyCoverage: string[];
  imageQuality: string;
  symbol: AuthorityField;
  timeframe: AuthorityField;
  currentPrice: AuthorityField;
  decision: string;
  setupState: string;
  readinessScore: number;
  degraded: boolean;
  market: {
    bias: string;
    structure: string;
    volatility: string;
    momentum: string;
    mtfAlignment: string;
  };
  qualityGates: {
    imageAuthority: string;
    structureQuality: string;
    liquidityEvidence: string;
    entryQuality: string;
    invalidationQuality: string;
    riskRewardQuality: string;
  };
  tradePlan: {
    direction: string | null;
    entryZone: string | null;
    stopLoss: string | null;
    tp1: string | null;
    tp2: string | null;
    tp3: string | null;
    rr1: string | null;
    rr2: string | null;
    rr3: string | null;
    trigger: string | null;
    invalidation: string | null;
    setupType: string | null;
  };
  opportunities: Opportunity[];
  nextRequiredEvent: string | null;
  nextBestInput: string | null;
  evidence: string[];
  contradictions: string[];
  limitations: string[];
  council: CouncilMember[];
  rolesCompleted: string[];
  leadLatencyMs?: number;
  pipelineMs?: number;
};

type BackendStatus = {
  ready: boolean;
  engine: string;
  architecture: string;
  roles: number;
  chartPackMax: number;
  strategyFamilies: number;
  externalProviderDependency: boolean;
  issue: string | null;
};

type VisionResponse = {
  proof: string;
  role: 'VISION ANALYST';
  model: string;
  canonical: Record<string, unknown>;
  report: Record<string, unknown>;
  attempts?: number;
  latencyMs?: number;
  imageCount?: number;
  imageBytes?: number;
};

type SpecialistResponse = {
  proof: string;
  role: SpecialistRole;
  model: string;
  report: {
    stance?: string;
    summary?: string;
    evidence?: string[];
    contradictions?: string[];
    unknown?: string[];
    candidateSetups?: string[];
    nextRequiredEvent?: string;
  };
  attempts?: number;
  latencyMs?: number;
};

type SpecialistFailure = {
  role: SpecialistRole;
  code: string;
};

type PreparedChart = {
  id: string;
  name: string;
  previewUrl: string;
  dataUrl: string;
  kb: number;
};

type StageKey =
  | 'prepare'
  | 'vision'
  | 'structure'
  | 'opportunity'
  | 'risk'
  | 'lead';

type StageStatus = 'idle' | 'running' | 'done' | 'failed';

type StageState = {
  status: StageStatus;
  detail: string;
};

const SYMBOLS = [
  'AUTO',
  'XAUUSD',
  'BTCUSD',
  'BTCUSDT',
  'EURUSD',
  'GBPUSD',
  'USDJPY',
  'GBPJPY',
];
const TIMEFRAMES = ['AUTO', 'M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];
const SESSIONS = ['AUTO', 'ASIA', 'LONDON OPEN', 'NY OPEN', 'NY LUNCH'];
const MODES = ['SCALPING', 'DAY TRADE', 'SWING TRADE'];

const SPECIALISTS: Array<{
  key: 'structure' | 'opportunity' | 'risk';
  role: SpecialistRole;
  label: string;
}> = [
  {
    key: 'structure',
    role: 'STRUCTURE ANALYST',
    label: 'MTF structure',
  },
  {
    key: 'opportunity',
    role: 'OPPORTUNITY ANALYST',
    label: 'Six-strategy opportunity sweep',
  },
  {
    key: 'risk',
    role: 'RISK CRITIC',
    label: 'Risk + adversarial challenge',
  },
];

function initialStages(): Record<StageKey, StageState> {
  return {
    prepare: { status: 'idle', detail: 'No chart pack prepared' },
    vision: { status: 'idle', detail: 'Waiting' },
    structure: { status: 'idle', detail: 'Waiting' },
    opportunity: { status: 'idle', detail: 'Waiting' },
    risk: { status: 'idle', detail: 'Waiting' },
    lead: { status: 'idle', detail: 'Waiting' },
  };
}

function normalizeLabel(value: string) {
  return value.replaceAll('_', ' ');
}

function authorityTone(authority: Authority) {
  if (authority === 'OBSERVED' || authority === 'USER_SUPPLIED') return 'good';
  if (authority === 'INFERRED') return 'warn';
  return 'muted';
}

function stageIcon(status: StageStatus) {
  if (status === 'done') return <Check size={15} />;
  if (status === 'failed') return <XCircle size={15} />;
  if (status === 'running')
    return <LoaderCircle className='stage-spinner' size={15} />;
  return <Circle size={11} />;
}

function extractApiError(error: unknown) {
  const candidate = error as {
    message?: unknown;
    response?: {
      data?: unknown;
    };
  };

  const data = candidate?.response?.data;
  if (typeof data === 'string') return data;

  if (data && typeof data === 'object') {
    const value = (data as Record<string, unknown>).error;
    if (typeof value === 'string') return value;
  }

  return typeof candidate?.message === 'string'
    ? candidate.message
    : 'SCANNER_REQUEST_FAILED';
}

function friendlyApiError(code: string, stage?: string) {
  const context = stage ? stage + ': ' : '';

  if (code.includes('ASTRA_AI_RATE_LIMITED'))
    return context + 'The ASTRA AI service is temporarily busy. Retry shortly.';
  if (code.includes('ASTRA_AI_IMAGE_TOO_LARGE'))
    return context + 'The chart pack exceeded the AI payload limit. Remove one image or use cleaner screenshots.';
  if (code.includes('ASTRA_AI_REQUEST_REJECTED'))
    return context + 'The ASTRA AI service rejected this request.';
  if (code.includes('ASTRA_AI_TEMPORARILY_UNAVAILABLE'))
    return context + 'The ASTRA AI service is temporarily unavailable.';
  if (code.includes('VALID_IMAGE_DATA_REQUIRED'))
    return context + 'A valid chart image is required.';
  if (
    code.toLowerCase().includes('network error') ||
    code.toLowerCase().includes('failed to fetch')
  )
    return context + 'The app connection dropped before this stage completed.';
  if (
    code.includes('status code 502') ||
    code.includes('status code 503') ||
    code.includes('status code 504')
  )
    return context + 'The ASTRA AI route did not complete. No trade result was fabricated.';

  return context + code;
}

function compressImage(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onerror = () => reject(new Error('Could not read image.'));
    reader.onload = () => {
      const img = new Image();

      img.onerror = () => reject(new Error('Could not decode image.'));
      img.onload = () => {
        const maxSide = 1280;
        const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
        const width = Math.max(1, Math.round(img.width * scale));
        const height = Math.max(1, Math.round(img.height * scale));
        const canvas = document.createElement('canvas');

        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        if (!ctx) {
          reject(new Error('Image processing is unavailable.'));
          return;
        }

        ctx.drawImage(img, 0, 0, width, height);
        resolve(canvas.toDataURL('image/jpeg', 0.8));
      };

      img.src = String(reader.result);
    };

    reader.readAsDataURL(file);
  });
}

function approxImageKb(dataUrl: string) {
  const base64 = dataUrl.split(',')[1] ?? '';
  return Math.round(((base64.length * 3) / 4) / 1024);
}

function directionIcon(direction: string) {
  if (direction === 'BUY') return <ArrowUpRight size={18} />;
  if (direction === 'SELL') return <ArrowDownRight size={18} />;
  return <Radar size={18} />;
}

function App() {
  const runRef = useRef(0);
  const [backendStatus, setBackendStatus] = useState<BackendStatus | null>(null);
  const [statusBusy, setStatusBusy] = useState(false);
  const [charts, setCharts] = useState<PreparedChart[]>([]);
  const [symbol, setSymbol] = useState('AUTO');
  const [timeframe, setTimeframe] = useState('AUTO');
  const [session, setSession] = useState('AUTO');
  const [mode, setMode] = useState('DAY TRADE');
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult] = useState<ScanResult | null>(null);
  const [councilOpen, setCouncilOpen] = useState(false);
  const [stages, setStages] = useState(initialStages());

  const refreshStatus = useCallback(async () => {
    setStatusBusy(true);
    try {
      const response = await api.get('/api/status');
      setBackendStatus(response.data as BackendStatus);
    } catch {
      setBackendStatus({
        ready: false,
        engine: 'ASTRA',
        architecture: 'MTF_CANONICAL_OPPORTUNITY_ENGINE',
        roles: 5,
        chartPackMax: 4,
        strategyFamilies: 6,
        externalProviderDependency: true,
        issue: 'STATUS_UNAVAILABLE',
      });
    } finally {
      setStatusBusy(false);
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  const canAnalyze =
    charts.length > 0 && !busy && backendStatus?.ready === true;

  const readinessTone = useMemo(() => {
    if (!result) return 'neutral';
    if (result.readinessScore >= 80) return 'good';
    if (result.readinessScore >= 55) return 'warn';
    return 'neutral';
  }, [result]);

  function updateStage(
    key: StageKey,
    patch: Partial<StageState>
  ) {
    setStages(previous => ({
      ...previous,
      [key]: {
        ...previous[key],
        ...patch,
      },
    }));
  }

  async function handleFiles(event: ChangeEvent<HTMLInputElement>) {
    const incoming = Array.from(event.target.files ?? []).slice(
      0,
      Math.max(0, 4 - charts.length)
    );
    event.target.value = '';

    if (incoming.length === 0) return;

    const invalid = incoming.find(file => !file.type.startsWith('image/'));
    if (invalid) {
      setErrorMessage('Every chart must be an image file.');
      return;
    }

    const oversized = incoming.find(file => file.size > 10 * 1024 * 1024);
    if (oversized) {
      setErrorMessage('Each source image must be 10 MB or smaller.');
      return;
    }

    setErrorMessage('');
    setResult(null);
    setStages(initialStages());

    try {
      const prepared = await Promise.all(
        incoming.map(async file => {
          const dataUrl = await compressImage(file);
          return {
            id:
              Date.now().toString(36) +
              '-' +
              Math.random().toString(36).slice(2, 9),
            name: file.name,
            previewUrl: URL.createObjectURL(file),
            dataUrl,
            kb: approxImageKb(dataUrl),
          } satisfies PreparedChart;
        })
      );

      if ([...charts, ...prepared].reduce((sum, c) => sum + c.kb, 0) > 2600) {
        prepared.forEach(c => URL.revokeObjectURL(c.previewUrl));
        throw new Error('Chart pack exceeds 2.6 MB. Use fewer or smaller screenshots.');
      }
      setCharts(previous => [...previous, ...prepared].slice(0, 4));
    } catch (caught) {
      setErrorMessage(
        caught instanceof Error
          ? caught.message
          : 'Chart optimization failed.'
      );
    }
  }

  function removeChart(id: string) {
    runRef.current += 1;
    setCharts(previous => {
      const target = previous.find(item => item.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return previous.filter(item => item.id !== id);
    });
    setResult(null);
    setErrorMessage('');
    setStages(initialStages());
  }

  function clearCharts() {
    runRef.current += 1;
    charts.forEach(chart => URL.revokeObjectURL(chart.previewUrl));
    setCharts([]);
    setResult(null);
    setErrorMessage('');
    setBusy(false);
    setStages(initialStages());
  }

  async function analyze() {
    if (!canAnalyze) return;

    const currentRun = runRef.current + 1;
    runRef.current = currentRun;
    const pipelineStarted = performance.now();
    let activePhase: StageKey = 'prepare';

    setBusy(true);
    setResult(null);
    setErrorMessage('');
    setStages(initialStages());

    const totalKb = charts.reduce((sum, chart) => sum + chart.kb, 0);
    updateStage('prepare', {
      status: 'done',
      detail:
        charts.length +
        ' chart' +
        (charts.length === 1 ? '' : 's') +
        ' · ' +
        totalKb +
        ' KB prepared locally',
    });

    const hints = {
      symbolHint: symbol === 'AUTO' ? null : symbol,
      timeframeHint: timeframe === 'AUTO' ? null : timeframe,
      session: session === 'AUTO' ? null : session,
      tradeMode: mode,
    };

    try {
      activePhase = 'vision';
      updateStage('vision', {
        status: 'running',
        detail:
          charts.length > 1
            ? 'Canonicalizing multi-timeframe chart pack'
            : 'Canonicalizing chart',
      });

      const visionResponse = await api.post('/api/analyze/vision', {
        imageDataUrls: charts.map(chart => chart.dataUrl),
        ...hints,
      });

      if (runRef.current !== currentRun) return;

      const vision = visionResponse.data as VisionResponse;
      updateStage('vision', {
        status: 'done',
        detail:
          vision.model +
          (vision.latencyMs
            ? ' · ' + (vision.latencyMs / 1000).toFixed(1) + 's'
            : ''),
      });

      const specialistTasks = SPECIALISTS.map(async specialist => {
        updateStage(specialist.key, {
          status: 'running',
          detail: specialist.label,
        });

        try {
          const response = await api.post('/api/analyze/specialist', {
            canonical: vision.canonical,
            visionProof: vision.proof,
            role: specialist.role,
            ...hints,
          });

          const data = response.data as SpecialistResponse;
          updateStage(specialist.key, {
            status: 'done',
            detail:
              data.model +
              (data.latencyMs
                ? ' · ' + (data.latencyMs / 1000).toFixed(1) + 's'
                : ''),
          });

          return {
            ok: true as const,
            data,
          };
        } catch (caught) {
          const code = extractApiError(caught);
          updateStage(specialist.key, {
            status: 'failed',
            detail: friendlyApiError(code),
          });

          return {
            ok: false as const,
            failure: {
              role: specialist.role,
              code,
            } satisfies SpecialistFailure,
          };
        }
      });

      const specialistResults = await Promise.all(specialistTasks);
      if (runRef.current !== currentRun) return;

      const reports = specialistResults.flatMap(item =>
        item.ok ? [item.data] : []
      );
      const failures = specialistResults.flatMap(item =>
        item.ok ? [] : [item.failure]
      );

      activePhase = 'lead';
      updateStage('lead', {
        status: 'running',
        detail: 'Opportunity matrix + deterministic readiness gates',
      });

      const finalResponse = await api.post('/api/analyze/final', {
        canonical: vision.canonical,
        visionProof: vision.proof,
        vision: vision.report,
        reports,
        failures,
        ...hints,
      });

      if (runRef.current !== currentRun) return;

      const finalResult = finalResponse.data as ScanResult;
      finalResult.pipelineMs = Math.round(
        performance.now() - pipelineStarted
      );

      setResult(finalResult);
      updateStage('lead', {
        status: 'done',
        detail:
          finalResult.leadModel +
          (finalResult.leadLatencyMs
            ? ' · ' + (finalResult.leadLatencyMs / 1000).toFixed(1) + 's'
            : ''),
      });
    } catch (caught) {
      if (runRef.current !== currentRun) return;

      const code = extractApiError(caught);
      updateStage(activePhase, {
        status: 'failed',
        detail: friendlyApiError(code),
      });

      setErrorMessage(
        friendlyApiError(
          code,
          activePhase === 'vision'
            ? 'Vision'
            : activePhase === 'lead'
              ? 'Final adjudication'
              : 'Scanner'
        )
      );
    } finally {
      if (runRef.current === currentRun) setBusy(false);
    }
  }

  const completedRoles = result?.rolesCompleted.length ?? 0;

  return (
    <main className='shell'>
      <section className='scanner-card hero-card'>
        <div className='brand-icon'>
          <BrainCircuit size={34} strokeWidth={1.9} />
        </div>
        <div className='brand-copy'>
          <div className='eyebrow'>AUREON Ω</div>
          <h1>MARKET INTELLIGENCE</h1>
          <p>
            5-ROLE COUNCIL <span>•</span> ASTRA INTELLIGENCE ENGINE
          </p>
        </div>
        <div className='header-status' aria-label='backend status'>
          <span
            className={
              backendStatus?.ready
                ? 'status-dot online'
                : 'status-dot'
            }
          />
        </div>
      </section>

      <section className='health-strip'>
        <div>
          <span
            className={
              backendStatus?.ready
                ? 'health-light ready'
                : 'health-light'
            }
          />
          <strong>
            {backendStatus === null
              ? 'CHECKING OPPORTUNITY ENGINE'
              : backendStatus.ready
                ? 'ASTRA CONFIGURED'
                : 'AI ENGINE DEGRADED'}
          </strong>
          <small>
            {backendStatus?.ready
              ? '5 roles · 6 strategy families · up to 4 chart timeframes'
              : backendStatus?.issue ?? 'Checking ASTRA AI backend'}
          </small>
        </div>
        <button
          className='icon-button'
          onClick={() => void refreshStatus()}
          disabled={statusBusy}
          aria-label='Recheck AI engine'
        >
          <RefreshCw
            size={17}
            className={statusBusy ? 'stage-spinner' : ''}
          />
        </button>
      </section>

      {backendStatus !== null && !backendStatus.ready && (
        <section className='setup-banner'>
          <ShieldCheck size={20} />
          <div>
            <strong>Opportunity engine unavailable</strong>
            <span>
              AUREON Ω remains fail-closed until the ASTRA AI route is available.
            </span>
          </div>
        </section>
      )}

      <section className='scanner-card upload-panel'>
        <div className='section-heading'>
          <div>
            <span className='kicker'>MTF CHART PACK</span>
            <h2>Upload 1–4 market charts</h2>
          </div>
          <div className='chart-count'>{charts.length}/4</div>
        </div>

        <p className='helper'>
          One chart works. For stronger chart context, add higher context
          plus lower execution timeframes — for example H4, H1, M15 and M5.
        </p>

        {charts.length === 0 ? (
          <label className='drop-zone'>
            <input
              type='file'
              accept='image/*'
              multiple
              onChange={handleFiles}
            />
            <div className='upload-orb'>
              <UploadCloud size={28} />
            </div>
            <strong>SELECT CHART SCREENSHOTS</strong>
            <span>MT4 · MT5 · TradingView · Broker charts</span>
            <small>
              Up to four images · optimized locally before one vision pass
            </small>
          </label>
        ) : (
          <>
            <div className='preview-grid'>
              {charts.map((chart, index) => (
                <div className='preview-tile' key={chart.id}>
                  <img src={chart.previewUrl} alt={'Chart ' + (index + 1)} />
                  <span className='preview-index'>#{index + 1}</span>
                  <button
                    className='tile-remove'
                    onClick={() => removeChart(chart.id)}
                    disabled={busy}
                    aria-label={'Remove ' + chart.name}
                  >
                    <X size={15} />
                  </button>
                  <div className='tile-meta'>
                    <strong>{chart.name}</strong>
                    <span>{chart.kb} KB</span>
                  </div>
                </div>
              ))}

              {charts.length < 4 && (
                <label className='add-chart-tile'>
                  <input
                    type='file'
                    accept='image/*'
                    multiple
                    onChange={handleFiles}
                  />
                  <Plus size={24} />
                  <strong>ADD TIMEFRAME</strong>
                  <span>{4 - charts.length} slot(s) left</span>
                </label>
              )}
            </div>
            <div className='chart-pack-note'>
              <ImageIcon size={16} />
              <span>
                AUREON Ω will identify each visible timeframe independently
                and build one canonical MTF state.
              </span>
            </div>
          </>
        )}
      </section>

      <section className='scanner-card controls-panel'>
        <div className='section-heading compact'>
          <div>
            <span className='kicker'>ANALYSIS CONTEXT</span>
            <h2>Optional chart hints</h2>
          </div>
          <Layers3 size={21} />
        </div>

        <p className='helper'>
          AUTO remains preferred. Manual symbol/timeframe hints are treated as
          USER_SUPPLIED evidence and never as visual observations.
        </p>

        <div className='control-grid'>
          <label>
            <span>SYMBOL</span>
            <select
              value={symbol}
              onChange={event => setSymbol(event.target.value)}
              disabled={busy}
            >
              {SYMBOLS.map(item => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
          <label>
            <span>PRIMARY TIMEFRAME HINT</span>
            <select
              value={timeframe}
              onChange={event => setTimeframe(event.target.value)}
              disabled={busy}
            >
              {TIMEFRAMES.map(item => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
        </div>

        <div className='chip-label'>TRADING SESSION</div>
        <div className='chip-row'>
          {SESSIONS.map(item => (
            <button
              key={item}
              className={session === item ? 'chip active' : 'chip'}
              onClick={() => setSession(item)}
              disabled={busy}
            >
              {item}
            </button>
          ))}
        </div>

        <div className='chip-label'>TRADING MODE</div>
        <div className='chip-row three'>
          {MODES.map(item => (
            <button
              key={item}
              className={mode === item ? 'chip active' : 'chip'}
              onClick={() => setMode(item)}
              disabled={busy}
            >
              {item}
            </button>
          ))}
        </div>
      </section>

      <section className='scanner-card strategy-panel'>
        <div className='section-heading compact'>
          <div>
            <span className='kicker'>OPPORTUNITY COVERAGE</span>
            <h2>Six strategy families</h2>
          </div>
          <Radar size={21} />
        </div>
        <div className='strategy-chips'>
          {[
            'Trend continuation',
            'Liquidity sweep reversal',
            'Breakout retest',
            'Range extreme reversal',
            'MSS + FVG retrace',
            'S/R rejection',
          ].map(item => (
            <span key={item}>{item}</span>
          ))}
        </div>
      </section>

      <button
        className='analyze-button'
        disabled={!canAnalyze}
        onClick={() => void analyze()}
      >
        {busy ? (
          <>
            <LoaderCircle className='stage-spinner' size={24} />
            SCANNING OPPORTUNITIES
          </>
        ) : (
          <>
            <Sparkles size={24} />
            SCAN OPPORTUNITIES
          </>
        )}
      </button>

      <div className='execution-note'>
        <ShieldCheck size={16} />
        <span>
          More opportunities, not lower standards. No automatic trade execution.
        </span>
      </div>

      {(busy || Object.values(stages).some(stage => stage.status !== 'idle')) && (
        <section className='scanner-card pipeline-card'>
          <div className='section-heading compact'>
            <div>
              <span className='kicker'>LIVE PIPELINE</span>
              <h2>Opportunity scan status</h2>
            </div>
            <Activity size={21} />
          </div>

          <div className='stage-list'>
            {[
              ['prepare', 'Chart pack preparation'],
              ['vision', 'MTF vision analyst'],
              ['structure', 'Structure analyst'],
              ['opportunity', 'Opportunity analyst'],
              ['risk', 'Risk + adversarial critic'],
              ['lead', 'Lead opportunity adjudication'],
            ].map(item => {
              const key = item[0] as StageKey;
              const stage = stages[key];

              return (
                <div
                  className={'stage-row ' + stage.status}
                  key={key}
                >
                  <div className='stage-icon'>
                    {stageIcon(stage.status)}
                  </div>
                  <div>
                    <strong>{item[1]}</strong>
                    <span>{stage.detail}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {errorMessage && (
        <section className='error-card'>
          <AlertTriangle size={20} />
          <div>
            <strong>Scanner stopped safely</strong>
            <span>{errorMessage}</span>
          </div>
        </section>
      )}

      {result && (
        <section className='results'>
          <article className='scanner-card verdict-card'>
            <div className='result-topline'>
              <span>
                {String(result.symbol.value ?? 'UNKNOWN')} ·{' '}
                {String(result.timeframe.value ?? 'UNKNOWN')}
              </span>
              <span
                className={
                  result.degraded
                    ? 'live-pill degraded'
                    : 'live-pill'
                }
              >
                <Wifi size={14} />
                {completedRoles}/5 ROLES
              </span>
            </div>

            <div className='verdict-grid'>
              <div>
                <span className='kicker'>BEST CURRENT STATE</span>
                <h2>{normalizeLabel(result.decision)}</h2>
                <p className='state-line'>
                  <Circle size={10} fill='currentColor' />
                  {normalizeLabel(result.setupState)}
                </p>
              </div>

              <div className={'score-ring ' + readinessTone}>
                <strong>{Math.round(result.readinessScore)}</strong>
                <span>READINESS</span>
              </div>
            </div>

            <div className='authority-row'>
              <div>
                <span>CHART PACK</span>
                <strong>{result.chartCount} FRAME(S)</strong>
              </div>
              <div>
                <span>CHART REFERENCE</span>
                <strong>{result.currentPrice.value ?? '—'}</strong>
                <small
                  className={authorityTone(
                    result.currentPrice.authority
                  )}
                >
                  {result.currentPrice.authority}
                </small>
              </div>
            </div>

            <div className='runtime-row'>
              <span>
                <Clock3 size={14} />
                {result.pipelineMs
                  ? (result.pipelineMs / 1000).toFixed(1) + 's pipeline'
                  : 'Pipeline complete'}
              </span>
              <span>{result.reasoningEffort} REASONING</span>
            </div>
          </article>

          <article className='scanner-card radar-card'>
            <div className='section-heading compact'>
              <div>
                <span className='kicker'>OPPORTUNITY RADAR</span>
                <h2>
                  {result.opportunities.length} conditional setup
                  {result.opportunities.length === 1 ? '' : 's'}
                </h2>
              </div>
              <Radar size={22} />
            </div>

            {result.opportunities.length === 0 ? (
              <div className='wait-box'>
                <Radar size={24} />
                <div>
                  <strong>NO QUALIFIED SCENARIO</strong>
                  <span>
                    The supplied chart pack did not support a traceable conditional setup.
                  </span>
                </div>
              </div>
            ) : (
              <div className='opportunity-list'>
                {result.opportunities.map((opportunity, index) => (
                  <div
                    className={
                      'opportunity-card ' +
                      opportunity.direction.toLowerCase()
                    }
                    key={
                      opportunity.setupType +
                      opportunity.direction +
                      index
                    }
                  >
                    <div className='opportunity-head'>
                      <div className='opportunity-direction'>
                        {directionIcon(opportunity.direction)}
                        <div>
                          <span>#{index + 1} · {opportunity.status}</span>
                          <strong>
                            {opportunity.direction} ·{' '}
                            {normalizeLabel(opportunity.setupType)}
                          </strong>
                        </div>
                      </div>
                      <div className='mini-score'>
                        <strong>{opportunity.readinessScore}</strong>
                        <span>READY</span>
                      </div>
                    </div>

                    <p className='opportunity-thesis'>
                      {opportunity.thesis}
                    </p>

                    <div className='opportunity-meta'>
                      <div>
                        <span>TIMEFRAME</span>
                        <strong>{opportunity.timeframe}</strong>
                      </div>
                      <div>
                        <span>ENTRY</span>
                        <strong>{opportunity.entryZone ?? 'PENDING'}</strong>
                      </div>
                      <div>
                        <span>STOP</span>
                        <strong>{opportunity.stopLoss ?? 'PENDING'}</strong>
                      </div>
                      <div>
                        <span>TP1</span>
                        <strong>{opportunity.tp1 ?? 'PENDING'}</strong>
                      </div>
                    </div>

                    <div className='opportunity-trigger'>
                      <span>TRIGGER</span>
                      <strong>
                        {opportunity.trigger ??
                          opportunity.nextRequiredEvent ??
                          'Await confirmation'}
                      </strong>
                    </div>

                    <div className='opportunity-invalidation'>
                      <span>INVALIDATION</span>
                      <strong>
                        {opportunity.invalidation ?? 'Not yet traceable'}
                      </strong>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </article>

          {result.nextBestInput && (
            <article className='scanner-card input-request'>
              <div>
                <span className='kicker'>NEXT BEST INPUT</span>
                <h2>Improve chart evidence</h2>
              </div>
              <p>{result.nextBestInput}</p>
            </article>
          )}

          <article className='scanner-card market-card'>
            <div className='section-heading compact'>
              <div>
                <span className='kicker'>MARKET MODEL</span>
                <h2>Multi-timeframe context</h2>
              </div>
              <Activity size={21} />
            </div>

            <div className='metric-grid'>
              <div><span>BIAS</span><strong>{result.market.bias}</strong></div>
              <div><span>STRUCTURE</span><strong>{result.market.structure}</strong></div>
              <div><span>MTF ALIGNMENT</span><strong>{result.market.mtfAlignment}</strong></div>
              <div><span>MOMENTUM</span><strong>{result.market.momentum}</strong></div>
            </div>
          </article>

          <article className='scanner-card gates-card'>
            <div className='section-heading compact'>
              <div>
                <span className='kicker'>QUALITY GATES</span>
                <h2>Execution authority</h2>
              </div>
              <Gauge size={21} />
            </div>

            <div className='gate-grid'>
              {Object.entries(result.qualityGates).map(entry => (
                <div className='gate-item' key={entry[0]}>
                  <span>{normalizeLabel(entry[0]).toUpperCase()}</span>
                  <strong>{String(entry[1])}</strong>
                </div>
              ))}
            </div>
          </article>

          <article className='scanner-card plan-card'>
            <div className='section-heading compact'>
              <div>
                <span className='kicker'>EXECUTION-READY PLAN</span>
                <h2>{result.tradePlan.direction ?? 'NO TRADE'}</h2>
              </div>
              <Target size={22} />
            </div>

            {result.tradePlan.direction ? (
              <>
                <div className='plan-grid'>
                  <div className='wide'>
                    <span>ENTRY ZONE</span>
                    <strong>{result.tradePlan.entryZone ?? '—'}</strong>
                  </div>
                  <div><span>STOP</span><strong>{result.tradePlan.stopLoss ?? '—'}</strong></div>
                  <div><span>TP1</span><strong>{result.tradePlan.tp1 ?? '—'}</strong><small>{result.tradePlan.rr1 ?? ''}</small></div>
                  <div><span>TP2</span><strong>{result.tradePlan.tp2 ?? '—'}</strong><small>{result.tradePlan.rr2 ?? ''}</small></div>
                  <div><span>TP3</span><strong>{result.tradePlan.tp3 ?? '—'}</strong><small>{result.tradePlan.rr3 ?? ''}</small></div>
                </div>

                <div className='condition-box'>
                  <Crosshair size={19} />
                  <div>
                    <span>TRIGGER</span>
                    <strong>{result.tradePlan.trigger ?? 'Not established'}</strong>
                  </div>
                </div>

                <div className='condition-box danger'>
                  <ShieldCheck size={19} />
                  <div>
                    <span>INVALIDATION</span>
                    <strong>{result.tradePlan.invalidation ?? 'Not established'}</strong>
                  </div>
                </div>
              </>
            ) : (
              <div className='wait-box'>
                <Gauge size={24} />
                <div>
                  <strong>NO EXECUTION YET</strong>
                  <span>
                    Opportunity Radar may still contain forming/watch scenarios.
                  </span>
                </div>
              </div>
            )}

            {result.nextRequiredEvent && (
              <div className='next-event'>
                <span>NEXT REQUIRED EVENT</span>
                <strong>{result.nextRequiredEvent}</strong>
              </div>
            )}
          </article>

          <article className='scanner-card ledger-card'>
            <div className='section-heading compact'>
              <div>
                <span className='kicker'>EVIDENCE LEDGER</span>
                <h2>Why this ranking</h2>
              </div>
              <CheckCircle2 size={21} />
            </div>

            <div className='ledger-list'>
              {result.evidence.map((item, index) => (
                <div className='ledger-item good-row' key={'e-' + index}>
                  <CheckCircle2 size={17} />
                  <span>{item}</span>
                </div>
              ))}
              {result.contradictions.map((item, index) => (
                <div className='ledger-item bad-row' key={'c-' + index}>
                  <AlertTriangle size={17} />
                  <span>{item}</span>
                </div>
              ))}
              {result.limitations.map((item, index) => (
                <div className='ledger-item muted-row' key={'l-' + index}>
                  <Circle size={10} />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </article>

          <article className='scanner-card council-card'>
            <button
              className='council-toggle'
              onClick={() => setCouncilOpen(open => !open)}
            >
              <div>
                <span className='kicker'>ANALYSIS COUNCIL</span>
                <h2>{completedRoles}/5 roles completed</h2>
              </div>
              <ChevronDown
                className={councilOpen ? 'rotate' : ''}
                size={22}
              />
            </button>

            {councilOpen && (
              <div className='council-list'>
                {result.council.map((member, index) => (
                  <div
                    className='council-member'
                    key={member.role + member.model + index}
                  >
                    <div className='member-title'>
                      <strong>{member.role}</strong>
                      <span>{member.stance}</span>
                    </div>
                    <small>{member.model}</small>
                    <p>{member.summary}</p>
                    {member.latencyMs ? (
                      <em>{(member.latencyMs / 1000).toFixed(1)}s</em>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </article>

          <button className='reset-button' onClick={clearCharts}>
            <RotateCcw size={18} />
            NEW CHART PACK
          </button>
        </section>
      )}

      {!busy && !result && !errorMessage && (
        <section className='scanner-card empty-card'>
          <BrainCircuit size={32} />
          <div>
            <span className='kicker'>OPPORTUNITY ENGINE</span>
            <h2>Scan scenarios, not just one answer.</h2>
            <p>
              AUREON Ω can now inspect up to four chart timeframes in one
              pass, test six strategy families, rank multiple conditional
              opportunities, and keep all scenarios conditional until
              live closed-candle, quote and risk checks are independently verified.
            </p>
          </div>
        </section>
      )}

      <footer>
        <span>AUREON Ω NEURAL SCANNER</span>
        <small>
          More valid opportunities · Same fail-closed execution standard
        </small>
      </footer>
    </main>
  );
}

export default App;
