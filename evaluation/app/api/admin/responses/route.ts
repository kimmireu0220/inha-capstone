import { bindings, reply, isAdmin } from '@/lib/server';
import { SCHEMA, tasks, type Submission } from '@/lib/survey';
type Row = {
  id: string;
  received_at: string;
  age: string;
  exposure: string;
  payload: string;
};
const cell = (v: unknown) => {
  let s = String(v ?? '');
  if (/^[=+@\-\t\r]/.test(s)) s = "'" + s;
  return '"' + s.replaceAll('"', '""') + '"';
};
export async function GET(req: Request) {
  if (!(await isAdmin(req)))
    return reply({ error: '관리자 로그인이 필요합니다.' }, 401);
  try {
    const url = new URL(req.url);
    const db = bindings().DB;
    const download = url.searchParams.get('format') === 'csv';
    if (download) {
      const stream = new ReadableStream({
        async start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(
            encoder.encode(
              '\uFEFF' +
                [
                  '참여번호',
                  '설문버전',
                  '서버접수시각',
                  '시작시각',
                  '연령대',
                  '제시순번',
                  '이미지ID',
                  '평가항목',
                  '응답값',
                  '응답시각',
                  '원본이미지SHA256',
                  '결과이미지SHA256',
                ]
                  .map(cell)
                  .join(',') +
                '\r\n',
            ),
          );
          try {
            let after = '';
            for (;;) {
              const page = await db
                .prepare(
                  'SELECT id,received_at,age,exposure,payload FROM submissions WHERE schema = ? AND id > ? ORDER BY id LIMIT 100',
                )
                .bind(SCHEMA, after)
                .all<Row>();
              if (!page.results.length) break;
              for (const row of page.results) {
                const d = JSON.parse(row.payload) as Submission & {
                  imageHashes: Record<string, Record<string, string>>;
                };
                for (const [i, t] of tasks(d.order).entries()) {
                  const a = d.answers[t.id];
                  const h = d.imageHashes[t.candidate.id];
                  controller.enqueue(
                    encoder.encode(
                      [
                        row.id,
                        d.schema,
                        row.received_at,
                        d.startedAt,
                        d.age,
                        i + 1,
                        t.candidate.id,
                        t.kind,
                        a.value,
                        a.updatedAt,
                        h[t.kind === 'face' ? 'referenceCrop' : 'reference'],
                        h[t.kind === 'face' ? 'candidateCrop' : 'candidate'],
                      ]
                        .map(cell)
                        .join(',') + '\r\n',
                    ),
                  );
                }
              }
              after = page.results.at(-1)!.id;
            }
            controller.close();
          } catch (e) {
            controller.error(e);
          }
        },
      });
      return new Response(stream, {
        headers: {
          'Content-Type': 'text/csv; charset=utf-8',
          'Content-Disposition': 'attachment; filename="human-evaluation.csv"',
          'Cache-Control': 'no-store',
        },
      });
    }
    const count = await db
      .prepare('SELECT count(*) AS total FROM submissions WHERE schema = ?')
      .bind(SCHEMA)
      .first<{ total: number }>();
    const rows = await db
      .prepare(
        'SELECT id,received_at,age,exposure FROM submissions WHERE schema = ? ORDER BY received_at DESC LIMIT 100',
      )
      .bind(SCHEMA)
      .all();
    return reply({ total: count?.total ?? 0, rows: rows.results });
  } catch {
    return reply({ error: '응답 목록을 불러오지 못했습니다.' }, 503);
  }
}
