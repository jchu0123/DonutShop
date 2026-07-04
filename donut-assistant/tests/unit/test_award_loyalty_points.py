# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Unit tests for the award_loyalty_points agent tool.

One test per security assertion (S1–S8) as required by the TDD Planning Gate.
Each test resets the in-memory stores before running to avoid inter-test
state pollution.
"""

import pytest

import app.agent as agent_module
from app.agent import (
    AWARDED_ORDERS,
    LOYALTY_BALANCES,
    REGISTERED_USERS,
    _MAX_TOTAL_BALANCE,
    award_loyalty_points,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_stores() -> None:
    """Restore LOYALTY_BALANCES and AWARDED_ORDERS to a clean initial state."""
    for uid in REGISTERED_USERS:
        LOYALTY_BALANCES[uid] = 0
        AWARDED_ORDERS[uid].clear()


@pytest.fixture(autouse=True)
def clean_stores():
    """Auto-reset stores before every test in this module."""
    _reset_stores()
    yield
    _reset_stores()


# A valid registered user and order for reuse across tests.
_USER = "user_123"
_ORDER = "order-001"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_happy_path_awards_points() -> None:
    """Nominal success: points are credited and the new balance is returned."""
    result = award_loyalty_points(_USER, _ORDER, 100)

    assert "Success" in result
    assert "100" in result
    assert LOYALTY_BALANCES[_USER] == 100
    assert _ORDER in AWARDED_ORDERS[_USER]


def test_successive_awards_accumulate() -> None:
    """Multiple distinct orders accumulate correctly in the balance."""
    award_loyalty_points(_USER, "order-A", 50)
    award_loyalty_points(_USER, "order-B", 75)

    assert LOYALTY_BALANCES[_USER] == 125


# ---------------------------------------------------------------------------
# S1 — Unregistered user is blocked
# ---------------------------------------------------------------------------

def test_unregistered_user_blocked() -> None:
    """S1: A user_id absent from REGISTERED_USERS must be rejected."""
    result = award_loyalty_points("ghost_user", _ORDER, 10)

    assert result.startswith("Error")
    assert "not registered" in result
    # No balance entry should exist for an unknown user
    assert "ghost_user" not in LOYALTY_BALANCES


# ---------------------------------------------------------------------------
# S2 — Zero or negative points are rejected by Pydantic
# ---------------------------------------------------------------------------

def test_zero_points_rejected() -> None:
    """S2: points=0 violates the gt=0 field constraint."""
    result = award_loyalty_points(_USER, _ORDER, 0)

    assert result.startswith("Error")
    assert LOYALTY_BALANCES[_USER] == 0


def test_negative_points_rejected() -> None:
    """S2: Negative points must not credit or debit the account."""
    result = award_loyalty_points(_USER, _ORDER, -50)

    assert result.startswith("Error")
    assert LOYALTY_BALANCES[_USER] == 0


# ---------------------------------------------------------------------------
# S3 — Per-transaction cap enforced by Pydantic
# ---------------------------------------------------------------------------

def test_excessive_points_rejected() -> None:
    """S3: points > 500 violates the le=500 field constraint."""
    result = award_loyalty_points(_USER, _ORDER, 501)

    assert result.startswith("Error")
    assert LOYALTY_BALANCES[_USER] == 0


# ---------------------------------------------------------------------------
# S4 — Blank order_id is rejected
# ---------------------------------------------------------------------------

def test_blank_order_id_rejected() -> None:
    """S4: A whitespace-only order_id is caught after stripping."""
    result = award_loyalty_points(_USER, "   ", 10)

    assert result.startswith("Error")
    assert LOYALTY_BALANCES[_USER] == 0


# ---------------------------------------------------------------------------
# S5 — Duplicate order_id for same user is blocked
# ---------------------------------------------------------------------------

def test_duplicate_order_blocked() -> None:
    """S5: The same order_id cannot be credited to the same user twice."""
    first = award_loyalty_points(_USER, _ORDER, 100)
    assert "Success" in first

    second = award_loyalty_points(_USER, _ORDER, 100)
    assert second.startswith("Error")
    assert "already been awarded" in second
    # Balance must not have changed after the duplicate attempt
    assert LOYALTY_BALANCES[_USER] == 100


# ---------------------------------------------------------------------------
# S6 — Injection characters in user_id are rejected
# ---------------------------------------------------------------------------

def test_injection_chars_in_user_id() -> None:
    """S6: user_id containing SQL/shell injection chars must be rejected."""
    malicious_ids = [
        "user'; DROP TABLE users; --",
        "user\nROOT",
        'user"admin"',
        "user;id",
    ]
    for bad_id in malicious_ids:
        result = award_loyalty_points(bad_id, _ORDER, 10)
        assert result.startswith("Error"), f"Expected Error for user_id={bad_id!r}"


# ---------------------------------------------------------------------------
# S6 — Injection characters in order_id are rejected
# ---------------------------------------------------------------------------

def test_injection_chars_in_order_id() -> None:
    """S6: order_id containing injection chars must be rejected."""
    malicious_orders = [
        "../../../etc/passwd",
        "order\x00null",
        "order;rm -rf /",
        "order'or'1'='1",
    ]
    for bad_order in malicious_orders:
        result = award_loyalty_points(_USER, bad_order, 10)
        assert result.startswith("Error"), f"Expected Error for order_id={bad_order!r}"
    # No balance mutation should have occurred
    assert LOYALTY_BALANCES[_USER] == 0


# ---------------------------------------------------------------------------
# S7 — Total balance cap prevents unbounded accumulation
# ---------------------------------------------------------------------------

def test_balance_cap_enforced() -> None:
    """S7: An award that would push the balance past _MAX_TOTAL_BALANCE is blocked."""
    # Manually set the balance to just below the cap
    LOYALTY_BALANCES[_USER] = _MAX_TOTAL_BALANCE - 10

    # An award that would exactly exceed the cap
    result = award_loyalty_points(_USER, _ORDER, 500)

    assert result.startswith("Error")
    assert "exceed" in result
    # Balance must remain unchanged
    assert LOYALTY_BALANCES[_USER] == _MAX_TOTAL_BALANCE - 10


def test_award_exactly_at_cap_succeeds() -> None:
    """S7: An award that brings the balance exactly to _MAX_TOTAL_BALANCE is allowed."""
    LOYALTY_BALANCES[_USER] = _MAX_TOTAL_BALANCE - 100

    result = award_loyalty_points(_USER, _ORDER, 100)

    assert "Success" in result
    assert LOYALTY_BALANCES[_USER] == _MAX_TOTAL_BALANCE
