import { ai, error, json, router, configurationIssues } from './runtime.ts';

type SpecialistRole =
  | 'STRUCTURE ANALYST'
  | 'OPPORTUNITY ANALYST'
  | 'RISK CRITIC';

type AnalyzeHints = {
  symbolHint?: string | null;
  timeframeHint?: string | null;
  session?: string | null;
  tradeMode?: string | null;
};

type VisionBody = AnalyzeHints & {
  imageDataUrls?: string[];
};

type SpecialistBody = AnalyzeHints & {
  role?: SpecialistRole;
  canonical?: unknown;
};

type SpecialistEnvelope = {
  role: SpecialistRole;
  model: string;
  report: Record<string, unknown>;
  latencyMs?: number;
};

type SpecialistFailure = {
  role: SpecialistRole;
  code: string;
};

type FinalBody = AnalyzeHints & {
  canonical?: unknown;
  vision?: unknown;
  reports?: SpecialistEnvelope[];
  failures?: SpecialistFailure[];
};

const SPECIALIST_ROLES: SpecialistRole[] = [
  'STRUCTURE ANALYST',
  'OPPORTUNITY ANALYST',
  'RISK CRITIC',
];

const STRATEGY_COVERAGE = [
  'TREND_CONTINUATION',
  'LIQUIDITY_SWEEP_REVERSAL',
  'BREAKOUT_RETEST',
  'RANGE_EXTREME_REVERSAL',
  'MSS_FVG_RETRACE',
  'SUPPORT_RESISTANCE_REJECTION',
];

const CHART_SCHEMA = {
  type: 'object',
  properties: {
    imageIndex: { type: 'number' },
    imageQuality: { type: 'string' },
    symbol: { type: 'string' },
    timeframe: { type: 'string' },
    currentPrice: { type: 'string' },
    priceScaleVisible: { type: 'boolean' },
    chartPlatform: { type: 'string' },
    observations: { type: 'array', items: { type: 'string' } },
    structureHints: { type: 'array', items: { type: 'string' } },
    liquidityHints: { type: 'array', items: { type: 'string' } },
    patterns: { type: 'array', items: { type: 'string' } },
    visibleIndicators: { type: 'array', items: { type: 'string' } },
    levels: {
      type: 'object',
      properties: {
        support: { type: 'array', items: { type: 'string' } },
        resistance: { type: 'array', items: { type: 'string' } },
        swingHighs: { type: 'array', items: { type: 'string' } },
        swingLows: { type: 'array', items: { type: 'string' } },
      },
      required: ['support', 'resistance', 'swingHighs', 'swingLows'],
    },
    limitations: { type: 'array', items: { type: 'string' } },
  },
  required: [
    'imageIndex',
    'imageQuality',
    'symbol',
    'timeframe',
    'currentPrice',
    'priceScaleVisible',
    'chartPlatform',
    'observations',
    'structureHints',
    'liquidityHints',
    'patterns',
    'visibleIndicators',
    'levels',
    'limitations',
  ],
};

const VISION_SCHEMA = {
  type: 'object',
  properties: {
    symbol: { type: 'string' },
    overallImageQuality: { type: 'string' },
    charts: {
      type: 'array',
      items: CHART_SCHEMA,
    },
    mtfSummary: {
      type: 'object',
      properties: {
        highestTimeframe: { type: 'string' },
        lowestTimeframe: { type: 'string' },
        alignment: { type: 'string' },
        dominantBias: { type: 'string' },
        conflicts: { type: 'array', items: { type: 'string' } },
        missingTimeframes: { type: 'array', items: { type: 'string' } },
      },
      required: [
        'highestTimeframe',
        'lowestTimeframe',
        'alignment',
        'dominantBias',
        'conflicts',
        'missingTimeframes',
      ],
    },
    mergedLevels: {
      type: 'object',
      properties: {
        support: { type: 'array', items: { type: 'string' } },
        resistance: { type: 'array', items: { type: 'string' } },
        liquidity: { type: 'array', items: { type: 'string' } },
      },
      required: ['support', 'resistance', 'liquidity'],
    },
    limitations: { type: 'array', items: { type: 'string' } },
  },
  required: [
    'symbol',
    'overallImageQuality',
    'charts',
    'mtfSummary',
    'mergedLevels',
    'limitations',
  ],
};

