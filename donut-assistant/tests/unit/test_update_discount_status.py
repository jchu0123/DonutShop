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
Unit tests for the update_discount_status agent tool.
"""

import copy
import pytest

from app.agent import (
    DISCOUNT_CODES,
    ADMIN_USERS,
    update_discount_status,
    redeem_discount_code,
    process_cart_checkout,
    CARTS,
    REGISTERED_USERS,
    COMPLETED_ORDERS,
    LOYALTY_BALANCES,
    AWARDED_ORDERS,
)

_INITIAL_CARTS = {
    "cart-001": {
        "user_id": "user_123",
        "items": [
            {"name": "Glazed Donut",            "price": 1.50, "qty": 2},
            {"name": "Chocolate Frosted Donut", "price": 1.75, "qty": 1},
        ],
        "status": "open",
    },
}

def _reset_stores() -> None:
    CARTS.clear()
    CARTS.update(copy.deepcopy(_INITIAL_CARTS))
    COMPLETED_ORDERS.clear()
    for code, info in DISCOUNT_CODES.items():
        info["redeemed"] = False
        info["active"] = True
    for uid in REGISTERED_USERS:
        LOYALTY_BALANCES[uid] = 0
        if uid in AWARDED_ORDERS:
            AWARDED_ORDERS[uid].clear()

@pytest.fixture(autouse=True)
def clean_stores():
    _reset_stores()
    yield
    _reset_stores()

def test_happy_path_deactivate_and_activate():
    # Deactivate FROSTING20
    result = update_discount_status("admin_user", "FROSTING20", active=False)
    assert "Success" in result
    assert "deactivated" in result
    assert DISCOUNT_CODES["FROSTING20"]["active"] is False

    # Activate FROSTING20
    result = update_discount_status("admin_user", "FROSTING20", active=True)
    assert "Success" in result
    assert "activated" in result
    assert DISCOUNT_CODES["FROSTING20"]["active"] is True

def test_unauthorized_user_blocked():
    # Use a non-admin user ID
    result = update_discount_status("user_123", "FROSTING20", active=False)
    assert "Error" in result
    assert "not authorized" in result
    assert DISCOUNT_CODES["FROSTING20"]["active"] is True

def test_nonexistent_code_rejected():
    result = update_discount_status("admin_user", "INVALIDCODE", active=False)
    assert "Error" in result
    assert "not found" in result

def test_input_validation_disallowed_characters():
    bad_admin_ids = ["admin; DROP TABLE", "admin\nROOT", "admin' OR '1'='1"]
    for bad_id in bad_admin_ids:
        result = update_discount_status(bad_id, "FROSTING20", active=False)
        assert "Error" in result
        assert "disallowed characters" in result or "Invalid input" in result
        assert DISCOUNT_CODES["FROSTING20"]["active"] is True

    bad_codes = ["FROSTING;123", "FROSTING\n20", "../FROSTING"]
    for bad_code in bad_codes:
        result = update_discount_status("admin_user", bad_code, active=False)
        assert "Error" in result
        assert "disallowed characters" in result or "Invalid input" in result

def test_case_insensitivity_normalization():
    result = update_discount_status("admin_user", "frosting20", active=False)
    assert "Success" in result
    assert "deactivated" in result
    assert DISCOUNT_CODES["FROSTING20"]["active"] is False

def test_inactive_code_cannot_be_redeemed():
    # Deactivate the code
    update_discount_status("admin_user", "FROSTING20", active=False)

    # Attempt to redeem
    result = redeem_discount_code("FROSTING20", "user_123")
    assert "Error" in result
    assert "inactive" in result
    assert DISCOUNT_CODES["FROSTING20"]["redeemed"] is False

def test_inactive_code_ignored_during_checkout():
    # Deactivate the code
    update_discount_status("admin_user", "FROSTING20", active=False)

    # Attempt to use in checkout
    result = process_cart_checkout("user_123", "cart-001", discount_code="FROSTING20")
    assert "Success" in result
    # Checkout subtotal: 2*1.50 + 1*1.75 = 4.75. Inactive code means NO discount applied (subtotal unchanged).
    assert "4.75" in result
    assert "inactive" in result
    assert DISCOUNT_CODES["FROSTING20"]["redeemed"] is False
