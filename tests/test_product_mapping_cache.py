from __future__ import annotations

from urllib.error import URLError

from src import product_mapping
from src.product_mapping import (
    CODE_HEADER,
    DEFAULT_MAPPING_URL,
    PRODUCT_HEADER,
    VARIANT_HEADER,
    load_product_mapping,
)


def _mapping_csv() -> str:
    return (
        f"{PRODUCT_HEADER},SKU,{VARIANT_HEADER},{CODE_HEADER}\n"
        "Desk,P00001,Blue,DESK BLUE\n"
    )


def test_remote_mapping_uses_bundled_cache_when_ssl_fails(tmp_path, monkeypatch) -> None:
    bundled_cache = tmp_path / "bundled.csv"
    bundled_cache.write_text(_mapping_csv(), encoding="utf-8")
    monkeypatch.setattr(product_mapping, "_bundled_mapping_path", lambda: bundled_cache)
    monkeypatch.setattr(
        product_mapping,
        "_user_mapping_cache_path",
        lambda: tmp_path / "missing-user-cache.csv",
    )

    def fail_download(_source: str) -> str:
        raise URLError("certificate verify failed")

    monkeypatch.setattr(product_mapping, "_read_url_text", fail_download)
    product_mapping._MAPPING_CACHE.clear()

    rows = load_product_mapping(DEFAULT_MAPPING_URL)

    assert len(rows) == 1
    assert rows[0].code == "DESK BLUE"


def test_remote_mapping_refreshes_user_cache(tmp_path, monkeypatch) -> None:
    user_cache = tmp_path / "user-cache.csv"
    monkeypatch.setattr(product_mapping, "_user_mapping_cache_path", lambda: user_cache)
    monkeypatch.setattr(product_mapping, "_read_url_text", lambda _source: _mapping_csv())
    product_mapping._MAPPING_CACHE.clear()

    rows = load_product_mapping(DEFAULT_MAPPING_URL)

    assert len(rows) == 1
    assert rows[0].code == "DESK BLUE"
    assert user_cache.read_text(encoding="utf-8") == _mapping_csv()
