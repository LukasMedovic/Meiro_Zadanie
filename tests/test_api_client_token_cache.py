from showads_client.api_client import ShowAdsClient, AuthToken


def test_token_cached(monkeypatch):
    client = ShowAdsClient()
    called = {"n": 0}

    def fake_auth():
        # Simulujeme realne spravanie: nastavime cache a vratime token
        called["n"] += 1
        client._token = AuthToken("TOKEN")
        return "TOKEN"

    # Nahradime metodu instancie
    monkeypatch.setattr(client, "authenticate", fake_auth)

    # 1. volanie -> authenticate prebehne
    client.send_bulk([{"name": "A", "age": 25, "banner_id": 1}])
    # 2. volanie -> token je uz v cache, authenticate sa nesmie volat znova
    client.send_bulk([{"name": "B", "age": 26, "banner_id": 2}])

    assert called["n"] == 1
