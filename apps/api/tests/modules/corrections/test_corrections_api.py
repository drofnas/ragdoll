from __future__ import annotations

from tests.modules._phase10_helpers import auth_headers, register_and_login


def test_corrections_submit_list_verify_and_reject(api_client):
    token = register_and_login(api_client, email="owner@example.com")

    first = api_client.post(
        "/api/v1/corrections",
        headers=auth_headers(token),
        json={"proposed_value": "Atlas is paused", "rationale": "manual fix"},
    )
    assert first.status_code == 200, first.text
    first_id = first.json()["id"]
    assert first.json()["status"] == "pending"

    listing = api_client.get("/api/v1/corrections", headers=auth_headers(token))
    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] >= 1

    verify = api_client.post(
        f"/api/v1/corrections/{first_id}/verify",
        headers=auth_headers(token),
        json={"review_notes": "confirmed"},
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["status"] == "verified"
    assert verify.json()["citation"]["source_tier"] == "verified"

    second = api_client.post(
        "/api/v1/corrections",
        headers=auth_headers(token),
        json={"proposed_value": "Atlas is cancelled", "rationale": "incorrect note"},
    )
    assert second.status_code == 200, second.text
    second_id = second.json()["id"]

    reject = api_client.post(
        f"/api/v1/corrections/{second_id}/reject",
        headers=auth_headers(token),
        json={"review_notes": "not accepted"},
    )
    assert reject.status_code == 200, reject.text
    assert reject.json()["status"] == "rejected"
