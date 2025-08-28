import os, importlib
from click.testing import CliRunner


def test_env_overrides(monkeypatch):
    # Prepis env pred importom modulu
    monkeypatch.setenv("MIN_AGE", "21")
    monkeypatch.setenv("BULK_BATCH_SIZE", "2")
    # Reload modulu, aby sa nanovo nacital settings dataclass
    from showads_client import config as cfg

    importlib.reload(cfg)
    assert cfg.settings.min_age == 21
    assert cfg.settings.bulk_batch_size == 2
