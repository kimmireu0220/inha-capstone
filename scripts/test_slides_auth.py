"""Offline checks for explicit Slides reauthorization without deck mutation."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import update_google_slides as slides
from google.auth.exceptions import RefreshError


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.token = Path(self.temp.name) / 'token.json'
        self.token.touch()
        self.client = Path(self.temp.name) / 'client.json'
        self.client.touch()
        self.patcher = patch.object(slides, 'TOKEN_FILE', self.token)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_valid_token_does_not_start_login(self):
        creds = Mock(valid=True)
        with patch.object(slides.Credentials, 'from_authorized_user_file', return_value=creds), \
             patch.object(slides.InstalledAppFlow, 'from_client_secrets_file') as flow:
            self.assertIs(slides.credentials(self.client), creds)
            flow.assert_not_called()

    def test_refresh_failure_preserves_token_without_leaking_error(self):
        creds = Mock(valid=False, expired=True, refresh_token=True)
        creds.refresh.side_effect = RefreshError('sensitive provider response')
        before = self.token.read_bytes()
        with patch.object(slides.Credentials, 'from_authorized_user_file', return_value=creds), \
             patch.object(slides, 'Request'), \
             patch.object(slides.InstalledAppFlow, 'from_client_secrets_file') as flow:
            with self.assertRaises(SystemExit) as error:
                slides.credentials(self.client)
            self.assertIn('--reauthorize --auth-only', str(error.exception))
            self.assertNotIn('sensitive', str(error.exception))
            self.assertEqual(before, self.token.read_bytes())
            flow.assert_not_called()

    def test_explicit_reauthorization_only_saves_after_success(self):
        creds = Mock()
        creds.to_json.return_value = '{}'
        flow = Mock()
        flow.run_local_server.return_value = creds
        with patch.object(slides.Credentials, 'from_authorized_user_file') as load, \
             patch.object(slides.InstalledAppFlow, 'from_client_secrets_file', return_value=flow):
            self.assertIs(slides.credentials(self.client, reauthorize=True), creds)
            load.assert_not_called()
            flow.run_local_server.assert_called_once_with(port=0, open_browser=False, timeout_seconds=300)
        self.assertEqual(self.token.read_text(), '{}')
        self.assertEqual(self.token.stat().st_mode & 0o777, 0o600)

    def test_failed_login_preserves_token(self):
        flow = Mock()
        flow.run_local_server.side_effect = TimeoutError()
        before = self.token.read_bytes()
        with patch.object(slides.InstalledAppFlow, 'from_client_secrets_file', return_value=flow):
            with self.assertRaises(TimeoutError):
                slides.credentials(self.client, reauthorize=True)
        self.assertEqual(self.token.read_bytes(), before)

    def test_auth_only_never_opens_slides_service(self):
        with patch('sys.argv', ['update_google_slides.py', '--reauthorize', '--auth-only']), \
             patch.object(slides, 'credentials') as auth, patch.object(slides, 'build') as build:
            slides.main()
            self.assertTrue(auth.call_args.kwargs['reauthorize'])
            build.assert_not_called()


if __name__ == '__main__':
    unittest.main()
