---
branch: agent-r1-auth
exclusive_path: src/auth/
shared_interface: shared_interfaces.py
tests: true
context: "Auth module with JWT + password hashing"
done_when: "Login, logout, refresh, password hashing work. All tests green."
dependencies:
  - shared_interfaces.py
---

## Kontext

Du baust das Authentication-Modul fuer eine FastAPI-Anwendung.
Das Projekt nutzt Python 3.12+, FastAPI, SQLAlchemy.

`shared_interfaces.py` im Projekt-Root definiert:
- `User` — Core user dataclass
- `AuthToken` — JWT token wrapper
- `AuthProvider` — Protocol das du implementieren musst

## Exklusiver Dateipfad

Du arbeitest NUR in `src/auth/`. Erstelle dort:
```
src/auth/
├── __init__.py
├── jwt_handler.py       # JWT creation, validation, refresh
├── password.py          # Password hashing (bcrypt)
├── middleware.py         # FastAPI auth middleware
├── dependencies.py      # FastAPI Depends() helpers
└── exceptions.py        # Auth-specific exceptions
```

NICHT aendern: shared_interfaces.py, oder Dateien ausserhalb src/auth/.

## Aufgabe

1. **JWT Handler** (`jwt_handler.py`)
   - Implementiere `AuthProvider` Protocol aus shared_interfaces
   - Token creation mit configurable expiry (env: JWT_SECRET, JWT_EXPIRY)
   - Token validation mit proper error handling
   - Refresh token flow

2. **Password Hashing** (`password.py`)
   - bcrypt-basiert
   - `hash_password(plain: str) -> str`
   - `verify_password(plain: str, hashed: str) -> bool`

3. **FastAPI Middleware** (`middleware.py`)
   - Bearer token extraction
   - Automatic user injection via `request.state.user`
   - Configurable public routes (no auth required)

4. **Dependencies** (`dependencies.py`)
   - `get_current_user` — FastAPI Depends(), raises 401
   - `require_role(role: str)` — Role-based access, raises 403

## Imports

```python
from shared_interfaces import User, AuthToken, AuthProvider
```

## Tests

Erstelle Tests in `tests/auth/`:
- `test_jwt_handler.py` — Token create, validate, refresh, expired, invalid
- `test_password.py` — Hash, verify, wrong password
- `test_middleware.py` — With token, without token, expired token, public route
- `test_dependencies.py` — Valid user, no auth, wrong role

Minimum 12 Tests:
- 6 Happy Path
- 4 Edge Cases (expired, invalid, malformed, empty)
- 2 Error Cases (wrong role, missing secret)

## Qualitaets-Checkliste

- [ ] Type Hints auf allen public functions
- [ ] Keine hardcoded secrets (alles aus env vars)
- [ ] Logging statt print() (use logging.getLogger)
- [ ] Alle Tests gruen mit `pytest tests/auth/ -v`
- [ ] Kein Code ausserhalb src/auth/ und tests/auth/

## Branch

```bash
git checkout agent-r1-auth
```
