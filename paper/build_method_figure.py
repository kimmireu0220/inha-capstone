"""Draw the conceptual method diagram without altering experiment images.

SVG elements and their PNG raster counterpart share the same coordinates.
"""
from pathlib import Path
import hashlib
import json
import math
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'paper/figures'
FONT = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
SOURCES = [
    'local-studio/instruction_pipeline.py',
    'local-studio/request_state.py',
    'experiments/instruction-eligibility-v1/method.py',
    'experiments/operation-scope-v2/method.py',
    'experiments/clause-normalization-v1/method.py',
]
DPI = 300
SCALE = DPI / 2.54


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    width, height = round(16 * SCALE), round(4.7 * SCALE)
    canvas = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(canvas)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="16cm" height="4.7cm" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="white"/>']

    def point(x, y):
        return (x * SCALE, (4.7 - y) * SCALE)

    def line(start, end):
        a, b = point(*start), point(*end)
        draw.line([a, b], fill='black', width=3)
        svg.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="black" stroke-width="3"/>')

    def text(x, y, value, size=9.5):
        font_px = size * DPI / 72
        font = ImageFont.truetype(FONT, round(font_px))
        items = value.split('\n')
        line_height = font_px * 1.35
        for i, item in enumerate(items):
            a, b = point(x, y)
            b += (i - (len(items) - 1) / 2) * line_height
            draw.text((a, b), item, font=font, fill='black', anchor='mm')
            svg.append(f'<text x="{a}" y="{b}" font-family="Apple SD Gothic Neo, sans-serif" font-size="{font_px}" text-anchor="middle" dominant-baseline="central" fill="black">{escape(item)}</text>')

    def arrow(start, end):
        a, b = point(*start), point(*end)
        dx, dy = b[0] - a[0], b[1] - a[1]
        norm = math.hypot(dx, dy)
        dx, dy = dx / norm, dy / norm
        tip = 15
        base = (b[0] - dx * tip, b[1] - dy * tip)
        draw.line([a, base], fill='black', width=3)
        triangle = [b, (base[0] - dy * 6, base[1] + dx * 6),
                    (base[0] + dy * 6, base[1] - dx * 6)]
        draw.polygon(triangle, fill='black')
        svg.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{base[0]}" y2="{base[1]}" stroke="black" stroke-width="3"/>')
        svg.append('<polygon points="' + ' '.join(f'{x},{y}' for x,y in triangle) + '" fill="black"/>')

    for x, w in [(0.2, 3.3), (4.5, 3.3), (8.8, 3.1), (12.9, 2.9)]:
        a, b = point(x, 2.98), point(x + w, 1.48)
        draw.rectangle([a, b], fill='#f2f2f2', outline='black', width=3)
        svg.append(f'<rect x="{a[0]}" y="{a[1]}" width="{w*SCALE}" height="{1.5*SCALE}" fill="#f2f2f2" stroke="black" stroke-width="3"/>')
    text(1.85, 2.54, '언어 모델', 10)
    text(1.85, 2.13, '변경 내용 추출', 9.5)
    text(1.85, 1.72, '고정 지침·예시 / 1회 호출', 7.9)
    text(6.15, 2.24, '코드 검사\n상태 갱신', 10)
    text(10.35, 2.24, '프롬프트 작성', 10)
    text(14.35, 2.24, '이미지 생성', 10)
    for start, end in [(3.5, 4.5), (7.8, 8.8), (11.9, 12.9)]:
        arrow((start + .04, 2.23), (end - .06, 2.23))
    text(4.0, 2.57, '변경값', 7.7)
    text(8.3, 2.57, '새 상태', 7.7)
    text(12.4, 2.57, '조건', 7.7)

    # Prior state enters code validation only; source image enters generation only.
    text(4.0, 4.27, '새 편집 요청', 10)
    line((4.0, 3.99), (4.0, 3.58))
    line((1.85, 3.58), (6.15, 3.58))
    arrow((1.85, 3.58), (1.85, 3.04))
    arrow((6.15, 3.58), (6.15, 3.04))
    text(14.35, 4.27, '최초 사진', 10)
    arrow((14.35, 3.98), (14.35, 3.04))
    text(6.15, .42, '직전 편집 상태', 9.5)
    arrow((6.15, .74), (6.15, 1.42))
    svg.append('</svg>')

    png_path = OUT / 'instruction-pipeline.png'
    svg_path = OUT / 'instruction-pipeline.svg'
    canvas.save(png_path, dpi=(DPI, DPI))
    svg_path.write_text('\n'.join(svg) + '\n')
    record = {
        'date': '2026-10-28',
        'kind': 'conceptual_method_diagram',
        'description': 'Implementation-derived data flow; not an experimental output image.',
        'width_cm': 16,
        'height_cm': 4.7,
        'source_sha256': {name: sha(ROOT / name) for name in SOURCES},
        'script': 'paper/build_method_figure.py',
        'script_sha256': sha(Path(__file__).resolve()),
        'outputs': {str(path.relative_to(ROOT)): sha(path) for path in [png_path, svg_path]},
    }
    (OUT / 'instruction-pipeline-provenance.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    print('Built conceptual method diagram (16 x 4.7 cm)')


if __name__ == '__main__':
    main()
