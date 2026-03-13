---
branch: agent-rROUND-NAME
exclusive_path: src/MODULE/
shared_interface: shared_interfaces.py
tests: true
context: "Erweiterung von MODULE um FEATURE"
done_when: "FEATURE funktioniert, bestehende Tests weiterhin gruen"
dependencies:
  - shared_interfaces.py
---

## Kontext

Bestehendes Modul `src/MODULE/` wird um FEATURE erweitert.
Bestehende Funktionalitaet: WAS_EXISTIERT_SCHON
Neue Funktionalitaet: WAS_DAZU_KOMMT

## Exklusiver Dateipfad

NUR in `src/MODULE/` arbeiten. Bestehende Dateien duerfen geaendert werden,
aber bestehende public APIs muessen kompatibel bleiben.

## Bestehender Code (NICHT brechen!)

```
WICHTIGE_BESTEHENDE_FUNKTIONEN_ODER_KLASSEN
```

## Aufgabe

1. **Erweiterung 1**
   - WAS und WIE
   - Bestehende API bleibt kompatibel

2. **Erweiterung 2**
   - WAS und WIE

## Tests

In `tests/MODULE/`:
- Bestehende Tests muessen weiterhin gruen sein!
- Neue Tests fuer FEATURE:
  - WELCHE_TESTS

Minimum 8 neue Tests + alle bestehenden gruen.

## Qualitaets-Checkliste

- [ ] Bestehende Tests gruen (Regression Check)
- [ ] Neue Tests fuer neues Feature
- [ ] Type Hints auf allen neuen functions
- [ ] Kein Code ausserhalb des exklusiven Pfads

## Branch

```bash
git checkout agent-rROUND-NAME
```
