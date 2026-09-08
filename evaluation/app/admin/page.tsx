'use client';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import '../review.css';
import '../survey/survey.css';
type Data = {
  total: number;
  rows: { id: string; received_at: string; age: string; exposure: string }[];
};
export default function Admin() {
  const [data, setData] = useState<Data | null>(null),
    [password, setPassword] = useState(''),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  async function refresh() {
    setBusy(true);
    try {
      const r = await fetch('/api/admin/responses');
      const d = (await r.json()) as Data & { error?: string };
      if (r.status === 401) {
        setData(null);
        return;
      }
      if (!r.ok) throw new Error(d.error);
      setData(d);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : '연결에 실패했습니다.');
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    void refresh();
  }, []);
  async function login() {
    setBusy(true);
    try {
      const r = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      const d = (await r.json()) as { error?: string };
      if (!r.ok) throw new Error(d.error);
      setPassword('');
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : '로그인에 실패했습니다.');
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    const r = await fetch('/api/admin/logout', { method: 'POST' });
    if (r.ok) setData(null);
    else setError('로그아웃하지 못했습니다. 다시 시도해주세요.');
  }
  return (
    <main className="trigger-review">
      {!data ? (
        <section className="survey-intro">
          <span className="eyebrow">연구자 전용</span>
          <h1>응답 관리</h1>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void login();
            }}
          >
            <label>
              관리자 접속 암호
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {error && <p role="alert">{error}</p>}
            <Button disabled={busy || !password}>로그인</Button>
          </form>
        </section>
      ) : (
        <>
          <section className="tr-question">
            <h1>수집된 응답 {data.total}건</h1>
            <p>
              최신 100건을 표시합니다. CSV에는 전체 참여자의 문항별 응답과 제시
              순서가 포함됩니다.
            </p>
            <a href="/api/admin/responses?format=csv">전체 응답 CSV 다운로드</a>
            <div className="tr-answer">
              <Button disabled={busy} onClick={refresh}>
                새로고침
              </Button>
              <Button variant="outline" onClick={logout}>
                로그아웃
              </Button>
            </div>
            {error && <p role="alert">{error}</p>}
          </section>
          {data.total === 0 ? (
            <p>아직 제출된 응답이 없습니다.</p>
          ) : (
            <div className="admin-table">
              <table>
                <thead>
                  <tr>
                    <th>접수 시각</th>
                    <th>참여 번호</th>
                    <th>연령대</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((r) => (
                    <tr key={r.id}>
                      <td>{new Date(r.received_at).toLocaleString('ko-KR')}</td>
                      <td>{r.id}</td>
                      <td>{r.age}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </main>
  );
}
