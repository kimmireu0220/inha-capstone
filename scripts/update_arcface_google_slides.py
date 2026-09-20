"""Add the verified ArcFace result to the existing research deck."""

from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


PRESENTATION_ID = "1UjTZ-HbxiGbb3QH2mnUWeFUk-_o9POx3Ay134fZ9qb8"
TOKEN_FILE = Path.home() / ".config/inha-capstone/google-slides-token.json"
SCOPES = ["https://www.googleapis.com/auth/presentations"]

REPLACEMENTS = {
    "p14": {
        "g409d78e8dcd_8_116": "평가 지표: MAE · SSIM · LPIPS · ArcFace",
        "p14_i5": (
            "MAE·LPIPS는 낮을수록, SSIM·ArcFace는 높을수록 원본에 가까움\n"
            "얼굴 거리와 얼굴 특징 유사도를 함께 비교"
        ),
    },
    "g40a042314fc_1_0": {
        "g40a042314fc_1_6": (
            "얼굴 LPIPS  일괄 0.087120 / 순차 0.108710  19.9% 감소\n"
            "ArcFace 0.922 / 0.714 · LPIPS·SSIM·ArcFace 18/18쌍 일괄 유리"
        ),
    },
    "p24": {
        "p24_i9": (
            "6명 × 3회 = 최종 18쌍\n"
            "LPIPS 평균 19.9% 감소 · SSIM 18/18쌍 일괄 유리\n"
            "ArcFace 0.922 / 0.714 · 18/18쌍 일괄 유리"
        ),
    },
}

NOTES = {
    "p14": (
        "발표 설명\n"
        "얼굴 영역의 픽셀 및 지각 차이는 MAE, SSIM, LPIPS로 계산했습니다. "
        "ArcFace는 얼굴을 512차원 특징으로 바꾼 뒤 원본과의 코사인 유사도를 계산합니다. "
        "ArcFace 값이 높을수록 원본의 얼굴 특징에 가깝습니다.\n\n"
        "근거\n"
        "https://github.com/kimmireu0220/inha-capstone/blob/main/experiments/nonhuman-followup-v1/metrics/PROTOCOL.md\n"
        "https://openaccess.thecvf.com/content_CVPR_2019/html/Deng_ArcFace_Additive_Angular_Margin_Loss_for_Deep_Face_Recognition_CVPR_2019_paper.html\n"
        "https://github.com/deepinsight/insightface"
    ),
    "g40a042314fc_1_0": (
        "발표 설명\n"
        "같은 사이트의 생성 과정을 가상 인물 6명에게 각각 3번 적용했습니다. "
        "최종 18쌍에서 일괄 방식의 얼굴 LPIPS가 평균 19.9% 낮았습니다. "
        "원본 대비 ArcFace 유사도는 일괄 0.922, 순차 0.714였고 18쌍 모두 일괄 방식이 높았습니다.\n\n"
        "근거\n"
        "https://github.com/kimmireu0220/inha-capstone/blob/main/experiments/studio-multiperson-v1/RESULTS.md\n"
        "https://github.com/kimmireu0220/inha-capstone/blob/main/experiments/studio-multiperson-v1/arcface-results.json"
    ),
    "p24": (
        "발표 설명\n"
        "직전 결과를 계속 입력하면 원본과의 얼굴 차이가 쌓였습니다. "
        "편집기는 최초 원본과 현재 요구를 따로 저장하고 두 생성 방식을 선택할 수 있게 구성했습니다. "
        "6명에게 세 번씩 적용한 최종 18쌍에서 LPIPS, SSIM, ArcFace가 모두 일괄 방식에 유리했습니다.\n\n"
        "근거\n"
        "https://github.com/kimmireu0220/inha-capstone/blob/main/paper/manuscript.inha.pdf\n"
        "https://github.com/kimmireu0220/inha-capstone/blob/main/experiments/studio-multiperson-v1/RESULTS.md"
    ),
}

ARCFACE_ROW = [
    "ArcFace\n얼굴 특징 유사도",
    "512차원 얼굴 임베딩의 코사인 유사도",
    "얼굴 정체성 특징 보존을 확인",
    "높을수록 원본 얼굴 특징과 유사",
]


def replace_text_requests(object_id, value):
    return [
        {"deleteText": {"objectId": object_id, "textRange": {"type": "ALL"}}},
        {"insertText": {"objectId": object_id, "insertionIndex": 0, "text": value}},
    ]


def main():
    credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    service = build("slides", "v1", credentials=credentials)
    presentation = service.presentations().get(presentationId=PRESENTATION_ID).execute()
    slide_by_id = {slide["objectId"]: slide for slide in presentation["slides"]}
    requests = []
    for slide_id, elements in REPLACEMENTS.items():
        present_ids = {e["objectId"] for e in slide_by_id[slide_id].get("pageElements", [])}
        for element_id, value in elements.items():
            if element_id not in present_ids:
                raise RuntimeError(f"Missing element {element_id} on {slide_id}")
            requests.extend(replace_text_requests(element_id, value))
    for slide_id, value in NOTES.items():
        notes_id = slide_by_id[slide_id]["slideProperties"]["notesPage"]["notesProperties"]["speakerNotesObjectId"]
        requests.extend(replace_text_requests(notes_id, value))
    metric_table = next(
        element for element in slide_by_id["p14"]["pageElements"]
        if element["objectId"] == "p14_i9"
    )
    rows = metric_table["table"]["rows"]
    if rows == 4:
        requests.append({
            "insertTableRows": {
                "tableObjectId": "p14_i9",
                "cellLocation": {"rowIndex": 3, "columnIndex": 0},
                "insertBelow": True,
                "number": 1,
            }
        })
    elif rows != 5:
        raise RuntimeError(f"Unexpected metric-table row count: {rows}")
    for column, value in enumerate(ARCFACE_ROW):
        if rows == 5:
            requests.append({
                "deleteText": {
                    "objectId": "p14_i9",
                    "cellLocation": {"rowIndex": 4, "columnIndex": column},
                    "textRange": {"type": "ALL"},
                }
            })
        requests.append({
            "insertText": {
                "objectId": "p14_i9",
                "cellLocation": {"rowIndex": 4, "columnIndex": column},
                "insertionIndex": 0,
                "text": value,
            }
        })
    requests.append({
        "updateTableRowProperties": {
            "objectId": "p14_i9",
            "rowIndices": [0, 1, 2, 3, 4],
            "tableRowProperties": {
                "minRowHeight": {"magnitude": 800000, "unit": "EMU"}
            },
            "fields": "minRowHeight",
        }
    })
    service.presentations().batchUpdate(
        presentationId=PRESENTATION_ID, body={"requests": requests}
    ).execute()
    print(f"Updated {len(REPLACEMENTS)} slides and {len(NOTES)} speaker notes")


if __name__ == "__main__":
    main()
