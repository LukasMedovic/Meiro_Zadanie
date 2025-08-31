import io, csv
from click.testing import CliRunner
from showads_client.cli import main as cli


def test_validate_missing_headers_exit2():
    runner = CliRunner()
    # CSV bez povinnych hlaviciek
    f = io.StringIO()
    w = csv.writer(f)
    w.writerow(["FullName", "Age", "Banner_id"])  # missing Cookie
    w.writerow(["Alice", "25", "5"])
    with runner.isolated_filesystem():
        with open("bad.csv", "w", encoding="utf-8") as out:
            out.write(f.getvalue())
        result = runner.invoke(cli, ["validate", "bad.csv"])
        assert result.exit_code == 2
        assert "CSV must contain headers" in result.output
