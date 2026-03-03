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
from garth import sso
from garminconnect import Garmin
import pickle


class NeedMfaChallenge(Exception):
    """Raised when Garmin requires an MFA challenge during login."""


@dataclass
class LoginResult:
    ok: bool
    error_code: Optional[str] = None
    message: str | None = None


def _config_token_path(config_dir: Path) -> Path:
    """Return the path where we store the garth token.

    For compatibility with python-garminconnect/garth, we let garth
    manage its own token filenames (oauth1_token.json, oauth2_token.json)
    under the given directory. This helper is kept for backwards
    compatibility but currently unused.
    """

    return config_dir


def login(
    username: str,
    password: str,
    config_dir: Path,
    mfa_code: str | None = None,
) -> LoginResult:
    """Perform login using garth + python-garminconnect.

    Two-step MFA-aware flow compatible with garth 0.5.x:

    - First call without mfa_code:
      * Use garth.login(..., return_on_mfa=True).
      * If it returns ("needs_mfa", state), we surface NEED_MFA so the
        caller can ask the user for a code.
      * If it returns tokens directly, login succeeded without MFA.

    - Second call with mfa_code:
      * Call garth.login(username, password, mfa_code=mfa_code) to
        complete the challenge in one step.

    Any other failure is surfaced as LOGIN_FAILED.
    """

    config_dir.mkdir(parents=True, exist_ok=True)
    token_dir = _config_token_path(config_dir)

    try:
        if mfa_code:
            # Second step: complete login with a known MFA code using
            # the stored client_state from the previous NEED_MFA step.
            state_path = config_dir / "garth_mfa_state.pkl"
            if not state_path.exists():
                return LoginResult(
                    ok=False,
                    error_code="MFA_STATE_MISSING",
                    message="MFA state missing; run login without --mfa-code first",
                )

            client_state = pickle.loads(state_path.read_bytes())
            # Use sso.resume_login to complete login.
            oauth1, oauth2 = sso.resume_login(client_state, mfa_code)
            garth.client.configure(oauth1_token=oauth1, oauth2_token=oauth2, domain=oauth1.domain)
            state_path.unlink(missing_ok=True)
        else:
            # First step: detect whether MFA is required without blocking
            # on user input.
            result = sso.login(username, password, client=garth.client, return_on_mfa=True)
            if isinstance(result, tuple) and len(result) >= 1 and result[0] == "needs_mfa":
                # Persist MFA client_state for the second step.
                _, client_state = result
                state_path = config_dir / "garth_mfa_state.pkl"
                state_path.write_bytes(pickle.dumps(client_state))
                raise NeedMfaChallenge("MFA required")
            # Otherwise, login succeeded without MFA (tokens already on client).

        # Save tokens into the directory so python-garminconnect can
        # reuse them via its tokenstore mechanism.
        garth.save(str(token_dir))
    except NeedMfaChallenge:
        return LoginResult(ok=False, error_code="NEED_MFA", message="MFA required; rerun with --mfa-code")
    except Exception as exc:  # noqa: BLE001
        return LoginResult(ok=False, error_code="LOGIN_FAILED", message=str(exc))

    return LoginResult(ok=True, error_code=None, message=None)


def resume_session(config_dir: Path) -> bool:
    """Try to resume an existing session.

    Returns True on success, False if no valid session is available.
    """

    token_dir = _config_token_path(config_dir)
    if not token_dir.exists():
        return False

    try:
        garth.resume(str(token_dir))
        # Touch a simple call to confirm the session is valid.
        _ = garth.client.username  # type: ignore[attr-defined]
        return True
    except GarthException:
        return False
    except Exception:
        return False


def make_client(config_dir: Path) -> Garmin:
    """Construct a Garmin client using existing Garth session.

    We rely on python-garminconnect's built-in Garth integration:
    - Garmin instance has a .garth attribute used by Garmin.login().
    - If GARMINTOKENS is not set or tokens are invalid, Garmin.login()
      will fall back to credential flow (which we want to avoid here).

    For Phase 1 we assume that Garmintokens are managed by garth and that
    our sync uses an already-authenticated environment.
    """

    client = Garmin()
    # Point GARMINTOKENS to our garth token directory so Garmin can
    # reuse the same token store. This avoids re-entering credentials.
    import os

    os.environ.setdefault("GARMINTOKENS", str(config_dir))
    client.login(tokenstore=str(config_dir))
    return client


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
