"""Check native readback; --reviewed-all attests actual preview inspection."""
import argparse
import hashlib
import json
from pathlib import Path
from publish_method_slides import ROOT, IDS, SOURCES, IMAGE_COMMIT, spec, sha
from update_google_slides import PRESENTATION_ID


def text_of(text):
    return ''.join(e.get('textRun', {}).get('content', '') for e in text.get('textElements', [])).rstrip('\n')


def verify(deck):
    assert deck['presentationId'] == PRESENTATION_ID
    assert [s['objectId'] for s in deck['slides']] == IDS
    expected = spec()
    counts = {'tables': 0, 'images': 0, 'notes': 0}
    for number, (slide, item) in enumerate(zip(deck['slides'], expected), 1):
        sid = slide['objectId']
        els = {e['objectId']: e for e in slide.get('pageElements', [])}
        for key in ['title', 'body', 'intro', 'below', 'foot']:
            if key in item:
                assert text_of(els[sid+'_method_'+key]['shape']['text']) == item[key], (number, key)
        assert text_of(els[sid+'_method_num']['shape']['text']) == str(number)
        if 'table' in item:
            rows = [[text_of(c['text']) for c in r['tableCells']] for r in els[sid+'_method_table']['table']['tableRows']]
            assert rows == item['table'], number
            counts['tables'] += 1
        if 'person' in item:
            provenance = json.loads((ROOT/SOURCES[2]).read_text())
            figure = next(f for f in provenance['figures'] if item['person'] in f['figure'])
            for j, source in enumerate(figure['sources']):
                img = els[sid+f'_method_image{j}']['image']
                assert img['sourceUrl'] == f'https://raw.githubusercontent.com/kimmireu0220/inha-capstone/{IMAGE_COMMIT}/'+source['source']
                assert sha(ROOT/source['source']) == source['sha256']
                crop = img.get('imageProperties', {}).get('cropProperties', {})
                assert all(crop.get(key, 0) == 0 for key in ['leftOffset', 'rightOffset', 'topOffset', 'bottomOffset', 'angle'])
                counts['images'] += 1
        notes = slide['slideProperties']['notesPage']
        nid = notes['notesProperties']['speakerNotesObjectId']
        note = next(e for e in notes['pageElements'] if e['objectId'] == nid)
        assert text_of(note['shape']['text']) == item['notes'], number
        counts['notes'] += 1
    assert counts == {'tables': 3, 'images': 8, 'notes': 10}
    return expected, counts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot-dir', type=Path, required=True)
    p.add_argument('--reviewed-all', action='store_true')
    args = p.parse_args()
    snapshot = args.snapshot_dir/'presentation.json'
    deck = json.loads(snapshot.read_text())
    expected, counts = verify(deck)
    print(f'Native text, tables, image provenance and notes verified: {counts}')
    if args.reviewed_all:
        record = {'date': '2026-10-06', 'presentation_id': PRESENTATION_ID, 'revision_id': deck['revisionId'],
                  'slides': len(IDS), 'slide_ids': IDS,
                  'paper_alignment': 'S/T constrained state updates with P/S image limitations',
                  'source_sha256': {path: sha(ROOT/path) for path in SOURCES},
                  'script_sha256': {path: sha(ROOT/path) for path in ['scripts/publish_method_slides.py', 'scripts/verify_method_slides.py']},
                  'content_sha256': hashlib.sha256(json.dumps(expected, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                  'editable_evidence': counts, 'snapshot_sha256': sha(snapshot),
                  'visual_check': {'method': 'Google Slides native LARGE thumbnails, all ten reviewed at 1600x900',
                                   'reviewed_slides': list(range(1, len(IDS)+1)),
                                   'visible_overlap_or_clipping_found': False,
                                   'preview_sha256': {str(n): sha(args.snapshot_dir/f'slide-{n:02d}.png') for n in range(1, len(IDS)+1)}},
                  'scope': 'Presentation fidelity and source alignment, not independent scientific validation'}
        (ROOT/'artifacts/slides-verification.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