const SPECIALIST_SCHEMA = {
  type: 'object',
  properties: {
    stance: { type: 'string' },
    summary: { type: 'string' },
    evidence: { type: 'array', items: { type: 'string' } },
    contradictions: { type: 'array', items: { type: 'string' } },
    unknown: { type: 'array', items: { type: 'string' } },
    candidateSetups: { type: 'array', items: { type: 'string' } },
    nextRequiredEvent: { type: 'string' },
  },
  required: [
    'stance',
    'summary',
    'evidence',
    'contradictions',
    'unknown',
    'candidateSetups',
    'nextRequiredEvent',
  ],
};

const OPPORTUNITY_SCHEMA = {
  type: 'object',
  properties: {
    direction: { type: 'string' },
    status: { type: 'string' },
    setupType: { type: 'string' },
    timeframe: { type: 'string' },
    thesis: { type: 'string' },
    trigger: { type: 'string' },
    entryZone: { type: 'string' },
    stopLoss: { type: 'string' },
    tp1: { type: 'string' },
    tp2: { type: 'string' },
    tp3: { type: 'string' },
    rr1: { type: 'string' },
    rr2: { type: 'string' },
    rr3: { type: 'string' },
    invalidation: { type: 'string' },
    nextRequiredEvent: { type: 'string' },
    evidence: { type: 'array', items: { type: 'string' } },
    contradictions: { type: 'array', items: { type: 'string' } },
    gates: {
      type: 'object',
      properties: {
        structure: { type: 'string' },
        trigger: { type: 'string' },
        invalidation: { type: 'string' },
        target: { type: 'string' },
        mtf: { type: 'string' },
        contradiction: { type: 'string' },
      },
      required: [
        'structure',
        'trigger',
        'invalidation',
        'target',
        'mtf',
        'contradiction',
      ],
    },
  },
  required: [
    'direction',
    'status',
    'setupType',
    'timeframe',
    'thesis',
    'trigger',
    'entryZone',
    'stopLoss',
    'tp1',
    'tp2',
    'tp3',
    'rr1',
    'rr2',
    'rr3',
    'invalidation',
    'nextRequiredEvent',
    'evidence',
    'contradictions',
    'gates',
  ],
};

const FINAL_SCHEMA = {
  type: 'object',
  properties: {
    imageQuality: { type: 'string' },
    symbol: { type: 'string' },
    symbolAuthority: { type: 'string' },
    timeframe: { type: 'string' },
    timeframeAuthority: { type: 'string' },
    currentPrice: { type: 'string' },
    currentPriceAuthority: { type: 'string' },
    market: {
      type: 'object',
      properties: {
        bias: { type: 'string' },
        structure: { type: 'string' },
        volatility: { type: 'string' },
        momentum: { type: 'string' },
        mtfAlignment: { type: 'string' },
      },
      required: [
        'bias',
        'structure',
        'volatility',
        'momentum',
        'mtfAlignment',
      ],
    },
    qualityGates: {
      type: 'object',
      properties: {
        imageAuthority: { type: 'string' },
        structureQuality: { type: 'string' },
        liquidityEvidence: { type: 'string' },
        entryQuality: { type: 'string' },
        invalidationQuality: { type: 'string' },
        riskRewardQuality: { type: 'string' },
      },
      required: [
        'imageAuthority',
        'structureQuality',
        'liquidityEvidence',
        'entryQuality',
        'invalidationQuality',
        'riskRewardQuality',
      ],
    },
    opportunities: {
      type: 'array',
      items: OPPORTUNITY_SCHEMA,
    },
    overallEvidence: { type: 'array', items: { type: 'string' } },
    contradictions: { type: 'array', items: { type: 'string' } },
    limitations: { type: 'array', items: { type: 'string' } },
    nextBestInput: { type: 'string' },
  },
  required: [
    'imageQuality',
    'symbol',
    'symbolAuthority',
    'timeframe',
    'timeframeAuthority',
    'currentPrice',
    'currentPriceAuthority',
    'market',
    'qualityGates',
    'opportunities',
    'overallEvidence',
    'contradictions',
    'limitations',
    'nextBestInput',
  ],
};

function parseImage(dataUrl: string) {
  const match = /^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$/.exec(
    dataUrl
  );
  if (!match) throw new Error('VALID_IMAGE_DATA_REQUIRED');

  const data = match[2];
  const approxBytes = Math.round((data.length * 3) / 4);
  if (approxBytes > 2_000_000) throw new Error('IMAGE_TOO_LARGE');

  return {
    data,
    mimeType: match[1],
    approxBytes,
  };
}

