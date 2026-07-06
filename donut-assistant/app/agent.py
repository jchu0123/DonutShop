# ruff: noqa
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

import os
import uuid as _uuid
from functools import cached_property
from typing import Any, Optional

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import Client, types
from pydantic import ValidationError

from app.app_utils.typing import CartCheckoutRequest, LoyaltyAwardRequest, DiscountStatusUpdateRequest


class CustomGemini(Gemini):
    api_key: str = os.environ.get("GOOGLE_API_KEY", "")

    @cached_property
    def api_client(self) -> Client:
        from google.genai import Client

        base_url, api_version = self._base_url_and_api_version
        kwargs_for_http_options = {
            "headers": self._tracking_headers(),
            "retry_options": self.retry_options,
            "base_url": base_url,
        }
        if api_version:
            kwargs_for_http_options["api_version"] = api_version

        kwargs = {
            "http_options": types.HttpOptions(**kwargs_for_http_options),
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        else:
            kwargs["vertexai"] = True

        if self.model.startswith("projects/"):
            kwargs["vertexai"] = True

        return Client(**kwargs)

    @cached_property
    def _live_api_client(self) -> Client:
        from google.genai import Client

        base_url, _ = self._base_url_and_api_version
        kwargs = {
            "http_options": types.HttpOptions(
                headers=self._tracking_headers(),
                api_version=self._live_api_version,
                base_url=base_url,
            ),
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        else:
            kwargs["vertexai"] = True

        if self.model.startswith("projects/"):
            kwargs["vertexai"] = True

        return Client(**kwargs)


# In-memory store for discount codes and their redemption status
DISCOUNT_CODES = {
    "FROSTING20": {"redeemed": False, "active": True, "discount": "20% off frosting products"},
    "SPRINKLES30": {"redeemed": False, "active": True, "discount": "30% off sprinkles products"},
    "GLAZED10": {"redeemed": False, "active": True, "discount": "10% off glazed products"},
    "JELLY15": {"redeemed": False, "active": True, "discount": "15% off jelly products"},
    "BOSTON25": {"redeemed": False, "active": True, "discount": "25% off Boston Cream products"},
    "MAPLE20": {"redeemed": False, "active": True, "discount": "20% off maple bacon products"},
    "FRITTER10": {"redeemed": False, "active": True, "discount": "10% off apple fritters"},
    "BLUEBERRY15": {"redeemed": False, "active": True, "discount": "15% off blueberry products"},
    "CHOCO20": {"redeemed": False, "active": True, "discount": "20% off double chocolate products"},
    "MATCHA25": {"redeemed": False, "active": True, "discount": "25% off matcha products"},
}

# In-memory store for registered users
REGISTERED_USERS = {"user_123", "user_abc", "customer_donut", "vip_customer"}

# In-memory store for registered administrators
ADMIN_USERS = {"admin_user", "admin_boss"}


# Loyalty points balance per user  {user_id: int}
LOYALTY_BALANCES: dict[str, int] = {uid: 0 for uid in REGISTERED_USERS}

# Tracks which order IDs have already been awarded per user, preventing
# double-crediting (S5).  {user_id: set[str]}
AWARDED_ORDERS: dict[str, set[str]] = {uid: set() for uid in REGISTERED_USERS}

# Maximum accumulated balance a user may hold (S7).
_MAX_TOTAL_BALANCE = 1_000_000

# Loyalty points automatically awarded per successful checkout.
_LOYALTY_POINTS_PER_ORDER = 100

# In-memory cart store: {cart_id: {"user_id", "items", "status"}}
# status ∈ {"open", "checked_out"}
CARTS: dict[str, dict] = {
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

# Completed order audit log: {order_id: dict}
COMPLETED_ORDERS: dict[str, dict] = {}


def get_donut_menu() -> str:
    """Get the menu and prices of the donut store.

    Returns:
        A formatted string listing the available donuts and their prices.
    """
    return (
        "Donut Menu:\n"
        "- Glazed Donut: $1.50 (Eligible for GLAZED10)\n"
        "- Chocolate Frosted Donut: $1.75 (Eligible for FROSTING20)\n"
        "- Strawberry Sprinkles Donut: $1.85 (Eligible for SPRINKLES30)\n"
        "- Jelly-Filled Donut: $2.00 (Eligible for JELLY15)\n"
        "- Boston Cream Donut: $2.20 (Eligible for BOSTON25)\n"
        "- Maple Bacon Donut: $2.50 (Eligible for MAPLE20)\n"
        "- Apple Fritter: $2.25 (Eligible for FRITTER10)\n"
        "- Cinnamon Twist: $1.95\n"
        "- Old Fashioned Glazed Donut: $1.60\n"
        "- Blueberry Cake Donut: $1.70 (Eligible for BLUEBERRY15)\n"
        "- Red Velvet Cake Donut: $1.80\n"
        "- Coconut Toasted Donut: $1.90\n"
        "- Powdered Sugar Donut: $1.40\n"
        "- Lemon Filled Donut: $2.10\n"
        "- Cronut (Croissant Donut): $3.00\n"
        "- Double Chocolate Donut: $1.80 (Eligible for CHOCO20)\n"
        "- Vanilla Frosted Donut: $1.75\n"
        "- Cinnamon Roll Donut: $2.25\n"
        "- Pumpkin Spice Cake Donut: $1.85\n"
        "- Sour Cream Donut: $1.70\n"
        "- Salted Caramel Glazed Donut: $2.10\n"
        "- Bavarian Cream Donut: $2.15\n"
        "- Cookies and Cream Donut: $2.20\n"
        "- Matcha Green Tea Donut: $2.30 (Eligible for MATCHA25)\n"
        "- Apple Cider Donut: $1.85\n"
        "- S'mores Donut: $2.40\n"
        "- Raspberry Jam Donut: $2.05\n"
        "- Peanut Butter Cup Donut: $2.45\n"
        "- Pistachio Glazed Donut: $2.35\n"
        "- Lemon Poppyseed Donut: $1.95\n"
        "- Banana Pudding Donut: $2.10\n"
        "- Coconut Cream Donut: $2.20\n"
        "- Salted Caramel Pretzel Donut: $2.50\n"
        "- White Chocolate Raspberry Donut: $2.40\n"
        "- Caramel Apple Donut: $2.25\n"
        "- Espresso Cake Donut: $1.90\n"
        "- Rocky Road Donut: $2.30\n"
        "- Maple Pecan Donut: $2.15\n"
        "- Mint Chocolate Chip Donut: $2.20\n"
        "- Key Lime Pie Donut: $2.10"
    )


def redeem_discount_code(code: str, user_id: str) -> str:
    """Redeems a single-use discount code for a registered user.

    Args:
        code: The discount code to redeem (e.g., FROSTING20, SPRINKLES30).
        user_id: The registered user ID of the customer.

    Returns:
        A string indicating if the discount code was successfully redeemed or the error message.
    """
    if user_id not in REGISTERED_USERS:
        return f"Error: User ID '{user_id}' is not registered. Registration is required to redeem codes."

    code_upper = code.strip().upper()
    if code_upper not in DISCOUNT_CODES:
        return f"Error: Invalid discount code '{code}'."

    code_info = DISCOUNT_CODES[code_upper]
    if not code_info.get("active", True):
        return f"Error: Discount code '{code_upper}' is currently inactive."

    if code_info["redeemed"]:
        return f"Error: Discount code '{code_upper}' has already been redeemed."

    code_info["redeemed"] = True
    return f"Success: Discount code '{code_upper}' has been successfully redeemed! Enjoy your {code_info['discount']}."


def award_loyalty_points(user_id: str, order_id: str, points: int) -> str:
    """Awards loyalty points to a registered user after a successful purchase.

    Args:
        user_id:  The registered user's ID (alphanumeric, underscore, hyphen only).
        order_id: The unique identifier of the completed purchase order.
        points:   Number of points to award (1–500 per transaction).

    Returns:
        A string confirming the award and new balance, or a descriptive error
        message if the request is invalid or blocked by a security guard.

    Note:
        This implementation uses in-memory dicts and is not thread-safe for
        concurrent requests targeting the same user_id/order_id pair (S8).
    """
    # --- Input validation: S2 (points > 0), S3 (points <= 500), S6 (safe chars) ---
    try:
        req = LoyaltyAwardRequest(
            user_id=user_id,
            order_id=order_id.strip(),
            points=points,
        )
    except ValidationError as exc:
        first_error = exc.errors()[0]
        return f"Error: Invalid input — {first_error['msg']}."

    # --- S4: order_id must be non-blank after stripping whitespace ---
    if not req.order_id:
        return "Error: order_id must not be blank."

    # --- S1: caller must be a registered user ---
    if req.user_id not in REGISTERED_USERS:
        return f"Error: User '{req.user_id}' is not registered. Registration is required to earn loyalty points."

    # --- S5: duplicate order guard — same order cannot be credited twice ---
    if req.order_id in AWARDED_ORDERS[req.user_id]:
        return (
            f"Error: Loyalty points for order '{req.order_id}' have already been "
            f"awarded to user '{req.user_id}'."
        )

    # --- S7: balance cap — prevent unbounded accumulation ---
    current_balance = LOYALTY_BALANCES[req.user_id]
    if current_balance + req.points > _MAX_TOTAL_BALANCE:
        return (
            f"Error: Awarding {req.points} point(s) would exceed the maximum "
            f"allowed balance of {_MAX_TOTAL_BALANCE:,}."
        )

    # --- Commit the award ---
    LOYALTY_BALANCES[req.user_id] += req.points
    AWARDED_ORDERS[req.user_id].add(req.order_id)
    new_balance = LOYALTY_BALANCES[req.user_id]

    return (
        f"Success: {req.points} loyalty point(s) awarded to '{req.user_id}' "
        f"for order '{req.order_id}'. New balance: {new_balance} point(s)."
    )


def process_cart_checkout(
    user_id: str,
    cart_id: str,
    discount_code: str | None = None,
) -> str:
    """Applies an optional discount and processes a cart to a completed order.

    Args:
        user_id:       The registered user's ID performing the checkout.
        cart_id:       The unique identifier of the cart to check out.
        discount_code: Optional single-use discount code to apply.

    Returns:
        A success string with the order ID and final total, or a descriptive
        error message if any validation or security guard fires.

    Note:
        On success the function internally calls award_loyalty_points to credit
        the user. The in-memory stores are not thread-safe for concurrent
        checkouts on the same cart_id.
    """
    # --- Input validation: C2 (blank cart_id), C3 (injection chars) ---
    try:
        req = CartCheckoutRequest(
            user_id=user_id,
            cart_id=cart_id.strip(),
            discount_code=discount_code,
        )
    except ValidationError as exc:
        return f"Error: Invalid input \u2014 {exc.errors()[0]['msg']}."

    # --- C2: blank cart_id after strip ---
    if not req.cart_id:
        return "Error: cart_id must not be blank."

    # --- C1: user must be registered ---
    if req.user_id not in REGISTERED_USERS:
        return f"Error: User '{req.user_id}' is not registered."

    # --- C4: cart must exist ---
    cart = CARTS.get(req.cart_id)
    if cart is None:
        return f"Error: Cart '{req.cart_id}' not found."

    # --- C5: cart must belong to the requesting user (IDOR guard) ---
    if cart["user_id"] != req.user_id:
        return (
            f"Error: Cart '{req.cart_id}' does not belong to user '{req.user_id}'."
        )

    # --- C7: prevent double-processing ---
    if cart["status"] == "checked_out":
        return f"Error: Cart '{req.cart_id}' has already been checked out."

    # --- C6: cart must have at least one line item ---
    if not cart["items"]:
        return f"Error: Cart '{req.cart_id}' is empty."

    # --- Compute subtotal ---
    subtotal = sum(item["price"] * item["qty"] for item in cart["items"])

    # --- C8 / C9: optional discount application ---
    discount_note = ""
    if req.discount_code:
        code_upper = req.discount_code.strip().upper()
        code_info = DISCOUNT_CODES.get(code_upper)
        if code_info is None:
            discount_note = (
                f" (discount code '{code_upper}' not recognised \u2014 no discount applied)"
            )
        elif not code_info.get("active", True):
            discount_note = (
                f" (discount code '{code_upper}' is inactive \u2014 no discount applied)"
            )
        elif code_info["redeemed"]:
            discount_note = (
                f" (discount code '{code_upper}' already redeemed \u2014 no discount applied)"
            )
        else:
            # Redeem and apply a flat 20% discount
            code_info["redeemed"] = True
            subtotal = subtotal * 0.80
            discount_note = f" (discount '{code_upper}' applied: 20% off)"

    # --- C10: total is floored at $0.00 ---
    final_total = max(0.0, round(subtotal, 2))

    # --- Commit order ---
    order_id = f"order-{_uuid.uuid4().hex[:8]}"
    COMPLETED_ORDERS[order_id] = {
        "user_id": req.user_id,
        "cart_id": req.cart_id,
        "items": list(cart["items"]),
        "total": final_total,
        "discount_code": req.discount_code,
    }
    cart["status"] = "checked_out"

    # --- Auto-award loyalty points ---
    total_donuts = sum(item["qty"] for item in cart["items"])
    points_to_award = min(500, total_donuts * 50)
    award_loyalty_points(req.user_id, order_id, points_to_award)

    return (
        f"Success: Order '{order_id}' placed for user '{req.user_id}'. "
        f"Final total: ${final_total:.2f}{discount_note}. "
        f"{points_to_award} loyalty point(s) awarded."
    )


def update_discount_status(admin_id: str, code: str, active: bool) -> str:
    """Allows administrators to activate or deactivate discount codes.

    Args:
        admin_id: The ID of the administrator performing the action.
        code:     The discount code to update.
        active:   True to activate, False to deactivate.

    Returns:
        A success or error message.
    """
    try:
        req = DiscountStatusUpdateRequest(
            admin_id=admin_id,
            code=code.strip(),
            active=active,
        )
    except ValidationError as exc:
        first_error = exc.errors()[0]
        return f"Error: Invalid input — {first_error['msg']}."

    if req.admin_id not in ADMIN_USERS:
        return f"Error: User '{req.admin_id}' is not authorized as an administrator."

    code_upper = req.code.upper()
    if code_upper not in DISCOUNT_CODES:
        return f"Error: Discount code '{req.code}' not found."

    DISCOUNT_CODES[code_upper]["active"] = req.active
    status_str = "activated" if req.active else "deactivated"
    return f"Success: Discount code '{code_upper}' has been {status_str}."


def get_loyalty_points(user_id: str) -> str:
    """Retrieve the total loyalty points balance for a registered user.

    Args:
        user_id: The registered user ID of the customer.

    Returns:
        A string indicating the user's loyalty points balance or an error message.
    """
    if user_id not in REGISTERED_USERS:
        return f"Error: User ID '{user_id}' is not registered."

    balance = LOYALTY_BALANCES[user_id]
    return f"Success: User '{user_id}' has {balance} loyalty points."


root_agent = Agent(
    name="donut_assistant",
    model=CustomGemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a friendly and helpful AI shopping assistant for a donut store. "
        "Your goal is to help customers browse the donut menu, redeem discount codes, check their loyalty points balance, and assist administrators with managing discount codes. "
        "You must ask for the customer's registered user ID to redeem a discount code or check loyalty points, and verify administrator ID before changing discount status. "
        "Use the available tools to get the menu, redeem discount codes, check loyalty points, and update discount statuses."
    ),
    tools=[get_donut_menu, redeem_discount_code, award_loyalty_points, process_cart_checkout, update_discount_status, get_loyalty_points],
)

app = App(
    root_agent=root_agent,
    name="app",
)
