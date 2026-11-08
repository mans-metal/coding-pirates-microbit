"""Checks for the micro:bit site. Standard library only.

Run from the project folder:  python3 -m unittest discover -s tests -v
"""
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import blocks  # noqa: E402

LANGS = ("en", "da")
ALLOWED_HOSTS = {"makecode.microbit.org", "tinkercademy.com"}
VOID = {"meta", "link", "img", "br", "hr", "input", "source"}
SVG_FORBIDDEN = re.compile(r"<script|href=|xlink|foreignObject|\son[a-z]+\s*=|javascript:", re.I)


class Page(HTMLParser):
    """Collects what the checks need from one HTML file."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skeleton, self.ids, self.imgs, self.links, self.tags = [], set(), [], [], set()
        self.lang = None
        self.title = ""
        self._in_title = False
        self.attrs_seen = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.add(tag)
        self.attrs_seen.extend(a)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "title":
            self._in_title = True
        if "id" in a:
            self.ids.add(a["id"])
        sk = [tag, a.get("id", ""), a.get("class", "")]
        if tag == "a":
            sk.append(a.get("href", ""))
        sk.append((bool(a.get("alt", "").strip()), bool(a.get("aria-label", "").strip()),
                   a.get("hreflang", "")))
        if tag == "img":
            self.imgs.append(a)
            sk.append(re.sub(r"\.(en|da)\.svg$", ".LANG.svg", a.get("src", "")))
        if tag in ("a", "link", "img", "script", "iframe", "source"):
            ref = a.get("href") if tag in ("a", "link") else a.get("src")
            if ref:
                self.links.append((tag, ref))
        self.skeleton.append(tuple(sk))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def parse(path):
    p = Page()
    p.feed(Path(path).read_text(encoding="utf-8"))
    return p


def lang_pages(lang):
    return sorted((ROOT / lang).glob("*.html"))


def all_pages():
    return [ROOT / "index.html"] + lang_pages("en") + lang_pages("da")


class Languages(unittest.TestCase):
    def test_same_pages_in_both_languages(self):
        names = {l: {p.name for p in lang_pages(l)} for l in LANGS}
        self.assertEqual(names["en"], names["da"])

    def test_same_structure(self):
        """Same tags, ids, classes and links, so the two languages stay in step."""
        for en in lang_pages("en"):
            da = ROOT / "da" / en.name
            sk_en, sk_da = parse(en).skeleton, parse(da).skeleton
            self.assertEqual(len(sk_en), len(sk_da), en.name)
            for a, b in zip(sk_en, sk_da):
                self.assertEqual(a, b, "%s differs near %s" % (en.name, a))

    def test_lang_attribute(self):
        self.assertEqual(parse(ROOT / "index.html").lang, "en")
        for l in LANGS:
            for p in lang_pages(l):
                self.assertEqual(parse(p).lang, l, p)

    def test_titles_not_empty(self):
        for p in all_pages():
            self.assertTrue(parse(p).title.strip(), p)

    def test_each_language_uses_its_own_block_pictures(self):
        for l, other in (("en", "da"), ("da", "en")):
            for p in lang_pages(l):
                for img in parse(p).imgs:
                    src = img.get("src", "")
                    if "/blocks/" in src:
                        self.assertTrue(src.endswith(".%s.svg" % l), "%s uses %s" % (p, src))
                        self.assertNotIn(".%s.svg" % other, src)


class Navigation(unittest.TestCase):
    def test_language_switcher_on_every_language_page(self):
        for l in LANGS:
            for p in lang_pages(l):
                text = p.read_text(encoding="utf-8")
                self.assertIn('<details class="lang">', text, p)
                for target in LANGS:
                    href = "../%s/%s" % (target, p.name)
                    self.assertIn('href="%s"' % href, text, "%s misses %s" % (p, href))
                    self.assertTrue((p.parent / href).resolve().exists(), href)
                self.assertEqual(len(re.findall(r'aria-current="page"', text)), 1, p)
                self.assertRegex(text, r'<a href="\.\./%s/%s"[^>]*aria-current="page"' % (l, p.name))

    def test_links_resolve(self):
        for p in all_pages():
            for tag, ref in parse(p).links:
                u = urlparse(ref)
                if u.scheme or u.netloc:
                    continue
                target = (p.parent / u.path).resolve() if u.path else p
                self.assertTrue(target.exists(), "%s links to missing %s" % (p, ref))
                if u.fragment and target.suffix == ".html":
                    self.assertIn(u.fragment, parse(target).ids, "%s: no #%s in %s" % (p, u.fragment, target.name))

    def test_every_lesson_is_listed_on_the_index(self):
        for l in LANGS:
            index = (ROOT / l / "index.html").read_text(encoding="utf-8")
            nav = re.search(r'<section id="lessons">.*?</section>', index, re.S)
            self.assertIsNotNone(nav, l)
            for p in lang_pages(l):
                if p.name != "index.html":
                    self.assertIn('href="%s"' % p.name, nav.group(0), "%s/%s is not in the lessons list" % (l, p.name))

    def test_root_page_links_both_languages(self):
        text = (ROOT / "index.html").read_text(encoding="utf-8")
        for l in LANGS:
            self.assertIn('href="%s/index.html"' % l, text)


class Accessibility(unittest.TestCase):
    def test_images_have_alt_text(self):
        for p in all_pages():
            for img in parse(p).imgs:
                self.assertTrue(img.get("alt", "").strip(), "%s: %s has no alt" % (p, img.get("src")))


class Safety(unittest.TestCase):
    def test_no_scripts_forms_or_embeds(self):
        for p in all_pages():
            page = parse(p)
            for bad in ("script", "iframe", "form", "object", "embed", "input", "button"):
                self.assertNotIn(bad, page.tags, "%s uses <%s>" % (p, bad))
            self.assertFalse([a for a in page.attrs_seen if a.startswith("on")], p)
            self.assertNotRegex(p.read_text(encoding="utf-8"), r"(?i)(href|src)\s*=\s*['\"]\s*javascript:")

    def test_only_local_resources_and_known_links(self):
        for p in all_pages():
            for tag, ref in parse(p).links:
                u = urlparse(ref)
                if tag != "a":
                    self.assertFalse(u.scheme or u.netloc, "%s loads %s from outside" % (p, ref))
                elif u.scheme or u.netloc:
                    self.assertEqual(u.scheme, "https", ref)
                    self.assertIn(u.hostname, ALLOWED_HOSTS, "%s links to %s" % (p, ref))

    def test_stylesheet_loads_nothing_remote(self):
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        self.assertNotRegex(css, r"@import|url\(")

    def test_svg_files_contain_no_scripts_or_links(self):
        for svg in (ROOT / "images" / "blocks").glob("*.svg"):
            self.assertIsNone(SVG_FORBIDDEN.search(svg.read_text(encoding="utf-8")), svg.name)


class BlockPictures(unittest.TestCase):
    def test_pictures_are_up_to_date(self):
        want = blocks.build()
        have = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "images" / "blocks").glob("*.svg")}
        self.assertEqual(set(want), set(have), "run python3 tools/blocks.py")
        for name, svg in want.items():
            self.assertEqual(svg, have[name], "%s is out of date, run python3 tools/blocks.py" % name)

    def test_every_picture_is_used_in_both_languages(self):
        used = set()
        for p in all_pages():
            for img in parse(p).imgs:
                if "/blocks/" in img.get("src", ""):
                    used.add(Path(img["src"]).name)
        unused = set(blocks.build()) - used
        self.assertFalse(unused, "pictures no page uses: %s" % sorted(unused))


if __name__ == "__main__":
    unittest.main()
