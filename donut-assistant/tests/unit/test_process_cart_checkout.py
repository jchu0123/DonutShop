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
Unit tests for the process_cart_checkout agent tool.

One test per security assertion (C1–C10) as required by the TDD Planning Gate.
Fixtures reset all in-memory stores before each test to prevent inter-test
state pollution.
"""

import copy

import pytest

import app.agent as agent_module
from app.agent import (
    AWARDED_ORDERS,
    CARTS,
    COMPLETED_ORDERS,
    DISCOUNT_CODES,
    LOYALTY_BALANCES,
    REGISTERED_USERS,
    process_cart_checkout,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_INITIAL_CARTS = {
    "cart-001": {
        "user_id": "user_123",
        "items": [
            {"name": "Glazed Donut",            "price": 1.50, "qty": 2},
            {"name": "Chocolate Frosted Donut", "price": 1.75, "qty": 1},
        ],
        "status": "open",
    },
    "cart-002": {
        "user_id": "customer_donut",
        "items": [
            {"name": "Boston Cream Donut", "price": 2.20, "qty": 3},
        ],
        "status": "open",
    },
}

_INITIAL_DISCOUNT_CODES = {
    "FROSTING20": {"redeemed": False, "discount": "20% off frosting products"},
    "SPRINKLES30": {"redeemed": False, "discount": "30% off sprinkles products"},
}


def _reset_stores() -> None:
    """Restore all in-memory stores to a clean initial state."""
    CARTS.clear()
    CARTS.update(copy.deepcopy(_INITIAL_CARTS))

    COMPLETED_ORDERS.clear()

    for code, info in DISCOUNT_CODES.items():
        info["redeemed"] = False
        info["active"] = True

    for uid in REGISTERED_USERS:
        LOYALTY_BALANCES[uid] = 0
        AWARDED_ORDERS[uid].clear()


@pytest.fixture(autouse=True)
def clean_stores():
    _reset_stores()
    yield
    _reset_stores()


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_happy_path_no_discount() -> None:
    """Nominal checkout without a discount code."""
    result = process_cart_checkout("user_123", "cart-001")

    assert "Success" in result
    # cart-001 subtotal: 2*1.50 + 1*1.75 = 4.75
    assert "4.75" in result
    assert CARTS["cart-001"]["status"] == "checked_out"
    assert len(COMPLETED_ORDERS) == 1
    # Loyalty points auto-awarded (3 donuts * 50 points = 150 points)
    assert LOYALTY_BALANCES["user_123"] == 150
    assert "150 loyalty point(s) awarded" in result


def test_happy_path_valid_discount() -> None:
    """Valid discount reduces total by 20% and flips code to redeemed."""
    result = process_cart_checkout("user_123", "cart-001", discount_code="FROSTING20")

    assert "Success" in result
    # 4.75 * 0.80 = 3.80
    assert "3.80" in result
    assert "FROSTING20" in result
    assert DISCOUNT_CODES["FROSTING20"]["redeemed"] is True


def test_discount_code_case_insensitive() -> None:
    """Discount codes are uppercased before lookup."""
    result = process_cart_checkout("user_123", "cart-001", discount_code="frosting20")

    assert "Success" in result
    assert "3.80" in result
    assert DISCOUNT_CODES["FROSTING20"]["redeemed"] is True


# ---------------------------------------------------------------------------
# C1 — Unregistered user blocked
# ---------------------------------------------------------------------------

def test_unregistered_user_blocked() -> None:
    """C1: A user_id not in REGISTERED_USERS must be rejected."""
    result = process_cart_checkout("ghost_user", "cart-001")

    assert result.startswith("Error")
    assert "not registered" in result
    assert CARTS["cart-001"]["status"] == "open"


# ---------------------------------------------------------------------------
# C2 — Blank cart_id rejected
# ---------------------------------------------------------------------------

def test_blank_cart_id_rejected() -> None:
    """C2: Whitespace-only cart_id is caught after stripping."""
    result = process_cart_checkout("user_123", "   ")

    assert result.startswith("Error")
    assert LOYALTY_BALANCES["user_123"] == 0


# ---------------------------------------------------------------------------
# C3 — Injection characters in cart_id rejected
# ---------------------------------------------------------------------------

def test_injection_chars_in_cart_id() -> None:
    """C3: cart_id containing injection chars must be rejected."""
    malicious_ids = [
        "cart'; DROP TABLE carts; --",
        "cart\nROOT",
        "../../../etc/passwd",
        "cart;rm -rf /",
    ]
    for bad_id in malicious_ids:
        result = process_cart_checkout("user_123", bad_id)
        assert result.startswith("Error"), f"Expected Error for cart_id={bad_id!r}"


# ---------------------------------------------------------------------------
# C4 — Non-existent cart rejected
# ---------------------------------------------------------------------------

def test_cart_not_found() -> None:
    """C4: A cart_id that does not exist in CARTS must return an error."""
    result = process_cart_checkout("user_123", "cart-999")

    assert result.startswith("Error")
    assert "not found" in result


# ---------------------------------------------------------------------------
# C5 — Cart-hijacking (IDOR) blocked
# ---------------------------------------------------------------------------

def test_cart_belongs_to_different_user() -> None:
    """C5: A user must not be able to check out another user's cart."""
    # cart-001 belongs to user_123; user_abc tries to check it out
    result = process_cart_checkout("user_abc", "cart-001")

    assert result.startswith("Error")
    assert "does not belong" in result
    assert CARTS["cart-001"]["status"] == "open"


