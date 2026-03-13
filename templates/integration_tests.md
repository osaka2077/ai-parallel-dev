---
branch: agent-rROUND-NAME
exclusive_path: tests/integration/
shared_interface: shared_interfaces.py
tests: true
context: "Integration-Tests fuer MODULE_A + MODULE_B Zusammenspiel"
done_when: "Cross-Modul Flows getestet, alle gruen"
dependencies:
  - shared_interfaces.py
  - src/MODULE_A/
  - src/MODULE_B/
---

## Kontext

Schreibe Integration-Tests die das Zusammenspiel von MODULE_A und MODULE_B testen.
Einzelne Unit-Tests existieren bereits — hier geht es um den FLOW.

## Exklusiver Dateipfad

NUR in `tests/integration/` arbeiten.

## Zu testende Flows

1. **Flow 1:** BESCHREIBUNG
   - Startet bei MODULE_A
   - Geht durch MODULE_B
   - Ergebnis: WAS_PASSIERT

2. **Flow 2:** BESCHREIBUNG

3. **Error Flow:** BESCHREIBUNG
   - Was passiert wenn MODULE_A fehlschlaegt?
   - Propagiert der Fehler korrekt zu MODULE_B?

## Tests

Minimum 8 Integration-Tests:
- 4 Happy Path Flows
- 2 Error Propagation
- 2 Edge Cases (Timing, Concurrency, Empty Data)

## Qualitaets-Checkliste

- [ ] Kein Quellcode geaendert
- [ ] Tests nutzen echte Module (kein Mocking der getesteten Module)
- [ ] Externe Dependencies duerfen gemockt werden (DB, APIs)

## Branch

```bash
git checkout agent-rROUND-NAME
```
