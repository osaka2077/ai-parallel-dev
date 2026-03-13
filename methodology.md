# AI-Orchestrated Parallel Development
## Die definitive Methodik für maximale Qualität, Geschwindigkeit und Konsistenz

*Version 2.0 — März 2026*

---

## SCHNELLSTART (Lies nur das — starte in 10 Minuten)

```
Du brauchst:  Claude Chat (Web) + Claude Code (mind. 2 Terminals)
              Chat = dein Koordinator. Code = deine Arbeiter.
Erste Runde:  Nimm LITE-Modus (siehe unten). Kein Tooling nötig.

Schritt 1: shared_interfaces definieren
  → Erstelle eine Datei mit den Types/Interfaces die alle Agents teilen.
  → Committe sie VOR dem Start. Kein Agent darf sie ändern.

Schritt 2: 2-4 Prompts schreiben (je 60-100 Zeilen)
  → 1 Prompt = 1 Agent = 1 exklusiver Dateipfad
  → Nutze ein Template aus prompts/templates/ wenn vorhanden
  → Jeder Prompt enthält: Interface-Import, Pfad, Test-Anforderungen

Schritt 3: Agents starten (1 Claude Code Terminal pro Agent)
  → Prompt reinkopieren, Agent arbeiten lassen

Schritt 4: Merge wenn fertig
  → Prüfe: Tests grün? Dateien im richtigen Pfad? Lint clean?
  → git merge, dann volle Test-Suite 1× laufen lassen

Schritt 5: Ergebnisse zurück an Chat
  → Was hat funktioniert? Was nicht?
  → Chat analysiert, notiert in learnings.md, plant nächste Runde

Das ist die GESAMTE Methodik in 5 Schritten.
Alles andere im Dokument macht diese 5 Schritte schneller, sicherer und skalierbarer.
```

### Welcher Modus passt zu deinem Projekt?

```
┌─────────────────────────────────────────────────────────────────────────┐
│ LITE                    │ STANDARD                │ FULL                │
│ Kleine Projekte         │ Mittlere Projekte       │ Große Projekte      │
│ 1-3 Agents              │ 4-8 Agents              │ 8+ Agents           │
├─────────────────────────┼─────────────────────────┼─────────────────────┤
│ Code-Intelligence:      │ Code-Intelligence:      │ Code-Intelligence:  │
│ grep + find reicht      │ grep + ast-grep         │ ast-grep/SourceGraph│
│                         │                         │ + Cross-Validation  │
├─────────────────────────┼─────────────────────────┼─────────────────────┤
│ ✗ Kein Orchestrator     │ ✓ Orchestrator Stufe 2  │ ✓ Orchestrator      │
│   (manuell, geht auch)  │   (semi-auto)           │   Stufe 3 (auto)    │
├─────────────────────────┼─────────────────────────┼─────────────────────┤
│ ✗ Keine Prompt-         │ ✓ Templates + Validator │ ✓ Templates +       │
│   Templates (custom OK) │                         │   Validator + Score │
├─────────────────────────┼─────────────────────────┼─────────────────────┤
│ ✗ Kein Health-          │ ○ Health optional       │ ✓ Health Monitor    │
│   Monitoring            │                         │   + Auto-Recovery   │
├─────────────────────────┼─────────────────────────┼─────────────────────┤
│ ✗ Kein .ai/ System      │ ✓ learnings.md +        │ ✓ Volles .ai/       │
│   (ERRORS.md reicht)    │   errors.md             │   + Auto-Bootstrap  │
├─────────────────────────┼─────────────────────────┼─────────────────────┤
│ Serieller Merge         │ ✓ Batch-Merge           │ ✓ Batch-Merge +     │
│ (wenige Agents = OK)    │                         │   Bisect + Tiered   │
├─────────────────────────┼─────────────────────────┼─────────────────────┤
│ Budget: SMALL ($30-50)  │ Budget: MEDIUM ($50-100)│ Budget: LARGE+      │
│ Modus: B oder C         │ Modus: B                │ Modus: A oder B     │
├─────────────────────────┼─────────────────────────┼─────────────────────┤
│ Typisch: Web-Features,  │ Typisch: SaaS-Module,   │ Typisch: Compiler,  │
│ Bugfixes, kleine APIs   │ neue Domains, Refactors │ Frameworks, ML Sys  │
└─────────────────────────┴─────────────────────────┴─────────────────────┘

→ Im Zweifel: Starte mit LITE. Skaliere hoch wenn nötig.
→ Alles unter "STANDARD" und "FULL" im Dokument ist OPTIONAL für LITE.
```

---

## DAS MODELL: DREI ROLLEN, BEWUSSTE TRENNUNG

### Warum drei Rollen — und warum Chat NICHT dasselbe ist wie die Agents

```
Das zentrale Architektur-Prinzip dieser Methodik:

  PLANUNG und AUSFÜHRUNG müssen in GETRENNTEN KONTEXTEN stattfinden.

Warum? Wegen Context-Management:

  Chat (Web-Interface):
  ├── Context enthält: Strategie, Rundenhistorie, Learnings, Merge-Ergebnisse
  ├── Context enthält NICHT: 50.000 Zeilen Code-Details aus Terminal 4
  ├── Bleibt SAUBER für strategisches Denken
  └── Kann stundenlang/tagelang dieselbe Conversation führen

  Agent (Claude Code Terminal):
  ├── Context enthält: EINEN Prompt, EINEN Pfad, EINE Aufgabe
  ├── Context enthält NICHT: Was die anderen 7 Agents machen
  ├── Ist VOLL mit Code-Details (genau richtig für Implementierung)
  └── Session ist ephemer, task-fokussiert, disposable

Wenn man beides in EINEM Tool macht:
  → Das Tool liest 20 Dateien für die Planung → Context füllt sich
  → Es führt Code aus → noch mehr Context
  → Es soll strategisch analysieren → aber der Context ist voll mit Code
  → DAS HIRN WIRD DÜMMER JE MEHR ES ARBEITET

Die Trennung Chat ↔ Agents ist kein Workaround.
Es ist SEPARATION OF CONCERNS auf Context-Window-Ebene.
```

