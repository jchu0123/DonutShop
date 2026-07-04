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
import sys
from unittest.mock import MagicMock

# Check if we are running integration tests
is_integration = any("integration" in arg for arg in sys.argv)

if not is_integration:
    # Mock google auth before imports happen in the tests (for unit tests only)
    import google.auth
    mock_creds = MagicMock()
    mock_creds.quota_project_id = "dummy-project"
    mock_creds.token = "dummy-token"
    mock_creds.valid = True
    google.auth.default = MagicMock(return_value=(mock_creds, "dummy-project"))

    # Mock vertexai init
    import vertexai
    vertexai.init = MagicMock()