# ---------------------------------------------------------------------------
# C6 — Empty cart rejected
# ---------------------------------------------------------------------------

def test_empty_cart_rejected() -> None:
    """C6: A cart with no line items must not generate an order."""
    CARTS["cart-empty"] = {
        "user_id": "user_123",
        "items": [],
        "status": "open",
    }
    # Also initialise loyalty stores for user
    LOYALTY_BALANCES.setdefault("user_123", 0)
    AWARDED_ORDERS.setdefault("user_123", set())

    result = process_cart_checkout("user_123", "cart-empty")

    assert result.startswith("Error")
    assert "empty" in result
    assert len(COMPLETED_ORDERS) == 0


# ---------------------------------------------------------------------------
# C7 — Already-checked-out cart blocked
# ---------------------------------------------------------------------------

def test_already_checked_out_cart_blocked() -> None:
    """C7: Double-processing the same cart must be rejected."""
    first = process_cart_checkout("user_123", "cart-001")
    assert "Success" in first

    second = process_cart_checkout("user_123", "cart-001")
    assert second.startswith("Error")
    assert "already been checked out" in second
    # Only one completed order should exist
    assert len(COMPLETED_ORDERS) == 1


# ---------------------------------------------------------------------------
# C8 — Invalid discount code → checkout still succeeds with a warning
# ---------------------------------------------------------------------------

def test_invalid_discount_code_ignored() -> None:
    """C8: An unrecognised code does not block checkout; a note is included."""
    result = process_cart_checkout("user_123", "cart-001", discount_code="BOGUS99")

    assert "Success" in result
    assert "not recognised" in result
    # Full price charged (4.75)
    assert "4.75" in result


def test_already_redeemed_discount_ignored() -> None:
    """C8: A previously redeemed code does not block checkout."""
    DISCOUNT_CODES["FROSTING20"]["redeemed"] = True

    result = process_cart_checkout("user_123", "cart-001", discount_code="FROSTING20")

    assert "Success" in result
    assert "already redeemed" in result
    # Full price charged
    assert "4.75" in result


# ---------------------------------------------------------------------------
# C10 — Total never negative
# ---------------------------------------------------------------------------

def test_total_never_negative() -> None:
    """C10: A discount cannot drive the total below $0.00."""
    # Seed a cart with a very small subtotal
    CARTS["cart-tiny"] = {
        "user_id": "user_123",
        "items": [{"name": "Sample", "price": 0.01, "qty": 1}],
        "status": "open",
    }
    LOYALTY_BALANCES.setdefault("user_123", 0)
    AWARDED_ORDERS.setdefault("user_123", set())

    result = process_cart_checkout("user_123", "cart-tiny", discount_code="FROSTING20")

    assert "Success" in result
    # 0.01 * 0.80 = 0.008 → rounds to 0.01, but either way must not be negative
    order = next(iter(COMPLETED_ORDERS.values()))
    assert order["total"] >= 0.0


# ---------------------------------------------------------------------------
# Dynamic loyalty points tests
# ---------------------------------------------------------------------------

def test_loyalty_points_calculated_on_donut_quantity() -> None:
    """Loyalty points awarded should be 50 per donut ordered."""
    CARTS["cart-dynamic"] = {
        "user_id": "user_123",
        "items": [
            {"name": "Glazed Donut", "price": 1.50, "qty": 4},
        ],
        "status": "open",
    }
    LOYALTY_BALANCES.setdefault("user_123", 0)
    AWARDED_ORDERS.setdefault("user_123", set())

    result = process_cart_checkout("user_123", "cart-dynamic")

    assert "Success" in result
    # 4 donuts * 50 = 200 points
    assert "200 loyalty point(s) awarded" in result
    assert LOYALTY_BALANCES["user_123"] == 200


def test_loyalty_points_capped_at_500() -> None:
    """Loyalty points awarded should be capped at 500 per checkout."""
    CARTS["cart-capped"] = {
        "user_id": "user_123",
        "items": [
            {"name": "Glazed Donut", "price": 1.50, "qty": 12},
        ],
        "status": "open",
    }
    LOYALTY_BALANCES.setdefault("user_123", 0)
    AWARDED_ORDERS.setdefault("user_123", set())

    result = process_cart_checkout("user_123", "cart-capped")

    assert "Success" in result
    # 12 donuts * 50 = 600 points, capped at 500
    assert "500 loyalty point(s) awarded" in result
    assert LOYALTY_BALANCES["user_123"] == 500
