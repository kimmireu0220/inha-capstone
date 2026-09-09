'use client';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  SCHEMA,
  candidates,
  tasks,
  validSubmission,
  type Submission,
} from '@/lib/followup-recheck';
import '../review.css';
import '../survey/survey.css';
const KEY = SCHEMA + '-draft';
export default function Survey() {
  const [draft, setDraft] = useState<Submission | null>(null),
    [ready, setReady] = useState(false),
    [index, setIndex] = useState(0),
    [age] = useState('응답하지 않음'),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [receipt, setReceipt] = useState('');
  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const d = JSON.parse(raw);
        if (
          d.schema === SCHEMA &&
          Array.isArray(d.order) &&
          d.order.length === candidates.length &&
          new Set(d.order).size === candidates.length &&
          d.order.every((id: string) => candidates.some((c) => c.id === id)) &&
          d.answers
        ) {
          setDraft(d);
          const next = tasks(d.order).findIndex(
            (t) => !t.options.some((o) => o[0] === d.answers[t.id]?.value),
          );
          setIndex(next < 0 ? candidates.length : next);
        }
      }
    } catch {
      setError('임시 응답을 불러오지 못했습니다. 새로 시작해주세요.');
    }
    setReady(true);
  }, []);
  useEffect(() => {
    if (draft)
      try {
        localStorage.setItem(KEY, JSON.stringify(draft));
      } catch {
        setError(
          '이 브라우저에서 임시 저장이 안 됩니다. 제출 전까지 이 페이지를 닫지 마세요.',
        );
      }
  }, [draft]);
  function start() {
    if (!age) return;
    const order = candidates.map((c) => c.id);
    for (let i = order.length - 1; i > 0; i--) {
      const j = Math.floor(
        (crypto.getRandomValues(new Uint32Array(1))[0] / 4294967296) * (i + 1),
      );
      [order[i], order[j]] = [order[j], order[i]];
    }
    setDraft({
      schema: SCHEMA,
      id: crypto.randomUUID(),
      age,
      startedAt: new Date().toISOString(),
      order,
      answers: {},
    });
    setError('');
  }
  function move(i: number) {
    setIndex(i);
    window.scrollTo({ top: 0 });
  }
  async function submit() {
    if (!draft || !validSubmission(draft) || busy) return;
    setBusy(true);
    setError('');
    try {
      const r = await fetch('/api/followup/recheck', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft),
      });
      const d = (await r.json()) as { error?: string; receipt: string };
      if (!r.ok) throw new Error(d.error || '저장에 실패했습니다.');
      setReceipt(d.receipt);
      try {
        localStorage.removeItem(KEY);
      } catch {}
    } catch (e) {
      setError(
        (e instanceof Error ? e.message : '연결에 실패했습니다.') +
          ' 응답은 유지됩니다. 다시 제출해주세요.',
      );
    } finally {
      setBusy(false);
    }
  }
  if (!ready) return <main className="trigger-review">불러오는 중…</main>;
  if (receipt)
    return (
      <main className="trigger-review">
        <section className="survey-intro">
          <span className="eyebrow">제출 완료</span>
          <h1>평가해주셔서 감사합니다.</h1>
          <p>응답이 연구자에게 전달되었습니다. 이제 페이지를 닫아도 됩니다.</p>
          <p className="receipt">
            접수 번호
            <br />
            {receipt}
          </p>
        </section>
      </main>
    );
  if (!draft)
    return (
      <main className="trigger-review">
        <section className="survey-intro">
          <span className="eyebrow">인물 이미지 평가 · 두 문항 다시 평가</span>
          <h1>
            편집된 얼굴을
            <br />
            어떻게 보셨나요?
          </h1>
          <p>
            원본과 편집된 이미지를 비교해 피부의 부자연스러운 변화와 정도를 평가해주세요. 정답은 없습니다.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              start();
            }}
          >
            {error && <p role="alert">{error}</p>}
            <Button type="submit" disabled={!age}>
              두 문항 평가하기 →
            </Button>
          </form>
        </section>
      </main>
    );
  const list = tasks(draft.order),
    item = list[index],
    count = list.filter((t) =>
      t.options.some((o) => o[0] === draft.answers[t.id]?.value),
    ).length;
  return (
    <main className="trigger-review public-survey">
      <header>
        <strong>인물 이미지 평가</strong>
        <span>
          {count} / {list.length} 응답
        </span>
      </header>
      <progress aria-label="응답 진행" value={count} max={list.length} />
      {error && (
        <p role="alert" className="survey-error">
          {error}
        </p>
      )}
      {item ? (
        <>
          <section className="tr-question">
            <span>
              {item.kind === 'face'
                ? '1부 · 얼굴 변화'
                : '2부 · 인물 얼굴 보존'}{' '}
              · {index + 1} / {list.length}
            </span>
            <h1>
              {item.kind === 'face'
                ? '원본에 없던 부자연스러운 피부 무늬나 얼굴 변형이 보이나요?'
                : '바꾸라고 하지 않은 얼굴이 원본과 동일하게 보존됐나요?'}
            </h1>
            <p>
              {item.kind === 'face'
                ? '원래 있던 주름·모공과 귀걸이는 제외해주세요. 밝기나 위치 차이만으로 피부 무늬가 생겼다고 판단하지 마세요.'
                : '같은 사람으로 보이는지와 얼굴형·이목구비·표정·시선이 유지됐는지를 함께 판단해주세요. 피부의 부자연스러운 무늬는 앞 평가에서 따로 판단했습니다.'}
            </p>
            <small>이미지를 누르면 원래 크기로 볼 수 있습니다.</small>
          </section>
          <section
            className={'tr-images ' + (item.kind === 'face' ? 'crop' : '')}
            aria-label="비교 이미지"
          >
            {(['reference', 'candidate'] as const).map((k) => {
              const src =
                item.candidate[
                  item.kind === 'face'
                    ? k === 'reference'
                      ? 'referenceCrop'
                      : 'candidateCrop'
                    : k
                ];
              return (
                <figure key={item.id + k}>
                  <figcaption>{k === 'reference' ? '원본' : '결과'}</figcaption>
                  <a href={src} target="_blank" rel="noreferrer">
                    {item.kind === 'face' ? (
                      <div style={{ position: 'relative', overflow: 'hidden', width: 320, maxWidth: '100%', aspectRatio: '8 / 9' }}>
                        <img src={src} alt={k === 'reference' ? '원본 얼굴' : '편집된 얼굴'} style={{ position: 'absolute', maxWidth: 'none', width: '320%', height: '426.666667%', left: -(item.candidate.roi[0] / 320 * 100) + '%', top: -(item.candidate.roi[1] / 360 * 100) + '%', objectFit: 'fill' }} />
                      </div>
                    ) : <img src={src} alt={k === 'reference' ? '원본 인물' : '편집된 인물'} />}
                  </a>
                </figure>
              );
            })}
          </section>
          <div className="tr-answer" role="group" aria-label="평가 선택">
            {item.options.map(([value, label]) => (
              <Button
                key={value}
                variant={
                  draft.answers[item.id]?.value === value
                    ? 'default'
                    : 'outline'
                }
                aria-pressed={draft.answers[item.id]?.value === value}
                onClick={(event) => {
                  if (event.detail > 1) return;
                  setDraft({
                    ...draft,
                    answers: {
                      ...draft.answers,
                      [item.id]: { value, updatedAt: new Date().toISOString() },
                    },
                  });
                  move(index + 1);
                }}
              >
                {label}
              </Button>
            ))}
          </div>
          <footer>
            <Button
              variant="outline"
              disabled={index === 0}
              onClick={() => move(index - 1)}
            >
              ← 이전
            </Button>
            <Button
              disabled={!draft.answers[item.id]}
              onClick={() => move(index + 1)}
            >
              {index === list.length - 1 ? '응답 확인' : '다음 →'}
            </Button>
          </footer>
        </>
      ) : (
        <section className="tr-finish">
          <h1>응답을 제출해주세요.</h1>
          <p>
            {list.length}문항 중 {count}문항에 답했습니다. 제출 버튼을 누르면
            연구자에게 전달됩니다.
          </p>
          <Button disabled={busy || !validSubmission(draft)} onClick={submit}>
            {busy ? '저장 중…' : '응답 제출하기'}
          </Button>
          <Button variant="outline" disabled={busy} onClick={() => move(0)}>
            처음부터 응답 검토
          </Button>
          <details>
            <summary>문항별 응답 확인·수정</summary>
            {list.map((t, i) => (
              <button
                className="tr-summary"
                disabled={busy}
                key={t.id}
                onClick={() => move(i)}
              >
                {i + 1}. {t.kind === 'face' ? '얼굴 변화' : '얼굴 보존'} —{' '}
                {t.options.find(
                  (o) => o[0] === draft.answers[t.id]?.value,
                )?.[1] || '미응답'}
              </button>
            ))}
          </details>
        </section>
      )}
    </main>
  );
}
