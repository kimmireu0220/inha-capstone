import {
  bindings,
  reply,
  sameOrigin,
  sameSecret,
  session,
  sessionCookie,
} from '@/lib/server';
export async function POST(req: Request) {
  if (!sameOrigin(req)) return reply({ error: '잘못된 접근입니다.' }, 403);
  try {
    const raw = await req.text();
    if (raw.length > 1024) return reply({ error: '잘못된 요청입니다.' }, 400);
    const { password } = JSON.parse(raw);
    const secret = bindings().ADMIN_PASSWORD;
    if (!secret || secret.length < 32)
      return reply(
        { error: '관리자 접속 설정이 아직 완료되지 않았습니다.' },
        503,
      );
    if (typeof password !== 'string' || !(await sameSecret(password, secret)))
      return reply({ error: '접속 암호가 맞지 않습니다.' }, 401);
    const r = reply({ ok: true });
    r.headers.set('Set-Cookie', sessionCookie(req, await session()));
    return r;
  } catch {
    return reply({ error: '로그인할 수 없습니다.' }, 400);
  }
}
