from app.infrastructure.catalog import IUSQ_LISTING_ID


def test_valuation_requires_an_explicit_listing_without_defaulting_to_iusq(ledger):
    client, _, _, account_id = ledger
    assert client.get(f"/api/accounts/{account_id}/valuation").status_code == 422
    response = client.get(
        f"/api/accounts/{account_id}/valuation", params={"listing_id": str(IUSQ_LISTING_ID)}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "empty"
