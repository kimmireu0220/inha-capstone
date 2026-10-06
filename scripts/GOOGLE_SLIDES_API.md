# Google Slides API 관리

2026-10-06 OAuth 재승인과 최신 방법 논문 반영을 완료했다. [발표 자료](../artifacts/README.md)는 10장이다. 토큰과 OAuth 클라이언트 파일은 저장소 밖의 `~/.config/inha-capstone/`에만 둔다.

## 읽기와 편집

먼저 현재 내용과 실제 미리보기를 비공개 빌드 폴더에 저장한다.

```sh
.venv-slides/bin/python scripts/inspect_google_slides.py --output-dir .codex-build/slides-inspection --thumbnails
```

모든 장을 검토한 뒤 아래 명령으로 변경 계획을 확인한다. `--apply`를 추가해야 실제 수정한다. 스냅샷과 현재 리비전이 다르면 중단하며, API 리비전 잠금으로 동시 수정을 덮어쓰지 않는다. 이 명령은 기존 발표를 최신 10장 구성으로 정리하므로 별도 추가한 페이지가 있다면 먼저 의도를 확인한다.

```sh
.venv-slides/bin/python scripts/publish_method_slides.py --snapshot .codex-build/slides-inspection/presentation.json
```

변경 후 새 폴더에 다시 읽고, 전체 미리보기를 직접 확인한다. `verify_method_slides.py --snapshot-dir <새 폴더>`는 수치·본문·표·노트·이미지 출처를 대조한다. 모든 장을 실제로 검토했을 때만 `--reviewed-all`로 검증 기록을 저장한다. 미리보기 URL이 포함된 원본 스냅샷은 커밋하지 않는다.

## 필요할 때만 재인증

```sh
.venv-slides/bin/python scripts/update_google_slides.py --reauthorize --auth-only
```

이 명령은 승인 주소를 출력하고 최대 5분간 기다린다. 성공한 뒤에만 토큰을 교체하고 권한을 0600으로 설정한다. 실패 시 기존 토큰을 보존한다. 슬라이드에는 접근하거나 쓰지 않는다.

필요 패키지는 `google-api-python-client`, `google-auth-oauthlib`다. 이전 이미지 삽입 및 ArcFace 전용 갱신 코드는 Git 이력으로 정리했다. 현재 발표에 과거 객체 ID나 수치를 재삽입하지 않는다.
