"""Tests for database helper utilities."""

from signal_common.db import parse_polygon_ticker


def test_parse_polygon_ticker_strips_and_uppercases():
    assert parse_polygon_ticker("  brk.b  ") == "BRK.B"


def test_parse_polygon_ticker_removes_invalid_chars():
    assert parse_polygon_ticker("A$APL") == "AAPL"


def test_parse_polygon_ticker_empty_fallback():
    assert parse_polygon_ticker("") == ""
