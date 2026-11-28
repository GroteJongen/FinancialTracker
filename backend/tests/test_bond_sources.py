from decimal import Decimal

import pytest

from app.infrastructure import bond_sources as source


def cpi_html():
    monthly = "".join("<td>100,1</td>" for _ in range(12))
    yearly = "".join("<td>102,9</td>" for _ in range(12))
    return f"<table><tr><td>Poprzedni miesiąc = 100</td><td>2025</td>{monthly}</tr><tr><td>Analogiczny miesiąc poprzedniego roku = 100</td><td>2025</td>{yearly}</tr><tr><td>Analogiczny okres narastający poprzedniego roku = 100</td><td>2025</td>{monthly}</tr></table>"


def test_only_year_on_year_table_is_used():
    result = source.parse_inflation(cpi_html())
    assert len(result) == 12
    assert result[(2025, 9)] == Decimal("2.9")


def test_bad_or_ambiguous_cpi_fails_closed():
    with pytest.raises(source.SourceUnavailable):
        source.parse_inflation("<html>Maintenance</html>")
    with pytest.raises(source.SourceUnavailable):
        source.parse_inflation(cpi_html() + cpi_html())
    with pytest.raises(source.SourceUnavailable):
        source.parse_inflation(cpi_html().replace("102,9", "NaN"))


def test_series_and_margin_are_matched_to_the_requested_issue():
    html = "<ul><li>Seria: COI1130</li><li>Oprocentowanie: 4,75%, w pierwszym roku. marża 1,50% + inflacja</li></ul>Charakterystyka obligacji"
    result = source.parse_terms("COI1130", html)
    assert result.annual_rate == Decimal("4.75")
    assert result.margin == Decimal("1.50")
    with pytest.raises(source.SourceUnavailable):
        source.parse_terms("COI1030", html)
    with pytest.raises(source.SourceUnavailable):
        source.parse_terms("COI1130", html.replace("marża 1,50%", "brak marży"))


def test_provider_url_cannot_be_selected_by_user():
    with pytest.raises(ValueError):
        source.series_url("https://localhost/secret")
    with pytest.raises(source.SourceUnavailable):
        source.Redirect().redirect_request(None, None, 302, "", {}, "http://127.0.0.1/private")
