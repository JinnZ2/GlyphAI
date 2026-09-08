"""Price sources behind a single seam.

`MockPriceSource` is the Phase 0 behaviour: fixed regional data, no network.
`LivePriceSource` reads a real product page through `PoliteFetcher` and
`price_extractor`.

Regional in-store pricing is still mock. Real per-region retail pricing needs
per-vendor store-inventory APIs that do not exist here; inventing it from a
single product URL would be fabrication. `LivePriceSource` is therefore honest
about scope: it reports what a page actually says, and `is_live` marks which
numbers are real.
"""

from decision_model import (SOURCE_KINDS, SOURCE_KIND_DERIVED,
                            SOURCE_KIND_MOCK, SOURCE_KIND_OBSERVED)
from price_extractor import extract_offer
from web_fetch import PoliteFetcher, FetchError, RobotsDenied

MOCK_REGIONS = {
    "90301": {"in_store": 8.99, "online": 10.49, "distance": 2.1},
    "90210": {"in_store": 7.75, "online": 9.99, "distance": 7.5},
    "90001": {"in_store": 9.25, "online": 9.25, "distance": 0.3},
}


class MockPriceSource:
    """Fixed regional data. Same numbers regardless of product or ZIP."""

    is_live = False

    def regional_prices(self, product_name, zip_code):
        return {
            region: dict(info, source_kind=SOURCE_KIND_MOCK)
            for region, info in MOCK_REGIONS.items()
        }


class LivePriceSource:
    """Reads real offers from product pages.

    Only `fetch_offer` is live. `regional_prices` delegates to the mock, since
    a product URL says nothing about in-store pricing in three ZIP codes.
    """

    is_live = True

    def __init__(self, fetcher=None, **fetcher_kwargs):
        self.fetcher = fetcher or PoliteFetcher(**fetcher_kwargs)
        self._mock = MockPriceSource()

    def fetch_offer(self, url):
        """Return an offer dict for a product URL.

        On failure returns a dict with `error` set rather than raising, so a
        single unreachable vendor cannot abort a multi-product run.
        """
        try:
            html = self.fetcher.fetch(url)
        except RobotsDenied as e:
            return {"url": url, "price": None, "error": "robots_denied",
                    "detail": str(e)}
        except FetchError as e:
            return {"url": url, "price": None, "error": "fetch_failed",
                    "detail": str(e)}
        offer = extract_offer(html, url=url)
        if offer.get("price") is None:
            offer["error"] = "no_structured_price"
            offer["detail"] = (
                "Page carries no JSON-LD, microdata or price meta tags. "
                "Price unknown - not free.")
        return offer

    def regional_prices(self, product_name, zip_code):
        return self._mock.regional_prices(product_name, zip_code)


def get_source(name="mock", **kwargs):
    """Factory used by the CLI: 'mock' or 'live'."""
    if name == "live":
        return LivePriceSource(**kwargs)
    if name == "mock":
        return MockPriceSource()
    raise ValueError(f"Unknown price source: {name!r}")
