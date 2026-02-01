from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Any
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials  # type: ignore[import-untyped]
from google.auth.transport.requests import Request  # type: ignore[import-untyped]
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-untyped]
from googleapiclient.discovery import build  # type: ignore[import-untyped]

from config import get_settings
from src.core.exceptions import YouTubeAuthError

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


class YouTubeAuth:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._token_path = self._settings.youtube.token_file
        self._client_secrets_path = self._settings.youtube.client_secrets_file
        self._credentials: Optional[Credentials] = None
        self._youtube: Any = None
        self._analytics: Any = None

    def authenticate(self, headless: bool = False) -> Credentials:
        if self._credentials and self._credentials.valid:
            return self._credentials
        
        if self._token_path.exists():
            creds = self._load_token()
            if creds and creds.valid:
                self._credentials = creds
                return creds
            if creds and creds.expired and creds.refresh_token:
                try:
                    self._credentials = creds
                    self._refresh_token()
                    return self._credentials  # type: ignore
                except Exception:
                    pass
        
        self._credentials = self._run_oauth_flow(headless=headless)
        return self._credentials

    @property
    def credentials(self) -> Credentials:
        return self.authenticate(headless=False)

    @property
    def youtube(self) -> Any:
        if self._youtube is None:
            self._youtube = build("youtube", "v3", credentials=self.credentials)
        return self._youtube

    @property
    def analytics(self) -> Any:
        if self._analytics is None:
            self._analytics = build("youtubeAnalytics", "v2", credentials=self.credentials)
        return self._analytics

    def _load_or_create_credentials(self) -> Credentials:
        if self._token_path.exists():
            try:
                return self._load_token()
            except Exception:
                pass
        return self._run_oauth_flow()

    def _load_token(self) -> Credentials:
        with open(self._token_path, "r") as f:
            token_data = json.load(f)
        
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes"),
        )
        
        if creds.expired and creds.refresh_token:
            self._credentials = creds
            self._refresh_token()
            if self._credentials is not None:
                return self._credentials
        
        return creds

    def _save_token(self, creds: Credentials) -> None:
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }
        with open(self._token_path, "w") as f:
            json.dump(token_data, f, indent=2)

    def _run_oauth_flow(self, headless: bool = False) -> Credentials:
        if not self._client_secrets_path.exists():
            raise YouTubeAuthError(
                f"client_secrets.json not found at {self._client_secrets_path}"
            )
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self._client_secrets_path),
                scopes=SCOPES,
            )
            
            if headless:
                flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
                auth_url, _ = flow.authorization_url(prompt="consent")
                print(f"\n아래 URL을 브라우저에서 열어 인증하세요:\n\n{auth_url}\n")
                code = input("인증 후 표시되는 코드를 입력하세요: ").strip()
                flow.fetch_token(code=code)
                creds = flow.credentials
            else:
                try:
                    creds = flow.run_local_server(port=0, open_browser=True)
                except Exception:
                    print("\n브라우저를 열 수 없습니다. --headless 옵션을 사용하세요.\n")
                    raise
            
            self._save_token(creds)
            return creds
        except Exception as e:
            raise YouTubeAuthError(f"OAuth flow failed: {e}") from e

    def _refresh_token(self) -> None:
        if not self._credentials:
            raise YouTubeAuthError("No credentials to refresh")
        
        try:
            self._credentials.refresh(Request())
            self._save_token(self._credentials)
            self._youtube = None
            self._analytics = None
        except Exception as e:
            self._token_path.unlink(missing_ok=True)
            raise YouTubeAuthError(f"Token refresh failed: {e}") from e

    def revoke(self) -> bool:
        if self._credentials and self._credentials.token:
            import requests
            response = requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": self._credentials.token},
                headers={"content-type": "application/x-www-form-urlencoded"},
            )
            self._token_path.unlink(missing_ok=True)
            self._credentials = None
            self._youtube = None
            self._analytics = None
            return response.status_code == 200
        return False

    def is_authenticated(self) -> bool:
        try:
            creds = self.credentials
            return creds is not None and not creds.expired
        except YouTubeAuthError:
            return False
