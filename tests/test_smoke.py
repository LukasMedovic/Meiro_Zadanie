import io, csv, json
from showads_client.cli import main as cli
from click.testing import CliRunner


def _make_csv(rows):
    headers = ["name", "age", "banner_id"]
    f = io.StringIO()
    w = csv.DictWriter(f, fieldnames=headers)
    w.writeheader()
    w.writerows(rows)
    return f.getvalue()


def test_validate_smoke():
    runner = CliRunner()
    data = _make_csv(
        [
            {"name": "Alice", "age": "25", "banner_id": "5"},
            {"name": "Bob", "age": "17", "banner_id": "3"},
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


def test_send_smoke():
    runner = CliRunner()
    data = _make_csv([{"name": "Alice", "age": "25", "banner_id": "5"}])
    with runner.isolated_filesystem():
        with open("data.csv", "w", encoding="utf-8") as f:
            f.write(data)
        result = runner.invoke(cli, ["send", "data.csv"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["sent"] == 1