### Die drei Rollen

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                        DU — DER STRATEGE                            │
│                                                                     │
│   Entscheidet WAS gebaut wird und WARUM                            │
│   Setzt Prioritäten, definiert die Vision                          │
│   Gibt grünes Licht, reviewt Ergebnisse                            │
│   Sagt: "Runde 4: Native Compilation. Modus B."                   │
│                                                                     │
│   Optional: Orchestrator-Script für mechanische Arbeit             │
│   (Terminal-Management, Dispatch, Merge, Reporting)                │
│                                                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                   CLAUDE CHAT — DAS HIRN                            │
│                  (Web-Interface, geschützter Context)               │
│                                                                     │
│   Plant Waves, schreibt Prompts, analysiert Ergebnisse             │
│   Denkt strategisch: "Wir brauchen kein LLVM von Grund auf,       │
│   wir ändern das Cargo-Target"                                      │
│   Passt Pläne in Echtzeit an wenn etwas Unerwartetes passiert      │
│                                                                     │
│   Kontext kommt aus .ai/ Persistenz-Dateien:                       │
│   context_bootstrap.md + learnings.md + decisions_log.md           │
│   → Überlebt Session-Grenzen, Context-Kompression, Neustarts      │
│                                                                     │
│   Code-Intelligence: Fragt Code-Fakten ab wenn nötig               │
│   (grep, ast-grep, SourceGraph — je nach Projekt und Setup)       │
│                                                                     │
│   SIEHT NUR: Reports, Metriken, Merge-Ergebnisse, Strategisches  │
│   SIEHT NICHT: Implementierungsdetails der einzelnen Agents        │
│                                                                     │
└──────────┬──────────────────────────────────────────────────────────┘
           │
           │  schreibt Prompts, dispatcht
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│               AGENTS — DIE AUSFÜHRER                                │
│              (Claude Code Terminals, jeweils isoliert)              │
│                                                                     │
│   Bekommen EINEN fokussierten Prompt                                │
│   Schreiben Code + Tests                                            │
│   Committen auf exklusive Dateipfade                                │
│   Wissen NICHTS vom Gesamtprojekt                                  │
│   Brauchen es auch nicht                                            │
│                                                                     │
│   Bis zu 8 Terminals × 1-3 Agents                                  │
│   Parallel, unabhängig, disposable                                 │
│                                                                     │
│   Qualität kommt vom Prompt, nicht vom Agent                       │
│                                                                     │
│   Nutzen Code-Intelligence für ihren eigenen Scope:                │
│   (Claude Code's eingebaute Grep/Glob/Read Tools)                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Warum diese Aufteilung funktioniert

**Du** triffst Entscheidungen die kein AI treffen sollte: Was ist das Produkt?
Wer sind die Nutzer? Lohnt sich das? Pivot oder weitermachen?

**Chat (Hirn)** hat etwas das kein einzelner Agent hat: das VOLLE Bild.
Nicht weil sein Context Window unendlich ist — sondern weil `.ai/` Dateien
alles Wichtige persistent speichern. Chat weiß aus `learnings.md` dass
`__version__` Shadowing 13 Dateien betroffen hat. Aus `round_reports/round01.md`
dass Runde 1 zu breit war. Aus `decisions_log.md` dass die drei Produktrichtungen
denselben Compiler-Kern teilen. Ein Agent in Terminal 4 weiß nichts davon —
und das ist gut so. Er braucht nur seinen Prompt.

Wenn Chats Context Window voll wird oder eine neue Session startet: 2 Minuten
`context_bootstrap.md` lesen und Chat ist zurück.

**Agents** sind austauschbar. Wenn einer scheitert, starte einen neuen.
Die Intelligenz steckt im Prompt, nicht im Agent.

### Code-Intelligence: Ein Werkzeug, keine Rolle

```
Das Original-Dokument hatte "GitNexus" als vierte Rolle — ein Knowledge Graph
der den Code als Graph darstellt. Das Problem: GitNexus ist kein Produkt.

Die FUNKTION (Code-Fakten abfragen) ist essenziell.
Das WIE hängt vom Projekt und Setup ab:

┌──────────────────────────────────────────────────────────────────────────┐
│ WERKZEUG              │ WANN                    │ WAS ES KANN            │
├───────────────────────┼─────────────────────────┼────────────────────────┤
│ grep / rg             │ Immer. Default.          │ Text-Suche, Imports,   │
│                       │ Kein Setup nötig.        │ Klassen, Funktionen    │
├───────────────────────┼─────────────────────────┼────────────────────────┤
│ find / ls / tree      │ Immer. Default.          │ Dateistruktur,         │
│                       │ Kein Setup nötig.        │ Pfad-Validierung       │
├───────────────────────┼─────────────────────────┼────────────────────────┤
│ git log / git diff    │ Immer. Default.          │ Änderungshistorie,     │
│                       │ Kein Setup nötig.        │ Blame, Diff            │
├───────────────────────┼─────────────────────────┼────────────────────────┤
│ ast-grep              │ Ab STANDARD. Optional.   │ Strukturelle Suche,    │
│                       │ pip install ast-grep     │ AST-basierte Patterns  │
├───────────────────────┼─────────────────────────┼────────────────────────┤
│ Claude Code Explore   │ Ab STANDARD. Eingebaut.  │ Codebase-Exploration,  │
│ (Agent subtype)       │ Kein Setup nötig.        │ Zusammenhänge finden   │
├───────────────────────┼─────────────────────────┼────────────────────────┤
│ SourceGraph           │ Ab FULL. Optional.       │ Code-Suche über Repos, │
│                       │ Self-hosted oder Cloud   │ Cross-Referenzen       │
├───────────────────────┼─────────────────────────┼────────────────────────┤
│ Knowledge Graph       │ Ab FULL. Optional.       │ Dependency-Graph,      │
│ (Neo4j + Custom)      │ Aufwändigstes Setup      │ Impact-Analyse,        │
│                       │                          │ Cypher-Queries         │
└───────────────────────┴─────────────────────────┴────────────────────────┘

Grundregel: grep + find + git reicht für 80% aller Projekte.
Alles darüber ist OPTIONAL und muss seinen Setup-Aufwand rechtfertigen.

Egal welches Werkzeug: CROSS-VALIDIEREN.
  → Jede kritische Aussage ("existiert nicht", "keine Abhängigkeiten")
    mit mindestens einem zweiten Werkzeug gegenchecken.
  → Ein Tool das sagt "0 Ergebnisse" kann auch "Index kaputt" bedeuten.
```

---

## DER ZYKLUS: 6 PHASEN PRO RUNDE

```
    ┌──────────────────────────────────────────────────────┐
    │                                                      │
    │  PHASE 0          PHASE 1          PHASE 2           │
    │  Code-        ──→ Planung ───────→ Execution         │
    │  Intelligence      & Prompts        (parallel)       │
    │  [Chat]            [Chat]           [Agents]         │
    │                                                      │
    │  PHASE 5          PHASE 4          PHASE 3           │
    │  Nächste    ←──── Analyse  ←────── Integration       │
    │  Runde             & Review         & Merge          │
    │  [Stratege]        [Chat]           [Chat+Stratege]  │
    │                                                      │
    └──────────────────────────────────────────────────────┘
```

---

### PHASE 0: Code-Intelligence (~10-15 min)
**Wer:** Chat
**Ziel:** Verstehen was WIRKLICH im Code steht — nicht was wir glauben

Bevor ein einziger Prompt geschrieben wird, sammeln wir Fakten:

```
Schritt 0a: Session Recovery (wenn neue Session oder Kontext dünn)
   → context_bootstrap.md lesen (~30 Sek)
   → Letzten Round Report lesen (~30 Sek)
   → learnings.md + decisions_log.md lesen (~60 Sek)
   → Chat ist voll einsatzfähig in ~2 min

Schritt 0b: Code-Fakten sammeln (mit verfügbaren Werkzeugen)

1. Was existiert zum Thema dieser Runde?
   rg -l "thema" --type py
   find . -name "*thema*" -type f
   rg "class.*Thema|def.*thema" --type py
   → Welche Module, Klassen, Funktionen gibt es schon?

2. Was bricht wenn wir hier eingreifen?
   rg "import.*Modul|from.*Modul" --type py
   → Für jedes Ergebnis: eine weitere rg-Runde (2 Levels tief = Blast Radius)
   pytest --collect-only -q | grep "modul"
   → Welche Tests decken das Modul ab?

3. 360°-Ansicht der Schlüssel-Klassen:
   rg "class SchluesselKlasse" --type py (Definition)
   rg "from.*import.*SchluesselKlasse" --type py (Wer importiert?)
   rg "SchluesselKlasse\." --type py (Wer ruft Methoden auf?)

4. Strukturelle Fragen:
   find . -path "*/pfad/*" -type f (Existiert etwas in geplanten Pfaden?)
   git log --oneline -20 (Was wurde kürzlich geändert?)

5. Cross-Validation:
   → Alle Ergebnisse plausibel? Stimmt die Anzahl?
   → Bei Zweifeln: zweites Werkzeug nutzen
   → Bei >2 Abweichungen: genauer hinschauen bevor Phase 1

Optional (wenn ast-grep/SourceGraph/Knowledge Graph verfügbar):
   ast-grep -p 'class $CLASS { $$$ }' (strukturelle Suche)
   sourcegraph search 'repo:mein-repo type:symbol compile' (Cross-Repo)
   cypher: MATCH (f:Function)-[:CALLS]->(g) WHERE g.name='compile' RETURN f
```

**Output von Phase 0:**
```
Intelligence Report:
─────────────────────
Thema: Native Compilation Backend

Existierende Assets:
- RustCompiler (backend/rust_compiler.py) — ruft cargo auf
- CargoProjectGenerator — generiert Cargo.toml
- targets.py — hat wasm32, wasi, native Stubs
- CompilationPipeline Stage 6 — aktuell WASM-only

Blast Radius:
- Änderung an Stage 6 betrifft: SDK decorator, CLI compile, Browser bundler
- KRITISCH: @kf.compile ruft Pipeline auf — muss weiterhin funktionieren

Lücken:
- Kein ctypes FFI Bridge
- Kein JIT-System
- Keine x86/ARM-spezifischen Optimierungen
- targets.py hat native als Stub, nicht implementiert

Empfehlung:
- targets.py erweitern statt neu schreiben
- Stage 6 braucht Target-Routing (wasm vs native)
- FFI Bridge als neues Modul (kernelforge/ffi/)
─────────────────────
```

---

### PHASE 1: Planung & Prompts (~20-30 min)
**Wer:** Du (Stratege) + Chat (Hirn)
**Ziel:** Aus der Intelligence einen konkreten, ausführbaren Plan machen

#### Schritt 1.1: Du gibst die Richtung vor

```
Du: "Runde 4: Native Backend. Wir brauchen echte .so/.dylib Dateien
     statt nur WASM. Und ein JIT-System. Modus B. Budget MEDIUM."
```

Das ist deine echte Strategie-Arbeit — Richtung, Modus, Budget.
Chat macht den Rest (Prompts, Interfaces, Pfad-Validierung).

#### Schritt 1.2: Chat erstellt die Pre-Conditions

**shared_interfaces.py** — basierend auf Code-Intelligence:

```python
# shared_interfaces_round4.py
# Committed VOR Runden-Start. Kein Agent darf dies ändern.

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

class NativeTarget(Enum):
    """Compilation targets for native code generation."""
    X86_64_LINUX = "x86_64-unknown-linux-gnu"
    X86_64_MACOS = "x86_64-apple-darwin"
    AARCH64_LINUX = "aarch64-unknown-linux-gnu"
    AARCH64_MACOS = "aarch64-apple-darwin"
    WASM32 = "wasm32-unknown-unknown"
    WASM32_WASI = "wasm32-wasi"

class JITTier(Enum):
    """JIT compilation tiers."""
    TIER0_PYTHON = 0      # Python fallback (immediate)
    TIER1_CRANELIFT = 1   # Fast compile (~100ms), moderate speed
    TIER2_LLVM = 2        # Slow compile (~3-5s), maximum speed

@dataclass
class NativeCompileResult:
    """Result of native compilation."""
    success: bool
    library_path: Optional[Path] = None
    target: Optional[NativeTarget] = None
    tier: JITTier = JITTier.TIER0_PYTHON
    compile_time: float = 0.0
    binary_size: int = 0
    errors: list = None
    diagnostics: list = None
```

**pre_merge_lint.py** — als git hook im Repo.

#### Schritt 1.3: Chat definiert Waves und schreibt Agent-Prompts

Basierend auf:
- Deiner strategischen Richtung
- Code-Intelligence (was existiert, was bricht)
- Learnings aus vorherigen Runden (aus .ai/learnings.md)
- shared_interfaces.py (was die Agents importieren)
- Prompt-Templates (aus prompts/templates/ — wenn passend)

Jeder Prompt ist:
- Basiert auf einem Template (new_module, extend_module, refactor, etc.)
  oder custom wenn kein Template passt
- Fokussiert auf EINEN Agent (kein Mega-Prompt)
- ~60-120 Zeilen (nicht 500)
- Enthält shared_interfaces Import
- Enthält Qualitäts-Checkliste
- Enthält spezifische Test-Cases (Happy + Edge + Error)
- Wird in Schritt 1.5 automatisch validiert vor Dispatch

#### Schritt 1.4: Dateipfad-Validierung

```
Chat prüft mit verfügbaren Werkzeugen:

find . -path "*/kernelforge/native/*" -type f | wc -l
→ Ergebnis: 0 Dateien → Pfad ist frei ✓

find . -path "*/kernelforge/ffi/*" -type f | wc -l
→ Ergebnis: 0 Dateien → Pfad ist frei ✓

find . -path "*/kernelforge/jit_engine/*" -type f | wc -l
→ Ergebnis: 0 Dateien → Pfad ist frei ✓
```

**Output von Phase 1:** Fertige Prompts für alle Agents + shared_interfaces.py + validierte Dateipfade.

#### Schritt 1.5: Prompt Validation (automatisiert — VOR Dispatch)

```
WARUM: "Qualität kommt vom Prompt" heißt auch:
       "Schlechter Prompt = 8 Agents produzieren gleichzeitig Müll"
       Ein Validator fängt das ab BEVOR es $50-100 kostet.

orchestrate validate ./prompts/round4/
→ Prüft JEDEN Prompt gegen Pflicht-Kriterien:

┌──────────────────────────────────────────────────────────────────┐
│ STRUKTURELLE CHECKS (automatisch, sofort)                        │
├──────────────────────────────────────────────────────────────────┤
│ □ Länge: 60-120 Zeilen? (zu kurz = vage, zu lang = unfokussiert)│
│ □ shared_interfaces Import vorhanden?                            │
│ □ Exklusiver Dateipfad definiert?                                │
│ □ Test-Anforderungen: mind. 12, davon 2 Edge + 1 Error?         │
│ □ Qualitäts-Checkliste enthalten?                                │
│ □ Branch-Name definiert (agent-<id>-<name>)?                     │
├──────────────────────────────────────────────────────────────────┤
│ SEMANTISCHE CHECKS (automatisch, braucht Kontext)               │
├──────────────────────────────────────────────────────────────────┤
│ □ Dateipfad kollidiert nicht mit anderen Prompts der Wave?       │
│ □ Dateipfad existiert nicht bereits im Repo? (find Check)        │
│ □ Referenziert keine Module die erst in einer späteren Wave      │
│   entstehen? (Abhängigkeits-Check gegen manifest.yaml)           │
│ □ Modell-Tier passt zur Task-Komplexität?                        │
│   (Haiku für Architektur-Task → Warnung)                         │
├──────────────────────────────────────────────────────────────────┤
│ CROSS-PROMPT CHECKS (automatisch, über alle Prompts der Runde)  │
├──────────────────────────────────────────────────────────────────┤
│ □ Kein Pfad-Overlap zwischen Agents derselben Wave?              │
│ □ Alle shared_interfaces Types die im Prompt verwendet werden    │
│   existieren tatsächlich in shared_interfaces.py?                │
│ □ Summe aller Agent-Budgets ≤ Runden-Budget?                     │
└──────────────────────────────────────────────────────────────────┘

Ergebnis:
  ✓ PASS: Alle Checks bestanden → Dispatch freigegeben
  ⚠ WARN: Nicht-kritische Issues → Empfehlung, kein Blocker
  ✗ FAIL: Kritische Issues → Dispatch BLOCKIERT bis gefixt
```

---

### PROMPT-TEMPLATES: QUALITÄTSBODEN GARANTIEREN

```
WARUM Templates: Nicht jeder Prompt muss from scratch geschrieben werden.
80% der Struktur ist immer gleich — nur der Task-spezifische Teil ändert sich.
Templates garantieren einen MINDEST-Qualitätsboden.

prompts/
└── templates/                      ← Wiederverwendbare Vorlagen
    ├── new_module.md               ← Neues Modul von Grund auf
    ├── extend_module.md            ← Bestehendes Modul erweitern
    ├── refactor.md                 ← Refactoring mit Tests erhalten
    ├── write_tests.md              ← Tests für bestehenden Code
    ├── integration_tests.md        ← Cross-Modul Integration-Tests
    └── fix_bug.md                  ← Bug-Fix mit Regression-Test

Wirkung:
  Ohne Templates: ~15 min/Prompt, 4-5 Validator-Issues, Qualität schwankt
  Mit Templates:  ~5 min/Prompt, 0-1 Validator-Issues, Mindestqualität garantiert
```

#### Template-Beispiel: new_module.md

```markdown
# Agent Prompt: Neues Modul — {MODUL_NAME}

## Kontext
Du arbeitest an {PROJEKT_NAME}.
Dein EINZIGER Fokus: {EINE_SATZ_BESCHREIBUNG}

## Interfaces
Importiere und nutze AUSSCHLIESSLICH:
\`\`\`python
from {SHARED_INTERFACES} import {TYPES}
\`\`\`

## Dein exklusiver Pfad
ALLE Dateien die du erstellst MÜSSEN unter diesem Pfad liegen:
  {EXKLUSIVER_PFAD}/

Du darfst KEINE Dateien außerhalb dieses Pfads erstellen oder ändern.

## Was du baust
{DETAILLIERTE_BESCHREIBUNG}

### Anforderungen
1. {ANFORDERUNG_1}
2. {ANFORDERUNG_2}
3. {ANFORDERUNG_3}

### Architektur-Vorgaben
- {PATTERN_ODER_STRUKTUR}
- {IMPORT_CHAIN}

## Tests (PFLICHT)
Erstelle Tests unter {TEST_PFAD}/

### Mindestens 12 Tests:
- Happy Path (mind. 6):
  1. {HAPPY_1}
  2. {HAPPY_2}
  3. ...
- Edge Cases (mind. 3):
  1. {EDGE_1}
  2. {EDGE_2}
  3. ...
- Error Cases (mind. 3):
  1. {ERROR_1}
  2. {ERROR_2}
  3. {ERROR_3}

## Qualitäts-Checkliste (vor Commit prüfen)
□ Alle Tests grün: pytest {TEST_PFAD}/ -v
□ Type Hints auf allen public Functions
□ Docstrings auf allen public Classes/Functions
□ Nur shared_interfaces Types verwendet (keine eigenen Enums/Dataclasses)
□ Keine Imports aus anderen Agent-Pfaden
□ __init__.py vorhanden mit sauberen Exports

## Branch
Committe auf Branch: agent-{ID}-{NAME}
Commit Message: feat({SCOPE}): {BESCHREIBUNG}
```

---

### PHASE 2: Execution (~15-45 min je nach Modus)
**Wer:** Agents (Claude Code auf bis zu 8 Terminals)
**Ziel:** Code schreiben, Tests schreiben, committen

#### Modus A: Maximale Qualität
```
1 Wave pro Durchgang. Bis zu 8 Agents auf 8 Terminals.
Jeder Agent = 1 fokussierter Prompt.
~15-20 min pro Durchgang.

Wann: Neue Domains, kritische Architecture, Foundation-Runden.

Modell-Mix:  2× Opus (Architektur-Agents)
             4× Sonnet (Feature-Agents)
             2× Haiku (Test/Boilerplate-Agents)
Budget:      $30-50 pro Runde
```

#### Modus B: Balanced (Empfehlung für die meisten Runden)
```
2-3 Waves pro Durchgang. 2-3 Agents pro Terminal.
~25-35 min pro Durchgang.

Wann: Feature-Erweiterung, Standard-Runden.

Modell-Mix:  2× Opus (nur wenn neue Patterns nötig)
             10× Sonnet (Kern-Agents)
             6× Haiku (Tests + Boilerplate)
Budget:      $50-80 pro Runde
```

#### Modus C: Maximaler Durchsatz
```
Alle Waves in einem Durchgang.
~45-60 min.

Wann: Prototyping, Breadth-Runden wo Qualität weniger kritisch ist.

Modell-Mix:  2× Opus (nur kritische Pfade)
             20× Sonnet (Bulk-Arbeit)
             20× Haiku (Repetitive Tasks)
Budget:      $80-130 pro Runde
```

#### Pipeline-Modus (für alle Modi anwendbar)

```
STATT:  Warte bis alle 8 fertig → seriell mergen → nächste Wave
BESSER: Kombination aus Batch-Merge + Terminal-Wiederverwendung

Terminal 1: ██████ done ─┐
Terminal 2: ████████ done┤ Batch-Merge aller → Affected Tests → OK
Terminal 3: ██████ done ─┤ (3 min statt 30 min seriell)
Terminal 4: ████ done ───┘
                           ↓ sofort nächste Wave dispatchen
Terminal 1: ██████ done ─┐
Terminal 2: ████ done ───┤ Batch-Merge Wave 2 → Affected Tests → OK
Terminal 3: ████████ done┘
                           ↓
Full Suite (1× am Ende): 10 min → alles grün ✓
```

#### Während die Agents laufen

```
Orchestrator Stufe 1 (manuell):
  Du: Tab-Switching, Monitoring, manuell mergen wenn fertig
  Aufwand: ~30-60 min aktive Aufmerksamkeit

Orchestrator Stufe 2 (semi-auto, empfohlen):
  Du: Gelegentlich "orchestrate status" prüfen
      "orchestrate merge" + "orchestrate next" wenn bereit
  Aufwand: ~5 min alle 15 min — dazwischen andere Arbeit möglich

Orchestrator Stufe 3 (vollautomatisch):
  Du: Nichts. Script dispatcht, merged, dispatcht weiter.
      Du wirst benachrichtigt wenn alles fertig oder etwas failed.
  Aufwand: 0 min — du wirst gepingt wenn du gebraucht wirst
```

Chat überwacht: Agent Health (Details → Sektion "Agent Health Monitoring").

#### Agent Health Monitoring (WÄHREND Phase 2)

##### Automatische Health Checks (alle 60 Sekunden)

```
┌────────────────────────────────────────────────────────────────────┐
│ CHECK 1: HEARTBEAT                                                 │
│ Ist der Agent noch aktiv? (Letzte Dateiänderung < 5 min?)         │
│ → Aktiv: ✓                                                        │
│ → Inaktiv seit 5+ min: ⚠ STALLED — evtl. stuck in Loop           │
│ → Inaktiv seit 15+ min: ✗ TIMEOUT — Agent wird abgebrochen        │
├────────────────────────────────────────────────────────────────────┤
│ CHECK 2: PFAD-COMPLIANCE                                           │
│ Schreibt der Agent nur in seinen exklusiven Pfad?                  │
│ → git diff --name-only zeigt geänderte Dateien                    │
│ → Dateien außerhalb des Pfads? ✗ VIOLATION — sofort stoppen       │
├────────────────────────────────────────────────────────────────────┤
│ CHECK 3: TOKEN-BUDGET                                              │
│ Wie viele Tokens hat der Agent verbraucht?                         │
│ → < 80% des Agent-Budgets: ✓                                     │
│ → 80-100%: ⚠ WARN — Agent muss bald fertig werden                │
│ → >100%: ✗ BUDGET_EXCEEDED — Agent wird abgebrochen               │
├────────────────────────────────────────────────────────────────────┤
│ CHECK 4: OUTPUT-PLAUSIBILITÄT (bei Completion)                     │
│ Hat der Agent sinnvollen Output produziert?                        │
│ → Code-Dateien erstellt? (mind. 1 .py/.ts Datei)                  │
│ → Test-Dateien erstellt? (mind. 1 test_ Datei)                    │
│ → Commit gemacht mit beschreibender Message?                       │
│ → Alle 3 JA: ✓ HEALTHY                                           │
│ → Test-Datei fehlt: ⚠ INCOMPLETE — evtl. noch laufend            │
│ → Kein Code: ✗ NO_OUTPUT — Agent hat nichts produziert            │
└────────────────────────────────────────────────────────────────────┘
```

##### Failure-Klassifikation

```
KLASSE A — AUTOMATISCH BEHEBBAR (kein menschliches Eingreifen)
──────────────────────────────────────────────────────────────
  TIMEOUT:        Agent hängt seit 15+ min
  BUDGET_EXCEEDED: Agent hat Token-Budget überschritten
  NO_OUTPUT:      Agent hat nach Timeout nichts produziert
  → Aktion: Agent stoppen. Terminal freigeben.
    Prompt in Retry-Queue mit Fehler-Kontext.

KLASSE B — BRAUCHT PROMPT-ANPASSUNG (Chat muss eingreifen)
──────────────────────────────────────────────────────────────
  INCOMPLETE:     Code aber keine Tests (oder umgekehrt)
  STALLED:        Agent kommt nicht weiter (Loop, Compile-Error)
  PARTIAL_COMMIT: Agent hat halb-fertigen Code committed
  → Aktion: Agent stoppen. Branch inspizieren.
    Chat analysiert: Was fehlt? Warum steckt er fest?
    Neuer Prompt mit Kontext: "Du hast X gebaut, aber Y fehlt noch."

KLASSE C — SICHERHEITSRELEVANT (sofort stoppen)
──────────────────────────────────────────────────────────────
  VIOLATION:      Agent schreibt außerhalb seines Pfads
  WRONG_BRANCH:   Agent committed auf falschen Branch
  DELETES_CODE:   Agent löscht bestehenden Code statt zu erweitern
  → Aktion: Agent SOFORT stoppen. Branch verwerfen (git branch -D).
    Nicht automatisch retrien — Prompt muss überprüft werden.
```

##### Recovery-Entscheidungsbaum

```
Agent meldet sich als fertig (oder wird gestoppt):
│
├─ ✓ HEALTHY (Code + Tests + Commit + im Pfad)
│  → Weiter zu Stufe 1 Pre-Merge Validation
│
├─ ⚠ INCOMPLETE (Code aber keine Tests)
│  ├─ Laufzeit < 50% des Erwarteten? → Warten, evtl. noch nicht fertig
│  └─ Laufzeit > 80%? → Stoppen. Retry-Prompt:
│     "Fortsetzung: Du hast [Module] gebaut. Schreibe jetzt Tests."
│
├─ ⚠ STALLED (keine Aktivität seit 5+ min, nicht fertig)
│  ├─ Letzte Änderung war ein Compile-Error?
│  │  → Retry mit Hint: "Bekannter Compile-Error: [Error-Message]"
│  └─ Letzte Änderung war Code?
│     → Agent scheint in einer Schleife. Stoppen.
│       Retry mit vereinfachtem Prompt (Scope reduzieren).
│
├─ ✗ TIMEOUT (15+ min keine Aktivität)
│  ├─ Hat der Agent IRGENDETWAS produziert?
│  │  ├─ JA: Branch behalten. Neuer Agent vollendet die Arbeit.
│  │  └─ NEIN: Branch löschen. Neuer Agent mit gleichem Prompt.
│  └─ Retry-Counter > 2? → Agent überspringen, Task in nächste Wave.
│
├─ ✗ VIOLATION (Pfad-Verletzung)
│  → Branch sofort verwerfen
│  → Prompt überprüfen: War der exklusive Pfad klar genug?
│  → Prompt fixen, dann retry
│
└─ ✗ BUDGET_EXCEEDED
   → Branch behalten (was da ist, ist da)
   → Wenn brauchbar: manuell zu Ende bringen
   → Wenn nicht: retry mit Haiku (günstiger) oder Scope reduzieren
```

##### Kaskadierende Failures: Wave-Abhängigkeiten

```
Problem: Wave 2 braucht Output von Wave 1.
         Was wenn ein Wave-1-Agent scheitert?

manifest.yaml definiert Abhängigkeiten:
  waves:
    - name: "Wave 1: Foundation"
      agents: [agent-401, agent-402, agent-403, agent-404]
    - name: "Wave 2: Features"
      depends_on: "Wave 1"
      required_agents: [agent-401, agent-402]  ← NUR diese sind Pflicht
      agents: [agent-405, agent-406, agent-407, agent-408]

Wenn agent-403 (Wave 1) scheitert:
  1. Ist agent-403 in required_agents von Wave 2?
     → NEIN: Wave 2 kann starten. agent-403 wird parallel retried.
     → JA: Wave 2 wartet bis agent-403 retried und gemerged ist.

  2. Retry schlägt 2× fehl?
     → Chat analysiert: Ist der Task zu komplex? Scope reduzieren?
     → Oder: Task in Wave 2 verschieben (Abhängigkeit umkehren)
     → Letzter Ausweg: Task manuell erledigen, Runde fortsetzen

required_agents = Minimum das fertig sein MUSS bevor nächste Wave startet.
Nicht alle Agents einer Wave müssen erfolgreich sein.
```

---

### PHASE 3: Integration & Merge (~10-25 min statt ~60-90 min)
**Wer:** Du (Stratege) + Chat (Analyse bei Failures)
**Ziel:** Alles zusammenführen, Konsistenz sicherstellen

#### Das Bottleneck-Problem (und die Lösung)

```
VORHER — Serieller Merge (volle Suite nach JEDEM Agent):
──────────────────────────────────────────────────────────
Agent 1: merge → pytest VOLL (8 min) → OK
Agent 2: merge → pytest VOLL (8 min) → OK
...
Agent 8: merge → pytest VOLL (8 min) → OK
Total: 8 × 9 min = 72 min pro Wave. Bei 3 Waves: 3,5+ STUNDEN.

NACHHER — Tiered Merge (3-Stufen-Teststrategie):
──────────────────────────────────────────────────────────
Stufe 1: Agent-Tests VOR Merge (parallel, pro Agent)     ~0 min extra
Stufe 2: Batch-Merge + Affected Tests (pro Wave)         ~8-12 min
Stufe 3: Full Suite (1× pro Runde, am Ende)               ~8-10 min
Total: 12-22 min pro Runde. Das ist 75-85% schneller.
```

#### Stufe 1: Agent-Tests (VOR dem Merge — parallel)

```
Jeder Agent führt SEINE Tests in SEINEM Branch aus, BEVOR er merged wird.
Das passiert während Phase 2 — kein extra Zeitaufwand.

Agent-Branch Anforderung (im Prompt):
  "Vor dem Commit: pytest tests/<dein_pfad>/ muss grün sein."

Pre-Merge Validierung prüft automatisch:
  1. Hat der Agent committed?                    → Nein = reject
  2. Sind alle Agent-eigenen Tests grün?         → Nein = reject
  3. pre_merge_lint.py clean?                    → Nein = reject
  4. Dateien nur in exklusivem Pfad?             → Nein = reject

Ergebnis: Nur validierte, lint-cleane Agents kommen überhaupt zum Merge.
```

#### Stufe 2: Batch-Merge + Affected Tests (pro Wave)

```
STATT:  Agents einzeln mergen, nach jedem die volle Suite
BESSER: Alle Agents einer Wave AUF EINMAL mergen, dann NUR betroffene Tests

Voraussetzung: Exklusive Dateipfade sind GARANTIERT (Stufe 1 prüft das).

Batch-Merge Ablauf:
  1. Pfad-Exklusivität verifizieren
     → Keine Überlappung? → Batch-Merge möglich ✓
     → Überlappung gefunden? → Fallback auf seriellen Merge

  2. Alle Wave-Branches auf einmal mergen
     git merge agent-401 agent-402 agent-403 agent-404

  3. Betroffene Tests ermitteln (NICHT volle Suite):
     Methode A (schnell): pytest --collect-only + Pfad-Matching
     Methode B (präzise): Impact-Analyse auf alle geänderten Dateien
     Methode C (Fallback): Alle Tests der geänderten Verzeichnisse

  4. Nur betroffene Tests laufen lassen
     → ~1-3 min statt ~8-10 min für volle Suite
     → 0 Failures: Wave-Merge bestätigt ✓
     → Failures: Bisect-Strategie (siehe unten)
```

#### Bisect-Strategie: Wenn Batch-Tests fehlschlagen

```
Problem: 8 Agents gemerged, 2 Tests schlagen fehl. Welcher Agent ist schuld?

SCHLECHT: Alle Merges rückgängig, einzeln neu mergen (zurück zu seriell)
BESSER:  Binary Search — 3 Schritte statt 8

Ablauf:
  1. 8 Agents gemerged → 2 Tests FAIL
  2. Rollback. Merge nur Agent 1-4 → Tests?
     → PASS → Problem ist in Agent 5-8
  3. Merge Agent 5-6 dazu → Tests?
     → FAIL → Problem ist Agent 5 oder 6
  4. Merge nur Agent 5 dazu → Tests?
     → PASS → Agent 6 ist der Schuldige

  3 Schritte statt 8 = ~60% weniger Bisect-Zeit
```

#### Stufe 3: Full Suite (1× pro Runde)

```
WANN: Nach der LETZTEN Wave einer Runde. Nicht nach jeder Wave.
WARUM: Fängt subtile Cross-Wave-Interaktionen die Affected Tests verpassen.

  pytest (volle Suite)
  → PASS: Runde ist clean ✓ → weiter zu Phase 4
  → FAIL: Welche Wave hat es verursacht?
    → git log --oneline zeigt Wave-Grenzen (Tags!)
    → Bisect zwischen Waves (nicht zwischen Agents)
```

---

### PHASE 4: Analyse & Review (~10-15 min)
**Wer:** Chat (Hirn) — NICHT die Agents
**Ziel:** Lernen. Jede Runde besser als die letzte.

Du gibst Chat die Ergebnisse (Merge-Logs, Test-Outputs, Kosten).
Chat analysiert — sein Context ist SAUBER weil er nicht implementiert hat.

```
Post-Runde Report:
───────────────────────────────
Runde 4 Analyse

Tests:
  Neue Tests: +470 (14.442 → 14.912)
  Pro Agent Durchschnitt: 58.75
  Edge-Cases: 94 (20% — Ziel >25%)
  Error-Cases: 47 (10% — Ziel >15%)

Merge (Tiered Strategy):
  Stufe 1 Rejections: 1 Agent rejected (Tests im Branch rot)
  Stufe 2 Batch-Merges: 3 Waves, alle Batch-clean
  Stufe 2 Bisects: 0 (kein Batch-Failure)
  Stufe 3 Full Suite: PASS (0 Failures)
  Merge-Dauer: 22 min (vs 240 min seriell — 90% Verbesserung)

Code-Intelligence Insights:
  Höchste Kopplung: CompilationPipeline (47 eingehende Imports)
  → Risiko: Pipeline wird zum God Object. Nächste Runde: Refactoring?

Kosten:
  Budget: MEDIUM ($100)
  Verbraucht: ~$72 (72%) — geschätzt, Token-basiert
  Aufschlüsselung:
    Tier 1 (Opus):   2 Agents × ~$12  = ~$24
    Tier 2 (Sonnet): 5 Agents × ~$4   = ~$20
    Tier 3 (Haiku):  3 Agents × ~$1   = ~$3
    Chat (Planung):  ~$15
    Code-Intelligence: ~$10
  Optimierung: Agent 4 hätte als Haiku laufen können (nur Boilerplate)

Agent Health:
  Healthy: 6/8 (75%)
  Incomplete: 1 (retried, dann OK)
  Timeout: 1 (retried mit Scope-Reduktion)

Prompt-Qualität:
  Template-Nutzung: 6/8 aus Template, 2 custom
  Score-Verteilung: 2× A, 4× B, 1× B-, 1× C
  Schwächster Prompt: Agent 7 (C) — zu vager Scope
  Korrelation: Template-Prompts Ø Score B+, Custom-Prompts Ø Score B-

Empfehlungen für Runde 5:
  1. Error-Case Quote erhöhen: "mind. 3 Error-Cases" statt 1
  2. Pipeline-Refactoring: Strategy Pattern für Targets einführen
  3. Agent 4-ähnliche Tasks auf Haiku downgraden
  4. refactor.md Template: Scope-Section konkretisieren
───────────────────────────────
```

---

### PHASE 5: Nächste Runde vorbereiten (~5 min)
**Wer:** Du (Stratege)
**Ziel:** Richtung für die nächste Runde vorgeben

```
Du: "Die Analyse zeigt dass die Pipeline zu stark gekoppelt ist.
     Runde 5: Breiterer Python-Support — Classes und Generators.
     Aber zuerst das Pipeline-Refactoring als Tier 1."

Chat: "Verstanden. Ich starte Phase 0 für Runde 5."
```

Der Zyklus beginnt von vorne — aber mit mehr Wissen, besseren Metriken
und einem aktualisierten Code-Verständnis.

---

## SHARED FILES: DAS PROBLEM DER NICHT-EXKLUSIVEN DATEIEN

### Das Problem

Exklusive Dateipfade sind das Fundament der Methodik. Aber in realen
Projekten gibt es Dateien die JEDER Agent braucht oder die KEIN Agent
exklusiv besitzen kann:

```
Typische Shared Files:
  - package.json / requirements.txt / pyproject.toml  (Dependencies)
  - Database Migrations (001_create_users.py, 002_add_roles.py)
  - Route-Registrierung (urls.py, routes/index.ts)
  - Config-Files (.env.example, docker-compose.yml)
  - __init__.py mit Exports die neue Module einbinden
  - CSS/Tailwind Globals (wenn kein CSS Modules)
  - CI/CD Pipeline-Configs (.github/workflows/ci.yml)
```

### Strategie 1: Pre-Commit + Post-Merge Reconciliation (Empfehlung)

```
VORHER (in Phase 1):
  Chat identifiziert welche Shared Files betroffen sein werden.
  shared_interfaces.py enthält die CONTRACTS.
  Shared Files werden NICHT von Agents geändert.

NACHHER (in Phase 3, nach Batch-Merge):
  Ein dedizierter "Reconciliation-Schritt" harmonisiert Shared Files:
  1. Dependencies: Chat merged requirements.txt manuell
     (oder: jeder Agent hat eine agent_requirements.txt → Chat merged)
  2. Migrations: Nummern werden post-merge korrigiert
  3. Route-Registrierung: Chat fügt neue Routes hinzu
  4. __init__.py Exports: Chat aktualisiert nach Merge

Aufwand: ~5-10 min pro Wave. Deutlich weniger als Merge-Konflikte lösen.
```

### Strategie 2: Dedizierter Reconciliation-Agent

```
Ein separater Agent (Haiku reicht) der NACH dem Batch-Merge läuft:

Prompt: "Die folgenden Module wurden soeben gemerged:
         [Liste der Agent-Outputs mit neuen Dateien]
         Aktualisiere:
         1. requirements.txt (neue Dependencies)
         2. src/__init__.py (neue Exports)
         3. src/routes/index.ts (neue Route-Registrierungen)
         Ändere NICHTS ANDERES."

Vorteil: Automatisierbar, konsistent, günstig (Haiku, <$1)
Nachteil: Noch ein Agent der fehlschlagen kann
```

### Strategie 3: Agent-spezifische Fragment-Dateien

```
Statt eine zentrale Datei zu ändern, erstellt jeder Agent ein Fragment:

Agent 1 erstellt: requirements.agent401.txt
  cranelift-codegen==0.99.0
  target-lexicon==0.12.0

Agent 2 erstellt: requirements.agent402.txt
  pyo3==0.20.0

Post-Merge Script (oder Reconciliation-Agent):
  cat requirements.txt requirements.agent*.txt | sort -u > requirements.txt
  rm requirements.agent*.txt

Vorteil: Kein Merge-Konflikt möglich. Vollautomatisch.
Nachteil: Nicht alle Shared Files lassen sich so fragmentieren.
```

### Entscheidungsmatrix

```
Shared File Typ              │ Empfohlene Strategie
─────────────────────────────┼──────────────────────────────
Dependencies (pip/npm)       │ Fragment-Dateien (Strategie 3)
Database Migrations          │ Post-Merge Renumbering (Strategie 1)
Route-Registrierung          │ Fragment oder Reconciliation-Agent
__init__.py Exports          │ Reconciliation-Agent (Strategie 2)
Config-Files                 │ Pre-Commit: Chat bereitet vor (Strategie 1)
CSS Globals                  │ CSS Modules nutzen → Problem verschwindet
CI/CD Configs                │ Nicht von Agents ändern lassen → Chat macht
```

---

## DER INFORMATIONSFLUSS

```
                    Du weißt:
                    - Vision & Strategie
                    - Geschäftliche Prioritäten
                    - "Für wen bauen wir das?"
                           │
                           ▼
                    ┌──────────────┐
                    │  ENTSCHEID-  │
                    │    UNG       │
                    │  "Runde 4:   │
                    │  Native."    │
                    └──────┬───────┘
                           │
              ┌────────────┼─────────────────┐
              │            │                 │
              ▼            ▼                 ▼
      ┌──────────────┐  ┌──────────┐  ┌──────────────┐
      │ Code-        │  │ Chat     │  │  .ai/ Dateien│
      │ Intelligence │  │ (Hirn)   │  │  (persistent) │
      │              │  │          │  │               │
      │ Was IST      │  │ Was SOLL │  │  Was WAR      │
      │ im Code?     │  │ passieren│  │  + WARUM      │
      │              │  │          │  │               │
      │ grep, find,  │  │ Plant,   │  │ learnings.md  │
      │ git, ast-grep│  │ schreibt │  │ decisions.md  │
      │ (Werkzeuge)  │  │ Prompts  │  │ round_reports │
      └────┬─────────┘  └────┬─────┘  └──────┬───────┘
           │                 │                │
           └─────────────────┼────────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │   PROMPTS    │
                      │ (fokussiert, │
                      │  präzise,    │
                      │  validiert)  │
                      └──────┬───────┘
                             │
              ┌──────────────┼──────────────┐
              │    │    │    │    │    │    │
              ▼    ▼    ▼    ▼    ▼    ▼    ▼
             T1   T2   T3   T4   T5   T6   T7   T8
             ██   ██   ██   ██   ██   ██   ██   ██
              │    │    │    │    │    │    │    │
              └────┴────┴────┴────┴────┴────┴────┘
                             │
                             ▼
                      ┌──────────────┐
                      │  MERGE +     │
                      │  TIERED      │
                      │  TESTING     │
                      └──────┬───────┘
                             │
                             ▼
                      ┌──────────────┐
                      │  ANALYSE     │
                      │  (zurück an  │
                      │   Chat)      │
                      └──────┬───────┘
                             │
                             ▼
                      Zurück zu DIR
```

### Was jede Rolle NICHT tun sollte

**Du sollst NICHT:**
- Prompts schreiben (das macht Chat)
- Code reviewen (das machen Tests + Analyse)
- Merge-Bugs fixen (das macht Chat)
- Agents managen (die sind autonom)
- Terminals manuell managen (Orchestrator ab Stufe 2)
- Merges manuell ausführen (Orchestrator oder Script)

**Chat (Hirn) soll NICHT:**
- Produkt-Entscheidungen treffen ("für wen ist das?")
- Code implementieren (das machen Agents — Context-Trennung!)
- Agents ersetzen (Chat plant, Agents führen aus)
- Sich auf Context Window als Langzeitgedächtnis verlassen
  (dafür gibt es .ai/ Persistenz-Dateien)
- Learnings oder Entscheidungen nur "im Kopf" behalten
  (immer in learnings.md / decisions_log.md schreiben)

**Agents sollen NICHT:**
- Das Gesamtprojekt verstehen (unnötig und kontextsprengend)
- Andere Module ändern (exklusive Dateipfade!)
- Shared Files ändern (→ Reconciliation nach Merge)
- Architektur-Entscheidungen treffen (die kommen vom Prompt)
- Kreativ werden wo Präzision gefragt ist (Prompt gibt die Richtung)

---

## PERSISTENZ: GEDÄCHTNIS ÜBER SESSIONS HINWEG

### Das Problem

```
Context Window Limits:
  - Endlich: Selbst mit Kompression gehen Details verloren
  - Flüchtig: Chat-Session endet → ALLES ist weg
  - Degradierend: Ab Runde 5-8 werden frühe Runden komprimiert
  - Nicht übertragbar: Neues Chat-Fenster = Neustart bei Null

Was verloren geht wenn der Kontext bricht:
  - WELCHE Bugs aufgetreten sind und wie sie gefixt wurden
  - WARUM Architektur-Entscheidungen getroffen wurden
  - WELCHE Muster funktioniert haben und welche nicht
  → Chat macht dieselben Fehler nochmal.
```

### Die Lösung: Externalisiertes Projektgedächtnis

```
.ai/                                    ← Lebt im Repo, wird committed
├── context_bootstrap.md                ← Auto-generiert nach jeder Runde
│                                          (<500 Zeilen, optimiert für Ingest)
│
├── project_state.md                    ← Aktueller Stand: Was existiert,
│                                          was ist geplant, was ist offen
│
├── decisions_log.md                    ← Jede Architektur-Entscheidung
│                                          mit Datum, Rationale, Alternativen
│
├── learnings.md                        ← Akkumulierte Regeln aus allen Runden
│                                          "Nie X tun weil Y passiert"
│
├── errors.md                           ← Jeder Bug + Lösung
│
└── round_reports/                      ← Phase-4-Output jeder Runde
    ├── round01.md
    ├── round02.md
    └── ...
```

### context_bootstrap.md — Das Kernstück

```
Wird AUTOMATISCH nach jeder Runde (Phase 4) neu generiert.
Enthält genau das was Chat braucht um Phase 0 zu starten —
nicht mehr, nicht weniger.

Aufbau (~300-500 Zeilen):

───────────────────────────────
# Context Bootstrap — KernelForge
# Auto-generiert: 2026-03-12, nach Runde 4

## Projekt-Überblick (10 Zeilen)
KernelForge: Python-zu-WASM/Native Compiler mit SDK, CLI, Browser-Runtime.
Stack: Python 3.12, Rust Backend, 8-Stage Compilation Pipeline.
Aktuelle Codebasis: ~45.000 LOC, 14.912 Tests.

## Letzte 3 Runden (je ~20 Zeilen)
### Runde 4: Native Compilation Backend
- Ziel: .so/.dylib statt nur WASM
- Ergebnis: NativeBackend, FFI Bridge, JIT Tier 0+1 funktionieren
- Offene Issues: JIT Tier 2 (LLVM) noch nicht implementiert

## Top 10 Learnings
1. __version__ Shadowing: Nie ein Modul so nennen wie ein Package-Attribut
2. shared_interfaces VOR den Agents committen, nicht während
3. Runde 1 war zu breit — max 3 neue Domains pro Runde
4. CompilationPipeline hat 52 eingehende Imports — nächstes Refactoring nötig

## Aktive Architektur-Entscheidungen
- Pipeline nutzt Strategy Pattern seit Runde 3
- FFI Bridge über ctypes, nicht cffi (Grund: stdlib)
- JIT nutzt Cranelift für Tier 1, LLVM für Tier 2 (geplant)

## Bekannte Risiken
- CompilationPipeline: 52 eingehende Imports (God Object Tendenz)
- Keine Windows-CI → native library paths ungetestet auf Windows

## Nächste Runde: Vorschlag
Basierend auf Runde 4 Analyse: Python Class Support + Pipeline Refactoring
───────────────────────────────
```

### Session-Recovery-Protokoll

```
Wenn eine neue Chat-Session beginnt (neues Fenster, Kontext voll, Neustart):

Schritt 1: context_bootstrap.md lesen (~30 Sekunden)
  → Chat weiß: Was ist das Projekt, was ist passiert, was sind die Regeln

Schritt 2: Letzten Round Report lesen (~30 Sekunden)
  → Chat weiß: Details der letzten Runde (Tests, Kosten, Metriken)

Schritt 3: learnings.md lesen (~20 Sekunden)
  → Chat weiß: Was NICHT tun (akkumulierte Fehler-Vermeidung)

Schritt 4: decisions_log.md lesen (~30 Sekunden)
  → Chat weiß: WARUM Dinge so sind wie sie sind

Total: ~2 Minuten. Chat ist voll einsatzfähig.
```

### Wann welche Datei aktualisiert wird

```
┌──────────────────────┬────────────────────────────────────────────┐
│ Datei                │ Wann aktualisiert                          │
├──────────────────────┼────────────────────────────────────────────┤
│ context_bootstrap.md │ AUTO nach Phase 4 jeder Runde              │
├──────────────────────┼────────────────────────────────────────────┤
│ project_state.md     │ Nach Phase 3 (Merge) — was existiert jetzt │
├──────────────────────┼────────────────────────────────────────────┤
│ decisions_log.md     │ Während Phase 1 — Architektur-Entscheid.   │
├──────────────────────┼────────────────────────────────────────────┤
│ learnings.md         │ Nach Phase 4 — neue Learnings aus Analyse  │
├──────────────────────┼────────────────────────────────────────────┤
│ errors.md            │ Sofort wenn ein Bug auftritt und gefixt    │
├──────────────────────┼────────────────────────────────────────────┤
│ round_reports/       │ Am Ende von Phase 4 (Report = Datei)       │
└──────────────────────┴────────────────────────────────────────────┘

Nach Phase 4:
  git add .ai/ && git commit -m "chore(ai): update project state after round <N>"
  → Persistenz-Dateien sind Teil der Git-Geschichte
```

---

## ROLLBACK-STRATEGIE: WENN ETWAS SCHIEFGEHT

### Git-Tagging (Pflicht ab STANDARD-Modus)

```
Tags werden AUTOMATISCH gesetzt (vom Orchestrator oder manuell):

  Vor Runde:           round-4-start
  Vor jeder Wave:      round-4-wave-1-pre-merge
  Nach jeder Wave:     round-4-wave-1-post-merge
  Nach Full Suite:     round-4-complete

Damit hat man JEDERZEIT einen sauberen Rücksprungpunkt.

git tag -a round-4-wave-1-pre-merge -m "Before Wave 1 batch merge"
git tag -a round-4-wave-1-post-merge -m "After Wave 1 merge + affected tests pass"
```

### Rollback-Szenarien

```
Szenario 1: Wave-Merge bricht Tests
  → Bisect findet schuldigen Agent
  → git reset --hard round-4-wave-1-pre-merge
  → Agent fixen, nochmal mergen

Szenario 2: Full Suite findet subtilen Bug nach allen Waves
  → git log --oneline round-4-start..HEAD zeigt alle Wave-Merges
  → Bisect ZWISCHEN Waves:
    git reset --hard round-4-wave-2-post-merge → Tests?
    → PASS → Problem in Wave 3
    → git reset --hard round-4-wave-3-pre-merge
    → Wave 3 Agents einzeln mergen um Schuldigen zu finden

Szenario 3: Bug fällt erst Tage später auf
  → Round-Tags zeigen genau wo jede Runde aufhört
  → git bisect start HEAD round-3-complete
  → Normales Git-Bisect findet den Commit

WICHTIG: Rollback auf Tags ist sicher weil es bekannte gute Zustände sind.
         Niemals blind git reset --hard ohne vorher den Zielzustand zu kennen.
```

---

## CI/CD INTEGRATION

### Das Problem

```
Die Methodik beschreibt Merge und Testing, aber nicht wie das
in eine bestehende CI/CD Pipeline passt. In der Realität:
  - Branch Protection Rules verhindern Direct-Push auf main
  - CI muss grün sein bevor gemerged wird
  - Code Review ist oft Pflicht
  - Artifacts (Docker Images, Builds) müssen erstellt werden
```

### Empfohlene Integration

```
OPTION A: Orchestrator merged auf Integration-Branch (Empfehlung)
───────────────────────────────────────────────────────────────────

  main ─────────────────────────────────────────── (geschützt)
    │
    └─── round-4-integration ──── (temporärer Branch für diese Runde)
              │
              ├─ agent-401 ─┐
              ├─ agent-402 ─┤ Batch-Merge auf Integration-Branch
              ├─ agent-403 ─┤ (NICHT auf main!)
              └─ agent-404 ─┘
                             │
                             ▼
              CI läuft auf round-4-integration
              Full Suite + Lint + Build
                             │
                             ▼
              PR: round-4-integration → main
              (Review, CI grün, dann Merge)

  Vorteile:
    - main bleibt immer grün
    - Standard-PR-Workflow bleibt erhalten
    - CI validiert die gesamte Runde als Einheit
    - Code Review ist möglich (auf dem PR)


OPTION B: Feature-Branch pro Runde mit Squash
───────────────────────────────────────────────────────────────────

  Wie Option A, aber: Squash-Merge auf main
  → 1 Commit pro Runde in der main-History
  → Saubere History, aber Details gehen verloren
  → Git-Tags vor Squash setzen um Details zu bewahren


OPTION C: Direct-Merge (nur für Solo-Projekte ohne CI)
───────────────────────────────────────────────────────────────────

  Wie im Dokument beschrieben: Agents → main
  → Einfachster Workflow, aber kein Safety Net
  → Nur wenn Branch Protection nicht existiert/nötig ist
```

### GitHub Actions Beispiel

```yaml
# .github/workflows/round-validation.yml
name: Round Validation

on:
  pull_request:
    branches: [main]
    # Nur für Round-Integration-Branches
    paths: ['**']

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Full Test Suite
        run: pytest --tb=short -q

      - name: Lint
        run: ruff check .

      - name: Type Check
        run: mypy . --ignore-missing-imports

      - name: Shared Interfaces Integrity
        run: python -c "import shared_interfaces; print('OK')"

      - name: Path Exclusivity Check
        run: |
          # Prüfe dass kein Agent-Commit Dateien außerhalb seines Pfads ändert
          # (Details hängen vom Projekt ab)
          echo "Path exclusivity: OK"
```

---

## KOSTEN-MANAGEMENT

### Realistische Kosten (Token-basiert)

```
WICHTIG: Kosten hängen von TOKEN-VERBRAUCH ab, nicht von der Anzahl Prompts.
Die folgenden Zahlen sind HEURISTIKEN basierend auf typischen Agent-Runs.
Tatsächliche Kosten können 50-200% davon abweichen.

┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  TIER 1 — OPUS (Nur wenn nötig)                                    │
│                                                                     │
│  Wann: Neue Architektur, komplexe Algorithmen, System-Design       │
│  Typisch: 1-2 Agents pro Runde                                    │
│  Geschätzte Kosten: ~$8-25 pro Agent-Run                          │
│  (Varianz hoch — abhängig von Context-Größe und Dauer)            │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  TIER 2 — SONNET (Default für die meisten Tasks)                   │
│                                                                     │
│  Wann: Feature-Implementierung, Module erweitern, Standard-Code   │
│  Typisch: 4-5 Agents pro Runde                                    │
│  Geschätzte Kosten: ~$2-8 pro Agent-Run                           │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  TIER 3 — HAIKU (Für Routine-Tasks)                                │
│                                                                     │
│  Wann: Tests schreiben, Boilerplate, Docs, einfache Erweiterungen │
│  Typisch: 2-3 Agents pro Runde                                    │
│  Geschätzte Kosten: ~$0.50-2 pro Agent-Run                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Entscheidungsmatrix:
  Muss der Agent Architektur-Entscheidungen treffen?  → Opus
  Gibt es ein klares Muster/Template?                 → Sonnet
  Ist der Task hauptsächlich repetitiv/mechanisch?    → Haiku
```

### Budget-Caps

```
Budget wird VOR der Runde festgelegt:

  SMALL  = $50   (Bug-Fixes, kleine Features, Refactoring)
  MEDIUM = $100  (Standard-Features, neue Module)
  LARGE  = $200  (Neue Domains, Major-Features)
  XL     = $300  (Foundation-Runden, Architektur-Umbau)

Regeln:
  - Budget ist eine OBERGRENZE, keine Prognose
  - Wenn 80% geschätzt erreicht: verbleibende Agents auf Haiku downgraden
  - Wenn 100% geschätzt erreicht: Runde beenden, Analyse machen
  - Tatsächliche Kosten nach Runde im Claude Dashboard prüfen
    → In Phase 4 Report als echte Zahl eintragen

Kosten-Tracking:
  Geschätzt (Heuristik):  orchestrate.py trackt pro Agent-Tier
  Tatsächlich (exakt):     Claude Dashboard / API Usage nach der Runde
  → Phase 4 vergleicht beides und kalibriert Heuristik für nächste Runde
```

---

## ORCHESTRATOR: DIE STRATEGEN-LAST REDUZIEREN

### Das Problem

```
Was der Stratege WIRKLICH tun muss (ohne Automatisierung):

Phase 1: Richtung geben                              ~2 min    ← Strategie ✓
Phase 2: 8 Terminals öffnen                          ~3 min    ← Mechanisch ✗
         Prompts in Terminals copy-pasten             ~10 min   ← Mechanisch ✗
         Überwachen wer fertig ist                    ~15-45 min← Warten ✗
         Pipeline-Modus: fertige Terminals erkennen   ~laufend  ← Monitoring ✗
Phase 3: git merge pro Agent-Branch                   ~5 min    ← Mechanisch ✗
         Tests nach Merge                             ~10 min   ← Mechanisch ✗
Phase 5: Nächste Richtung entscheiden                 ~5 min    ← Strategie ✓

Echte Strategie-Arbeit:  ~7 min
Mechanische Arbeit:       ~50-80 min
→ Der "Stratege" ist zu 90% ein Terminal-Operator.
```

### Die Lösung: orchestrate.py

Ein Script das ALLES Mechanische übernimmt. Der Stratege macht nur
noch das was kein Script kann: Entscheidungen treffen.

```
orchestrate.py — Kommandos:

  orchestrate start <round> [--mode A|B|C] [--budget MEDIUM]
    Liest Prompt-Dateien aus ./prompts/round<N>/
    Validiert alle Prompts, erstellt Branches
    Startet Budget-Tracking

  orchestrate status
    Dashboard: Fortschritt, Health, Budget pro Agent

  orchestrate merge [--batch] [--bisect-on-failure]
    Pre-Merge Validierung (Stufe 1)
    Batch-Merge + Affected Tests (Stufe 2)
    Bei Failure: Bisect (Binary Search)
    Setzt Git-Tags automatisch

  orchestrate next
    Dispatcht nächste Wave (respektiert required_agents)

  orchestrate health
    Health-Checks aller laufenden Agents

  orchestrate report
    Generiert Post-Runde Report + aktualisiert .ai/ Dateien

  orchestrate retry <agent-id> [--with-context "hint"]
    Re-dispatcht gescheiterten Agent mit Fehler-Kontext

  orchestrate skip <agent-id>
    Überspringt Agent, prüft Abhängigkeiten

  orchestrate test --full
    Volle Test-Suite (Stufe 3)

  orchestrate reset
    Setzt Runde zurück (cleanup Branches + State)
```

### Prompt-Datei-Konvention

```
prompts/
└── round4/
    ├── manifest.yaml          ← Reihenfolge, Tiers, Abhängigkeiten
    ├── wave1_agent1_opus.md
    ├── wave1_agent2_sonnet.md
    ├── wave1_agent3_sonnet.md
    ├── wave1_agent4_haiku.md
    ├── wave2_agent5_sonnet.md
    ├── wave2_agent6_sonnet.md
    ├── wave2_agent7_haiku.md
    └── wave2_agent8_haiku.md

manifest.yaml:
  round: 4
  mode: B
  budget: MEDIUM
  test_runner: pytest          # Konfigurierbar: pytest / jest / cargo test
  base_branch: main            # Konfigurierbar: main / develop / etc.
  timeout_minutes: 20
  max_retries: 2
  waves:
    - name: "Wave 1: Core Native Backend"
      agents:
        - file: wave1_agent1_opus.md
          tier: opus
          path: kernelforge/native/
          branch: agent-401-native-cargo
        - file: wave1_agent2_sonnet.md
          tier: sonnet
          path: kernelforge/native/targets/
          branch: agent-402-native-targets
    - name: "Wave 2: FFI + Integration"
      depends_on: "Wave 1"
      required_agents: [agent-401, agent-402]
      agents:
        - file: wave2_agent5_sonnet.md
          tier: sonnet
          path: kernelforge/ffi/
          branch: agent-405-ffi-bridge
```

### Automatisierungs-Stufen

```
STUFE 1: MANUELL MIT DASHBOARD (Einstieg)
──────────────────────────────────────────
Was automatisiert: Nur Status-Dashboard (orchestrate status)
Was manuell bleibt: Terminals, Prompts, Merge
Vorteil: Kein Setup, sofort nutzbar

STUFE 2: SEMI-AUTOMATISCH (Empfehlung)
──────────────────────────────────────────
Was automatisiert: Dispatch + Status + Merge + Tags
Was manuell bleibt: "start" und "next" bewusst auslösen
Vorteil: Mensch behält Kontrolle über Timing

STUFE 3: VOLLAUTOMATISCH (Für erfahrene Teams)
──────────────────────────────────────────
Was automatisiert: Alles
Was manuell bleibt: Nur strategische Entscheidungen
Vorteil: Maximaler Durchsatz
Risiko: Weniger Kontrolle — nur wenn Pipeline stabil ist
```

---

## QUALITÄTS-SÄULEN

### 1. Konsistenz durch shared_interfaces.py
```
Problem: Agent A baut KFType als Enum, Agent B als Dataclass.
Lösung: Beide importieren aus shared_interfaces.py.
Ergebnis: 100% Interface-Kompatibilität beim Merge.
```

### 2. Qualität durch validierte Prompts + Templates
```
Problem: Prompt-Qualität schwankt. Schlechter Prompt → 8 Agents, 8× Müll.
Lösung: Templates (80% Struktur vorgegeben) + automatischer Validator.
Ergebnis: Qualitätsboden GARANTIERT, nicht abhängig von Tagesform.
```

### 3. Verständnis durch Code-Intelligence
```
Problem: "Ich GLAUBE die Pipeline hat 7 Stages" (falsch, sie hat 8).
Lösung: grep/ast-grep/SourceGraph → Fakten statt Annahmen. Cross-validiert.
Ergebnis: Prompts basieren auf dem echten Code, nicht auf Erinnerung.
```

### 4. Geschwindigkeit durch Parallelismus + Pipeline
```
Problem: 8 Terminals, aber wir warten auf den langsamsten.
Lösung: Pipeline-Modus + Batch-Merge + Terminal-Wiederverwendung.
Ergebnis: ~30% weniger Idle-Time.
```

### 5. Produktivität durch externalisiertes Projektgedächtnis
```
Problem: Context Window ist endlich. Session endet → alles weg.
Lösung: .ai/ Persistenz-Dateien im Repo. Session Recovery in 2 Minuten.
Ergebnis: Jede Runde ist besser als die letzte — auch nach Neustart.
```

### 6. Performance durch Post-Runde Analyse
```
Problem: Wir wissen nicht ob Agents zu wenig Edge-Cases testen.
Lösung: Automatische Analyse: Tests pro Agent, Edge-Case-Quote, Lint-Rate.
Ergebnis: Daten-getriebene Verbesserung statt Bauchgefühl.
```

### 7. Wirtschaftlichkeit durch Modell-Tiers + Budget-Caps
```
Problem: 8× Opus pro Runde ist unnötig teuer.
Lösung: 3-Tier-System + Budget-Caps + Token-basiertes Tracking.
Ergebnis: 60-75% Kosten-Reduktion. Kalibrierung durch echte Daten.
```

### 8. Fokus durch Orchestrator-Automatisierung
```
Problem: "Stratege" verbringt 90% der Zeit mit Copy-Paste.
Lösung: orchestrate.py übernimmt Dispatch, Status, Merge, Reporting.
Ergebnis: Mensch macht nur Strategie (~7 min statt ~80 min mechanisch).
```

### 9. Robustheit durch Health Monitoring + Failure Recovery
```
Problem: 8 parallele Agents = 8 parallele Fehlerquellen. Kein Plan dafür.
Lösung: Health-Checks, Failure-Klassifikation A/B/C, Recovery-Baum.
Ergebnis: 70% der Failures automatisch behoben (Klasse A).
```

### 10. Sicherheit durch Context-Trennung Chat ↔ Agents
```
Problem: Wenn ein Tool plant UND ausführt, wird sein Context mit
         Implementierungsdetails verschmutzt. Strategisches Denken leidet.
Lösung: Chat (Web) = geschützter strategischer Context.
        Agents (Code) = fokussierter Implementations-Context.
Ergebnis: Chat bleibt auch nach 10 Runden strategisch klar.
         Agents bleiben fokussiert weil sie nur EINEN Task kennen.
```

---

## EIN KONKRETER DURCHLAUF (BEISPIEL)

### Du sagst:
> "Runde 5. Breiterer Python-Support: Classes und Generators."

### Phase 0 — Chat sammelt Code-Intelligence (~10 min):

```
rg "class.*compilation|class.*codegen" --type py -l
→ Findet: kernelforge/fixes/closure_in_optimize.py, codegen_v3/collection_codegen.py

rg "class IRNode" --type py -A5
→ IRNode hat 50+ Subklassen, aber keine IRClass

rg "import.*type_inference|from.*type_inference" --type py
→ Änderung betrifft: Pipeline, Codegen v3, Optimizer, SDK

rg "class KFType" --type py -A20
→ KFType Enum hat: INT, FLOAT, BOOL, STRING, ARRAY, DICT, VOID
→ Fehlt: CLASS, INSTANCE, METHOD, PROPERTY
```

### Phase 1 — Chat plant (~20 min):

```
shared_interfaces_round5.py:
  - KFType erweitert um CLASS, INSTANCE, METHOD, PROPERTY
  - IRClass, IRMethod, IRProperty Node-Types
  - ClassCompileResult mit Vtable-Info

Wave-Plan (Modus A):
  Wave 1: Class Parsing & Lowering (4 Agents)
  Wave 2: Class Codegen (4 Agents)
  Wave 3: Generators + Integration (4 Agents)

Budget: MEDIUM ($100)
```

### Phase 2 — Agents laufen:

```
orchestrate start 5 --mode A --budget MEDIUM
→ Prompts validiert, Wave 1 dispatcht

orchestrate status (gelegentlich prüfen)
→ 3/4 done, 1 laufend, 0 failed

orchestrate merge --batch && orchestrate next
→ Wave 1 Batch-Merge: clean ✓, Wave 2 dispatcht
```

### Phase 3 — Merge (~15 min):

```
Wave 1 Batch-Merge → Affected Tests → 0 failures ✓
Wave 2 Batch-Merge → 1 failure → Bisect: Agent 5 schuldig
  → Fix: Import aus shared_interfaces → Re-Merge → clean ✓
Wave 3 Batch-Merge → clean ✓
Full Suite (14.912 Tests) → 0 failures ✓
Total: 15 min (inkl. 1 Bisect + Fix)
```

### Phase 4 — Chat analysiert:

```
(Du gibst Chat die Merge-Logs und Test-Outputs)

Chat: "Runde 5 Analyse:
  Tests: +380, Edge-Cases 28% (über Ziel ✓)
  Merge: 1 Bisect (Format-Inkompatibilität, durch shared_interfaces vermeidbar)
  Kosten: ~$68 von $100 Budget
  Empfehlung: Strategy Pattern in Runde 6, Error-Cases erhöhen"
```

### Phase 5 — Du entscheidest:

> "Gut. Runde 6: Standard Library Support + Pipeline Refactoring."

---

## CHECKLISTEN

### Vor jeder Runde:
```
□ Session Recovery: context_bootstrap.md + letzter Round Report gelesen
□ Code-Intelligence: Bestandsaufnahme zum Thema (grep/find/git)
□ Cross-Validation: Ergebnisse plausibel? Zweites Werkzeug nutzen?
□ shared_interfaces.py für diese Runde erstellt und committed
□ pre_merge_lint.py als git hook aktiv
□ Du hast die strategische Richtung vorgegeben
□ Budget-Klasse festgelegt (SMALL/MEDIUM/LARGE/XL)
□ Modell-Tier pro Agent zugewiesen (Opus/Sonnet/Haiku)
□ Shared Files identifiziert → Reconciliation-Strategie gewählt
```

### Vor Dispatch:
```
□ orchestrate validate → alle PASS oder WARN
□ Strukturelle Checks: Länge, shared_interfaces, Tests, Checkliste
□ Cross-Prompt Checks: Kein Pfad-Overlap, Budget-Summe ≤ Limit
□ Template genutzt wo möglich
□ Modell-Tier passt zur Task-Komplexität
□ Git-Tag gesetzt: round-<N>-start
```

### Während Agents laufen (Phase 2):
```
□ Health-Checks aktiv (manuell oder via Orchestrator)
□ Stalled Agents (5+ min inaktiv): prüfen
□ Timeout Agents (15+ min): gestoppt, Retry dispatcht
□ Violations: sofort gestoppt, Branch verworfen
□ Budget-Warnung bei 80%: verbleibende ggf. Haiku
```

### Nach jeder Wave:
```
□ Git-Tag: round-<N>-wave-<W>-pre-merge
□ Stufe 1: Alle Agents validiert (Tests grün, Lint clean, Pfade exklusiv)
□ Stufe 2: Batch-Merge + Affected Tests grün
  (oder bei Failure: Bisect → schuldigen Agent fixen)
□ Git-Tag: round-<N>-wave-<W>-post-merge
□ Shared Files Reconciliation (falls betroffen)
```

### Nach letzter Wave:
```
□ Stufe 3: Full Suite grün
□ Git-Tag: round-<N>-complete
```

### Nach jeder Runde:
```
□ Ergebnisse an Chat geben → Post-Runde Analyse
□ .ai/ Persistenz-Dateien aktualisiert:
  □ round_reports/round<N>.md
  □ learnings.md erweitert
  □ decisions_log.md erweitert
  □ context_bootstrap.md NEU GENERIERT
  □ git commit der .ai/ Änderungen
□ Tatsächliche Kosten aus Claude Dashboard notiert
□ Stratege informiert → Richtung für nächste Runde
```

---

## SKALIERUNG AUF ANDERE PROJEKTE

### Validierungs-Status

```
┌────────────────────────┬───────────────┬─────────────────────────────────┐
│ Projekttyp             │ Status        │ Grundlage                       │
├────────────────────────┼───────────────┼─────────────────────────────────┤
│ Python-Compiler        │ ✓ VALIDIERT   │ KernelForge, 5+ Runden,        │
│ (Rust Backend)         │               │ reale Metriken vorhanden        │
├────────────────────────┼───────────────┼─────────────────────────────────┤
│ Web-App (SaaS)         │ ○ ADAPTIERT   │ Vollständiger Durchlauf         │
│                        │               │ beschrieben, nicht getestet     │
├────────────────────────┼───────────────┼─────────────────────────────────┤
│ Mobile / ML / Micro    │ △ SKIZZIERT   │ Konzept + Adaptations-Guide     │
└────────────────────────┴───────────────┴─────────────────────────────────┘
```

### Das Pattern ist immer gleich

```
Was IMMER gleich bleibt (Kern-Methodik):
  1. Stratege gibt Richtung
  2. Chat (Hirn) sammelt Code-Fakten mit verfügbaren Werkzeugen
  3. Chat plant Waves mit exklusiven Pfaden
  4. shared_interfaces VOR den Agents committen
  5. Agents führen parallel aus (Claude Code Terminals)
  6. Merge mit Tiered Testing + Rollback-Tags
  7. Ergebnisse zurück an Chat → Analyse verbessert nächste Runde
  8. Chat Context bleibt geschützt (KEINE Implementierungsdetails)

Was sich PRO PROJEKTTYP ändert:
  - Was "shared_interfaces" enthält (Types, Schemas, API Contracts, Proto)
  - Wie viele Agents sinnvoll sind (2-4 bei Web, 4-8 bei Backend, 2-3 bei ML)
  - Was "Code-Intelligence" bedeutet (grep reicht vs. SourceGraph nötig)
  - Was "Pre-Merge Lint" prüft (ESLint / ruff / cargo check / tsc)
  - Was "Tests" bedeutet (pytest / Jest / Playwright / Contract-Tests)
  - Welche Shared Files es gibt und wie man sie handhabt
  - Welche Merge-Konflikte typisch sind
```

### Web-App — Vollständiger Durchlauf

```
Kontext-Unterschiede zu Compiler-Projekten:
  Compiler: Tiefe Algorithmen, 8 Agents, GitNexus sinnvoll
  Web-App:  Breite Features, 3-5 Agents, grep reicht

Beispiel: "Runde 3 — Dashboard + Auth"

  shared_interfaces_round3.ts:
    export interface DashboardMetric { ... }
    export interface AuthContext { ... }
    export interface MetricUpdateEvent { ... }

  Wave 1 (3 Agents):
    Agent 1 (Sonnet): DB + API — Pfad: src/db/ + src/api/routes/dashboard.ts
    Agent 2 (Sonnet): Auth RBAC — Pfad: src/middleware/rbac.ts
    Agent 3 (Haiku):  WebSocket — Pfad: src/realtime/

  Wave 2 (3 Agents, depends_on Wave 1):
    Agent 4 (Sonnet): Dashboard-Components — Pfad: src/components/dashboard/
    Agent 5 (Sonnet): Realtime-Hook — Pfad: src/hooks/ + src/store/dashboard.ts
    Agent 6 (Haiku):  E2E Tests — Pfad: tests/e2e/ + tests/integration/

  Budget: SMALL ($50)
  Shared Files: package.json → Fragment-Strategie
                src/routes/index.ts → Reconciliation-Agent nach Merge

  Web-spezifische Merge-Risiken:
    - CSS-Konflikte → CSS Modules oder Tailwind (Scoping per Datei)
    - State-Konflikte → Exklusive Store-Slices pro Agent
    - Route-Konflikte → Route-Prefix pro Agent
```

### Mobile App — Adaptations-Guide

```
Was sich ändert:
  - shared_interfaces doppelt: iOS (Swift) + Android (Kotlin)
    ODER: gemeinsame Sprache (TypeScript für React Native)
  - Tests LANGSAMER: Emulator, UI-Tests, Screenshots
  - Max 4 Agents (Builds blockieren Ressourcen)
  - Wave-Struktur: Shared Logic → iOS → Android → E2E
```

### Data Pipeline / ML — Adaptations-Guide

```
Was FUNDAMENTAL anders ist:
  - NICHT-DETERMINISTISCH: Tests prüfen Ranges/Shapes, nicht exakte Werte
  - LANGSAM: Training dauert Minuten bis Stunden
  - RESSOURCEN: GPU-Zugang, nicht 8 Agents die alle GPU wollen
  - Max 3-4 Agents, Modus A fast immer, Budget LARGE
  - shared_interfaces = Schema-Definitionen (Avro, Protobuf, JSON Schema)
```

### Microservices — Adaptations-Guide

```
Was sich ändert:
  - shared_interfaces = API Contracts (OpenAPI, gRPC Proto)
  - Exklusive Pfade sind NATÜRLICH (1 Service = 1 Verzeichnis)
  - Tests: Contract-Tests (Pact) als Pflicht
  - Deploy-Reihenfolge: Waves MÜSSEN sie respektieren
  - 1 Agent pro Service (natürliche Isolation)
```

### Adaptations-Checkliste: Methodik auf neuen Projekttyp anwenden

```
Bevor du die Methodik auf ein neues Projekt anwendest, beantworte:

□ Was ist "shared_interfaces" hier?
□ Wie viele parallele Agents sind realistisch?
□ Was bedeutet "Pre-Merge Lint" hier?
□ Was bedeutet "Tests" hier?
□ Welche Shared Files gibt es? Welche Strategie?
□ Welche Merge-Konflikte sind typisch?
□ Wie schnell ist der Feedback-Loop?
□ Welche Code-Intelligence-Werkzeuge sind verfügbar/nötig?
□ Welcher Modus ist der Default?
□ Welches Budget ist realistisch?
```

---

## VALIDIERUNGS-ROADMAP

### Pilot-Runde (1 Runde, LITE-Modus)

```
Ziel: Methodik am eigenen Projekt testen, ohne vollen Setup-Aufwand.

1. VORBEREITUNG (~15 min)
   □ shared_interfaces für 1 Feature definieren
   □ 2-3 Prompts schreiben (custom, noch keine Templates)
   □ Exklusive Dateipfade zuweisen

2. DURCHFÜHRUNG (~30-45 min)
   □ 2-3 Agents parallel starten
   □ Beobachten: Wie lange brauchen sie? Wo scheitern sie?
   □ Manuell mergen, Tests laufen lassen

3. AUSWERTUNG (~15 min)
   □ Merge-Konflikte? → Pfade waren nicht exklusiv genug
   □ Interface-Inkompatibilität? → shared_interfaces war unvollständig
   □ Agent hat Prompt ignoriert? → Prompt war zu vage
   □ Alle Tests grün? → Methodik funktioniert für dein Projekt

4. ENTSCHEIDUNG
   □ Pilot erfolgreich → Skaliere auf STANDARD
   □ Pilot teilweise → Passe an, 2. Pilot
   □ Pilot gescheitert → Projekt passt nicht zur Methodik
```

### Skalierungs-Pfad (3 Runden)

```
Runde 1 — LITE:  2-3 Agents, manuell → Baseline-Metriken
Runde 2 — STANDARD:  4-6 Agents, Templates, Validator → Vergleich
Runde 3 — STANDARD+:  6-8 Agents, Orchestrator, Batch-Merge → Optimieren
Ab Runde 4:  Daten-getriebene Entscheidung ob FULL sich lohnt
```

### Erfolgs-Kriterien

```
Die Methodik FUNKTIONIERT wenn:
  ✓ Merge-Konflikte < 10% der Agents
  ✓ Agent-Erfolgsrate > 75%
  ✓ Merge-Zeit < 30% der Execution-Zeit
  ✓ Test-Regressions < 5% nach Merge

Die Methodik PASST NICHT wenn:
  ✗ Exklusive Pfade sind unmöglich (alles hängt zusammen)
  ✗ Agents brauchen Kontext über andere Agents
  ✗ Build-Zeiten > 10 min (Feedback-Loop zu langsam)
  ✗ Projekt hat < 500 LOC (Overhead übersteigt Nutzen)
```

---

## ZUSAMMENFASSUNG

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  DU entscheidest WAS und WARUM.                           │
│                                                            │
│  CHAT (Web) plant WIE — mit geschütztem Context,          │
│  der nicht durch Implementierungsdetails verschmutzt      │
│  wird. Wissen aus .ai/ Dateien überlebt Sessions.         │
│                                                            │
│  AGENTS (Claude Code) führen aus — fokussiert,            │
│  parallel, disposable. 1 Prompt = 1 Task = 1 Pfad.       │
│                                                            │
│  CODE-INTELLIGENCE (grep, ast-grep, SourceGraph)          │
│  liefert Fakten statt Annahmen. Immer cross-validiert.    │
│                                                            │
│  Die Trennung Chat ↔ Agents ist kein Workaround.         │
│  Es ist SEPARATION OF CONCERNS auf Context-Ebene.         │
│  Das Hirn bleibt klar. Die Hände bleiben fokussiert.     │
│                                                            │
│  Jede Runde ist besser als die letzte,                    │
│  weil das System aus sich selbst lernt.                    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```
