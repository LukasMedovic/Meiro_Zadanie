import io, csv
import time
from click.testing import CliRunner

import showads_client.cli as cli_mod
from showads_client.api_client import ShowAdsClient


def _csv(rows):
    f = io.StringIO()
    w = csv.DictWriter(f, fieldnames=["name", "age", "banner_id", "cookie"])
    w.writeheader()
    w.writerows(rows)
    return f.getvalue()


def test_project_key_not_logged(monkeypatch):
    monkeypatch.setenv("SHOWADS_PROJECT_KEY", "SECRET")
    monkeypatch.setenv("LOG_JSON", "true")
    runner = CliRunner()
    data = _csv(
        [
            {
                "name": "A",
                "age": "25",
                "banner_id": "1",
                "cookie": "00000000-0000-0000-0000-000000000001",
            }
        ]
    )
    with runner.isolated_filesystem():
        with open("data.csv", "w", encoding="utf-8") as f:
            f.write(data)
        result = runner.invoke(cli_mod.main, ["send", "data.csv", "--dry-run"])
        assert result.exit_code == 0
        assert "SECRET" not in result.output


def test_authenticate_parses_token(monkeypatch):
    client = ShowAdsClient(base_url="https://x", project_key="PK")

    captured: dict[str, object] = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["json"] = json
        captured["headers"] = headers

        class Resp:
            status_code = 200

            @staticmethod
            def json():
                return {"AccessToken": "T", "ExpiresIn": 1}

        return Resp()

    monkeypatch.setattr(client.session, "post", fake_post)

    token = client.authenticate()
    assert token == "T"
    assert captured["json"] == {"ProjectKey": "PK"}
    assert captured["headers"] is None


def test_authenticate_default_expiry(monkeypatch):
    client = ShowAdsClient(base_url="https://x", project_key="PK")

    def fake_post(url, json=None, timeout=None):

        class Resp:
            status_code = 200

            @staticmethod
            def json():
                return {"AccessToken": "T"}

        return Resp()

    monkeypatch.setattr(client.session, "post", fake_post)

    start = time.time()
    client.authenticate()
    assert 24 * 3600 - 5 <= client._token.expires_at - start <= 24 * 3600 + 5
