---
branch: agent-rROUND-NAME
exclusive_path: tests/MODULE/
shared_interface: shared_interfaces.py
tests: true
context: "Tests schreiben fuer MODULE"
done_when: "Minimum ANZAHL Tests, alle gruen, Coverage fuer Happy + Edge + Error"
dependencies:
  - shared_interfaces.py
  - src/MODULE/
---

## Kontext

Schreibe Tests fuer das bestehende Modul `src/MODULE/`.
Das Modul hat aktuell ANZAHL_BESTEHENDE Tests (oder keine).

## Exklusiver Dateipfad

NUR in `tests/MODULE/` arbeiten. Quellcode NICHT aendern.

## Zu testender Code

```
WICHTIGE_FUNKTIONEN_UND_KLASSEN_AUS_DEM_MODUL
```

## Test-Anforderungen

### Happy Path (mindestens 6)
1. TEST_BESCHREIBUNG
2. TEST_BESCHREIBUNG
3. TEST_BESCHREIBUNG
4. TEST_BESCHREIBUNG
5. TEST_BESCHREIBUNG
6. TEST_BESCHREIBUNG

### Edge Cases (mindestens 4)
1. TEST_BESCHREIBUNG
2. TEST_BESCHREIBUNG
3. TEST_BESCHREIBUNG
4. TEST_BESCHREIBUNG

### Error Cases (mindestens 2)
1. TEST_BESCHREIBUNG
2. TEST_BESCHREIBUNG

## Test-Stil

- pytest (nicht unittest)
- Factory Pattern statt Fixtures (Factory Boy oder eigene Factories)
- Jeder Test ist isoliert (eigene UUIDs, kein shared state)
- Descriptive names: `test_create_user_with_valid_email_returns_user`

## Qualitaets-Checkliste

- [ ] Minimum 12 Tests
- [ ] Alle Tests gruen
- [ ] Kein Quellcode geaendert (nur tests/)
- [ ] Test-Isolation (kein shared state)

## Branch

```bash
git checkout agent-rROUND-NAME
```
