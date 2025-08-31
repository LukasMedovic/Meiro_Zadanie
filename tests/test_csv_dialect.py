import json
from click.testing import CliRunner

from showads_client.cli import main as cli


def test_validate_handles_bom(tmp_path):
    content = "\ufeffname,age,banner_id,cookie\nA,25,1,00000000-0000-0000-0000-000000000001\n"
    p = tmp_path / "data.csv"
    p.write_text(content, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(p)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["valid"] == 1


def test_duplicate_headers_error(tmp_path):
    content = "name,age,age,cookie\nA,25,26,00000000-0000-0000-0000-000000000001\n"
    p = tmp_path / "data.csv"
    p.write_text(content, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(p)])
    assert result.exit_code == 2
    assert "duplicate headers" in result.output
