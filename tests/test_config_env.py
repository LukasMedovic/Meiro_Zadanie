import importlib


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("MIN_AGE", "21")
    monkeypatch.setenv("BULK_BATCH_SIZE", "2")
    from showads_client import config as cfg

    importlib.reload(cfg)
    assert cfg.settings.min_age == 21
    assert cfg.settings.bulk_batch_size == 2


def test_cli_overrides_env_and_dotenv(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("MIN_AGE=18\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MIN_AGE", "20")
    from showads_client.config import resolve_settings

    s = resolve_settings({"min_age": 25})
    assert s.min_age == 25
    s2 = resolve_settings({})
    assert s2.min_age == 20
