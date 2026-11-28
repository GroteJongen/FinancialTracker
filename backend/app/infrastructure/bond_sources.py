"""Public issue pages and GUS year-on-year CPI; no portfolio data is sent."""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.domain.bonds import parse_series

GUS_URL = "https://stat.gov.pl/obszary-tematyczne/ceny-handel/wskazniki-cen/wskazniki-cen-towarow-i-uslug-konsumpcyjnych-pot-inflacja-/miesieczne-wskazniki-cen-towarow-i-uslug-konsumpcyjnych-od-1982-roku/"
KINDS = {"TOS": "obligacje-3-letnie-tos", "COI": "obligacje-4-letnie-coi", "EDO": "obligacje-10-letnie-edo"}


class SourceUnavailable(Exception):
    pass


class Redirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != "https" or parsed.hostname not in {"stat.gov.pl", "www.obligacjeskarbowe.pl"} or parsed.username or parsed.password or parsed.port not in {None, 443}:
            raise SourceUnavailable("Untrusted provider redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str) -> str:
    try:
        with build_opener(Redirect()).open(Request(url, headers={"User-Agent": "FinancialTracker/1.0", "Accept": "text/html"}), timeout=4) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Provider response too large")
        return raw.decode("utf-8-sig")
    except Exception as exc:
        raise SourceUnavailable("Provider unavailable") from exc


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.rows = []
        self.row = None
        self.cell = None
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1
        if tag == "tr":
            self.row = []
        if tag in {"th", "td"} and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
            if self.cell is not None:
                self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)
        if tag in {"th", "td"} and self.cell is not None:
            self.row.append(" ".join(self.cell).strip())
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def plain(value):
    return " ".join(value.split())


@dataclass(frozen=True)
class SeriesTerms:
    series: str
    annual_rate: Decimal
    margin: Decimal | None
    source_url: str


def parse_terms(series: str, html: str) -> SeriesTerms:
    series = parse_series(series)
    parser = Text()
    parser.feed(html)
    text = plain(" ".join(parser.parts))
    found = re.search(r"Seria:\s*((?:TOS|COI|EDO)\d{4})", text)
    rate = re.search(r"Oprocentowanie:\s*([0-9]+(?:[,.][0-9]+)?)\s*%", text)
    if not found or found[1] != series or not rate:
        raise SourceUnavailable("Wrong or incomplete issue page")
    segment = text[found.start():].split("Charakterystyka obligacji")[0]
    margin = re.search(r"marża\s*([0-9]+(?:[,.][0-9]+)?)\s*%", segment, re.I)
    annual = Decimal(rate[1].replace(",", "."))
    extra = Decimal(margin[1].replace(",", ".")) if margin else None
    if not Decimal("0") <= annual <= Decimal("100") or (extra is not None and not Decimal("0") <= extra <= Decimal("100")):
        raise SourceUnavailable("Invalid issue rates")
    if series[:3] != "TOS" and extra is None:
        raise SourceUnavailable("Missing issue margin")
    return SeriesTerms(series, annual, extra, series_url(series))


def series_url(series: str) -> str:
    series = parse_series(series)
    return f"https://www.obligacjeskarbowe.pl/oferta-obligacji/{KINDS[series[:3]]}/{series.lower()}/"


def terms(series: str) -> SeriesTerms:
    return parse_terms(series, fetch(series_url(series)))


def parse_inflation(html: str) -> dict[tuple[int, int], Decimal]:
    parser = Text()
    parser.feed(html)
    active = False
    result = {}
    for row in parser.rows:
        header = unicodedata.normalize("NFD", plain(" ".join(row))).lower()
        header = "".join(ch for ch in header if not unicodedata.combining(ch))
        if "analogiczny" in header and "miesiac" in header and "poprzedniego" in header:
            active = True
        elif any(word in header for word in ("grudzien", "poprzedni miesiac", "narastajacy")):
            active = False
        if not active:
            continue
        year_at = next((index for index, cell in enumerate(row) if re.fullmatch(r"20\d{2}", plain(cell))), None)
        if year_at is None or len(row) - year_at != 13:
            continue
        year = int(row[year_at])
        for month, cell in enumerate(row[year_at + 1:], 1):
            cell = plain(cell)
            if not cell or cell in {".", "-", "x"}:
                continue
            if not re.fullmatch(r"\d{1,4}[,.]\d", cell):
                raise SourceUnavailable("Invalid CPI table cell")
            index = Decimal(cell.replace(",", "."))
            if not Decimal("0") < index < Decimal("1000"):
                raise SourceUnavailable("Invalid CPI index")
            key = year, month
            if key in result:
                raise SourceUnavailable("Ambiguous CPI table")
            result[key] = index - Decimal("100")
    if len(result) < 12:
        raise SourceUnavailable("Missing year-on-year CPI table")
    return result


def inflation():
    return parse_inflation(fetch(GUS_URL))
