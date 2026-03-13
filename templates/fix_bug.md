---
branch: agent-rROUND-NAME
exclusive_path: src/MODULE/
shared_interface: shared_interfaces.py
tests: true
context: "Bug-Fix: BUG_BESCHREIBUNG"
done_when: "Bug gefixt, Regression-Test geschrieben, alle Tests gruen"
dependencies:
  - shared_interfaces.py
---

## Kontext

Bug: BUG_BESCHREIBUNG
Reproduktion: WIE_REPRODUZIERT_MAN_DEN_BUG
Erwartetes Verhalten: WAS_SOLLTE_PASSIEREN
Tatsaechliches Verhalten: WAS_PASSIERT_STATTDESSEN

## Exklusiver Dateipfad

NUR in `src/MODULE/` und `tests/MODULE/` arbeiten.

## Aufgabe

1. **Bug lokalisieren**
   - HINWEIS_WO_DER_BUG_VERMUTLICH_LIEGT
   - Bestaetige mit einem failing Test

2. **Bug fixen**
   - MINIMALER Fix — nicht refactoren, nur den Bug fixen
   - Public API darf sich nicht aendern

3. **Regression-Test schreiben**
   - Test der den Bug reproduziert (muss VORHER rot sein)
   - Test der nach dem Fix gruen ist
   - Der Test verhindert dass der Bug zurueckkommt

## Tests

- Regression-Test fuer den spezifischen Bug
- ALLE bestehenden Tests muessen weiterhin gruen sein

## Qualitaets-Checkliste

- [ ] Bug reproduziert (failing Test)
- [ ] Minimaler Fix (kein Refactoring)
- [ ] Regression-Test geschrieben
- [ ] Alle bestehenden Tests gruen
- [ ] Kein Code ausserhalb des exklusiven Pfads

## Branch

```bash
git checkout agent-rROUND-NAME
```
