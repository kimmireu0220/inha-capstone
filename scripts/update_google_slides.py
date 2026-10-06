"""Shared Google Slides OAuth credentials and explicit authentication CLI."""

import argparse
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


PRESENTATION_ID = "1UjTZ-HbxiGbb3QH2mnUWeFUk-_o9POx3Ay134fZ9qb8"
SCOPES = ["https://www.googleapis.com/auth/presentations"]
TOKEN_FILE = Path.home() / ".config/inha-capstone/google-slides-token.json"
DEFAULT_CLIENT_FILE = Path.home() / ".config/inha-capstone/google-slides-client.json"


def credentials(client_file: Path, *, reauthorize=False):
    if TOKEN_FILE.exists() and not reauthorize:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                raise SystemExit(
                    "Google 인증을 갱신하지 못했습니다. 기존 토큰은 보존했습니다. "
                    "--reauthorize --auth-only로 다시 승인하세요."
                ) from None
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
            TOKEN_FILE.chmod(0o600)
            return creds

    if not client_file.is_file():
        raise SystemExit(
            "OAuth 인증 파일이 없습니다. GOOGLE_SLIDES_OAUTH_CLIENT에 Google Cloud에서 "
            "받은 Desktop app JSON의 경로를 지정하세요."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(client_file), SCOPES)
    print("표시되는 주소를 편할 때 직접 열고, 슬라이드 편집 계정으로 승인하세요.")
    creds = flow.run_local_server(port=0, open_browser=False, timeout_seconds=300)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    return creds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reauthorize", action="store_true", help="기존 토큰 대신 새 계정 승인을 요청")
    parser.add_argument("--auth-only", action="store_true", help="인증만 수행하며 슬라이드는 변경하지 않음")
    args = parser.parse_args()
    client_file = Path(os.environ.get("GOOGLE_SLIDES_OAUTH_CLIENT", str(DEFAULT_CLIENT_FILE))).expanduser()
    credentials(client_file, reauthorize=args.reauthorize)
    print("인증 완료. 슬라이드는 수정하지 않았습니다.")


if __name__ == "__main__":
    main()
