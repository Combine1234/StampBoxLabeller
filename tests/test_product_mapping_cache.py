from __future__ import annotations

from urllib.error import URLError

from src import product_mapping
from src.product_mapping import (
    CODE_HEADER,
    CODE_NAME_HEADER,
    COLOR_HEADER,
    DEFAULT_MAPPING_URL,
    DEFAULT_MAPPING_SHEETS,
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
    cached_rows = load_product_mapping(user_cache)
    assert len(cached_rows) == 1
    assert cached_rows[0].code == "DESK BLUE"


def test_default_mapping_downloads_all_configured_sheets(tmp_path, monkeypatch) -> None:
    user_cache = tmp_path / "user-cache.csv"
    requested_urls: list[str] = []

    def download(source: str) -> str:
        requested_urls.append(source)
        if "gid=0" in source:
            return (
                f"{PRODUCT_HEADER},SKU,{VARIANT_HEADER},{CODE_NAME_HEADER},{COLOR_HEADER}\n"
                "Desk,P00001,Blue,DESK,BLUE\n"
            )
        if "gid=798807419" in source:
            return "Desk,Blue\n"
        return "\nSOGOODS Rack,P00002,Silver,3 Shelf,Silver\n"

    monkeypatch.setattr(product_mapping, "_user_mapping_cache_path", lambda: user_cache)
    monkeypatch.setattr(product_mapping, "_read_url_text", download)
    product_mapping._MAPPING_CACHE.clear()

    rows = load_product_mapping(DEFAULT_MAPPING_URL)

    assert {row.code for row in rows} == {"DESK BLUE", "3 Shelf Silver"}
    assert len(requested_urls) == len(DEFAULT_MAPPING_SHEETS)
    assert {url.rsplit("gid=", 1)[-1] for url in requested_urls} == {
        gid for _name, gid in DEFAULT_MAPPING_SHEETS
    }