function rpcCode(caught: unknown) {
  const rpc = caught as {
    statusCode?: number;
    responseText?: string;
    message?: string;
  };
  const status = rpc?.statusCode;

  if (status === 429) return 'ASTRA_AI_RATE_LIMITED';
  if (status === 413) return 'ASTRA_AI_IMAGE_TOO_LARGE';
  if (status === 400 || status === 422) return 'ASTRA_AI_REQUEST_REJECTED';
  if (status && status >= 500) return 'ASTRA_AI_TEMPORARILY_UNAVAILABLE';

  const message = String(rpc?.message ?? '');
  if (message.includes('VALID_IMAGE_DATA_REQUIRED'))
    return 'VALID_IMAGE_DATA_REQUIRED';
  if (message.includes('IMAGE_TOO_LARGE')) return 'ASTRA_AI_IMAGE_TOO_LARGE';

  return 'ASTRA_AI_FAILED';
}

function rpcStatus(code: string) {
  if (code === 'ASTRA_AI_RATE_LIMITED') return 429;
  if (code === 'ASTRA_AI_IMAGE_TOO_LARGE') return 413;
  if (code === 'ASTRA_AI_REQUEST_REJECTED') return 422;
  if (code === 'VALID_IMAGE_DATA_REQUIRED') return 400;
  if (code === 'ASTRA_AI_TEMPORARILY_UNAVAILABLE') return 503;
  return 502;
}

function rolePrompt(role: SpecialistRole) {
  if (role === 'STRUCTURE ANALYST') {
    return [
      'Analyze the canonical multi-timeframe chart state as a market-structure specialist.',
      'Evaluate HH/HL/LH/LL, BOS, CHoCH/MSS, trend versus range, compression, expansion, displacement, support/resistance, liquidity geometry and cross-timeframe alignment.',
      'Identify whether lower-timeframe confirmation is missing.',
      'Do not add prices or observations absent from the canonical state.',
      'stance must be BULLISH, BEARISH, NEUTRAL, WAIT, or INSUFFICIENT_DATA.',
    ].join(' ');
  }

  if (role === 'OPPORTUNITY ANALYST') {
    return [
      'Search the canonical chart state for multiple distinct conditional trade opportunities rather than forcing one direction.',
      'Evaluate trend continuation, liquidity-sweep reversal, breakout-retest, range-extreme reversal, MSS/FVG retrace and support/resistance rejection.',
      'List candidate setup names only when supported by visible evidence.',
      'Look for both bullish and bearish scenarios when the chart supports both.',
      'Do not invent numeric levels.',
      'stance must be BULLISH, BEARISH, NEUTRAL, WAIT, or INSUFFICIENT_DATA.',
    ].join(' ');
  }

  return [
    'Act as both risk critic and adversarial challenger.',
    'Try to disprove candidate trades and identify false breaks, late entries, opposing liquidity, poor invalidation, weak reward geometry, missing lower-timeframe confirmation and conflicting higher-timeframe structure.',
    'Determine what would make a setup executable versus only watchable.',
    'Do not invent numeric levels.',
    'stance must be BULLISH, BEARISH, NEUTRAL, WAIT, or INSUFFICIENT_DATA.',
  ].join(' ');
}

function stringOrNull(value: unknown) {
  const text = String(value ?? '').trim();
  if (
    !text ||
    text === '—' ||
    text.toUpperCase() === 'UNKNOWN' ||
    text.toUpperCase() === 'N/A' ||
    text.toUpperCase() === 'NONE'
  ) {
    return null;
  }
  return text;
}

function authority(value: unknown) {
  const text = String(value ?? 'UNKNOWN').toUpperCase();
  if (
    text === 'OBSERVED' ||
    text === 'USER_SUPPLIED' ||
    text === 'INFERRED' ||
    text === 'UNKNOWN'
  ) {
    return text;
  }
  return 'UNKNOWN';
}

function gatePoints(
  value: unknown,
  mapping: Record<string, number>,
  fallback: number
) {
  const normalized = String(value ?? '').toUpperCase();
  return mapping[normalized] ?? fallback;
}

