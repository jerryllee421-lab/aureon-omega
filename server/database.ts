export function dbConfig() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key || new URL(url).protocol !== 'https:') throw new Error('DATABASE_UNCONFIGURED');
  return { url, key, modernSecret: key.startsWith('sb_secret_') };
}

export function credentialKind(key: string) {
  if (key.startsWith('sb_secret_')) return 'SB_SECRET';
  if (key.startsWith('sb_publishable_')) return 'SB_PUBLISHABLE';
  if (key.split('.').length === 3) return 'LEGACY_JWT';
  return 'UNKNOWN';
}

export function serverHeaders(key: string) {
  const headers: Record<string,string> = {
    apikey: key,
    'Content-Type': 'application/json',
    Prefer: 'return=representation',
  };
  // Modern sb_secret_ keys are opaque API-gateway credentials, not JWTs.
  // The Supabase gateway maps them to service_role internally.
  if (!key.startsWith('sb_secret_')) headers.Authorization = `Bearer ${key}`;
  return headers;
}

export async function database(path: string, method = 'GET', body?: unknown) {
  const { url, key } = dbConfig();
  const r = await fetch(url + '/rest/v1/' + path, {
    method,
    headers: serverHeaders(key),
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });
  if (!r.ok) {
    console.error(JSON.stringify({service:'supabase-rest',status:r.status,path:path.split('?')[0],method,credentialKind:credentialKind(key)}));
    throw new Error('DATABASE_REQUEST_FAILED');
  }
  return r.status === 204 ? null : r.json();
}

export async function authenticate(header?: string) {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key || !process.env.OWNER_USER_ID) throw new Error('AUTH_UNCONFIGURED');
  if (!header?.startsWith('Bearer ')) throw new Error('SIGN_IN_REQUIRED');
  const r = await fetch(url + '/auth/v1/user', {
    headers: { apikey: key, Authorization: header },
    signal: AbortSignal.timeout(10000),
  });
  if (!r.ok) throw new Error('SIGN_IN_REQUIRED');
  const user = await r.json();
  if (!user.id || user.id !== process.env.OWNER_USER_ID || user.is_anonymous) throw new Error('OWNER_ACCESS_REQUIRED');
  return String(user.id);
}
