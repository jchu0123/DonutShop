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
Unit tests for the get_loyalty_points agent tool.
"""

import pytest

from app.agent import (
    REGISTERED_USERS,
    LOYALTY_BALANCES,
    get_loyalty_points,
)


@pytest.fixture(autouse=True)
def clean_loyalty_balances():
    for uid in REGISTERED_USERS:
        LOYALTY_BALANCES[uid] = 0
    yield
    for uid in REGISTERED_USERS:
        LOYALTY_BALANCES[uid] = 0


def test_get_loyalty_points_success():
    # Set loyalty balance for test user
    LOYALTY_BALANCES["user_123"] = 450
    result = get_loyalty_points("user_123")
    assert "Success" in result
    assert "450" in result
    assert "user_123" in result


def test_get_loyalty_points_unregistered_user():
    result = get_loyalty_points("unregistered_guy")
    assert "Error" in result
    assert "not registered" in result
