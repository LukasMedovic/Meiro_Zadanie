from pathlib import Path
import csv
from click.testing import CliRunner
from showads_client.cli import main as cli


def test_validate_errors_out(tmp_path: Path) -> None:
    data = (
        "name,age,banner_id,cookie\n"
        "Alice,18,0,00000000-0000-0000-0000-000000000001\n"
        "Bob,xx,1,00000000-0000-0000-0000-000000000002\n"
    )
    csv_file = tmp_path / "data.csv"
    csv_file.write_text(data, encoding="utf-8")
    out_file = tmp_path / "errors.csv"
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(csv_file), "--errors-out", str(out_file)])
    assert result.exit_code == 0
    with out_file.open(newline="") as f:
        rows = list(csv.reader(f))
    assert rows == [
        ["name", "age", "banner_id", "cookie", "error"],
        [
            "Bob",
            "xx",
            "1",
            "00000000-0000-0000-0000-000000000002",
            "age must be an integer",
        ],
    ]