function readinessScore(
  opportunity: Record<string, unknown>,
  successfulSpecialists: number
) {
  const gates =
    opportunity.gates && typeof opportunity.gates === 'object'
      ? (opportunity.gates as Record<string, unknown>)
      : {};

  let score = 0;
  score += gatePoints(
    gates.structure,
    { HIGH: 18, STRONG: 18, MODERATE: 12, MEDIUM: 12, LOW: 5 },
    4
  );
  score += gatePoints(
    gates.trigger,
    { CONFIRMED: 22, FORMING: 12, PENDING: 12, MISSING: 0 },
    4
  );
  score += gatePoints(
    gates.invalidation,
    { CLEAR: 16, PARTIAL: 8, MISSING: 0 },
    3
  );
  score += gatePoints(
    gates.target,
    { CLEAR: 14, PARTIAL: 7, MISSING: 0 },
    3
  );
  score += gatePoints(
    gates.mtf,
    { ALIGNED: 15, MIXED: 8, CONFLICTED: 2, UNKNOWN: 4 },
    4
  );
  score += gatePoints(
    gates.contradiction,
    { LOW: 15, MODERATE: 8, MEDIUM: 8, HIGH: 0 },
    5
  );

  const status = String(opportunity.status ?? '').toUpperCase();
  const entryZone = stringOrNull(opportunity.entryZone);
  const stopLoss = stringOrNull(opportunity.stopLoss);
  const trigger = stringOrNull(opportunity.trigger);
  const invalidation = stringOrNull(opportunity.invalidation);

  if (!entryZone) score = Math.min(score, 72);
  if (!stopLoss) score = Math.min(score, 65);
  if (!trigger) score = Math.min(score, 55);
  if (!invalidation) score = Math.min(score, 55);

  if (status === 'WATCH') score = Math.min(score, 68);
  if (status === 'FORMING') score = Math.min(score, 79);
  if (status === 'INVALID') score = 0;

  if (successfulSpecialists === 2) score = Math.min(score, 84);
  if (successfulSpecialists === 1) score = Math.min(score, 62);
  if (successfulSpecialists === 0) score = Math.min(score, 45);

  return Math.max(0, Math.min(100, Math.round(score)));
}

export function normalizeOpportunity(
  value: unknown,
  successfulSpecialists: number
) {
  const raw =
    value && typeof value === 'object'
      ? (value as Record<string, unknown>)
      : {};
  const gates =
    raw.gates && typeof raw.gates === 'object'
      ? (raw.gates as Record<string, unknown>)
      : {};

  const direction = String(raw.direction ?? 'NEUTRAL').toUpperCase();
  const statusRaw = String(raw.status ?? 'WATCH').toUpperCase();
  const allowedStatus = new Set(['CONFIRMED', 'FORMING', 'WATCH', 'INVALID']);
  const status = allowedStatus.has(statusRaw) ? statusRaw : 'WATCH';

  const normalized = {
    direction:
      direction === 'BUY' || direction === 'SELL' ? direction : 'NEUTRAL',
    status,
    setupType: String(raw.setupType ?? 'UNCLASSIFIED'),
    timeframe: String(raw.timeframe ?? 'UNKNOWN'),
    thesis: String(raw.thesis ?? ''),
    trigger: stringOrNull(raw.trigger),
    entryZone: stringOrNull(raw.entryZone),
    stopLoss: stringOrNull(raw.stopLoss),
    tp1: stringOrNull(raw.tp1),
    tp2: stringOrNull(raw.tp2),
    tp3: stringOrNull(raw.tp3),
    rr1: stringOrNull(raw.rr1),
    rr2: stringOrNull(raw.rr2),
    rr3: stringOrNull(raw.rr3),
    invalidation: stringOrNull(raw.invalidation),
    nextRequiredEvent: stringOrNull(raw.nextRequiredEvent),
    evidence: Array.isArray(raw.evidence)
      ? raw.evidence.map(String).slice(0, 6)
      : [],
    contradictions: Array.isArray(raw.contradictions)
      ? raw.contradictions.map(String).slice(0, 5)
      : [],
    gates: {
      structure: String(gates.structure ?? 'UNKNOWN').toUpperCase(),
      trigger: String(gates.trigger ?? 'MISSING').toUpperCase(),
      invalidation: String(gates.invalidation ?? 'MISSING').toUpperCase(),
      target: String(gates.target ?? 'MISSING').toUpperCase(),
      mtf: String(gates.mtf ?? 'UNKNOWN').toUpperCase(),
      contradiction: String(gates.contradiction ?? 'HIGH').toUpperCase(),
    },
    readinessScore: 0,
    executable: false,
  };

  normalized.readinessScore = readinessScore(raw, successfulSpecialists);
  normalized.executable = false; // Screenshots cannot attest current closed-candle execution authority.
  const visuallyQualified =
    normalized.status === 'CONFIRMED' &&
    normalized.readinessScore >= 75 &&
    Boolean(
      normalized.entryZone &&
        normalized.stopLoss &&
        normalized.trigger &&
        normalized.invalidation
    );

  if (visuallyQualified) normalized.nextRequiredEvent = 'Verify current broker quote, closed-candle trigger, spread and risk limits before manual execution.';
  return normalized;
}

