"""Tests for sector keyword to ETF mapping and Polygon result parsing."""

from signal_common.sector_etfs import (
    benchmark_etf_from_description,
    normalize_sector_key,
    sector_from_polygon_result,
)


def test_normalize_sector_key_slug():
    assert normalize_sector_key("Health Care") == "health_care"


def test_benchmark_etf_from_description_xlk():
    etf, label = benchmark_etf_from_description("Semiconductor and related devices")
    assert etf == "XLK"
    assert label is not None


def test_benchmark_etf_from_description_unknown_maps_spy():
    etf, label = benchmark_etf_from_description("Miscellaneous manufacturing industries")
    assert etf == "SPY"
    assert label is not None


def test_sector_from_polygon_result_semiconductor():
    sk, sl, etf = sector_from_polygon_result({"sic_description": "Semiconductor and related devices"})
    assert sk != "unknown"
    assert etf == "XLK"
    assert sl is not None


def test_sector_from_polygon_result_empty():
    sk, sl, etf = sector_from_polygon_result({})
    assert sk == "unknown"
    assert sl is None
    assert etf is None
