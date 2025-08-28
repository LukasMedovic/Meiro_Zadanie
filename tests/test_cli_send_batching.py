import io, csv, json, importlib
from click.testing import CliRunner
from types import SimpleNamespace  # <<<


def _csv(rows):
    f = io.StringIO()
    w = csv.DictWriter(f, fieldnames=["name", "age", "banner_id"])
    w.writeheader()
    w.writerows(rows)
    return f.getvalue()


def test_send_respects_batch_size(monkeypatch):
    monkeypatch.setenv("BULK_BATCH_SIZE", "2")

    from showads_client import config as cfg

    importlib.reload(cfg)

    import showads_client.cli as cli_mod

    cli_mod.settings = SimpleNamespace(
        min_age=cfg.settings.min_age,
        max_age=cfg.settings.max_age,
        bulk_batch_size=2,
    )

    calls = []

    class FakeClient:
        def __init__(self):
            self._token = object()  # autent nie je potrebny

        def send_bulk(self, payload):
            calls.append(len(payload))
            return {"status": "stubbed", "sent": len(payload)}

    monkeypatch.setattr(cli_mod, "ShowAdsClient", FakeClient)

    data = _csv(
        [
            {"name": "A", "age": "25", "banner_id": "1"},
            {"name": "B", "age": "26", "banner_id": "2"},
            {"name": "C", "age": "27", "banner_id": "3"},
            {"name": "D", "age": "28", "banner_id": "4"},
            {"name": "E", "age": "29", "banner_id": "5"},
        ]
    )

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("data.csv", "w", encoding="utf-8") as f:
            f.write(data)
        result = runner.invoke(cli_mod.main, ["send", "data.csv"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["sent"] == 5
        assert calls == [2, 2, 1]
