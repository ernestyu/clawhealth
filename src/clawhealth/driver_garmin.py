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

    Phase 1 keeps this simple:
    - We call garth.login() which handles MFA internally (prompting via
      a handler).
    - For CLI/agent use we do not yet implement a custom MFA handler,
      but we expose a hook via mfa_code for future refinement.

    For now, any failure is surfaced as a generic error_code.
    """

    config_dir.mkdir(parents=True, exist_ok=True)
    token_path = _config_token_path(config_dir)

    try:
        # Use garth to perform login and persist session.
        garth.login(username, password)
        garth.save(str(token_path))
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
