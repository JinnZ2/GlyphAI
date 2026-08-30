"""Extract structured price data from a product page.

Prefers the machine-readable data sites publish for exactly this purpose,
in descending order of reliability:

  1. JSON-LD  (<script type="application/ld+json">, schema.org Product/Offer)
  2. Microdata (itemprop="price" / "priceCurrency" / "availability")
  3. Meta tags (og:price:amount, product:price:amount, twitter:data1)

This is deliberately not a CSS-selector scraper. Structured markup is stable,
published for machines, and does not break every time a site restyles.

Standard library only.
"""

import json
import re
from html.parser import HTMLParser

# schema.org availability values, normalised to a short token.
AVAILABILITY = {
    "instock": "IN_STOCK",
    "outofstock": "OUT_OF_STOCK",
    "preorder": "PREORDER",
    "backorder": "BACKORDER",
    "discontinued": "DISCONTINUED",
    "limitedavailability": "LIMITED",
}

_PRICE_CHARS = re.compile(r"[^0-9.,-]")


def parse_price(raw):
    """Turn '$1,299.00' / '1.299,00' / 19.99 into a float, or None."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = _PRICE_CHARS.sub("", str(raw)).strip()
    if not text:
        return None
    # Disambiguate 1.299,00 (European) from 1,299.00 (US) by last separator.
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        # A single comma is a decimal separator only when it looks like one.
        if re.match(r"^-?\d+,\d{1,2}$", text):
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def normalize_availability(raw):
    if not raw:
        return None
    token = str(raw).rsplit("/", 1)[-1].replace(" ", "").replace("_", "").lower()
    return AVAILABILITY.get(token)


class _PageParser(HTMLParser):
    """Collects JSON-LD blocks, microdata itemprops and meta tags."""

    META_PRICE_KEYS = ("og:price:amount", "product:price:amount",
                       "og:product:price:amount", "twitter:data1")
    META_CURRENCY_KEYS = ("og:price:currency", "product:price:currency",
                          "og:product:price:currency")

    def __init__(self):
        HTMLParser.__init__(self)
        self.ld_blocks = []
        self.microdata = {}
        self.meta = {}
        self.title = None
        self._in_ld = False
        self._in_title = False
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("type", "").strip().lower() == "application/ld+json":
            self._in_ld = True
            self._buffer = []
        elif tag == "title":
            self._in_title = True
            self._buffer = []
        elif tag == "meta":
            key = attrs.get("property") or attrs.get("name")
            content = attrs.get("content")
            if key and content and key not in self.meta:
                self.meta[key.lower()] = content
        # Microdata can sit on any tag; value may be in content= or the text.
        prop = attrs.get("itemprop")
        if prop and prop.lower() not in self.microdata:
            value = attrs.get("content") or attrs.get("href")
            if value:
                self.microdata[prop.lower()] = value

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld:
            self.ld_blocks.append("".join(self._buffer))
            self._in_ld = False
            self._buffer = []
        elif tag == "title" and self._in_title:
            self.title = "".join(self._buffer).strip() or None
            self._in_title = False
            self._buffer = []

    def handle_data(self, data):
        if self._in_ld or self._in_title:
            self._buffer.append(data)


def _iter_ld_nodes(value):
    """Walk a JSON-LD document, yielding every dict node (handles @graph/lists)."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            for node in _iter_ld_nodes(child):
                yield node
    elif isinstance(value, list):
        for item in value:
            for node in _iter_ld_nodes(item):
                yield node


def _has_type(node, wanted):
    node_type = node.get("@type")
    types = node_type if isinstance(node_type, list) else [node_type]
    return any(str(t).lower() == wanted for t in types if t)


def _from_json_ld(blocks):
    """Return (name, price, currency, availability, description) from JSON-LD."""
    name = price = currency = availability = None
    description = None
    for block in blocks:
        try:
            document = json.loads(block)
        except ValueError:
            continue  # A malformed block must not sink the whole page.
        nodes = list(_iter_ld_nodes(document))

        for node in nodes:
            if not _has_type(node, "product"):
                continue
            if name is None and node.get("name"):
                name = str(node["name"]).strip()
            if description is None and node.get("description"):
                description = str(node["description"]).strip()

        for node in nodes:
            is_offer = _has_type(node, "offer") or _has_type(node, "aggregateoffer")
            if not is_offer and "price" not in node and "lowPrice" not in node:
                continue
            candidate = parse_price(node.get("price", node.get("lowPrice")))
            if candidate is None:
                continue
            if price is None or candidate < price:
                price = candidate
                currency = node.get("priceCurrency") or currency
                availability = normalize_availability(node.get("availability")) or availability
    return name, price, currency, availability, description


def extract_offer(html, url=None):
    """Extract an offer from a product page.

    Returns a dict with name, price, currency, availability, source and url.
    `price` is None when the page carries no structured price data — callers
    must treat that as "unknown", never as free.
    """
    parser = _PageParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:
        pass  # Malformed HTML still yields whatever was parsed before the fault.

    name, price, currency, availability, ld_description = _from_json_ld(parser.ld_blocks)
    source = "json-ld" if price is not None else None

    if price is None:
        micro_price = parse_price(parser.microdata.get("price"))
        if micro_price is not None:
            price = micro_price
            currency = parser.microdata.get("pricecurrency") or currency
            availability = (normalize_availability(parser.microdata.get("availability"))
                            or availability)
            source = "microdata"

    if price is None:
        for key in _PageParser.META_PRICE_KEYS:
            meta_price = parse_price(parser.meta.get(key))
            if meta_price is not None:
                price = meta_price
                source = "meta"
                break
        if currency is None:
            for key in _PageParser.META_CURRENCY_KEYS:
                if parser.meta.get(key):
                    currency = parser.meta[key]
                    break

    if name is None:
        name = (parser.microdata.get("name") or parser.meta.get("og:title")
                or parser.title)

    # The detector scans this for urgency and subscription language, so prefer
    # the richest source available.
    description = (ld_description or parser.meta.get("description")
                   or parser.meta.get("og:description")
                   or parser.microdata.get("description") or "")

    return {
        "name": name.strip() if isinstance(name, str) else name,
        "price": price,
        "currency": (currency or "").upper() or None,
        "availability": availability,
        "description": description.strip(),
        "source": source,
        "url": url,
    }
