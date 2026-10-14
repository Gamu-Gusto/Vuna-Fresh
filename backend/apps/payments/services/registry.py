"""Checkout code calls get_provider(name) — never branches on provider name itself."""
from .direct_deposit import DirectDepositProvider
from .payfast import PayFastProvider

_PROVIDERS = {
    "payfast": PayFastProvider,
    "direct_deposit": DirectDepositProvider,
    # 'paystack': PayStackProvider,  — separate follow-up task, not built yet.
}


def get_provider(provider_name):
    provider_cls = _PROVIDERS.get(provider_name)
    if provider_cls is None:
        raise ValueError(f"Unknown or unsupported payment provider: {provider_name!r}")
    return provider_cls()
