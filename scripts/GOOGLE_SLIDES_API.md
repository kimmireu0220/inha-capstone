# Google Slides 이미지 삽입

대상: [연구 발표 슬라이드](https://docs.google.com/presentation/d/1UjTZ-HbxiGbb3QH2mnUWeFUk-_o9POx3Ay134fZ9qb8/edit)의 `6인물·3시드 확대 비교` 장. 비교 이미지 한 장을 삽입한다. 같은 이미지가 있으면 다시 넣지 않는다.

Google Cloud 프로젝트 `Inha Capstone Slides` (`zeta-post-509112-u2`)에 Google Slides API와 데스크톱 OAuth 클라이언트를 설정했다. 최초 승인과 이미지 삽입도 완료했다. [Google Slides API 빠른 시작](https://developers.google.com/workspace/slides/api/quickstart/python).

인증 파일은 저장소 밖의 `~/.config/inha-capstone/google-slides-client.json`에, 인증 토큰은 같은 폴더의 `google-slides-token.json`에 저장한다. 이후에는 아래 명령으로 대상 슬라이드를 확인하거나 이미지를 다시 삽입할 수 있다. 스크립트는 같은 이미지를 중복 삽입하지 않는다.

```sh
.venv-slides/bin/python scripts/update_google_slides.py
.venv-slides/bin/python scripts/update_google_slides.py --apply
```

새 컴퓨터라면 Python 가상환경을 만들고 `google-api-python-client`, `google-auth-oauthlib`를 설치한다. `--apply` 없이 실행하면 대상 슬라이드만 확인한다.
