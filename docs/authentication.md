# Authentication

This document explains how authentication works in the ARMS application.

The app uses JWT tokens for API authentication, but every token is also tied to a server-side session. This gives the flexibility of JWT auth while still allowing sessions to be revoked and managed centrally.

---

# Why Use This Approach

JWT authentication is stateless by default.

That works well for APIs, but it also has some downsides:

- once a token is issued, the server considers it valid until it expires
- revoked users may still have access until token expiry
- there’s no built-in way to track or manage active sessions
- logging out everywhere is difficult

To solve this, every JWT is linked to a `UserSession` record in the database.

During authentication we validate:

- the JWT itself
- the associated session

This means sessions can be revoked immediately, even if the JWT has not expired yet.

It also lets us:

- track active devices
- enforce idle session timeouts
- limit concurrent logins
- audit login activity

---

# Authentication Classes

Authentication is configured in `settings.py`:

```python
DEFAULT_AUTHENTICATION_CLASSES = [
    "core.authentication.SessionJWTAuthentication",
    "rest_framework_simplejwt.authentication.JWTAuthentication",
    "rest_framework.authentication.SessionAuthentication",
    "rest_framework.authentication.BasicAuthentication",
]
```

The main authentication class is:

```python
core.authentication.SessionJWTAuthentication
```

This extends DRF Simple JWT authentication and adds session validation on top of normal JWT checks.

During authentication it:

- validates the JWT
- checks the token contains a session_id
- validates the session exists and is active
- checks idle timeout expiry
- checks absolute session expiry

If any check fails, authentication is rejected.

# Login Flow

Login is handled by:

```python
core.viewsets.general_viewsets.SessionTokenLoginView
```

When a user logs in:

- credentials are validated
- a new UserSession is created
- access and refresh tokens are generated
- the refresh token hash is stored in the session
- session/device metadata is recorded

Stored session data includes:

- IP address
- user agent
- device/session family
- expiry timestamps

Login requests are also rate limited using LoginThrottle.

# JWT Tokens

Access tokens are used for authenticated API requests:

```http
Authorization: Bearer <token>
```

Tokens include values like:

```json
{
  "user_id": 15,
  "session_id": "uuid-here",
  "exp": 1712345678,
  "abs_exp": 1712380000
}
```

Authentication only succeeds if:

- the token is valid
- the session is active
- the session has not expired

# Sessions

Sessions are stored in:

```python
core.models.sessions.UserSession
```

Each session tracks:

- user
- session ID
- refresh token hash
- status
- expiry timestamps
- IP address
- user agent
- device/session family

Session states:

- Active
- Revoked
- Expired

The app uses two expiry rules:

| Type            | Description                             |
| --------------- | --------------------------------------- |
| Idle expiry     | session expires after inactivity        |
| Absolute expiry | maximum lifetime regardless of activity |

# Refresh Tokens

Token refresh is handled by:

```python
core.viewsets.general_viewsets.RefreshAPIView
```

When refreshing a token, the API:

- validates the refresh token
- checks the session is still active
- verifies token hashes
- generates a new access token
- rotates the refresh token

Refresh tokens are validated against stored token hashes instead of storing raw tokens directly.

This allows revoked or replaced refresh tokens to be rejected immediately.

# Security Settings

Global authentication/security settings are stored in:

```python
core.models.security.SecuritySettings
```

Configurable settings include:

- session idle timeout
- absolute session lifetime
- maximum concurrent sessions
- account lockout limits
- session revocation on password change

These settings are cached and can be updated dynamically.

# WebSocket Authentication

WebSocket authentication is handled by:

```python
inventory.middleware.JWTAuthMiddleware
```

The middleware:

- extracts the JWT from the request
- validates it using SessionJWTAuthentication
- attaches the authenticated user to the socket scope

Tokens can be passed through:

- Sec-WebSocket-Protocol
- query parameters

If authentication fails, the socket uses an anonymous user.

# Security Features

The authentication system includes:

- refresh token hashing (SHA-256)
- session revocation
- token rotation
- login throttling
- session/device tracking
- audit logging
- concurrent session limits
- IP tracking
