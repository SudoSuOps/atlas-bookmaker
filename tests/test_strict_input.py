#!/usr/bin/env python3
"""
tests/test_strict_input.py · validate the firm-doctrine strict-input gate.

This test guarantees the gate catches fabrications BEFORE they ship.
"""

from __future__ import annotations

from agent.tools.strict_input_check import run_strict_input_check


def test_passes_when_all_numbers_in_input():
    deal = {
        "asset_class": "Dollar General STNL",
        "market": "Tampa FL",
        "price": "$2.4M",
        "cap_rate": "6.85%",
        "lease_term": "12-yr NNN",
        "tenant_credit": "BBB / IG",
    }
    output = "Dollar General STNL · Tampa FL · $2.4M · 6.85% · 12-yr NNN · BBB / IG."
    result = run_strict_input_check(deal, output)
    assert result.pass_check, f"should pass · fabricated: {result.fabricated_tokens}"


def test_fails_on_fabricated_sf():
    deal = {"price": "$2.4M", "cap_rate": "6.85%"}
    output = "Building has 8,710 SF and trades at $2.4M cap 6.85%."
    result = run_strict_input_check(deal, output)
    assert not result.pass_check, "should catch fabricated 8,710 SF"
    assert any("SF" in tok or "8" in tok for tok in result.fabricated_tokens)


def test_fails_on_fabricated_noi():
    deal = {"price": "$2.4M", "cap_rate": "6.85%"}
    output = "NOI: $134,000 · price $2.4M · cap 6.85%."
    result = run_strict_input_check(deal, output)
    assert not result.pass_check
    assert any("$134" in tok or "134,000" in tok for tok in result.fabricated_tokens)


def test_passes_when_tbd_placeholder_used():
    deal = {"price": "$2.4M", "cap_rate": "6.85%"}
    output = "Building has [TBD: SF] · trades at $2.4M cap 6.85%."
    result = run_strict_input_check(deal, output)
    assert result.pass_check, "[TBD] should be honored as missing-value placeholder"


def test_passes_with_hedera_constants():
    """Hedera topic / operator are firm constants · always allowed."""
    deal = {"price": "$2.4M"}
    output = "Receipt: hashscan.io/topic/0.0.10291838/123 · operator 0.0.10291827 · $2.4M."
    result = run_strict_input_check(deal, output)
    assert result.pass_check


def test_year_2026_is_allowed():
    """Current year is universal · don't flag year-of-publication tokens."""
    deal = {"price": "$2.4M"}
    output = "Listed in 2026 · $2.4M asking."
    result = run_strict_input_check(deal, output)
    assert result.pass_check
