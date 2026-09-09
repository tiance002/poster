from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderPreset:
    id: str
    label: str
    imap_host: str
    imap_port: int = 993
    smtp_host: str = ""
    smtp_port: int = 465


PROVIDERS: dict[str, ProviderPreset] = {
    "qq": ProviderPreset("qq", "QQ Mail", "imap.qq.com", smtp_host="smtp.qq.com"),
    "netease": ProviderPreset(
        "netease", "NetEase Mail (163/126)", "imap.163.com", smtp_host="smtp.163.com"
    ),
    "139": ProviderPreset("139", "139 Mail", "imap.139.com", smtp_host="smtp.139.com"),
}


def get_provider(provider_id: str) -> ProviderPreset:
    try:
        return PROVIDERS[provider_id]
    except KeyError as error:
        raise ValueError(f"Unsupported provider: {provider_id}") from error
