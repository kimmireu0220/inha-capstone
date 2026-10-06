"""Save a read-only Slides snapshot and native previews for local inspection."""
import argparse
import json
from pathlib import Path
from urllib.request import urlopen
from googleapiclient.discovery import build
from update_google_slides import credentials, DEFAULT_CLIENT_FILE, PRESENTATION_ID


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--thumbnails', action='store_true')
    args = parser.parse_args()
    service = build('slides', 'v1', credentials=credentials(DEFAULT_CLIENT_FILE))
    deck = service.presentations().get(presentationId=PRESENTATION_ID).execute()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'presentation.json').write_text(json.dumps(deck, ensure_ascii=False, indent=2))
    print(f"Read {len(deck['slides'])} slides at revision {deck.get('revisionId')}", flush=True)
    if args.thumbnails:
        for index, slide in enumerate(deck['slides'], 1):
            thumbnail = service.presentations().pages().getThumbnail(
                presentationId=PRESENTATION_ID, pageObjectId=slide['objectId'],
                thumbnailProperties_thumbnailSize='LARGE').execute()
            with urlopen(thumbnail['contentUrl'], timeout=60) as response:
                (args.output_dir / f'slide-{index:02d}.png').write_bytes(response.read())
            print(f'Preview {index}', flush=True)


if __name__ == '__main__':
    main()
