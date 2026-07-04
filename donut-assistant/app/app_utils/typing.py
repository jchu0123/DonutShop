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

import re
import uuid
from typing import (
    Literal,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

# Allowlist for user/order IDs: alphanumeric, underscore, hyphen only.
# Blocks injection characters such as quotes, semicolons, and newlines (S6).
_SAFE_ID = re.compile(r"^[A-Za-z0-9_\-]+$")


class Feedback(BaseModel):
    """Represents feedback for a conversation."""

    score: int | float
    text: str | None = ""
    log_type: Literal["feedback"] = "feedback"
    service_name: Literal["donut-assistant"] = "donut-assistant"
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class LoyaltyAwardRequest(BaseModel):
    """Validated input for the award_loyalty_points tool.

    Constraints:
        user_id:  1–64 chars, alphanumeric/underscore/hyphen (S6).
        order_id: 1–128 chars, alphanumeric/underscore/hyphen (S4, S6).
        points:   1–500 per transaction (S2 prevents zero/negative; S3 caps value).
    """

    user_id: str = Field(..., min_length=1, max_length=64)
    order_id: str = Field(..., min_length=1, max_length=128)
    points: int = Field(..., gt=0, le=500)

    @field_validator("user_id", "order_id")
    @classmethod
    def no_injection_chars(cls, v: str) -> str:
        """Reject IDs containing characters outside the safe allowlist (S6)."""
        if not _SAFE_ID.match(v):
            raise ValueError(
                "ID contains disallowed characters; only letters, digits, "
                "underscores, and hyphens are permitted"
            )
        return v


class CartCheckoutRequest(BaseModel):
    """Validated input for the process_cart_checkout tool.

    Constraints:
        user_id:       Registered user performing checkout (C1, C3).
        cart_id:       Non-blank, safe-charset cart identifier (C2, C3).
        discount_code: Optional single-use code; normalised to uppercase before
                       lookup (C8). Not subject to the safe-ID regex since
                       codes may use alphanumeric patterns only anyway —
                       validated separately by DISCOUNT_CODES lookup.
    """

    user_id: str = Field(..., min_length=1, max_length=64)
    cart_id: str = Field(..., min_length=1, max_length=128)
    discount_code: str | None = Field(default=None)

    @field_validator("user_id", "cart_id")
    @classmethod
    def no_injection_chars(cls, v: str) -> str:
        """Reject IDs containing characters outside the safe allowlist (C3)."""
        if not _SAFE_ID.match(v):
            raise ValueError(
                "ID contains disallowed characters; only letters, digits, "
                "underscores, and hyphens are permitted"
            )
        return v


class DiscountStatusUpdateRequest(BaseModel):
    """Validated input for the update_discount_status tool.

    Constraints:
        admin_id: 1–64 chars, alphanumeric/underscore/hyphen.
        code:     1–64 chars, alphanumeric/underscore/hyphen.
        active:   boolean value.
    """

    admin_id: str = Field(..., min_length=1, max_length=64)
    code: str = Field(..., min_length=1, max_length=64)
    active: bool

    @field_validator("admin_id", "code")
    @classmethod
    def no_injection_chars(cls, v: str) -> str:
        """Reject IDs or codes containing characters outside the safe allowlist."""
        if not _SAFE_ID.match(v):
            raise ValueError(
                "ID/Code contains disallowed characters; only letters, digits, "
                "underscores, and hyphens are permitted"
            )
        return v
