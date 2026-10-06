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

    def test_missing_targets_fail_closed(self):
        with self.assertRaises(ValueError):
            publish.requests({'slides': []})

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
