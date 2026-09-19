"""Insert the six-person comparison image into the existing Google Slides deck.

Requires a Desktop OAuth client JSON from Google Cloud. The OAuth URL is printed
instead of opening a browser, so the user's active browser session is untouched.
"""

import argparse
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


PRESENTATION_ID = "1UjTZ-HbxiGbb3QH2mnUWeFUk-_o9POx3Ay134fZ9qb8"
SLIDE_TITLE = "6인물·3시드 확대 비교"
IMAGE_ID = "capstone_comparison_p03_314"
IMAGE_URL = (
    "https://raw.githubusercontent.com/kimmireu0220/inha-capstone/main/"
    "experiments/studio-multiperson-v1/comparison-P03-314.png"
)
SCOPES = ["https://www.googleapis.com/auth/presentations"]
TOKEN_FILE = Path.home() / ".config/inha-capstone/google-slides-token.json"
DEFAULT_CLIENT_FILE = Path.home() / ".config/inha-capstone/google-slides-client.json"


def credentials(client_file: Path):
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
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
    creds = flow.run_local_server(port=0, open_browser=False)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    return creds


def points(dimension):
    unit = dimension.get("unit", "EMU")
    magnitude = dimension["magnitude"]
    if unit == "PT":
        return magnitude
    if unit == "EMU":
        return magnitude / 12700
    raise ValueError(f"Unsupported page-size unit: {unit}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="실제 슬라이드에 이미지를 삽입")
    args = parser.parse_args()

    client_file = Path(
        os.environ.get("GOOGLE_SLIDES_OAUTH_CLIENT", str(DEFAULT_CLIENT_FILE))
    ).expanduser()
    service = build("slides", "v1", credentials=credentials(client_file))
    presentation = service.presentations().get(presentationId=PRESENTATION_ID).execute()
    matches = []
    for slide in presentation.get("slides", []):
        text = " ".join(
            element.get("textRun", {}).get("content", "")
            for page_element in slide.get("pageElements", [])
            for paragraph in page_element.get("shape", {}).get("text", {}).get("textElements", [])
            for element in [paragraph]
        )
        if SLIDE_TITLE in text:
            matches.append(slide)
    if len(matches) != 1:
        raise SystemExit(f"대상 제목이 있는 슬라이드가 {len(matches)}개입니다. 수정하지 않았습니다.")

    slide = matches[0]
    slide_id = slide["objectId"]
    if any(item["objectId"] == IMAGE_ID for item in slide.get("pageElements", [])):
        print(f"이미지가 이미 있습니다: {slide_id} ({IMAGE_ID})")
        return

    page_size = presentation["pageSize"]
    page_width = points(page_size["width"])
    page_height = points(page_size["height"])
    # Place the image below the title and two result lines, preserving aspect ratio.
    image_width = min(page_width * 0.61, (page_height * 0.58) * 1536 / 806)
    image_height = image_width * 806 / 1536
    x = (page_width - image_width) / 2
    y = page_height - image_height - page_height * 0.065
    request = {
        "createImage": {
            "objectId": IMAGE_ID,
            "url": IMAGE_URL,
            "elementProperties": {
                "pageObjectId": slide_id,
                "size": {
                    "width": {"magnitude": image_width, "unit": "PT"},
                    "height": {"magnitude": image_height, "unit": "PT"},
                },
                "transform": {
                    "scaleX": 1,
                    "scaleY": 1,
                    "translateX": x,
                    "translateY": y,
                    "unit": "PT",
                },
            },
        }
    }
    print(f"대상: 슬라이드 {slide_id}, 이미지 {IMAGE_ID}, {image_width:.0f}×{image_height:.0f}pt")
    if args.apply:
        service.presentations().batchUpdate(
            presentationId=PRESENTATION_ID, body={"requests": [request]}
        ).execute()
        print("삽입 완료:", f"https://docs.google.com/presentation/d/{PRESENTATION_ID}/edit")
    else:
        print("미리보기만 했습니다. 적용하려면 --apply를 추가하세요.")


if __name__ == "__main__":
    main()
