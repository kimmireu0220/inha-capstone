# Google Slides 이미지 삽입

## 현재 연결과 재인증

2026-10-06 현재 기존 OAuth 갱신이 실패했고 Google Drive 플러그인도 연결되지 않았다. 아래 스크립트는 과거 비교 슬라이드용이며 최신 S·T 논문을 반영하는 일괄 갱신 스크립트가 아니다. 현재 발표의 반영 상태는 [발표 자료 안내](../artifacts/README.md)를 기준으로 확인한다.

Google Drive 플러그인을 연결하거나, 기존 데스크톱 OAuth 방식으로 다음 명령을 사용해 재승인할 수 있다. 승인에는 슬라이드 편집 계정의 사용자 로그인이 필요하다.

```sh
.venv-slides/bin/python scripts/update_google_slides.py --reauthorize --auth-only
```

명령은 브라우저를 자동으로 열지 않고 승인 주소를 출력한다. 5분 동안 승인을 기다리며, 성공한 뒤에만 기존 토큰을 교체하고 파일 권한을 0600으로 설정한다. 실패한 인증으로 기존 토큰을 지우지 않는다. 이 명령은 슬라이드를 읽거나 변경하지 않는다. 토큰과 OAuth 클라이언트 파일을 저장소에 커밋하거나 채팅에 붙이지 않는다.

연결을 마친 다음에는 현재 슬라이드 내용과 배치를 다시 읽고 최신 논문의 범위에 맞게 수정해야 한다. 과거 객체 ID를 검증 없이 재사용하지 않는다.

## 과거 비교 슬라이드용 명령

대상: [연구 발표 슬라이드](https://docs.google.com/presentation/d/1UjTZ-HbxiGbb3QH2mnUWeFUk-_o9POx3Ay134fZ9qb8/edit)의 `6인물·3시드 확대 비교` 장. 비교 이미지 한 장을 삽입한다. 같은 이미지가 있으면 다시 넣지 않는다.

Google Cloud 프로젝트 `Inha Capstone Slides` (`zeta-post-509112-u2`)에 Google Slides API와 데스크톱 OAuth 클라이언트를 설정했다. 최초 승인과 이미지 삽입도 완료했다. [Google Slides API 빠른 시작](https://developers.google.com/workspace/slides/api/quickstart/python).

인증 파일은 저장소 밖의 `~/.config/inha-capstone/google-slides-client.json`에, 인증 토큰은 같은 폴더의 `google-slides-token.json`에 저장한다. 이후에는 아래 명령으로 대상 슬라이드를 확인하거나 이미지를 다시 삽입할 수 있다. 스크립트는 같은 이미지를 중복 삽입하지 않는다.

```sh
.venv-slides/bin/python scripts/update_google_slides.py
.venv-slides/bin/python scripts/update_google_slides.py --apply
```

ArcFace 지표와 18쌍 결과, 발표자 노트를 다시 반영할 때는 다음 명령을 사용한다.

```sh
.venv-slides/bin/python scripts/update_arcface_google_slides.py
```

새 컴퓨터라면 Python 가상환경을 만들고 `google-api-python-client`, `google-auth-oauthlib`를 설치한다. `--apply` 없이 실행하면 대상 슬라이드만 확인한다.
