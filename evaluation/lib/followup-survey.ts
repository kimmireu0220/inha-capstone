import candidates from '@/app/followup-survey/data.json';
export { candidates };
export const SCHEMA = 'followup-batch-sequential-human-v1';
export const AGES = [
  '19세 이하',
  '20대',
  '30대',
  '40대',
  '50대',
  '60대 이상',
  '응답하지 않음',
];
export const grades = [
  ['0', '없음'],
  ['1', '약함'],
  ['2', '뚜렷함'],
  ['3', '심함'],
  ['unknown', '판단 어려움'],
];
export const preserved = [
  ['2', '유지'],
  ['1', '일부 유지'],
  ['0', '미유지'],
  ['unknown', '판단 어려움'],
];
export type Answer = { value: string; updatedAt: string };
export type Submission = {
  schema: string;
  id: string;
  age: string;
  startedAt: string;
  order: string[];
  answers: Record<string, Answer>;
};
export function tasks(order: string[]) {
  return ['face', 'preservation'].flatMap((kind) =>
    order.map((id) => ({
      id: id + '-' + kind,
      candidate: candidates.find((c) => c.id === id)!,
      kind,
      options: kind === 'face' ? grades : preserved,
    })),
  );
}
export function validSubmission(d: Submission): boolean {
  if (
    !d ||
    d.schema !== SCHEMA ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
      d.id,
    ) ||
    !AGES.includes(d.age)
  )
    return false;
  if (
    !Array.isArray(d.order) ||
    d.order.length !== candidates.length ||
    new Set(d.order).size !== candidates.length ||
    d.order.some((id) => !candidates.some((c) => c.id === id))
  )
    return false;
  if (
    typeof d.startedAt !== 'string' ||
    !Number.isFinite(Date.parse(d.startedAt)) ||
    !d.answers ||
    Object.keys(d.answers).length !== candidates.length * 2
  )
    return false;
  return tasks(d.order).every((t) => {
    const a = d.answers[t.id];
    return (
      a &&
      t.options.some((o) => o[0] === a.value) &&
      typeof a.updatedAt === 'string' &&
      Number.isFinite(Date.parse(a.updatedAt))
    );
  });
}
