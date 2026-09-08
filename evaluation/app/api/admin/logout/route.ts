import { reply, sameOrigin, sessionCookie } from '@/lib/server';
export async function POST(req: Request) {
  if (!sameOrigin(req)) return reply({ error: '잘못된 접근입니다.' }, 403);
  const r = reply({ ok: true });
  r.headers.set('Set-Cookie', sessionCookie(req, '', true));
  return r;
}
