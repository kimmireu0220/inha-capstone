# 인물 이미지 공개 설문

- `/survey` (루트 연결): 연령대 선택 → 얼굴 변화 16문항 → 얼굴 보존 16문항 → 서버 제출.
- `/admin`: 관리자 접속 암호로 로그인, 최신 응답과 전체 CSV 다운로드.
- 같은 형식의 `/current-review` 예비 평가와 `/ten-stage` 얼굴 열화 화면은 유지한다. 형식이 다른 `/p03-review`, `/p03-stage4`, `/trigger-review` 혼합 설문은 제거했다.

공개 설문 버전은 `public-final-human-v2`다. 기존 결과 노출 여부와 참여 동의 체크박스는 사용자 요청으로 수집하지 않는다. DB의 호환용 exposure 필드는 `not_collected`이고 응답 CSV에서 제외한다. 과거 R01 응답과 섞지 않는다.

참여자마다 후보 순서를 무작위로 정해 브라우저 초안에 보존하고 두 평가 부문에 같은 순서를 적용한다. 제출 시 서버가 전체 응답과 후보 순서를 검증하고 이미지 SHA256을 기록한다. 참여 번호는 무작위 UUID이며 같은 번호와 같은 응답의 재시도는 중복 저장하지 않는다. 새 브라우저로 재참여하는 동일인을 식별하거나 차단하는 기능은 없다. 브라우저 초안은 임시 복구용이고 최종 응답은 Cloudflare D1에 저장한다.

## 개발 및 검증

```
npm run dev -- --port 8766
npx tsc --noEmit
npm run build
python3 scripts/test-survey.py
```

API 통합 검증은 localhost:8766과 로컬 DB만 사용한다. 테스트 응답은 실제 사람 평가가 아니다. `.dev.vars`에 최소 32자 이상의 무작위 `ADMIN_PASSWORD`가 필요하다. 접속 암호는 소스에 포함하지 않는다.

## Cloudflare 직접 배포

사용자가 Cloudflare 무료 플랜 배포를 선택했다. 기존 Sites project_id는 조회 시 NOT_FOUND여서 그대로 보존했고 새 Sites 프로젝트를 만들지 않았다. `wrangler.deploy.json`은 이 Cloudflare 계정용 설정으로 Git에서 제외한다. `wrangler.deploy.example.json`은 재설정용 예시다. 실제 설정은 `dist/server/wrangler.json`을 기반으로 생성하며 main/assets/D1 연결을 변경하고 `no_bundle`과 ESModule 규칙을 유지한다.

```
npm run build
npx wrangler d1 migrations apply DB --remote --config wrangler.deploy.json
npx wrangler deploy --config wrangler.deploy.json
npx wrangler secret put ADMIN_PASSWORD --config wrangler.deploy.json
```

무료 사용량을 넘으면 요청·저장이 실패할 수 있다. 유료 플랜이나 별도 도메인 구매는 설정하지 않는다. 이미지 파일은 정적 assets로 배포한다. 관리자 세션은 8시간 동안 유효한 HttpOnly/SameSite=Strict 쿠키이며 HTTPS에서는 Secure를 사용한다. 응답 API와 CSV는 서버에서 권한을 확인한다. API 성공 확인 전에는 사용자에게 제출 완료로 표시하지 않는다. 이메일 알림은 구현 범위에 포함하지 않았으며 관리 화면에서 확인한다.

## 현재 공개 주소

- 설문: https://inha-face-survey.inha-capstone-survey.workers.dev/survey
- 관리자: https://inha-face-survey.inha-capstone-survey.workers.dev/admin
- 관리자 접속 정보는 Git에서 제외된 `.admin-access.txt`에 보관한다.
- 2026-09-07 공개 배포 완료. 타입 검사와 빌드, 로컬 제출·중복·CSV 통합 검증 통과. 공개 주소에서 이미지·관리자 인증·D1 조회·CSV·로그아웃 검증 통과. 공개 DB에 테스트 응답은 생성하지 않았다.

## 2026-09-09 추가 실험 평가

- `/followup-survey`: P04/P05/P06 × 일괄/SBP × 2반복의 최종12개, 얼굴 변화12 + 얼굴 보존12 =24문항.
- `/followup-admin`: 기존 관리자 로그인으로 이번 설문 응답·CSV 조회.
- schema: `followup-batch-sequential-human-v1`. 기존32문항·응답을 변경하거나 합산하지 않는다.
- 첫 화면·문항·척도는 기존 설문 형식을 유지한다. 원본 파일을 그대로 제공하고 얼굴 변화 문항은 인물별320×360 ROI를 CSS로 표시한다. PNG를 재생성하거나 보정하지 않는다. 저장 payload에는 전체PNG SHA256과 표시좌표 `displayRegions`를 함께 기록한다. CSV에도 표시좌표가 있으며 얼굴 SHA256은 잘린 파일이 아닌 전체 원본 파일 해시다.
- 후보 ID는 무작위이며 방법명·점수는 공개 data/bundle에 포함하지 않는다. 해독표는 Git/배포에서 제외된 `private/followup-key.json`에 보관한다.
- 이번 참여를 요청한 연구자는 이미 결론·생성 이미지를 보았으므로 해당 응답은 결과 노출이 있는 예비 평가로 해석해야 한다. 참가자 전체의 블라인드 독립 평가라고 부르지 않는다. 노출 질문을 다시 추가하지 않았다.
- 이번24문항은 얼굴 열화·얼굴 보존만 수집한다. 편집 요구 충족의 독립 평가는 아직 포함하지 않았다.
- 로컬 검증: `python3 scripts/test-followup-survey.py`. 실제 사람 응답과 별개인 합성 테스트는 로컬에서만 생성하고, 확인 후 그 테스트 ID만 삭제한다.

### 두 문항 재평가

`/followup-recheck`는 사용자가 요청한 빠른 연속 응답의 두 얼굴 변화 문항만 다시 제시한다. 척도와 이미지/ROI는 최초 평가와 같고 이전 답은 표시하지 않는다. schema는 `followup-face-recheck-v1`, 저장 payload의 `correctsSubmission`은 최초 제출과 연결한다. 원본 응답은 덮어쓰지 않는다. 이 페이지는 연령대를 다시 묻지 않고 `응답하지 않음`으로 기록한다. 분석 시 최초 제출의 인구통계와 별도 재평가 기록임을 구분한다. 더블클릭의 두 번째 이벤트는 무시한다. 재평가는 기존 `/followup-admin`의 최초 평가 집계와 합산하지 않으며 별도 schema로 조회한다.
