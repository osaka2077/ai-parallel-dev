---
branch: agent-rROUND-NAME
exclusive_path: src/MODULE/
shared_interface: shared_interfaces.py
tests: true
context: "Refactoring von MODULE: GRUND"
done_when: "Refactoring abgeschlossen, ALLE bestehenden Tests gruen, keine API-Aenderungen"
dependencies:
  - shared_interfaces.py
---

## Kontext

Refactoring von `src/MODULE/` wegen: GRUND
(z.B. Performance, Lesbarkeit, neue Architektur, Dependency-Reduktion)

WICHTIG: Public API darf sich NICHT aendern. Nur interne Implementierung.

## Exklusiver Dateipfad

NUR in `src/MODULE/` arbeiten.

## Pre-flight: Abhaengigkeits-Check (Chat macht das VOR Agent-Start)

Bevor dieser Agent startet, pruefe mit GitNexus oder manuell:

1. **Impact-Analyse auf den exklusiven Pfad:**
   ```
   orchestrate preflight prompts/roundN/
   # oder manuell:
   gitnexus impact <Haupt-Symbol> --direction downstream --depth 2
   ```

2. **Pruefe Ergebnis:**
   - Gibt es Abhaengigkeiten AUSSERHALB des exklusiven Pfads?
   - Falls ja: Pfad erweitern ODER zweiten Agent zuweisen ODER Interface einfuegen

3. **Execution Flows validieren:**
   ```
   gitnexus query "MODULE workflow"
   ```
   - Welche Flows kreuzen die Pfadgrenze?
   - Muessen diese Flows nach dem Merge noch funktionieren?

Falls kein GitNexus verfuegbar: `grep -r "from MODULE import\|import MODULE" src/` als Fallback.

## Was sich aendern soll

1. AENDERUNG_1 — Warum: GRUND
2. AENDERUNG_2 — Warum: GRUND
3. AENDERUNG_3 — Warum: GRUND

## Was sich NICHT aendern darf

- Public API (Funktionssignaturen, Return-Types)
- Imports die andere Module nutzen
- shared_interfaces.py

## Tests

- ALLE bestehenden Tests muessen GRUEN bleiben
- Neue Tests fuer refactored Internals (wenn sinnvoll)
- Performance-Benchmark vorher/nachher (wenn Performance-Refactor)

## Qualitaets-Checkliste

- [ ] Alle bestehenden Tests gruen (KRITISCH!)
- [ ] Public API unveraendert
- [ ] Kein Code ausserhalb des exklusiven Pfads

## Branch

```bash
git checkout agent-rROUND-NAME
```
