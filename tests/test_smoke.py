import io, csv, json
from click.testing import CliRunner
from showads_client.cli import main as cli


def _make_csv(rows):
    headers = ["name", "age", "banner_id", "cookie"]
    f = io.StringIO()
    w = csv.DictWriter(f, fieldnames=headers)
    w.writeheader()
    w.writerows(rows)
    return f.getvalue()


def test_validate_smoke():
    runner = CliRunner()
    data = _make_csv(
        [
            {
                "name": "Alice",
                "age": "25",
                "banner_id": "5",
                "cookie": "00000000-0000-0000-0000-000000000001",
            },
            {
                "name": "Bob",
                "age": "17",
                "banner_id": "3",
                "cookie": "00000000-0000-0000-0000-000000000002",
            },
        ]
    )
    with runner.isolated_filesystem():
        with open("data.csv", "w", encoding="utf-8") as f:
            f.write(data)
        result = runner.invoke(cli, ["validate", "data.csv"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["valid"] == 1
        assert payload["invalid"] == 1


def test_send_smoke(monkeypatch):
    runner = CliRunner()

    class FakeClient:
        def __init__(self):
            self._token = object()

        def authenticate(self):
            pass

        def send_bulk(self, payload):
            return {"status": "ok", "sent": len(payload)}

    monkeypatch.setattr("showads_client.cli.ShowAdsClient", FakeClient)

    data = _make_csv(
        [
            {
                "name": "Alice",
                "age": "25",
                "banner_id": "5",
                "cookie": "00000000-0000-0000-0000-000000000001",
            }
        ]
    )
    with runner.isolated_filesystem():
        with open("data.csv", "w", encoding="utf-8") as f:
            f.write(data)
        result = runner.invoke(cli, ["send", "data.csv"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["rows_sent"] == 1
