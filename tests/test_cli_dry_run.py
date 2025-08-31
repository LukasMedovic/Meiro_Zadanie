import io, csv, json
from click.testing import CliRunner

import showads_client.cli as cli_mod


def _csv(rows):
    f = io.StringIO()
    w = csv.DictWriter(f, fieldnames=["name", "age", "banner_id", "cookie"])
    w.writeheader()
    w.writerows(rows)
    return f.getvalue()


def test_send_dry_run_no_network(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self):
            self._token = object()

        def authenticate(self):
            pass

        def send_bulk(self, payload):  # pragma: no cover - dry run
            calls.append(payload)
            return {"status": "stubbed", "sent": len(payload)}

    monkeypatch.setattr(cli_mod, "ShowAdsClient", FakeClient)

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
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("data.csv", "w", encoding="utf-8") as f:
            f.write(data)
        result = runner.invoke(cli_mod.main, ["send", "data.csv", "--dry-run"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["rows_would_send"] == 1
        assert calls == []
