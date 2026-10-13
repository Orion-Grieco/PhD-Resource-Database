"""Download a program page and reduce it to text an extractor can work with."""

import hashlib
import json
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "PhD-Resource-Database/0.1 (personal program tracker)"
TIMEOUT = httpx.Timeout(20.0, connect=10.0)
MAX_BYTES = 3_000_000


class FetchError(Exception):
    pass


@dataclass
class Page:
    url: str
    final_url: str
    title: str = ""
    headings: list[str] = field(default_factory=list)
    text: str = ""
    meta: dict[str, str] = field(default_factory=dict)
    json_ld: list = field(default_factory=list)
    html: str = ""

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


_SKIP_TAGS = {"script", "style", "noscript", "svg", "template", "iframe"}
_BLOCK_TAGS = {
    "p", "div", "section", "article", "li", "ul", "ol", "tr", "td", "th", "table",
    "h1", "h2", "h3", "h4", "h5", "h6", "br", "dt", "dd", "header", "footer", "main",
}


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title = ""
        self.headings: list[str] = []
        self.meta: dict[str, str] = {}
        self.json_ld: list = []
        self._skip_depth = 0
        self._in_title = False
        self._heading: list[str] | None = None
        self._ld_buf: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key and a.get("content"):
                self.meta[key] = a["content"].strip()
        elif tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self._ld_buf = []
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in ("h1", "h2"):
            self._heading = []
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "script" and self._ld_buf is not None:
            try:
                data = json.loads("".join(self._ld_buf))
                self.json_ld.extend(data if isinstance(data, list) else [data])
            except ValueError:
                pass
            self._ld_buf = None
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in ("h1", "h2") and self._heading is not None:
            text = " ".join("".join(self._heading).split())
            if text:
                self.headings.append(text)
            self._heading = None
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._ld_buf is not None:
            self._ld_buf.append(data)
            return
        if self._skip_depth:
            return
        if self._in_title:
            self.title += data
            return
        if self._heading is not None:
            self._heading.append(data)
        self.parts.append(data)


def parse_html(url: str, final_url: str, html: str) -> Page:
    parser = _PageParser()
    parser.feed(html)
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    text = "\n".join(line for line in lines if line)
    return Page(
        url=url,
        final_url=final_url,
        title=" ".join(parser.title.split()),
        headings=parser.headings,
        text=text,
        meta=parser.meta,
        json_ld=parser.json_ld,
        html=html,
    )


async def _allowed_by_robots(client: httpx.AsyncClient, url: str) -> bool:
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        resp = await client.get(robots_url)
    except httpx.HTTPError:
        return True
    if resp.status_code >= 400:
        return True
    rp = RobotFileParser()
    rp.parse(resp.text.splitlines())
    return rp.can_fetch(USER_AGENT, url)


async def fetch_page(url: str) -> Page:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, follow_redirects=True
    ) as client:
        if not await _allowed_by_robots(client, url):
            raise FetchError("This site's robots.txt does not allow automated fetching of that page.")
        try:
            resp = await client.get(url)
        except httpx.HTTPError as e:
            raise FetchError(f"Could not fetch the page: {e}") from e
    if resp.status_code >= 400:
        raise FetchError(f"The site returned HTTP {resp.status_code}.")
    ctype = resp.headers.get("content-type", "")
    if "html" not in ctype and "xml" not in ctype:
        raise FetchError(f"Expected a web page but got '{ctype or 'unknown'}' content.")
    html = resp.content[:MAX_BYTES].decode(resp.encoding or "utf-8", errors="replace")
    return parse_html(url, str(resp.url), html)
