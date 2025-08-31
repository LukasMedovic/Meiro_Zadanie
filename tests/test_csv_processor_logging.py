from pathlib import Path

import pytest

from showads_client.csv_processor import CSVProcessor


def test_invalid_row_logged(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    data = "name,age,banner_id,cookie\nAlice,18,0,00000000-0000-0000-0000-000000000001\nBob,xx,1,00000000-0000-0000-0000-000000000002\n"
    csv_file = tmp_path / "data.csv"
    csv_file.write_text(data, encoding="utf-8")

    processor = CSVProcessor(str(csv_file), 18, 99)
    list(processor)  # consume generator

    assert processor.invalid_rows == 1
    messages = [rec.message for rec in caplog.records]
    assert any("invalid_row" in msg for msg in messages)

