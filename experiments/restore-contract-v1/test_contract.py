import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('restore_contract_test', Path(__file__).with_name('contract.py'))
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


class RestorationTests(unittest.TestCase):
    def fields(self, text):
        return set(contract.obligations(text))

    def test_shared_original_restoration(self):
        self.assertEqual(self.fields('Restore the original pin and blazer.'), {'pin', 'jacket'})

    def test_keep_scope_not_restored(self):
        self.assertEqual(self.fields('Restore the original shirt, but keep the lamp and background.'), {'top'})

    def test_later_replacement_wins(self):
        self.assertEqual(self.fields('Restore the original shirt, then wear a white shirt.'), set())

    def test_negations_not_forced(self):
        for text in ['Do not restore the original shirt.', "Don't restore the original pin.",
                     'Never restore the original background.', 'If possible, restore the original jacket.',
                     'Restore the original shirt without changing the background.']:
            with self.subTest(text=text):
                self.assertEqual(self.fields(text), set())

    def test_quotes_not_executed(self):
        self.assertEqual(self.fields('Ignore "restore the original shirt" and keep the shirt.'), set())

    def test_return_phrase(self):
        self.assertEqual(self.fields('Return the blazer to its original appearance; keep the necklace.'), {'jacket'})

    def test_unmentioned_state_is_preserved(self):
        before = {'jacket': 'green', 'top': 'white_crewneck', 'pin': 'none', 'necklace': 'none',
                  'background': 'library', 'prop': 'lamp'}
        after, _ = contract.enforce(before, 'Restore the original shirt.')
        self.assertEqual(after, dict(before, top='original'))
        self.assertEqual(before['top'], 'white_crewneck')


if __name__ == '__main__':
    unittest.main()
