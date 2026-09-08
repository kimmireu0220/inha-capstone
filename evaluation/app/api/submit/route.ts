import { bindings, reply, sameOrigin, digest } from '@/lib/server';
import { validSubmission, tasks, type Submission } from '@/lib/survey';
import imageHashes from '@/db/image-hashes.json';
export async function POST(req: Request) {
  if (!sameOrigin(req))
    return reply({ error: '이 사이트에서 제출해주세요.' }, 403);
  if (!req.headers.get('content-type')?.startsWith('application/json'))
    return reply({ error: '잘못된 요청입니다.' }, 415);
  try {
    const raw = await req.text();
    if (raw.length > 40000) return reply({ error: '요청이 너무 큽니다.' }, 413);
    let input: Submission;
    try {
      input = JSON.parse(raw);
    } catch {
      return reply({ error: '잘못된 응답입니다.' }, 400);
    }
    if (!validSubmission(input))
      return reply(
        { error: '참여 정보와 32개 응답을 모두 확인해주세요.' },
        400,
      );
    const d = {
      schema: input.schema,
      id: input.id,
      age: input.age,
      startedAt: input.startedAt,
      order: input.order,
      answers: Object.fromEntries(
        tasks(input.order).map((t) => [
          t.id,
          {
            value: input.answers[t.id].value,
            updatedAt: input.answers[t.id].updatedAt,
          },
        ]),
      ),
    };
    const hash = await digest(JSON.stringify(d));
    const payload = JSON.stringify({ ...d, imageHashes });
    const db = bindings().DB;
    await db
      .prepare(
        'INSERT INTO submissions (id,schema,received_at,age,exposure,payload,payload_hash) VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',
      )
      .bind(
        d.id,
        d.schema,
        new Date().toISOString(),
        d.age,
        'not_collected',
        payload,
        hash,
      )
      .run();
    const saved = await db
      .prepare('SELECT payload_hash FROM submissions WHERE id = ?')
      .bind(d.id)
      .first<{ payload_hash: string }>();
    if (saved?.payload_hash !== hash)
      return reply(
        { error: '이 참여 번호는 이미 다른 응답으로 제출됐습니다.' },
        409,
      );
    return reply({ receipt: d.id });
  } catch {
    return reply({ error: '현재 응답을 저장할 수 없습니다.' }, 503);
  }
}
