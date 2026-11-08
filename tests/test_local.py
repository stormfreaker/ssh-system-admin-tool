import pytest

from sshadmin import local


def test_primary_ip_is_ipv4():
    parts = local.primary_ip().split(".")
    assert len(parts) == 4 and all(p.isdigit() for p in parts)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://x", "example.com"])
def test_rejects_non_http(url, tmp_path):
    with pytest.raises(ValueError):
        local.save_web_page(url, tmp_path / "p.html")


def test_refuses_overwrite(tmp_path):
    f = tmp_path / "p.html"
    f.write_text("keep me")
    with pytest.raises(FileExistsError):
        local.save_web_page("https://example.com", f)
