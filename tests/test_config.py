import pytest

from sshadmin.config import ConfigError, load_config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ("SSHADMIN_HOST", "SSHADMIN_USER", "SSHADMIN_PORT", "SSHADMIN_PASSWORD",
              "SSHADMIN_KEY_FILE", "SSHADMIN_KNOWN_HOSTS"):
        monkeypatch.delenv(k, raising=False)


def test_missing_settings_raise():
    with pytest.raises(ConfigError, match="SSHADMIN_HOST"):
        load_config(env_file=None)


def test_env_file_loaded(tmp_path):
    f = tmp_path / ".env"
    f.write_text("SSHADMIN_HOST=10.0.0.5\nSSHADMIN_USER=admin\nSSHADMIN_PORT=2222\n")
    cfg = load_config(f)
    assert (cfg.host, cfg.username, cfg.port) == ("10.0.0.5", "admin", 2222)


def test_bad_port(monkeypatch):
    monkeypatch.setenv("SSHADMIN_HOST", "h")
    monkeypatch.setenv("SSHADMIN_USER", "u")
    monkeypatch.setenv("SSHADMIN_PORT", "99999")
    with pytest.raises(ConfigError):
        load_config(env_file=None)


def test_password_hidden_in_repr(monkeypatch):
    monkeypatch.setenv("SSHADMIN_HOST", "h")
    monkeypatch.setenv("SSHADMIN_USER", "u")
    monkeypatch.setenv("SSHADMIN_PASSWORD", "s3cret")
    assert "s3cret" not in repr(load_config(env_file=None))
