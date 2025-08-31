import io, csv, json
from click.testing import CliRunner

import showads_client.cli as cli_mod
from showads_client.api_client import RateLimitError


def _csv(rows):
    f = io.StringIO()
    w = csv.DictWriter(f, fieldnames=["name", "age", "banner_id", "cookie"])
    w.writeheader()
    w.writerows(rows)
    return f.getvalue()


def test_metrics_file_written(monkeypatch):
    class FakeClient:
        def __init__(self):
            self._token = object()

        def authenticate(self):
            pass

        def send_bulk(self, payload):
            return {"status": "ok", "sent": len(payload)}

    monkeypatch.setattr(cli_mod, "ShowAdsClient", FakeClient)

    data = _csv(
        [
            {
                "name": "A",
                "age": "25",
                "banner_id": "1",
                "cookie": "00000000-0000-0000-0000-000000000001",
            },
            {
                "name": "B",
                "age": "26",
                "banner_id": "2",
                "cookie": "00000000-0000-0000-0000-000000000002",
            },
        ]
    )

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("data.csv", "w", encoding="utf-8") as f:
            f.write(data)
        result = runner.invoke(cli_mod.main, ["send", "data.csv", "--metrics-out", "m.json"])
        assert result.exit_code == 0
        with open("m.json", encoding="utf-8") as f:
            metrics = json.load(f)
        assert metrics["sent"] == 2
        assert "avg_batch_time_s" in metrics


def test_rate_limit_adapts_parallel(monkeypatch):
    calls = []

    class RLClient:
        def __init__(self):
            self._token = object()

        def authenticate(self):
            pass

        def send_bulk(self, payload):
            calls.append(len(payload))
            if len(calls) == 1:
                raise RateLimitError("429")
            return {"status": "ok", "sent": len(payload)}

    monkeypatch.setattr(cli_mod, "ShowAdsClient", RLClient)

    data = _csv(
        [
            {
                "name": "A",
                "age": "25",
                "banner_id": "1",
                "cookie": "00000000-0000-0000-0000-000000000001",
            },
            {
                "name": "B",
                "age": "26",
                "banner_id": "2",
                "cookie": "00000000-0000-0000-0000-000000000002",
            },
        ]
    )

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("data.csv", "w", encoding="utf-8") as f:
            f.write(data)
        result = runner.invoke(
            cli_mod.main,
            [
                "--bulk-batch-size",
                "1",
                "--parallel-requests",
                "2",
                "send",
                "data.csv",
                "--metrics-out",
                "m.json",
            ],
        )
        assert result.exit_code == 0
        with open("m.json", encoding="utf-8") as f:
            metrics = json.load(f)
        assert metrics["rate_limited"] == 1
        assert metrics["final_parallel"] == 1
        assert metrics["total_batches"] == 2
        assert metrics["max_retries"] == 1
