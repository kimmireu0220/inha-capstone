import { env } from 'cloudflare:workers';
type Bindings = { DB: D1Database; ADMIN_PASSWORD?: string };
export function bindings() {
  return env as unknown as Bindings;
}
export function reply(data: unknown, status = 200) {
  return Response.json(data, {
    status,
    headers: { 'Cache-Control': 'no-store' },
  });
}
export function sameOrigin(req: Request) {
  return req.headers.get('origin') === new URL(req.url).origin;
}
export async function digest(s: string) {
  return Array.from(
    new Uint8Array(
      await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)),
    ),
    (b) => b.toString(16).padStart(2, '0'),
  ).join('');
}
async function sign(value: string) {
  const secret = bindings().ADMIN_PASSWORD;
  if (!secret || secret.length < 32)
    throw new Error('관리자 설정이 필요합니다.');
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  return Array.from(
    new Uint8Array(
      await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(value)),
    ),
    (b) => b.toString(16).padStart(2, '0'),
  ).join('');
}
export async function sameSecret(a: string, b: string) {
  const x = await digest(a),
    y = await digest(b);
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x.charCodeAt(i) ^ y.charCodeAt(i);
  return diff === 0;
}
export async function session() {
  const expiry = String(Date.now() + 8 * 60 * 60 * 1000);
  return expiry + '.' + (await sign(expiry));
}
export async function isAdmin(req: Request) {
  try {
    const token = req.headers
      .get('cookie')
      ?.split(';')
      .map((x) => x.trim())
      .find((x) => x.startsWith('survey_admin='))
      ?.slice(13);
    if (!token) return false;
    const [expiry, signature] = token.split('.');
    if (
      !/^\d+$/.test(expiry) ||
      Number(expiry) < Date.now() ||
      Number(expiry) > Date.now() + 8 * 60 * 60 * 1000 ||
      !signature
    )
      return false;
    return await sameSecret(signature, await sign(expiry));
  } catch {
    return false;
  }
}
export function sessionCookie(req: Request, value: string, logout = false) {
  return (
    'survey_admin=' +
    value +
    '; HttpOnly; SameSite=Strict; Path=/; Max-Age=' +
    (logout ? '0' : '28800') +
    (new URL(req.url).protocol === 'https:' ? '; Secure' : '')
  );
}