function normalizeFinal(
  value: unknown,
  hints: AnalyzeHints,
  successfulSpecialists: number,
  chartCount: number
) {
  const raw =
    value && typeof value === 'object'
      ? (value as Record<string, unknown>)
      : {};
  const market =
    raw.market && typeof raw.market === 'object'
      ? (raw.market as Record<string, unknown>)
      : {};
  const gates =
    raw.qualityGates && typeof raw.qualityGates === 'object'
      ? (raw.qualityGates as Record<string, unknown>)
      : {};

  const opportunities = (Array.isArray(raw.opportunities)
    ? raw.opportunities
    : [])
    .map(item => normalizeOpportunity(item, successfulSpecialists))
    .filter(item => item.status !== 'INVALID')
    .sort((a, b) => b.readinessScore - a.readinessScore)
    .slice(0, 4);

  const best = opportunities[0] ?? null;
  const executable = opportunities.find(item => item.executable) ?? null;

  let decision = 'WAIT';
  let setupState = best ? 'FORMING' : 'INSUFFICIENT_DATA';

  if (executable?.direction === 'BUY') {
    decision =
      executable.readinessScore >= 88
        ? 'STRONG_BUY_SETUP'
        : 'BUY_SETUP';
    setupState = 'CONFIRMED';
  } else if (executable?.direction === 'SELL') {
    decision =
      executable.readinessScore >= 88
        ? 'STRONG_SELL_SETUP'
        : 'SELL_SETUP';
    setupState = 'CONFIRMED';
  } else if (best?.direction === 'BUY') {
    decision = 'FORMING_BULLISH';
  } else if (best?.direction === 'SELL') {
    decision = 'FORMING_BEARISH';
  }

  const imageQuality = String(raw.imageQuality ?? 'DEGRADED').toUpperCase();
  if (imageQuality === 'INVALID') {
    decision = 'INVALID_IMAGE';
    setupState = 'INSUFFICIENT_DATA';
  }

  const tradePlan = executable
    ? {
        direction: executable.direction,
        entryZone: executable.entryZone,
        stopLoss: executable.stopLoss,
        tp1: executable.tp1,
        tp2: executable.tp2,
        tp3: executable.tp3,
        rr1: executable.rr1,
        rr2: executable.rr2,
        rr3: executable.rr3,
        trigger: executable.trigger,
        invalidation: executable.invalidation,
        setupType: executable.setupType,
      }
    : {
        direction: null,
        entryZone: null,
        stopLoss: null,
        tp1: null,
        tp2: null,
        tp3: null,
        rr1: null,
        rr2: null,
        rr3: null,
        trigger: null,
        invalidation: null,
        setupType: null,
      };

  const limitations = Array.isArray(raw.limitations)
    ? raw.limitations.map(String).slice(0, 10)
    : [];

  limitations.push('Screenshot analysis is conditional, not live execution authority. Readiness is a rule score, not a win probability.');
  if (chartCount === 1) {
    limitations.push(
      'Only one chart timeframe was supplied. Multi-timeframe confirmation can increase execution authority.'
    );
  }

  if (successfulSpecialists < 3) {
    limitations.push(
      String(3 - successfulSpecialists) +
        ' of 3 reasoning specialist roles were unavailable and excluded.'
    );
  }

  return {
    imageQuality,
    symbol: {
      value: hints.symbolHint ?? stringOrNull(raw.symbol),
      authority: hints.symbolHint
        ? 'USER_SUPPLIED'
        : authority(raw.symbolAuthority),
    },
    timeframe: {
      value:
        chartCount > 1
          ? stringOrNull(raw.timeframe) ?? 'MULTI-TF'
          : hints.timeframeHint ?? stringOrNull(raw.timeframe),
      authority:
        chartCount > 1
          ? authority(raw.timeframeAuthority)
          : hints.timeframeHint
            ? 'USER_SUPPLIED'
            : authority(raw.timeframeAuthority),
    },
    currentPrice: {
      value: stringOrNull(raw.currentPrice),
      authority: authority(raw.currentPriceAuthority),
    },
    decision,
    setupState,
    readinessScore: best?.readinessScore ?? 0,
    market: {
      bias: String(market.bias ?? 'NEUTRAL'),
      structure: String(market.structure ?? 'UNKNOWN'),
      volatility: String(market.volatility ?? 'UNKNOWN'),
      momentum: String(market.momentum ?? 'UNKNOWN'),
      mtfAlignment: String(market.mtfAlignment ?? 'UNKNOWN'),
    },
    qualityGates: {
      imageAuthority: String(gates.imageAuthority ?? 'UNKNOWN'),
      structureQuality: String(gates.structureQuality ?? 'UNKNOWN'),
      liquidityEvidence: String(gates.liquidityEvidence ?? 'UNKNOWN'),
      entryQuality: String(gates.entryQuality ?? 'UNKNOWN'),
      invalidationQuality: String(gates.invalidationQuality ?? 'UNKNOWN'),
      riskRewardQuality: String(gates.riskRewardQuality ?? 'UNKNOWN'),
    },
    tradePlan,
    opportunities,
    nextRequiredEvent: best?.nextRequiredEvent ?? null,
    nextBestInput: stringOrNull(raw.nextBestInput),
    evidence: Array.isArray(raw.overallEvidence)
      ? raw.overallEvidence.map(String).slice(0, 12)
      : best?.evidence ?? [],
    contradictions: Array.isArray(raw.contradictions)
      ? raw.contradictions.map(String).slice(0, 10)
      : best?.contradictions ?? [],
    limitations: limitations.slice(0, 12),
  };
}

