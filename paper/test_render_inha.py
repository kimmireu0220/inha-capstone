import tempfile
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from render_inha import font_config


class FontConfigTests(unittest.TestCase):
    def test_existing_directories_and_xml_escaping(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            fonts = root / 'fonts & Korean'
            fonts.mkdir()
            xml = font_config([fonts, root / 'missing'], root / 'cache')
            tree = ET.fromstring(xml)
            self.assertEqual([element.text for element in tree.findall('dir')], [str(fonts)])
            self.assertEqual(tree.find('cachedir').text, str(root / 'cache'))

    def test_no_fonts_is_an_explicit_failure(self):
        with self.assertRaises(ValueError):
            font_config([], Path('/tmp/unused-font-cache'))


if __name__ == '__main__':
    unittest.main()
