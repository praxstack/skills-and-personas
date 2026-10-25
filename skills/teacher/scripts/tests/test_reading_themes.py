#!/usr/bin/env python3
"""Standard-library checks for portable authored-HTML theme injection."""
import importlib.util
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/embed_reading_themes.py"
spec = importlib.util.spec_from_file_location("reading_themes", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DATA = json.loads((ROOT / "assets/reading-themes/themes.json").read_text())


def luminance(color):
    values = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    rgb = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in values]
    return sum(c * w for c, w in zip(rgb, (.2126, .7152, .0722)))


def contrast(a, b):
    x, y = sorted((luminance(a), luminance(b)))
    return (y + .05) / (x + .05)


def mix(a, b, weight=.15):
    return "#" + "".join(f"{round(int(a[i:i+2], 16) * weight + int(b[i:i+2], 16) * (1-weight)):02x}" for i in (1, 3, 5))


class ReadingThemes(unittest.TestCase):
    def test_injection_is_early_and_idempotent(self):
        for html in ('<!doctype html><html><head><title>T</title></head><body>Hi</body></html>',
                     '<HTML lang="en">\n<HEAD data-test="x">\n<script>window.engine=true</script></HEAD><BODY>Hi</BODY></HTML>',
                     '<!doctype html><html><body>Hi</body></html>', '<h1>A fragment</h1>'):
            with self.subTest(html=html):
                out = module.embed_reading_themes(html)
                self.assertEqual(module.embed_reading_themes(out), out)
                self.assertEqual(out.count(module.START), 1)
                self.assertEqual(out.count('id="reading-themes-script"'), 1)
                if 'window.engine' in html:
                    self.assertLess(out.index('id="reading-themes-script"'), out.index('window.engine'))

    def test_headless_documents_preserve_doctype_and_prolog(self):
        for prolog in ('<!doctype html>',
                       '<!-- Before -->\n<!DOCTYPE html>\n<!-- After -->\n',
                       '\ufeff<!doctype html>\n'):
            for content in ('<title>T</title><p>Lesson</p>', 'Lesson', ''):
                with self.subTest(prolog=prolog, content=content):
                    out = module.embed_reading_themes(prolog + content)
                    self.assertTrue(out.startswith(prolog + '<head>'))
                    self.assertEqual(out.count(prolog), 1)
                    self.assertEqual(module.embed_reading_themes(out), out)
                    self.assertTrue(out.endswith('</head>' + content))

    def test_preserves_csp_charset_and_authored_content(self):
        metadata = '<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'none\'">'
        body = '<script>const example="<head>";</script><svg><path d="M0 0L3 4"/></svg><img src="untrusted.svg"><video src="data:video/mp4,AAAA"></video>'
        html = '<!doctype html><html><head>' + metadata + '</head><body>' + body + '</body></html>'
        out = module.embed_reading_themes(html)
        self.assertLess(out.index(metadata), out.index(module.START))
        self.assertEqual(module.BLOCK.sub('', out), html)
        self.assertIn(body, out)
        self.assertNotIn('unsafe-inline', out)
        self.assertEqual(module.embed_reading_themes(out), out)

    def test_parser_offsets_follow_lf_only_with_comment_separators(self):
        policy = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'none\'">'
        for separator in ('\r', '\v', '\f', '\x1c', '\x1d', '\x1e', '\x85', '\u2028', '\u2029'):
            for headless in (False, True):
                with self.subTest(separator=repr(separator), headless=headless):
                    prolog = '<!doctype html><!-- α' + separator + 'β -->\n'
                    html = (prolog + ('<html><head>' if not headless else '')
                            + '<!-- γ' + separator + 'δ -->\n' + policy
                            + ('</head><body>' if not headless else '') + '<p>Lesson π</p>')
                    out = module.embed_reading_themes(html)
                    expected = html.index(policy) + len(policy)
                    self.assertTrue(out.startswith(html[:expected] + ('' if not headless else '<head>') + module.START))
                    self.assertLess(out.index(policy), out.index(module.START))
                    self.assertEqual(module.embed_reading_themes(out), out)
                    if not headless:
                        self.assertEqual(module.BLOCK.sub('', out), html)

    def test_cli_can_replace_input_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / 'lesson.html'
            page.write_text('<html><head></head><body>π</body></html>', encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPT), str(page), '-o', str(page)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('π', page.read_text(encoding='utf-8'))
            first = page.read_bytes()
            subprocess.run([sys.executable, str(SCRIPT), str(page), '-o', str(page)], check=True)
            self.assertEqual(page.read_bytes(), first)

    def test_cli_preserves_authored_newline_bytes(self):
        documents = (
            '<!doctype html>\r\n<html><head><title>π</title></head>\r\n<body>café</body></html>\r\n'.encode('utf-8'),
            '<!doctype html>\r<html><head><title>π</title></head>\r<body>café</body></html>\r'.encode('utf-8'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, original in enumerate(documents):
                for in_place in (False, True):
                    with self.subTest(index=index, in_place=in_place):
                        source = root / f'lesson-{index}-{in_place}.html'
                        output = source if in_place else root / f'output-{index}.html'
                        source.write_bytes(original)
                        command = [sys.executable, str(SCRIPT), str(source), '-o', str(output)]
                        subprocess.run(command, check=True, capture_output=True, text=True)
                        injected = output.read_bytes()
                        stripped = re.sub(rb'<!-- reading-themes:start -->.*?<!-- reading-themes:end -->',
                                           b'', injected, flags=re.S)
                        self.assertEqual(stripped, original)
                        subprocess.run([sys.executable, str(SCRIPT), str(output), '-o', str(output)],
                                       check=True, capture_output=True, text=True)
                        self.assertEqual(output.read_bytes(), injected)

    def test_palette_shape_and_names(self):
        expected = ['graphite', 'slate', 'forest', 'mocha', 'indigo', 'midnight', 'amber', 'ember', 'moss', 'plum']
        self.assertEqual([p['id'] for p in DATA['palettes']], expected)
        self.assertEqual([p['group'] for p in DATA['palettes']], ['Dark'] * 5 + ['Night'] * 5)
        for p in DATA['palettes']:
            self.assertEqual(p['name'].lower(), p['id'])
            for key in ('bg', 'panel', 'ink', 'muted', 'accent', 'border'):
                self.assertRegex(p[key], r'^#[0-9a-f]{6}$')

    def test_text_controls_and_semantic_colors_have_measured_contrast(self):
        minima = {'primary': 99, 'secondary': 99, 'border': 99, 'semantic': 99}
        for p in DATA['palettes']:
            for bg in ('bg', 'panel'):
                for fg in ('ink', 'muted', 'accent'):
                    ratio = contrast(p[fg], p[bg])
                    category = 'primary' if fg == 'ink' else 'secondary'
                    minima[category] = min(minima[category], ratio)
                    self.assertGreaterEqual(ratio, 7 if fg == 'ink' else 4.5, (p['id'], fg, bg, ratio))
                ratio = contrast(p['border'], p[bg])
                minima['border'] = min(minima['border'], ratio)
                self.assertGreaterEqual(ratio, 3, (p['id'], 'border', bg, ratio))
            blue = '#adc7e6' if p['group'] == 'Night' else '#9ecbff'
            for semantic in (blue, '#efaa9f', '#afd2a6', p['accent']):
                ratio = contrast(semantic, mix(semantic, p['panel']))
                minima['semantic'] = min(minima['semantic'], ratio)
                self.assertGreaterEqual(ratio, 4.5, (p['id'], semantic, 'soft', ratio))
            self.assertGreaterEqual(contrast(p['bg'], blue), 4.5, (p['id'], 'on-blue'))
        print('\nMeasured contrast minima:', {k: round(v, 3) for k, v in minima.items()})

    def test_actual_export_color_tokens_are_all_mapped(self):
        template = ROOT / 'skills/explorable/scripts/bundle_templates.mjs'
        js = r"""
const {css,videoLesson}=await import(process.argv[1]);
const data={title:'Export contrast',subtitle:'Reading surfaces',sources:[],video:{captions:'WEBVTT\n\n',scenes:[{start:0,dur:1,chapter:'Boundary',say:'A caption',step:0,params:{}}]}};
console.log(JSON.stringify({html:videoLesson(data),tokens:[...new Set([...css.matchAll(/--([a-z0-9-]+):/g)].map(m=>m[1]))]}));
"""
        run = subprocess.run(['node', '--input-type=module', '-e', js, template.as_uri()], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(run.returncode, 0, run.stderr)
        exported = json.loads(run.stdout)
        output = module.embed_reading_themes(exported['html'])
        self.assertEqual(module.BLOCK.sub('', output), exported['html'])
        theme_style = re.search(r'<style id="reading-themes-style">(.*?)</style>', output, re.S).group(1)
        mapped = set(re.findall(r'--([a-z0-9-]+):', theme_style))
        self.assertTrue(set(exported['tokens']) <= mapped, set(exported['tokens']) - mapped)

    def test_embedded_resources_are_local_and_safe_to_parse(self):
        output = module.embed_reading_themes('<html><head></head><body></body></html>')
        self.assertIn('type="application/json"', output)
        self.assertNotIn('<script src=', output)
        self.assertNotIn('<link ', output)
        js = (ROOT / 'assets/reading-themes/themes.js').read_text()
        for prohibited in ('localStorage', 'sessionStorage', 'document.cookie', 'fetch(', 'eval(', 'innerHTML', 'new Function'):
            self.assertNotIn(prohibited, js)
        for p in DATA['palettes']:
            self.assertIn(f'data-reading-theme="{p["id"]}"', output)
        css = (ROOT / 'assets/reading-themes/themes.css').read_text()
        for token in ('paper', 'paper-2', 'card', 'wash', 'ink', 'ink-2', 'graphite', 'graphite-2', 'rule', 'rule-soft', 'line', 'muted', 'accent', 'blue', 'red', 'green', 'blue-soft', 'red-soft', 'green-soft', 'on-blue', 'focus', 'highlight', 'grid', 'margin', 'shadow', 'stroke-grain'):
            self.assertIn(f'--{token}:', css)


if __name__ == '__main__':
    unittest.main()