export const handler = router({
  'GET /api/_healthcheck': [
    async () =>
      json({
        message: 'Success',
        architecture: 'opportunity-engine-v2',
      }),
  ],

  'GET /api/status': [
    async () =>
      json({
        ready: configurationIssues().length === 0,
        engine: 'ASTRA',
        architecture: 'MTF_CANONICAL_OPPORTUNITY_ENGINE',
        roles: 5,
        chartPackMax: 4,
        strategyFamilies: STRATEGY_COVERAGE.length,
        externalProviderDependency: true,
        issue: configurationIssues().join(', ') || null,
      }),
  ],

  'POST /api/analyze/vision': [
    async ({ body }) => {
      const input = (body ?? {}) as VisionBody;
      const urls = Array.isArray(input.imageDataUrls)
        ? input.imageDataUrls.slice(0, 4)
        : [];

      if (urls.length === 0) return error('VALID_IMAGE_REQUIRED', 400);

      try {
        const parsed = urls.map(parseImage);
        const totalBytes = parsed.reduce(
          (sum, image) => sum + image.approxBytes,
          0
        );
        if (totalBytes > 2_800_000) {
          return error('ASTRA_AI_IMAGE_TOO_LARGE', 413);
        }

        const started = Date.now();
        const result = await ai.extract({
          system: [
            'You are the visual authority layer for AUREON Ω.',
            'You may receive one to four screenshots of the same market on different timeframes.',
            'Read only what is visible. Never invent hidden candles, news, spread, order flow, unseen indicators or price levels.',
            'Treat each image independently first, then build a cross-timeframe canonical state.',
            'If screenshots appear to show different symbols, report the conflict rather than merging them.',
            'Use UNKNOWN when text or values are unreadable.',
            'Numeric levels may be transcribed only when visibly supported by chart scale or annotations.',
          ].join(' '),
          prompt: [
            'Create a canonical multi-timeframe chart pack for downstream opportunity scanning.',
            'Index images in the same order they were supplied starting at 1.',
            'Extract timeframe, visible price, structure, liquidity, patterns, indicators and readable levels per image.',
            'Then summarize MTF alignment, dominant bias, conflicts, missing execution timeframes and merged visible levels.',
            'User context:',
            JSON.stringify({
              symbolHint: input.symbolHint ?? null,
              timeframeHint: input.timeframeHint ?? null,
              session: input.session ?? null,
              tradeMode: input.tradeMode ?? null,
            }),
          ].join(' '),
          images: parsed.map(image => ({
            data: image.data,
            mimeType: image.mimeType,
          })),
          schema: VISION_SCHEMA,
          maxRetries: 2,
          maxTokens: 2600,
          temperature: 0.1,
          thinkingMode: 'DEEP',
        });

        const canonical = result.data as Record<string, unknown>;
        const charts = Array.isArray(canonical.charts)
          ? canonical.charts
          : [];
        const limitations = Array.isArray(canonical.limitations)
          ? canonical.limitations.map(String)
          : [];

        return json({
          role: 'VISION ANALYST',
          model: process.env.AI_MODEL || 'UNCONFIGURED',
          canonical,
          report: {
            stance: 'NEUTRAL',
            summary:
              String(charts.length) +
              ' chart frame(s) canonicalized into one multi-timeframe market state.',
            evidence: [],
            contradictions: [],
            unknown: limitations.slice(0, 8),
            candidateSetups: [],
            nextRequiredEvent: '',
          },
          attempts: result.attempts,
          latencyMs: Date.now() - started,
          imageCount: parsed.length,
          imageBytes: totalBytes,
        });
      } catch (caught) {
        const code = rpcCode(caught);
        console.error('AUREON Ω MTF vision failed', code);
        return error(code, rpcStatus(code));
      }
    },
  ],

  'POST /api/analyze/specialist': [
    async ({ body }) => {
      const input = (body ?? {}) as SpecialistBody;
      if (!input.role || !SPECIALIST_ROLES.includes(input.role)) {
        return error('VALID_SPECIALIST_ROLE_REQUIRED', 400);
      }
      if (!input.canonical || typeof input.canonical !== 'object') {
        return error('CANONICAL_STATE_REQUIRED', 400);
      }

      try {
        const started = Date.now();
        const result = await ai.extract({
          system: [
            'You are one independent AUREON Ω market-analysis role.',
            'The canonical multi-timeframe state is authoritative.',
            'Never add prices, candles, indicators or context absent from that state.',
            'Search for conditional opportunities without lowering evidence standards.',
            'Do not expose chain-of-thought. Return concise auditable conclusions only.',
          ].join(' '),
          prompt: rolePrompt(input.role),
          content: JSON.stringify({
            canonical: input.canonical,
            strategyFamilies: STRATEGY_COVERAGE,
            userContext: {
              symbolHint: input.symbolHint ?? null,
              timeframeHint: input.timeframeHint ?? null,
              session: input.session ?? null,
              tradeMode: input.tradeMode ?? null,
            },
          }),
          schema: SPECIALIST_SCHEMA,
          maxRetries: 2,
          maxTokens:
            input.role === 'OPPORTUNITY ANALYST' ? 1200 : 950,
          temperature: 0.1,
          thinkingMode:
            input.role === 'STRUCTURE ANALYST' ||
            input.role === 'OPPORTUNITY ANALYST'
              ? 'DEEP'
              : 'FAST',
        });

        return json({
          role: input.role,
          model: process.env.AI_MODEL || 'UNCONFIGURED',
          report: result.data,
          attempts: result.attempts,
          latencyMs: Date.now() - started,
        });
      } catch (caught) {
        const code = rpcCode(caught);
        console.error('AUREON Ω specialist failed', input.role, code);
        return error(code, rpcStatus(code));
      }
    },
  ],

  'POST /api/analyze/final': [
    async ({ body }) => {
      const input = (body ?? {}) as FinalBody;
      if (!input.canonical || typeof input.canonical !== 'object') {
        return error('CANONICAL_STATE_REQUIRED', 400);
      }

      const reports = Array.isArray(input.reports)
        ? input.reports.slice(0, 3)
        : [];
      const failures = Array.isArray(input.failures)
        ? input.failures.slice(0, 3)
        : [];
      const canonical = input.canonical as Record<string, unknown>;
      const charts = Array.isArray(canonical.charts)
        ? canonical.charts
        : [];

      try {
        const started = Date.now();
        const result = await ai.extract({
          system: [
            'You are the lead adjudicator and opportunity engine for AUREON Ω Neural Scanner.',
            'Use DEEP reasoning over the canonical multi-timeframe state and independent specialist reports.',
            'The objective is to surface the maximum number of VALID conditional opportunities, not the maximum number of trades.',
            'Specialist reports are evidence, not votes.',
            'Evaluate all six supplied strategy families and retain up to four distinct opportunities with the strongest visible support.',
            'Bullish and bearish scenarios may coexist when each has a distinct trigger and invalidation.',
            'Never invent price levels. Numeric entry, stop and target values must be traceable to visible chart evidence.',
            'If only a higher timeframe is supplied, create watch/forming scenarios and request the missing lower execution timeframe instead of fabricating precision.',
            'Do not expose chain-of-thought.',
          ].join(' '),
          prompt: [
            'Build an opportunity matrix and overall market model.',
            'Opportunity status must be CONFIRMED, FORMING, WATCH, or INVALID.',
            'Direction must be BUY, SELL, or NEUTRAL.',
            'For unavailable numerical plan fields return an empty string.',
            'Gate values: structure HIGH/MODERATE/LOW; trigger CONFIRMED/FORMING/PENDING/MISSING; invalidation CLEAR/PARTIAL/MISSING; target CLEAR/PARTIAL/MISSING; mtf ALIGNED/MIXED/CONFLICTED/UNKNOWN; contradiction LOW/MODERATE/HIGH.',
            'Do not provide your own probability or win rate. Backend code will compute readiness deterministically from the gates.',
          ].join(' '),
          content: JSON.stringify({
            canonical: input.canonical,
            visionRole: input.vision ?? null,
            specialistReports: reports,
            failedRoles: failures,
            strategyFamilies: STRATEGY_COVERAGE,
            userContext: {
              symbolHint: input.symbolHint ?? null,
              timeframeHint: input.timeframeHint ?? null,
              session: input.session ?? null,
              tradeMode: input.tradeMode ?? null,
            },
          }),
          schema: FINAL_SCHEMA,
          maxRetries: 2,
          maxTokens: 3200,
          temperature: 0.1,
          thinkingMode: 'DEEP',
        });

        const normalized = normalizeFinal(
          result.data,
          input,
          reports.length,
          charts.length
        );

        const visionReport =
          input.vision && typeof input.vision === 'object'
            ? (input.vision as Record<string, unknown>)
            : {};

        const council = [
          {
            role: 'LEAD ADJUDICATOR',
            model: process.env.AI_MODEL || 'UNCONFIGURED',
            stance: normalized.decision,
            summary:
              'Deep opportunity adjudication across all supported strategy families and supplied chart timeframes.',
            latencyMs: Date.now() - started,
          },
          {
            role: 'VISION ANALYST',
            model: process.env.AI_MODEL || 'UNCONFIGURED',
            stance: String(visionReport.stance ?? 'NEUTRAL'),
            summary: String(
              visionReport.summary ??
                'Multi-timeframe canonical visual state supplied.'
            ),
            latencyMs: null,
          },
          ...reports.map(item => ({
            role: item.role,
            model: item.model,
            stance: String(item.report.stance ?? 'WAIT'),
            summary: String(item.report.summary ?? '').slice(0, 420),
            latencyMs: item.latencyMs ?? null,
          })),
          ...failures.map(item => ({
            role: item.role,
            model: 'UNAVAILABLE',
            stance: 'UNAVAILABLE',
            summary:
              'This role failed safely and was excluded from final adjudication.',
            latencyMs: null,
          })),
        ];

        return json({
          scanId: crypto.randomUUID(),
          generatedAt: new Date().toISOString(),
          architecture: 'OPPORTUNITY_ENGINE_V2',
          reasoningEffort: 'DEEP',
          leadModel: process.env.AI_MODEL || 'UNCONFIGURED',
          chartCount: charts.length,
          strategyCoverage: STRATEGY_COVERAGE,
          ...normalized,
          degraded: reports.length < 3,
          rolesCompleted: [
            'LEAD ADJUDICATOR',
            'VISION ANALYST',
            ...reports.map(item => item.role),
          ],
          council,
          leadLatencyMs: Date.now() - started,
          attempts: result.attempts,
        });
      } catch (caught) {
        const code = rpcCode(caught);
        console.error('AUREON Ω opportunity adjudication failed', code);
        return error(code, rpcStatus(code));
      }
    },
  ],
});
