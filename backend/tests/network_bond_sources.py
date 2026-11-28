"""Separate read-only probe of public source availability, never portfolio data."""

from app.infrastructure.bond_sources import SourceUnavailable, inflation, terms


if __name__ == "__main__":
    for series in ("TOS1129", "COI1130", "EDO1136"):
        try:
            result = terms(series)
            print("PASS: public issue source", series, result.annual_rate, result.margin)
        except SourceUnavailable as failure:
            print("UNAVAILABLE: issue source", series, str(failure), type(failure.__cause__).__name__)
    try:
        values = inflation()
        print("PASS: GUS year-on-year CPI", len(values), "months; latest", max(values))
    except SourceUnavailable as failure:
        print("UNAVAILABLE: GUS", str(failure), type(failure.__cause__).__name__)
