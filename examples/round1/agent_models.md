---
branch: agent-r1-models
exclusive_path: src/models/
shared_interface: shared_interfaces.py
tests: true
context: "SQLAlchemy models + repository pattern"
done_when: "User CRUD works, repository implements UserRepository protocol. Tests green."
dependencies:
  - shared_interfaces.py
---

## Kontext

Du baust die Datenbank-Models und Repositories fuer eine FastAPI-Anwendung.
Stack: Python 3.12+, SQLAlchemy 2.0 (async), PostgreSQL.

`shared_interfaces.py` definiert:
- `User` — Core user dataclass
- `UserRepository` — Protocol das du implementieren musst

## Exklusiver Dateipfad

NUR in `src/models/` arbeiten:
```
src/models/
├── __init__.py
├── base.py              # SQLAlchemy Base, engine setup
├── user.py              # User SQLAlchemy model
├── repository.py        # UserRepository implementation
└── exceptions.py        # Model-specific exceptions
```

NICHT aendern: shared_interfaces.py oder Dateien ausserhalb src/models/.

## Aufgabe

1. **Base Setup** (`base.py`)
   - SQLAlchemy async engine (DATABASE_URL from env)
   - AsyncSession factory
   - Base class for all models

2. **User Model** (`user.py`)
   - Maps to `users` table
   - Fields: id (UUID), email (unique), name, role, is_active, password_hash
   - created_at, updated_at timestamps

3. **Repository** (`repository.py`)
   - Implementiert `UserRepository` Protocol
   - Async CRUD operations
   - Proper error handling (IntegrityError → custom exception)

## Imports

```python
from shared_interfaces import User, UserRepository
```

## Tests

In `tests/models/`:
- `test_user_model.py` — Create, read, update, delete
- `test_repository.py` — All CRUD ops, duplicate email, not found

Minimum 10 Tests. Nutze SQLite in-memory fuer Tests.

## Branch

```bash
git checkout agent-r1-models
```
