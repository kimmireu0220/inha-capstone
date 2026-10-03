"""Render with the bundled document helper and explicit host font directories."""
import argparse
import os
from pathlib import Path
import subprocess
from xml.sax.saxutils import escape


def font_config(directories, cache):
    existing = [Path(path).resolve() for path in directories if Path(path).is_dir()]
    if not existing:
        raise ValueError('No readable font directory was found')
    return ('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
            '<fontconfig>\n' + ''.join(f'  <dir>{escape(str(path))}</dir>\n' for path in existing)
            + f'  <cachedir>{escape(str(cache.resolve()))}</cachedir>\n</fontconfig>\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True,
                        help='Dependency root returned by the workspace dependency loader')
    parser.add_argument('--renderer', type=Path, required=True,
                        help='Documents skill render_docx.py path')
    parser.add_argument('--input', type=Path, default=Path(__file__).parent / 'manuscript.inha.docx')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--font-dir', type=Path, action='append', default=[])
    args = parser.parse_args()
    python = args.runtime_root.resolve() / 'python/bin/python3'
    for path in (python, args.renderer, args.input):
        if not path.is_file():
            parser.error(f'Missing required file: {path}')
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cache = output / 'font-cache'
    cache.mkdir(exist_ok=True)
    directories = args.font_dir or [Path('/System/Library/Fonts'), Path('/Library/Fonts'),
                                   Path.home() / 'Library/Fonts', Path('/usr/share/fonts'),
                                   Path.home() / '.local/share/fonts']
    config = output / 'fonts.conf'
    config.write_text(font_config(directories, cache), encoding='utf-8')
    env = os.environ.copy()
    env['FONTCONFIG_FILE'] = str(config)
    subprocess.run([str(python), str(args.renderer.resolve()), str(args.input.resolve()),
                    '--output_dir', str(output), '--emit_pdf', '--verbose'], env=env, check=True)


if __name__ == '__main__':
    main()
