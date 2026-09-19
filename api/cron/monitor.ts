import { timingSafeEqual } from 'node:crypto';
import { checkMonitors } from '../../server/monitor.ts';

type RequestLike = {
  method?: string;
  headers: { authorization?: string | string[] };
};

type ResponseLike = {
  status(code: number): ResponseLike;
  json(body: unknown): void;
};

export default async function cronMonitor(req: RequestLike, res: ResponseLike) {
  if ((req.method || 'GET') !== 'GET') {
    res.status(405).json({ error: 'METHOD_NOT_ALLOWED' });
    return;
  }

  const configured = process.env.CRON_SECRET;
  const header = req.headers.authorization;
  const supplied = Array.isArray(header) ? header[0] : header;

  if (!configured || configured.length < 32 || !supplied) {
    res.status(401).json({ error: 'CRON_AUTH_REQUIRED' });
    return;
  }

  const expected = Buffer.from('Bearer ' + configured);
  const actual = Buffer.from(supplied);
  if (
    expected.length !== actual.length ||
    !timingSafeEqual(expected, actual) ||
    !process.env.OWNER_USER_ID
  ) {
    res.status(401).json({ error: 'CRON_AUTH_REQUIRED' });
    return;
  }

  try {
    res.status(200).json(await checkMonitors(process.env.OWNER_USER_ID));
  } catch (caught) {
    console.error('AUREON Ω cron monitor failed', caught instanceof Error ? caught.message : 'UNKNOWN');
    res.status(503).json({ error: 'MONITOR_CHECK_FAILED' });
  }
}
