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
  const [result, setResult] = useState<ScanResult | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [stages, setStages] = useState<Record<StageKey, StageState>>(
    initialStages
  );
  const [councilOpen, setCouncilOpen] = useState(false);

  const refreshStatus = useCallback(async () => {
    setStatusBusy(true);
    try {
      const response = await api.get('/api/status');
      setBackendStatus(response.data as BackendStatus);
    } catch (error) {
      setBackendStatus({
        ready: false,
        engine: 'ASTRA Intelligence Engine',
        architecture: 'OPPORTUNITY_ENGINE_V2',
        roles: 5,
        chartPackMax: 4,
        strategyFamilies: 6,
        externalProviderDependency: false,
        issue: extractApiError(error),
      });
    } finally {
      setStatusBusy(false);
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  const releasePreviews = useCallback((items: PreparedChart[]) => {
    items.forEach(item => URL.revokeObjectURL(item.previewUrl));
  }, []);

  useEffect(() => {
    return () => releasePreviews(charts);
  }, [charts, releasePreviews]);

  const addFiles = useCallback(
    async (event: ChangeEvent<HTMLInputElement>) => {
      const selected = Array.from(event.target.files ?? []);
      event.target.value = '';
      if (!selected.length) return;

      setErrorMessage('');

      const room = Math.max(0, 4 - charts.length);
      if (room === 0) {
        setErrorMessage('The MTF chart pack is already full. Remove a chart before adding another.');
        return;
      }

      const accepted = selected.slice(0, room);
      const next: PreparedChart[] = [];

      try {
        for (const file of accepted) {
          if (!file.type.startsWith('image/')) continue;
          const dataUrl = await compressImage(file);
          next.push({
            id: crypto.randomUUID(),
            name: file.name,
            previewUrl: URL.createObjectURL(file),
            dataUrl,
            kb: approxImageKb(dataUrl),
          });
        }
      } catch (error) {
        releasePreviews(next);
        setErrorMessage(
          error instanceof Error ? error.message : 'Image preparation failed.'
        );
        return;
      }

      setCharts(current => [...current, ...next].slice(0, 4));
      setResult(null);
      setStages(initialStages());
    },
    [charts.length, releasePreviews]
  );

  const removeChart = useCallback(
    (id: string) => {
      setCharts(current => {
        const target = current.find(item => item.id === id);
        if (target) URL.revokeObjectURL(target.previewUrl);
        return current.filter(item => item.id !== id);
      });
      setResult(null);
      setErrorMessage('');
      setStages(initialStages());
    },
    []
  );

  const clearCharts = useCallback(() => {
    setCharts(current => {
      releasePreviews(current);
      return [];
    });
    setResult(null);
    setErrorMessage('');
    setStages(initialStages());
    runRef.current += 1;
  }, [releasePreviews]);

  const updateStage = useCallback(
    (key: StageKey, status: StageStatus, detail: string) => {
      setStages(current => ({
        ...current,
        [key]: { status, detail },
      }));
    },
    []
  );

  const runScan = useCallback(async () => {
    if (!charts.length || busy) return;

    const runId = runRef.current + 1;
    runRef.current = runId;
    setBusy(true);
    setResult(null);
    setErrorMessage('');
    setCouncilOpen(false);
    setStages(initialStages());

    const started = performance.now();

    try {
      updateStage(
        'prepare',
        'done',
        `${charts.length} chart${charts.length === 1 ? '' : 's'} ready`
      );
      updateStage(
        'vision',
        'running',
        charts.length > 1
          ? 'Building canonical MTF chart state'
          : 'Reading chart evidence'
      );

      const visionResponse = await api.post('/api/analyze/vision', {
        imageDataUrls: charts.map(item => item.dataUrl),
        symbolHint: symbol,
        timeframeHint: timeframe,
        session,
        tradeMode: mode,
      });
      const vision = visionResponse.data as VisionResponse;

      if (runRef.current !== runId) return;

      updateStage(
        'vision',
        'done',
        `${vision.imageCount ?? charts.length} chart${charts.length === 1 ? '' : 's'} canonicalized`
      );

      const specialistResults: SpecialistResponse[] = [];
      const failures: SpecialistFailure[] = [];

      for (const specialist of SPECIALISTS) {
        if (runRef.current !== runId) return;

        updateStage(specialist.key, 'running', specialist.label);

        try {
          const specialistResponse = await api.post('/api/analyze/specialist', {
            role: specialist.role,
            visionProof: vision.proof,
          });
          const response = specialistResponse.data as SpecialistResponse;

          if (runRef.current !== runId) return;

          specialistResults.push(response);
          updateStage(
            specialist.key,
            'done',
            response.report.stance ?? 'Completed'
          );
        } catch (error) {
          const code = extractApiError(error);
          failures.push({ role: specialist.role, code });
          updateStage(specialist.key, 'failed', friendlyApiError(code));
        }
      }

      if (runRef.current !== runId) return;

      updateStage('lead', 'running', 'Ranking conditional opportunities');

      const finalResponse = await api.post('/api/analyze/final', {
        visionProof: vision.proof,
        reports: specialistResults.map(item => ({
          role: item.role,
          proof: item.proof,
        })),
      });
      const finalResult = finalResponse.data as ScanResult;

      if (runRef.current !== runId) return;

      updateStage(
        'lead',
        'done',
        finalResult.opportunities.length
          ? `${finalResult.opportunities.length} scenario${finalResult.opportunities.length === 1 ? '' : 's'} ranked`
          : 'No valid scenario'
      );

      setResult({
        ...finalResult,
        pipelineMs: Math.round(performance.now() - started),
      });
    } catch (error) {
      if (runRef.current !== runId) return;
      const code = extractApiError(error);
      setErrorMessage(friendlyApiError(code));
      setStages(current => {
        const next = { ...current };
        for (const key of Object.keys(next) as StageKey[]) {
          if (next[key].status === 'running') {
            next[key] = { status: 'failed', detail: friendlyApiError(code) };
          }
        }
        return next;
      });
    } finally {
      if (runRef.current === runId) setBusy(false);
    }
  }, [busy, charts, mode, session, symbol, timeframe, updateStage]);

  const totalChartKb = useMemo(
    () => charts.reduce((sum, chart) => sum + chart.kb, 0),
    [charts]
  );

  const completedRoles = result?.rolesCompleted?.length ?? 0;

  return (
    <main className='scanner-shell'>
      <header className='topbar'>
        <div className='brand-block'>
          <div className='brand-mark'>AΩ</div>
          <div>
            <div className='brand-line'>
              <strong>AUREON Ω</strong>
              <span>NEURAL SCANNER</span>
            </div>
            <small>5-ROLE COUNCIL • OPPORTUNITY ENGINE V2</small>
          </div>
        </div>

        <div className='status-cluster'>
          <div
            className={`status-chip ${backendStatus?.ready ? 'online' : 'offline'}`}
          >
            {backendStatus?.ready ? <Wifi size={14} /> : <AlertTriangle size={14} />}
            {backendStatus?.ready ? 'NATIVE AI READY' : 'AI UNAVAILABLE'}
          </div>
          <button
            className='icon-button'
            onClick={() => void refreshStatus()}
            disabled={statusBusy}
            title='Refresh scanner status'
          >
            <RefreshCw className={statusBusy ? 'spin' : ''} size={16} />
          </button>
        </div>
      </header>

      <section className='scanner-card upload-card'>
        <div className='section-heading'>
          <div>
            <span className='kicker'>MTF CHART PACK</span>
            <h1>Upload 1–4 market charts</h1>
          </div>
          <span className='count-badge'>{charts.length}/4</span>
        </div>

        <p className='section-copy'>
          One chart works. For stronger execution authority, add higher context
          plus lower execution timeframes — for example H4, H1, M15 and M5.
        </p>

        <div className='chart-pack-grid'>
          {charts.map((chart, index) => (
            <div className='chart-tile' key={chart.id}>
              <img src={chart.previewUrl} alt={chart.name} />
              <div className='chart-tile-overlay'>
                <div>
                  <strong>Chart {index + 1}</strong>
                  <span>{chart.name}</span>
                  <small>{chart.kb} KB</small>
                </div>
                <button onClick={() => removeChart(chart.id)} aria-label='Remove chart'>
                  <X size={16} />
                </button>
              </div>
            </div>
          ))}

          {charts.length < 4 && (
            <label className='chart-add-tile'>
              {charts.length ? <Plus size={28} /> : <UploadCloud size={32} />}
              <strong>{charts.length ? 'ADD TIMEFRAME' : 'SELECT CHARTS'}</strong>
              <span>
                {charts.length
                  ? `${4 - charts.length} slot${4 - charts.length === 1 ? '' : 's'} left`
                  : 'PNG · JPG · WEBP'}
              </span>
              <input
                type='file'
                accept='image/png,image/jpeg,image/webp'
                multiple
                onChange={addFiles}
              />
            </label>
          )}
        </div>

        {charts.length > 0 && (
          <div className='pack-note'>
            <Layers3 size={17} />
            <span>
              AUREON Ω will identify each visible timeframe independently and
              build one canonical MTF state.
            </span>
            <small>{totalChartKb} KB prepared</small>
          </div>
        )}
      </section>

      <section className='scanner-card control-card'>
        <div className='section-heading compact'>
          <div>
            <span className='kicker'>ANALYSIS CONTEXT</span>
            <h2>Optional chart hints</h2>
          </div>
          <Sparkles size={21} />
        </div>

        <p className='context-warning'>
          AUTO remains preferred. Manual symbol/timeframe hints are treated as
          USER_SUPPLIED evidence and never as visual observations.
        </p>

        <div className='control-grid'>
          <label>
            <span>SYMBOL</span>
            <select value={symbol} onChange={event => setSymbol(event.target.value)}>
              {SYMBOLS.map(value => <option key={value}>{value}</option>)}
            </select>
          </label>
          <label>
            <span>PRIMARY TIMEFRAME HINT</span>
            <select value={timeframe} onChange={event => setTimeframe(event.target.value)}>
              {TIMEFRAMES.map(value => <option key={value}>{value}</option>)}
            </select>
          </label>
          <label>
            <span>TRADING SESSION</span>
            <select value={session} onChange={event => setSession(event.target.value)}>
              {SESSIONS.map(value => <option key={value}>{value}</option>)}
            </select>
          </label>
          <label>
            <span>TRADE MODE</span>
            <select value={mode} onChange={event => setMode(event.target.value)}>
              {MODES.map(value => <option key={value}>{value}</option>)}
            </select>
          </label>
        </div>
      </section>

      <button
        className='scan-button'
        disabled={!charts.length || busy || backendStatus?.ready === false}
        onClick={() => void runScan()}
      >
        {busy ? (
          <>
            <LoaderCircle className='spin' size={20} />
            RUNNING AUREON Ω...
          </>
        ) : (
          <>
            <Radar size={20} />
            SCAN OPPORTUNITIES
          </>
        )}
      </button>

      {backendStatus?.ready === false && (
        <section className='scanner-card warning-card'>
          <AlertTriangle size={23} />
          <div>
            <strong>Scanner is not ready</strong>
            <span>
              {backendStatus.issue ??
                'The native AI route is currently unavailable. No fallback trade signal will be fabricated.'}
            </span>
          </div>
        </section>
      )}

      {(busy || Object.values(stages).some(stage => stage.status !== 'idle')) && (
        <section className='scanner-card pipeline-card'>
          <div className='section-heading compact'>
            <div>
              <span className='kicker'>LIVE PIPELINE</span>
              <h2>Native analysis council</h2>
            </div>
            <BrainCircuit size={21} />
          </div>

          <div className='pipeline-list'>
            {(Object.entries(stages) as Array<[StageKey, StageState]>).map(
              ([key, stage]) => (
                <div className={`pipeline-row ${stage.status}`} key={key}>
                  <div className='pipeline-icon'>{stageIcon(stage.status)}</div>
                  <div>
                    <strong>{normalizeLabel(key).toUpperCase()}</strong>
                    <span>{stage.detail}</span>
                  </div>
                </div>
              )
            )}
          </div>
        </section>
      )}

      {errorMessage && (
        <section className='scanner-card error-card'>
          <XCircle size={24} />
          <div>
            <strong>SCAN FAILED SAFELY</strong>
            <span>{errorMessage}</span>
          </div>
        </section>
      )}

      {result && (
        <section className='result-stack'>
          <article className={`scanner-card verdict-card ${result.decision.toLowerCase()}`}>
            <div className='verdict-topline'>
              <div>
                <span className='kicker'>AUREON VERDICT</span>
                <h2>{normalizeLabel(result.decision)}</h2>
              </div>
              <div className='score-orb'>
                <strong>{result.readinessScore}</strong>
                <span>READINESS</span>
              </div>
            </div>

            <div className='authority-grid'>
              <div>
                <span>SYMBOL</span>
                <strong>{String(result.symbol.value ?? 'UNKNOWN')}</strong>
                <em className={authorityTone(result.symbol.authority)}>
                  {result.symbol.authority}
                </em>
              </div>
              <div>
                <span>TIMEFRAME</span>
                <strong>{String(result.timeframe.value ?? 'UNKNOWN')}</strong>
                <em className={authorityTone(result.timeframe.authority)}>
                  {result.timeframe.authority}
                </em>
              </div>
              <div>
                <span>PRICE</span>
                <strong>{String(result.currentPrice.value ?? 'UNKNOWN')}</strong>
                <em className={authorityTone(result.currentPrice.authority)}>
                  {result.currentPrice.authority}
                </em>
              </div>
              <div>
                <span>CHARTS</span>
                <strong>{result.chartCount}</strong>
                <em>{result.imageQuality}</em>
              </div>
            </div>

            <div className='engine-strip'>
              <span>
                <Clock3 size={14} />
                {result.pipelineMs ? `${(result.pipelineMs / 1000).toFixed(1)}s pipeline` : 'pipeline complete'}
              </span>
              <span>{result.architecture}</span>
              <span>{result.degraded ? 'DEGRADED COUNCIL' : 'FULL COUNCIL'}</span>
            </div>
          </article>

          <article className='scanner-card radar-card'>
            <div className='section-heading compact'>
              <div>
                <span className='kicker'>OPPORTUNITY RADAR</span>
                <h2>
                  {result.opportunities.length
                    ? `${result.opportunities.length} ranked scenario${result.opportunities.length === 1 ? '' : 's'}`
                    : 'No valid scenario'}
                </h2>
              </div>
              <Radar size={22} />
            </div>

            <div className='strategy-strip'>
              {result.strategyCoverage.map(strategy => (
                <span key={strategy}>{normalizeLabel(strategy)}</span>
              ))}
            </div>

            {!result.opportunities.length ? (
              <div className='radar-empty'>
                <Gauge size={26} />
                <div>
                  <strong>WAIT</strong>
                  <span>
                    No scenario met the deterministic readiness gate. Better to
                    wait than manufacture a trade.
                  </span>
                </div>
              </div>
            ) : (
              <div className='opportunity-list'>
                {result.opportunities.map((opportunity, index) => (
                  <div
                    className={`opportunity-card ${opportunity.direction.toLowerCase()} ${
                      index === 0 ? 'top-ranked' : ''
                    }`}
                    key={`${opportunity.setupType}-${index}`}
                  >
                    <div className='opportunity-top'>
                      <div className='opportunity-title'>
                        <div className='direction-icon'>
                          {directionIcon(opportunity.direction)}
                        </div>
                        <div>
                          <span>
                            #{index + 1} · {opportunity.status}
                          </span>
                          <strong>
                            {opportunity.direction} · {normalizeLabel(opportunity.setupType)}
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
