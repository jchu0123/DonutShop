#!/usr/bin/env python3
"""
validate_tool_call.py
---------------------
PreToolUse hook validator for run_command executions.

The Gemini agent framework pipes the tool call payload as JSON to stdin.
Expected schema:
    {
        "tool": "run_command",
        "input": {
            "command": "<shell command string>",
            ...
        }
    }

Exit codes:
    0  — command is safe; agent proceeds normally.
    1  — command is blocked; agent receives an error and should not proceed.
"""

import json
import re
import sys


# ---------------------------------------------------------------------------
# Destructive command patterns
# Each entry is a (human_label, compiled_regex) tuple.
# A command matching ANY of these patterns is blocked.
# ---------------------------------------------------------------------------
BLOCKED_PATTERNS: list[tuple[str, re.Pattern]] = [
    # rm with force + recursive flags targeting root or sensitive paths
    ("rm -rf /",          re.compile(r"\brm\b.*-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/(?:\s|$)")),
    ("rm -fr /",          re.compile(r"\brm\b.*-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s+/(?:\s|$)")),
    # rm targeting home directory root
    ("rm -rf ~/",         re.compile(r"\brm\b.*-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+~/?")),
    # mkfs / format commands
    ("mkfs",              re.compile(r"\bmkfs\b")),
    # dd targeting block devices (e.g. dd if=... of=/dev/sd*)
    ("dd to block device",re.compile(r"\bdd\b.*\bof=/dev/[a-z]")),
    # Wipe disk utilities
    ("shred /dev",        re.compile(r"\bshred\b.*\b/dev/")),
    ("wipefs",            re.compile(r"\bwipefs\b")),
    # Fork bomb
    ("fork bomb",         re.compile(r":\(\)\s*\{.*:\|:&")),
    # Overwrite critical system files via redirection
    ("overwrite /etc/passwd", re.compile(r">\s*/etc/passwd")),
    ("overwrite /etc/shadow", re.compile(r">\s*/etc/shadow")),
    # curl/wget piped to shell (arbitrary remote code execution)
    ("curl pipe to shell",re.compile(r"\bcurl\b.+\|\s*(?:bash|sh|zsh|python3?)")),
    ("wget pipe to shell",re.compile(r"\bwget\b.+\|\s*(?:bash|sh|zsh|python3?)")),
    # chmod 777 on root or system dirs
    ("chmod 777 /",       re.compile(r"\bchmod\b.*777\s+/")),
]


def extract_command(payload: dict) -> str | None:
    """Return the command string from the tool call payload, or None."""
    tool_input = payload.get("input") or payload.get("tool_input") or {}
    # Support both 'command' and 'CommandLine' keys (framework variants)
    return tool_input.get("command") or tool_input.get("CommandLine")


def check_command(command: str) -> list[str]:
    """
    Return a list of violation labels for the given command string.
    An empty list means the command is safe.
    """
    violations: list[str] = []
    for label, pattern in BLOCKED_PATTERNS:
        if pattern.search(command):
            violations.append(label)
    return violations


def main() -> int:
    # Read the full stdin payload
    raw = sys.stdin.read().strip()

    if not raw:
        # No payload — nothing to validate; allow through
        return 0

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[validate_tool_call] WARNING: Could not parse stdin JSON: {exc}", file=sys.stderr)
        # Fail open: let the agent decide rather than silently blocking
        return 0

    command = extract_command(payload)
    if not command:
        # Not a run_command payload or no command field; allow through
        return 0

    violations = check_command(command)
    if violations:
        print(
            f"[validate_tool_call] BLOCKED command: {command!r}\n"
            f"  Matched destructive pattern(s): {', '.join(violations)}",
            file=sys.stderr,
        )
        return 1

    print(f"[validate_tool_call] OK: {command!r}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
