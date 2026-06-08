from app.providers.base import DataProvider

_provider: DataProvider = None

def set_data_provider(provider: DataProvider) -> None:
    global _provider
    _provider = provider

def get_data_provider() -> DataProvider:
    if _provider is None:
        raise RuntimeError("Data provider not initialized")
    return _provider