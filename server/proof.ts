import { createHmac, timingSafeEqual } from 'node:crypto';
function secret() {
  const source = process.env.PIPELINE_SIGNING_KEY || process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!source || source.length < 32) throw new Error('SIGNING_KEY_UNCONFIGURED');
  return createHmac('sha256', source).update('AUREON_PIPELINE_SIGNING_V1').digest();
}
export function sign(payload: unknown, userId: string, stage: string) {
  const body = Buffer.from(JSON.stringify({ payload, userId, stage, expires: Date.now() + 15 * 60_000 })).toString('base64url');
  return body + '.' + createHmac('sha256', secret()).update(body).digest('base64url');
}
export function verify(token: unknown, userId: string, stage: string): any {
  if (typeof token !== 'string' || token.length > 250_000) throw new Error('INVALID_STAGE_PROOF');
  const [body, mac, extra] = token.split('.');
  if (!body || !mac || extra) throw new Error('INVALID_STAGE_PROOF');
  const expected = createHmac('sha256', secret()).update(body).digest();
  const actual = Buffer.from(mac, 'base64url');
  if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) throw new Error('INVALID_STAGE_PROOF');
  const decoded = JSON.parse(Buffer.from(body, 'base64url').toString());
  if (decoded.userId !== userId || decoded.stage !== stage || decoded.expires <= Date.now()) throw new Error('INVALID_STAGE_PROOF');
  return decoded.payload;
}
