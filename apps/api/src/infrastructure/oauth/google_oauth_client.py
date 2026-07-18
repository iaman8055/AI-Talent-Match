import httpx

from src.application.auth.ports import GoogleUserInfo

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleOAuthClient:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def exchange_code(self, code: str) -> GoogleUserInfo:
        with httpx.Client(timeout=10.0) as client:
            token_response = client.post(
                _TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_response.status_code != 200:
                raise ValueError("Google token exchange failed")

            access_token = token_response.json().get("access_token")
            if not access_token:
                raise ValueError("Google token exchange returned no access token")

            userinfo_response = client.get(
                _USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_response.status_code != 200:
                raise ValueError("Failed to fetch Google user info")

        payload = userinfo_response.json()
        sub = payload.get("sub")
        email = payload.get("email")
        if not sub or not email:
            raise ValueError("Google user info missing sub or email")

        return GoogleUserInfo(
            sub=sub,
            email=email,
            full_name=payload.get("name", email),
            email_verified=bool(payload.get("email_verified", False)),
        )
