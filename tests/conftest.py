import pytest


@pytest.fixture(autouse=True)
def isolate_sampling_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep challenge defaults unless a test sets sampling env or args."""
    monkeypatch.setenv("CNPJ_LAKEHOUSE_SAMPLING_CONFIG", "")
    monkeypatch.delenv("CNPJ_LAKEHOUSE_SAMPLE_SIZE", raising=False)
    monkeypatch.delenv("CNPJ_LAKEHOUSE_PARALLEL_JOBS", raising=False)
