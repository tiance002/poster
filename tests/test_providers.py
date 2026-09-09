from app.providers import get_provider


def test_known_providers_have_secure_imap_defaults() -> None:
    assert get_provider("qq").imap_host == "imap.qq.com"
    assert get_provider("netease").imap_host == "imap.163.com"
    assert get_provider("139").imap_host == "imap.139.com"
    assert get_provider("qq").imap_port == 993
