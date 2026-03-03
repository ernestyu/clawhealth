"""Garmin driver for clawhealth (Phase 1).

This module wraps python-garminconnect + garth behind a small interface
suitable for CLI use:

- CLI-based login with optional MFA (two-step flow).
- Session persistence under a configurable config directory.
- Simple sync calls that return Python dicts for JSON output.

Notes:
- This is a first-pass implementation and intentionally narrow in scope.
- Error handling is geared towards clear error_code/message pairs for
  consumption by agents.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import garth
from garth.exc import GarthException
from garminconnect import Garmin


class NeedMfaChallenge(Exception):
    """Raised when Garmin requires an MFA challenge during login."""


@dataclass
class LoginResult:
    ok: bool
    error_code: Optional[str] = None
    message: str | None = None


def _config_token_path(config_dir: Path) -> Path:
    """Return the path where we store the garth token.

    We reuse garth's token format but keep it under clawhealth's
    config_dir, e.g. /opt/clawhealth/config/garth_token.
    """

    return config_dir / "garth_token.json"


def login(
    username: str,
    password: str,
    config_dir: Path,
    mfa_code: str | None = None,
) -> LoginResult:
    """Perform login using garth + python-garminconnect.

    Two-step MFA-aware flow:
    - First call without mfa_code:
      * If login succeeds without challenge, token is saved and we
        return ok=True.
      * If Garmin requires MFA, we raise NeedMfaChallenge and map it to
        error_code="NEED_MFA" so the caller can ask the user for a code.
    - Second call with mfa_code:
      * We pass a handler that returns the provided code.

    Any other failure is surfaced as LOGIN_FAILED.
    """

    config_dir.mkdir(parents=True, exist_ok=True)
    token_path = _config_token_path(config_dir)

    try:
        if mfa_code:
            # Advanced MFA flow: resume_login with a provided code.
            result1, result2 = garth.login(username, password, return_on_mfa=True)
            if result1 == "needs_mfa":
                garth.resume_login(result2, mfa_code)
            # If no MFA was required, result1/result2 are already the tokens.
        else:
            # Ask garth to return early when MFA is required.
            result1, _ = garth.login(username, password, return_on_mfa=True)
            if result1 == "needs_mfa":
                raise NeedMfaChallenge("MFA required")

        garth.save(str(token_path))
    except NeedMfaChallenge:
        return LoginResult(ok=False, error_code="NEED_MFA", message="MFA required; rerun with --mfa-code")
    except Exception as exc:  # noqa: BLE001
        return LoginResult(ok=False, error_code="LOGIN_FAILED", message=str(exc))

    return LoginResult(ok=True, error_code=None, message=None)


def resume_session(config_dir: Path) -> bool:
    """Try to resume an existing session.

    Returns True on success, False if no valid session is available.
    """

    token_path = _config_token_path(config_dir)
    if not token_path.exists():
        return False

    try:
        garth.resume(str(token_path))
        # Touch a simple call to confirm the session is valid.
        _ = garth.client.username  # type: ignore[attr-defined]
        return True
    except GarthException:
        return False
    except Exception:
        return False


def make_client(config_dir: Path) -> Garmin:
    """Construct a Garmin client using the resumed garth session.

    Assumes resume_session() has already been called.
    """

    return Garmin(session=garth.client)  # type: ignore[arg-type]


def fetch_daily_summary(
    client: Garmin,
    date_str: str,
) -> Dict[str, Any]:
    """Fetch a daily summary for a given date.

    This is intentionally minimal for Phase 1; we rely on
    python-garminconnect's get_stats_and_body() as a starting point.
    """

    # get_stats_and_body returns a dict with various keys including
    # steps, distance, calories, sleep, etc.
    return client.get_stats_and_body(date_str)
