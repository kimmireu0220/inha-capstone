"""Offline source/spec and revision-safe publication regression tests."""
import unittest
from unittest.mock import Mock, patch
import publish_method_slides as publish


class SlidesTests(unittest.TestCase):
    def test_spec_uses_frozen_numeric_results(self):
        slides = publish.spec()
        self.assertEqual(len(slides), 10)
        self.assertEqual(slides[2]['table'][-1][1:], ['29/32', '7/8', '0'])
        self.assertEqual(slides[3]['table'][-1][1:], ['29/32', '8/8', '1'])
        self.assertEqual(slides[6]['table'][1][1:], ['350/384', '358/384'])
        self.assertEqual(slides[6]['table'][2][1:], ['372/384', '374/384'])
        self.assertIn('재검토 4/16, 규칙 보정 16/16', slides[7]['body'])
        self.assertIn('별도 구현', slides[7]['foot'])
        self.assertIn('사후 진단', slides[8]['notes'])

    def test_missing_targets_fail_closed(self):
        with self.assertRaises(ValueError):
            publish.requests({'slides': []})
        with self.assertRaises(ValueError):
            publish.text_requests({'slides': []})

    def test_text_edits_preserve_objects(self):
        deck = {'slides': []}
        for sid, item in zip(publish.IDS, publish.spec()):
            elements = [{'objectId': sid+'_method_'+key, 'shape': {}}
                        for key in ['title', 'body', 'intro', 'below', 'foot'] if key in item]
            if 'table' in item:
                elements.append({'objectId': sid+'_method_table', 'table': {
                    'tableRows': [{'tableCells': [{} for _ in row]} for row in item['table']]}})
            if 'person' in item:
                elements.extend({'objectId': sid+f'_method_label{j}', 'shape': {}} for j in range(4))
            deck['slides'].append({'objectId': sid, 'pageElements': elements,
                'slideProperties': {'notesPage': {'notesProperties': {'speakerNotesObjectId': sid+'_notes'}}}})
        requests = publish.text_requests(deck)
        self.assertTrue(requests)
        self.assertTrue(all(set(r) <= {'deleteText', 'insertText'} for r in requests))
        self.assertEqual(sum('cellLocation' in r.get('insertText', {}) for r in requests), 49)
        deck['slides'][0]['pageElements'] = []
        with self.assertRaises(ValueError):
            publish.text_requests(deck)

    def test_editorial_cleanup(self):
        content = str(publish.spec())
        for phrase in ['논문 채택', '미확정', '새 훼손', '유리한 결과', '유지 보호만', '삭제 실행만',
                       '추가 확인이 필요', '아직 확인이 필요', '추가 검증이 필요']:
            self.assertNotIn(phrase, content)

    def test_plan_reuses_slides_and_native_evidence(self):
        deck = {'slides': [{'objectId': sid, 'pageElements': [], 'slideProperties': {'notesPage': {'notesProperties': {'speakerNotesObjectId': sid+'_notes'}}}} for sid in publish.IDS]}
        req = publish.requests(deck)
        self.assertEqual(sum('createTable' in r for r in req), 3)
        self.assertEqual(sum('createImage' in r for r in req), 8)
        self.assertFalse(any('createSlide' in r for r in req))
        self.assertFalse(any('deleteObject' in r for r in req))

    def test_stale_revision_never_writes(self):
        old = {'presentationId': publish.PRESENTATION_ID, 'revisionId': 'old', 'slides': []}
        service = Mock()
        service.presentations.return_value.get.return_value.execute.return_value = {'revisionId': 'new'}
        with patch('sys.argv', ['publish_method_slides.py', '--snapshot', 'ignored.json', '--apply']), \
             patch.object(publish.Path, 'read_text', return_value='{}'), \
             patch.object(publish.json, 'loads', return_value=old), \
             patch.object(publish, 'requests', return_value=[]), \
             patch.object(publish, 'credentials'), patch.object(publish, 'build', return_value=service):
            with self.assertRaises(SystemExit):
                publish.main()
        service.presentations.return_value.batchUpdate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
