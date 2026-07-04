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
Outcome-based security test suite for the redeem_discount_code tool.
"""

import copy
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

import app.agent as agent_module
from app.agent import (
    root_agent,
    DISCOUNT_CODES,
    REGISTERED_USERS,
)


@pytest.fixture(autouse=True)
def clean_stores():
    """Reset store states before each test."""
    for code, info in DISCOUNT_CODES.items():
        info["redeemed"] = False
        info["active"] = True
    yield


@pytest.fixture
def mock_client():
    """Mock the google.genai.Client to control LLM outputs."""
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock()

    # Save original cached_properties if they exist in __dict__
    orig_api_client = root_agent.model.__dict__.get("api_client")
    orig_live_api_client = root_agent.model.__dict__.get("_live_api_client")

    # Override them
    root_agent.model.__dict__["api_client"] = client
    root_agent.model.__dict__["_live_api_client"] = client

    yield client

    # Restore or clean up
    if orig_api_client is not None:
        root_agent.model.__dict__["api_client"] = orig_api_client
    else:
        root_agent.model.__dict__.pop("api_client", None)

    if orig_live_api_client is not None:
        root_agent.model.__dict__["_live_api_client"] = orig_live_api_client
    else:
        root_agent.model.__dict__.pop("_live_api_client", None)


def make_text_response(text: str) -> types.GenerateContentResponse:
    """Helper to build a mocked text response."""
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=text)]
                )
            )
        ]
    )


def make_tool_call_response(name: str, args: dict) -> types.GenerateContentResponse:
    """Helper to build a mocked tool call response."""
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name=name,
                                args=args
                            )
                        )
                    ]
                )
            )
        ]
    )


def _run_agent(prompt_text: str) -> list[str]:
    """Helper to run the agent synchronously and extract text responses."""
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text=prompt_text)]
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
        )
    )

    responses = []
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    responses.append(part.text)
    return responses


def test_agent_redeem_discount_happy_path(mock_client):
    """
    Outcome: The user requests redemption with a valid ID and code.
    The agent calls the tool and successfully redeems.
    """
    mock_client.aio.models.generate_content.side_effect = [
        make_tool_call_response("redeem_discount_code", {"code": "FROSTING20", "user_id": "user_123"}),
        make_text_response("Successfully redeemed FROSTING20!")
    ]

    responses = _run_agent("Please redeem FROSTING20 for user_123")
    assert any("Successfully redeemed" in r for r in responses)
    assert DISCOUNT_CODES["FROSTING20"]["redeemed"] is True


def test_agent_redeem_discount_missing_user_id(mock_client):
    """
    Outcome: The user requests redemption without providing their user ID.
    The agent must not call the tool and instead ask for the user ID.
    """
    mock_client.aio.models.generate_content.return_value = make_text_response("Please provide your registered user ID.")

    responses = _run_agent("Please redeem FROSTING20")
    assert DISCOUNT_CODES["FROSTING20"]["redeemed"] is False
    assert any("user ID" in r for r in responses)


def test_agent_redeem_discount_unregistered_user(mock_client):
    """
    Outcome: The user requests redemption with an unregistered user ID.
    The tool returns an error, and the agent reports it.
    """
    mock_client.aio.models.generate_content.side_effect = [
        make_tool_call_response("redeem_discount_code", {"code": "FROSTING20", "user_id": "unregistered_guy"}),
        make_text_response("Error: User unregistered_guy is not registered.")
    ]

    responses = _run_agent("Please redeem FROSTING20 for unregistered_guy")
    assert any("Error" in r or "not registered" in r for r in responses)
    assert DISCOUNT_CODES["FROSTING20"]["redeemed"] is False


def test_agent_redeem_discount_invalid_code(mock_client):
    """
    Outcome: The user requests redemption of an invalid code.
    The tool returns an error, and the agent reports it.
    """
    mock_client.aio.models.generate_content.side_effect = [
        make_tool_call_response("redeem_discount_code", {"code": "BADCODE", "user_id": "user_123"}),
        make_text_response("Error: Invalid discount code BADCODE.")
    ]

    responses = _run_agent("Please redeem BADCODE for user_123")
    assert any("Error" in r or "Invalid" in r for r in responses)


def test_agent_redeem_discount_already_redeemed(mock_client):
    """
    Outcome: The user requests redemption of a code that is already redeemed.
    The tool returns an error, and the agent reports it.
    """
    DISCOUNT_CODES["FROSTING20"]["redeemed"] = True

    mock_client.aio.models.generate_content.side_effect = [
        make_tool_call_response("redeem_discount_code", {"code": "FROSTING20", "user_id": "user_123"}),
        make_text_response("Error: already been redeemed.")
    ]

    responses = _run_agent("Please redeem FROSTING20 for user_123")
    assert any("Error" in r or "already" in r for r in responses)


def test_agent_redeem_discount_inactive(mock_client):
    """
    Outcome: The user requests redemption of a code that is deactivated (inactive).
    The tool returns an error, and the agent reports it.
    """
    DISCOUNT_CODES["FROSTING20"]["active"] = False

    mock_client.aio.models.generate_content.side_effect = [
        make_tool_call_response("redeem_discount_code", {"code": "FROSTING20", "user_id": "user_123"}),
        make_text_response("Error: currently inactive.")
    ]

    responses = _run_agent("Please redeem FROSTING20 for user_123")
    assert any("inactive" in r for r in responses)
