---
branch: agent-rROUND-NAME
exclusive_path: src/MODULE/
shared_interface: shared_interfaces.py
tests: true
context: "BESCHREIBUNG"
done_when: "AKZEPTANZKRITERIEN"
dependencies:
  - shared_interfaces.py
---

## Kontext

BESCHREIBUNG des Moduls und warum es gebraucht wird.
Stack: TECH_STACK
Relevante shared_interfaces: WELCHE_INTERFACES

## Exklusiver Dateipfad

NUR in `src/MODULE/` arbeiten:
```
src/MODULE/
├── __init__.py
├── FILE1.py           # BESCHREIBUNG
├── FILE2.py           # BESCHREIBUNG
└── exceptions.py      # Modul-spezifische Exceptions
```

NICHT aendern: shared_interfaces.py oder Dateien ausserhalb src/MODULE/.

## Aufgabe

1. **Komponente 1** (`file1.py`)
   - Implementiere INTERFACE aus shared_interfaces
   - DETAILS

2. **Komponente 2** (`file2.py`)
   - DETAILS

3. **Komponente 3** (`file3.py`)
   - DETAILS

## Imports

```python
from shared_interfaces import TYPE1, TYPE2, PROTOCOL
```

## Tests

In `tests/MODULE/`:
- `test_file1.py` — WELCHE_TESTS
- `test_file2.py` — WELCHE_TESTS

Minimum 12 Tests:
- 6 Happy Path
- 4 Edge Cases
- 2 Error Cases

## Qualitaets-Checkliste

- [ ] Type Hints auf allen public functions
- [ ] Keine hardcoded secrets
- [ ] Logging statt print()
- [ ] Alle Tests gruen
- [ ] Kein Code ausserhalb des exklusiven Pfads

## Branch

```bash
git checkout agent-rROUND-NAME
```
