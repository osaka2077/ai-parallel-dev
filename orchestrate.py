#!/usr/bin/env python3
"""
orchestrate.py — AI-Orchestrated Parallel Development CLI

Automatisiert die mechanische Arbeit des Strategen:
Terminal-Management, Dispatch, Health-Monitoring, Merge, Reporting.

Usage:
    orchestrate start <round> [--mode A|B|C] [--budget SMALL|MEDIUM|LARGE|XL]
    orchestrate status
    orchestrate merge [--batch] [--bisect-on-failure] [--dry-run]
    orchestrate health
    orchestrate validate <prompt-dir>
    orchestrate preflight [prompt-dir] [--depth N]
    orchestrate next
    orchestrate report
    orchestrate retry <agent-id> [--with-context "hint"]
    orchestrate skip <agent-id>
    orchestrate test --full
    orchestrate done <agent-id>
    orchestrate reset [--hard]
    orchestrate abort
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import re
import signal
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Generator

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

STATE_FILE = ".ai/orchestrator_state.json"
REPORTS_DIR = ".ai/round_reports"
PROMPTS_DIR = "prompts"

BUDGET_CAPS: dict[str, int] = {
    "SMALL": 50,
    "MEDIUM": 100,
    "LARGE": 200,
    "XL": 300,
}

# Heuristische Schaetzwerte pro Prompt-Aufruf (Token-basiert).
# Kalibriere nach 2-3 Runden mit echten Werten aus der Claude-Abrechnung.
TIER_COST_PER_PROMPT: dict[str, float] = {
    "opus": 8.0,
    "sonnet": 3.0,
    "haiku": 0.5,
}

HEALTH_INTERVAL_SEC = 60
HEARTBEAT_WARN_MIN = 5
HEARTBEAT_TIMEOUT_MIN = 15

# Konfigurierbarer Test-Runner (Default: pytest)
TEST_RUNNER: list[str] = ["pytest"]

logger = logging.getLogger("orchestrate")

# Flag fuer Ctrl+C Handling waehrend Merge
_merge_interrupted = False


# ---------------------------------------------------------------------------
# GitNexus Integration (optional)
# ---------------------------------------------------------------------------

def _detect_gitnexus() -> str | None:
    """Sucht GitNexus CLI: PATH, bekannte Pfade, .ai/config.yaml Override."""
    import shutil

    # 1. Config-Override
    config_path = Path(".ai/config.yaml")
    if config_path.exists() and yaml is not None:
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            gn_cfg = cfg.get("gitnexus", {})
            if isinstance(gn_cfg, dict):
                if not gn_cfg.get("enabled", True):
                    return None
                explicit = gn_cfg.get("cli_path")
                if explicit and Path(explicit).exists():
                    return str(explicit)
        except Exception:
            pass

    # 2. PATH lookup
    found = shutil.which("gitnexus")
    if found:
        return found

    # 3. Bekannte Pfade
    candidates = [
        Path.home() / ".gitnexus" / "bin" / "gitnexus",
        Path.home() / ".gitnexus" / "gitnexus",
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    return None


def _run_gitnexus(cmd: list[str], timeout: int = 30) -> dict[str, Any] | None:
    """Wrapper fuer GitNexus CLI-Aufruf. Gibt parsed JSON oder None zurueck."""
    if not _gitnexus_cli:
        return None
    try:
        full_cmd = [_gitnexus_cli, *cmd, "--format", "json"]
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            logger.debug("GitNexus Fehler: %s", result.stderr.strip())
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        logger.debug("GitNexus nicht verfuegbar: %s", e)
        return None


def _gitnexus_config() -> dict[str, Any]:
    """Laedt GitNexus-spezifische Config aus .ai/config.yaml."""
    config_path = Path(".ai/config.yaml")
    if not config_path.exists() or yaml is None:
        return {}
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("gitnexus", {}) if isinstance(cfg.get("gitnexus"), dict) else {}
    except Exception:
        return {}


# Modul-Level Detection beim Import
_gitnexus_cli: str | None = _detect_gitnexus()
_gitnexus_available: bool = _gitnexus_cli is not None


# ---------------------------------------------------------------------------
# Signal Handling
# ---------------------------------------------------------------------------

def _sigint_handler(signum: int, frame: Any) -> None:
    """Setzt Flag statt sofort abzubrechen — erlaubt sauberes Cleanup."""
    global _merge_interrupted
    _merge_interrupted = True
    logger.warning("\nCtrl+C erkannt — breche nach aktuellem Schritt sauber ab...")


# ---------------------------------------------------------------------------
# Enums & Data
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    MERGED = "MERGED"


class HealthStatus(str, Enum):
    ACTIVE = "ACTIVE"
    HEALTHY = "HEALTHY"
    STALLED = "STALLED"
    TIMEOUT = "TIMEOUT"
    INCOMPLETE = "INCOMPLETE"
    VIOLATION = "VIOLATION"
    NO_OUTPUT = "NO_OUTPUT"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    UNKNOWN = "UNKNOWN"


class FailureClass(str, Enum):
    A = "A"  # Auto-recoverable
    B = "B"  # Needs prompt adjustment
    C = "C"  # Security-stop


@dataclass
class AgentState:
    agent_id: str
    wave: str
    file: str
    tier: str
    path: str
    branch: str
    status: str = AgentStatus.PENDING.value
    health: str = HealthStatus.UNKNOWN.value
    retry_count: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    last_activity: str | None = None
    test_count: int = 0
    file_count: int = 0
    failure_class: str | None = None
    estimated_cost: float = 0.0


@dataclass
class RoundState:
    round_number: int
    mode: str
    budget_label: str
    budget_cap: int
    budget_spent: float = 0.0
    agents: list[dict[str, Any]] = field(default_factory=list)
    current_wave: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    waves: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Farbausgabe (Terminal)
# ---------------------------------------------------------------------------

class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"

    @staticmethod
    def enabled() -> bool:
        return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    @classmethod
    def c(cls, color: str, text: str) -> str:
        if cls.enabled():
            return f"{color}{text}{cls.RESET}"
        return text


# ---------------------------------------------------------------------------
# State Persistence (mit File-Locking)
# ---------------------------------------------------------------------------

def _state_path() -> Path:
    return Path(STATE_FILE)


@contextlib.contextmanager
def _file_lock(path: Path) -> Generator[None, None, None]:
    """Plattform-uebergreifendes File-Locking (Windows: msvcrt, Unix: fcntl)."""
    lock_path = path.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(lock_path, "w", encoding="utf-8")
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if sys.platform == "win32":
            import msvcrt
            try:
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()


def load_state() -> dict[str, Any]:
    p = _state_path()
    if not p.exists():
        return {}
    with _file_lock(p):
        return json.loads(p.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with _file_lock(p):
        p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Git Helpers
# ---------------------------------------------------------------------------

def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = ["git", *args]
    logger.debug("$ %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def git_branch_exists(branch: str) -> bool:
    r = git("rev-parse", "--verify", branch, check=False)
    return r.returncode == 0


def git_current_branch() -> str:
    r = git("rev-parse", "--abbrev-ref", "HEAD")
    return r.stdout.strip()


def git_changed_files(branch: str, base: str = "main") -> list[str]:
    r = git("diff", "--name-only", f"{base}...{branch}", check=False)
    if r.returncode != 0:
        return []
    return [f for f in r.stdout.strip().splitlines() if f]


def git_last_commit_time(branch: str) -> datetime | None:
    r = git("log", "-1", "--format=%cI", branch, check=False)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return datetime.fromisoformat(r.stdout.strip())


def _create_branch(branch: str, base: str = "HEAD") -> None:
    """Erstellt Branch OHNE den Working Tree zu wechseln."""
    git("branch", branch, base, check=False)


def _tag_round(tag_name: str) -> None:
    """Setzt ein Git-Tag fuer Rollback-Zwecke."""
    git("tag", "-f", tag_name, check=False)


# ---------------------------------------------------------------------------
# Agent-ID Matching (exakt, dann Prefix)
# ---------------------------------------------------------------------------

def _find_agent(agents: list[dict[str, Any]], agent_id: str) -> dict[str, Any] | None:
    """Findet Agent: erst exakter Match, dann Prefix-Match. Kein Substring."""
    for a in agents:
        if a["agent_id"] == agent_id:
            return a
    # Prefix-Match als Fallback (z.B. "auth" matched "auth-service")
    matches = [a for a in agents if a["agent_id"].startswith(agent_id)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        logger.warning("Mehrdeutiger Agent-ID '%s'. Matches: %s",
                        agent_id, [a["agent_id"] for a in matches])
    return None


# ---------------------------------------------------------------------------
# Konfiguration laden (.ai/config.yaml)
# ---------------------------------------------------------------------------

def _load_config() -> dict[str, Any]:
    """Laedt optionale Projekt-Konfiguration fuer Test-Runner etc."""
    global TEST_RUNNER
    config_path = Path(".ai/config.yaml")
    if not config_path.exists():
        return {}
    if yaml is None:
        return {}
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # Test-Runner konfigurierbar
    runner = config.get("test_runner")
    if isinstance(runner, str):
        TEST_RUNNER = runner.split()
    elif isinstance(runner, list):
        TEST_RUNNER = runner

    # Kosten-Kalibrierung
    cost_overrides = config.get("tier_costs")
    if isinstance(cost_overrides, dict):
        for tier, cost in cost_overrides.items():
            if isinstance(cost, (int, float)):
                TIER_COST_PER_PROMPT[tier] = float(cost)

    return config


# ---------------------------------------------------------------------------
# Manifest Parser
# ---------------------------------------------------------------------------

def load_manifest(round_number: int) -> dict[str, Any]:
    manifest_path = Path(PROMPTS_DIR) / f"round{round_number}" / "manifest.yaml"
    if not manifest_path.exists():
        logger.error("Manifest nicht gefunden: %s", manifest_path)
        sys.exit(1)

    if yaml is None:
        logger.error("PyYAML nicht installiert. Bitte: pip install pyyaml")
        sys.exit(1)

    with open(manifest_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Prompt Validator
# ---------------------------------------------------------------------------

# Strukturelle Checks via Frontmatter (primaer) + Regex-Fallback
VALIDATION_CHECKS = [
    ("SHARED_INTERFACE", r"shared_interfaces", "Referenziert shared_interfaces?"),
    ("EXCLUSIVE_PATH", r"(?:Exklusiv|EXKLUSIV|Dateipfad|NUR in|exclusive_path:)", "Exklusiver Dateipfad definiert?"),
    ("TEST_REQ", r"(?:pytest|test|Test|tests:)", "Test-Anforderungen enthalten?"),
    ("BRANCH_NAME", r"(?:Branch|branch|git checkout|branch:)", "Branch-Name spezifiziert?"),
    ("NO_MODIFY_SHARED", r"(?:NICHT|nicht|never|Never).*(?:shared_interfaces|änder)", "Verbot: shared_interfaces aendern?"),
    ("IMPORTS_LISTED", r"(?:import|from\s+\w+\s+import|dependencies:)", "Imports aufgelistet?"),
    ("CONTEXT_SECTION", r"(?:Kontext|Context|Hintergrund|context:)", "Kontext-Sektion vorhanden?"),
    ("ACCEPTANCE_CRITERIA", r"(?:Akzeptanz|Acceptance|Erfolgskriterien|Definition of Done|done_when:)", "Akzeptanzkriterien definiert?"),
    ("LINE_COUNT", None, "Promptlaenge 40-200 Zeilen?"),
    ("NO_PLACEHOLDER", r"\{\{.*?\}\}|TODO|FIXME|XXX", "Keine Platzhalter/TODOs?"),
]


def _parse_frontmatter(content: str) -> dict[str, Any] | None:
    """Versucht YAML-Frontmatter zu parsen (--- ... ---)."""
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    if yaml is None:
        return None
    try:
        return yaml.safe_load(content[3:end])
    except Exception:
        return None


def validate_prompt(filepath: Path) -> list[dict[str, Any]]:
    """Validiert einen einzelnen Prompt. Gibt Liste von Check-Ergebnissen zurueck."""
    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines()
    frontmatter = _parse_frontmatter(content)
    results: list[dict[str, Any]] = []

    for check_id, pattern, description in VALIDATION_CHECKS:
        passed = True

        if check_id == "LINE_COUNT":
            passed = 40 <= len(lines) <= 200
        elif check_id == "NO_PLACEHOLDER":
            # Invertiert: Platzhalter gefunden = FAIL
            if pattern and re.search(pattern, content):
                passed = False
        else:
            # Frontmatter-Check primaer, Regex als Fallback
            fm_key = _frontmatter_key_for_check(check_id)
            if frontmatter and fm_key and fm_key in frontmatter:
                passed = True
            elif pattern:
                passed = bool(re.search(pattern, content, re.IGNORECASE))
            else:
                passed = False

        results.append({
            "check": check_id,
            "description": description,
            "passed": passed,
        })

    return results


def _frontmatter_key_for_check(check_id: str) -> str | None:
    """Mappt Check-IDs auf erwartete Frontmatter-Keys."""
    return {
        "SHARED_INTERFACE": "shared_interface",
        "EXCLUSIVE_PATH": "exclusive_path",
        "TEST_REQ": "tests",
        "BRANCH_NAME": "branch",
        "IMPORTS_LISTED": "dependencies",
        "CONTEXT_SECTION": "context",
        "ACCEPTANCE_CRITERIA": "done_when",
    }.get(check_id)


def validate_cross_prompts(prompt_files: list[Path]) -> list[dict[str, Any]]:
    """Cross-Prompt Checks: Pfad-Ueberlappungen, Branch-Duplikate."""
    results: list[dict[str, Any]] = []
    paths_seen: dict[str, str] = {}
    branches_seen: dict[str, str] = {}

    for pf in prompt_files:
        content = pf.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(content)

        # Pfad-Extraktion: Frontmatter primaer, Regex Fallback
        path_value = None
        if frontmatter and "exclusive_path" in frontmatter:
            path_value = str(frontmatter["exclusive_path"])
        else:
            path_match = re.search(r"(?:Exklusiv|Pfad|path)[:\s]+([^\s\n]+/)", content, re.IGNORECASE)
            if path_match:
                path_value = path_match.group(1)

        if path_value:
            if path_value in paths_seen:
                results.append({
                    "check": "PATH_OVERLAP",
                    "description": f"Pfad-Ueberlappung: {path_value}",
                    "files": [paths_seen[path_value], pf.name],
                    "passed": False,
                })
            paths_seen[path_value] = pf.name

        # Branch-Extraktion: Frontmatter primaer, Regex Fallback
        branch_value = None
        if frontmatter and "branch" in frontmatter:
            branch_value = str(frontmatter["branch"])
        else:
            branch_match = re.search(r"(?:branch|Branch)[:\s]+(\S+)", content)
            if branch_match:
                branch_value = branch_match.group(1)

        if branch_value:
            if branch_value in branches_seen:
                results.append({
                    "check": "BRANCH_DUPLICATE",
                    "description": f"Branch-Duplikat: {branch_value}",
                    "files": [branches_seen[branch_value], pf.name],
                    "passed": False,
                })
            branches_seen[branch_value] = pf.name

    if not results:
        results.append({
            "check": "CROSS_VALIDATION",
            "description": "Keine Cross-Prompt-Konflikte",
            "passed": True,
        })

    return results


# ---------------------------------------------------------------------------
# Health Checks
# ---------------------------------------------------------------------------

def check_agent_health(agent: dict[str, Any]) -> HealthStatus:
    """Fuehrt 4 Health-Checks fuer einen Agent durch."""
    branch = agent["branch"]

    if not git_branch_exists(branch):
        return HealthStatus.UNKNOWN

    # Check 1: Heartbeat
    last_commit = git_last_commit_time(branch)
    if last_commit:
        age_min = (datetime.now(timezone.utc) - last_commit).total_seconds() / 60
        if age_min > HEARTBEAT_TIMEOUT_MIN:
            return HealthStatus.TIMEOUT
        if age_min > HEARTBEAT_WARN_MIN:
            return HealthStatus.STALLED
    else:
        return HealthStatus.NO_OUTPUT

    # Check 2: Pfad-Compliance
    changed = git_changed_files(branch)
    agent_path = agent["path"].rstrip("/")
    for f in changed:
        if not f.startswith(agent_path) and f != "shared_interfaces.py":
            return HealthStatus.VIOLATION

    # Check 3: Output-Plausibilitaet (bei DONE)
    if agent["status"] == AgentStatus.DONE.value:
        has_code = any(f.endswith((".py", ".ts", ".js", ".rs", ".go", ".java")) for f in changed)
        has_tests = any("test" in f.lower() for f in changed)
        if not has_code:
            return HealthStatus.NO_OUTPUT
        if not has_tests:
            return HealthStatus.INCOMPLETE
        return HealthStatus.HEALTHY

    return HealthStatus.ACTIVE


def classify_failure(health: HealthStatus) -> FailureClass:
    """Klassifiziert einen Health-Status in Failure-Klassen."""
    if health in (HealthStatus.TIMEOUT, HealthStatus.BUDGET_EXCEEDED, HealthStatus.NO_OUTPUT):
        return FailureClass.A
    if health in (HealthStatus.INCOMPLETE, HealthStatus.STALLED):
        return FailureClass.B
    if health == HealthStatus.VIOLATION:
        return FailureClass.C
    return FailureClass.A


# ---------------------------------------------------------------------------
# Test-Runner (konfigurierbar)
# ---------------------------------------------------------------------------

def _run_tests(test_args: list[str] | None = None, label: str = "Tests") -> bool:
    """Fuehrt Tests mit konfiguriertem Runner aus. Gibt True bei Erfolg."""
    cmd = TEST_RUNNER + (test_args or [])
    print(Color.c(Color.CYAN, f"\n  {label}: {' '.join(cmd)}"))
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        print(Color.c(Color.GREEN, f"  ✓ {label} bestanden"))
        return True
    print(Color.c(Color.RED, f"  ✗ {label} fehlgeschlagen"))
    if result.stdout:
        print(result.stdout[-500:])
    return False


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_start(args: argparse.Namespace) -> None:
    """orchestrate start <round> [--mode A|B|C] [--budget MEDIUM]"""
    round_num = args.round
    mode = args.mode or "B"
    budget_label = args.budget or "MEDIUM"
    budget_cap = BUDGET_CAPS.get(budget_label, 100)

    manifest = load_manifest(round_num)
    prompt_dir = Path(PROMPTS_DIR) / f"round{round_num}"

    # Prompt-Validierung vor Start
    prompt_files = sorted(prompt_dir.glob("*.md"))
    if not prompt_files:
        logger.error("Keine Prompt-Dateien in %s gefunden", prompt_dir)
        sys.exit(1)

    print(Color.c(Color.BOLD, f"\n=== RUNDE {round_num} — Modus {mode} — Budget {budget_label} (${budget_cap}) ===\n"))

    # Validierung
    print(Color.c(Color.CYAN, "Prompt-Validierung..."))
    all_passed = True
    for pf in prompt_files:
        results = validate_prompt(pf)
        failed = [r for r in results if not r["passed"]]
        if failed:
            all_passed = False
            print(f"  {Color.c(Color.RED, '✗')} {pf.name}:")
            for r in failed:
                print(f"    - {r['check']}: {r['description']}")
        else:
            print(f"  {Color.c(Color.GREEN, '✓')} {pf.name}: Alle Checks bestanden")

    cross = validate_cross_prompts(prompt_files)
    cross_failed = [r for r in cross if not r["passed"]]
    if cross_failed:
        all_passed = False
        for r in cross_failed:
            print(f"  {Color.c(Color.RED, '✗')} {r['description']}: {r.get('files', [])}")

    if not all_passed:
        print(Color.c(Color.YELLOW, "\n⚠ Validierungsfehler. --force zum Ueberspringen."))
        if not getattr(args, "force", False):
            sys.exit(1)

    print(Color.c(Color.GREEN, "✓ Alle Prompts validiert\n"))

    # State aufbauen
    agents: list[dict[str, Any]] = []
    waves_meta: list[dict[str, Any]] = []

    for wave_idx, wave in enumerate(manifest.get("waves", []), 1):
        wave_name = wave.get("name", f"Wave {wave_idx}")
        wave_agents = wave.get("agents", [])
        depends_on = wave.get("depends_on")
        required = wave.get("required_agents", [])

        waves_meta.append({
            "index": wave_idx,
            "name": wave_name,
            "depends_on": depends_on,
            "required_agents": required,
        })

        for ag in wave_agents:
            agent_file = ag.get("file", "")
            tier = ag.get("tier", "sonnet")
            cost = TIER_COST_PER_PROMPT.get(tier, 3.0)

            agents.append(asdict(AgentState(
                agent_id=ag.get("branch", agent_file),
                wave=wave_name,
                file=agent_file,
                tier=tier,
                path=ag.get("path", ""),
                branch=ag.get("branch", f"agent-{round_num}{wave_idx}-{agent_file}"),
                estimated_cost=cost,
            )))

    state = asdict(RoundState(
        round_number=round_num,
        mode=mode,
        budget_label=budget_label,
        budget_cap=budget_cap,
        started_at=_now_iso(),
        agents=agents,
        waves=waves_meta,
    ))
    save_state(state)

    # Git-Tag fuer Rollback
    _tag_round(f"round-{round_num}-start")

    # Erste Wave starten
    wave1_agents = [a for a in agents if a["wave"] == waves_meta[0]["name"]]
    print(Color.c(Color.BOLD, f"Wave 1: {waves_meta[0]['name']}"))
    print(f"  Agents: {len(wave1_agents)}")
    print()

    for a in wave1_agents:
        branch = a["branch"]
        prompt_path = prompt_dir / a["file"]
        print(f"  {Color.c(Color.CYAN, '→')} {a['agent_id']}")
        print(f"    Branch:  {branch}")
        print(f"    Prompt:  {prompt_path}")
        print(f"    Tier:    {a['tier']}")
        print(f"    Pfad:    {a['path']}")

        # Branch erstellen OHNE Working Tree zu wechseln
        if not git_branch_exists(branch):
            _create_branch(branch)

        a["status"] = AgentStatus.RUNNING.value
        a["started_at"] = _now_iso()

    state["agents"] = agents
    save_state(state)

    print(Color.c(Color.GREEN, f"\n✓ {len(wave1_agents)} Agents bereit."))
    print("  Prompts jetzt in die jeweiligen Terminals kopieren.")
    print("  Oder: claude --prompt-file <pfad> im jeweiligen Branch.\n")
    print(Color.c(Color.GRAY, "  Naechste Schritte:"))
    print(Color.c(Color.GRAY, "    orchestrate status   — Dashboard anzeigen"))
    print(Color.c(Color.GRAY, "    orchestrate health   — Health-Checks"))
    print(Color.c(Color.GRAY, "    orchestrate merge    — Wenn Agents fertig"))


def cmd_status(args: argparse.Namespace) -> None:
    """orchestrate status — Dashboard mit Echtzeit-Ueberblick."""
    state = load_state()
    if not state:
        print("Keine aktive Runde. Starte mit: orchestrate start <round>")
        return

    round_num = state["round_number"]
    mode = state["mode"]
    budget_cap = state["budget_cap"]
    budget_spent = state.get("budget_spent", 0)
    agents = state["agents"]

    budget_pct = (budget_spent / budget_cap * 100) if budget_cap > 0 else 0
    budget_color = Color.GREEN if budget_pct < 70 else (Color.YELLOW if budget_pct < 90 else Color.RED)

    print()
    print(Color.c(Color.BOLD, "┌──────────────────────────────────────────────────┐"))
    print(Color.c(Color.BOLD, f"│ RUNDE {round_num} — Modus {mode} — Budget: ") +
          Color.c(budget_color, f"${budget_spent:.0f}/${budget_cap} ({budget_pct:.0f}%)"))
    print(Color.c(Color.BOLD, "├──────────────────────────────────────────────────┤"))

    status_counts: dict[str, int] = {}

    for a in agents:
        st = a["status"]
        health = a.get("health", "UNKNOWN")
        status_counts[st] = status_counts.get(st, 0) + 1

        # Fortschrittsbalken
        if st in (AgentStatus.DONE.value, AgentStatus.MERGED.value):
            bar = "██████████"
            pct = "100%"
        elif st == AgentStatus.RUNNING.value:
            bar = "████░░░░░░"
            pct = "~50%"
        elif st == AgentStatus.FAILED.value:
            bar = "░░░░░░░░░░"
            pct = "FAIL"
        else:
            bar = "░░░░░░░░░░"
            pct = "  0%"

        # Farbe nach Status
        if st in (AgentStatus.DONE.value, AgentStatus.MERGED.value):
            line_color = Color.GREEN
        elif st == AgentStatus.FAILED.value:
            line_color = Color.RED
        elif health in (HealthStatus.STALLED.value, HealthStatus.INCOMPLETE.value):
            line_color = Color.YELLOW
        elif health == HealthStatus.VIOLATION.value:
            line_color = Color.RED
        else:
            line_color = Color.RESET

        health_icon = {
            HealthStatus.HEALTHY.value: "✓ HEALTHY",
            HealthStatus.ACTIVE.value: "✓ ACTIVE",
            HealthStatus.STALLED.value: "⚠ STALLED",
            HealthStatus.INCOMPLETE.value: "⚠ INCOMPLETE",
            HealthStatus.TIMEOUT.value: "✗ TIMEOUT",
            HealthStatus.VIOLATION.value: "✗ VIOLATION",
            HealthStatus.NO_OUTPUT.value: "✗ NO_OUTPUT",
            HealthStatus.BUDGET_EXCEEDED.value: "✗ BUDGET_EXCEEDED",
        }.get(health, "? UNKNOWN")

        agent_short = a["agent_id"][:25].ljust(25)
        print(Color.c(line_color, f"│  {bar} {pct:>5}  {agent_short} {health_icon}"))

    print(Color.c(Color.BOLD, "├──────────────────────────────────────────────────┤"))
    done = status_counts.get("DONE", 0) + status_counts.get("MERGED", 0)
    running = status_counts.get("RUNNING", 0)
    failed = status_counts.get("FAILED", 0)
    pending = status_counts.get("PENDING", 0)
    total = len(agents)
    print(f"│  Fertig: {done}/{total} | Laufend: {running}/{total} | Failed: {failed}/{total} | Pending: {pending}/{total}")

    if budget_pct >= 90:
        print(Color.c(Color.RED, f"│  ⚠ BUDGET-WARNUNG: {budget_pct:.0f}% verbraucht!"))
    print(Color.c(Color.BOLD, "└──────────────────────────────────────────────────┘"))
    print()


def cmd_health(args: argparse.Namespace) -> None:
    """orchestrate health — Health-Checks aller laufenden Agents."""
    state = load_state()
    if not state:
        print("Keine aktive Runde.")
        return

    agents = state["agents"]
    updated = False

    print(Color.c(Color.BOLD, "\nHealth-Check aller Agents:\n"))

    for a in agents:
        if a["status"] not in (AgentStatus.RUNNING.value, AgentStatus.DONE.value):
            continue

        health = check_agent_health(a)
        old_health = a.get("health", "UNKNOWN")

        a["health"] = health.value
        a["last_activity"] = _now_iso()

        if health.value != old_health:
            updated = True

        # Automatische Aktionen
        action = ""

        if health == HealthStatus.TIMEOUT:
            a["status"] = AgentStatus.FAILED.value
            a["failure_class"] = FailureClass.A.value
            action = "→ Agent gestoppt (Timeout). Retry-Queue."
        elif health == HealthStatus.VIOLATION:
            a["status"] = AgentStatus.FAILED.value
            a["failure_class"] = FailureClass.C.value
            action = "→ Agent gestoppt (Pfad-Violation). Branch pruefen!"
        elif health == HealthStatus.NO_OUTPUT:
            a["failure_class"] = FailureClass.A.value
            action = "→ Kein Output. Warte noch oder retry."

        color = {
            HealthStatus.HEALTHY: Color.GREEN,
            HealthStatus.ACTIVE: Color.GREEN,
            HealthStatus.STALLED: Color.YELLOW,
            HealthStatus.INCOMPLETE: Color.YELLOW,
            HealthStatus.TIMEOUT: Color.RED,
            HealthStatus.VIOLATION: Color.RED,
            HealthStatus.NO_OUTPUT: Color.RED,
        }.get(health, Color.GRAY)

        print(f"  {Color.c(color, health.value.ljust(15))} {a['agent_id']}")
        if action:
            print(f"    {Color.c(Color.YELLOW, action)}")

    if updated:
        save_state(state)

    print()


def cmd_merge(args: argparse.Namespace) -> None:
    """orchestrate merge [--batch] [--bisect-on-failure] [--dry-run]"""
    global _merge_interrupted
    _merge_interrupted = False

    state = load_state()
    if not state:
        print("Keine aktive Runde.")
        return

    agents = state["agents"]
    batch = getattr(args, "batch", False)
    bisect = getattr(args, "bisect_on_failure", False)
    dry_run = getattr(args, "dry_run", False)

    # Finde merge-bereite Agents (DONE + HEALTHY)
    mergeable = [
        a for a in agents
        if a["status"] == AgentStatus.DONE.value
        and a.get("health") in (HealthStatus.HEALTHY.value, HealthStatus.ACTIVE.value, None)
    ]

    if not mergeable:
        print("Keine merge-bereiten Agents. (Status muss DONE + HEALTHY sein)")
        print("Tipp: Setze Agent-Status manuell mit: orchestrate done <agent-id>")
        return

    print(Color.c(Color.BOLD, f"\nMerge: {len(mergeable)} Agents bereit\n"))

    if dry_run:
        print(Color.c(Color.YELLOW, "  [DRY-RUN] Keine Aenderungen werden durchgefuehrt.\n"))

    # Stufe 1: Pre-Merge Validierung
    validated: list[dict[str, Any]] = []
    for a in mergeable:
        branch = a["branch"]
        issues: list[str] = []

        if not git_branch_exists(branch):
            issues.append("Branch existiert nicht")

        changed = git_changed_files(branch)
        agent_path = a["path"].rstrip("/")
        out_of_path = [f for f in changed if not f.startswith(agent_path) and f != "shared_interfaces.py"]
        if out_of_path:
            issues.append(f"Dateien ausserhalb Pfad: {out_of_path[:3]}")

        if issues:
            print(f"  {Color.c(Color.RED, '✗')} {a['agent_id']}: {', '.join(issues)}")
            if not dry_run:
                a["status"] = AgentStatus.FAILED.value
                a["health"] = HealthStatus.VIOLATION.value
        else:
            print(f"  {Color.c(Color.GREEN, '✓')} {a['agent_id']}: Validierung bestanden")
            validated.append(a)

    if not validated:
        print(Color.c(Color.RED, "\nKeine Agents haben die Validierung bestanden."))
        if not dry_run:
            save_state(state)
        return

    if dry_run:
        print(Color.c(Color.YELLOW, f"\n  [DRY-RUN] Wuerde {len(validated)} Agents mergen."))
        return

    # Signal-Handler setzen fuer sauberen Ctrl+C
    old_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, _sigint_handler)

    try:
        # Git-Tag vor Merge
        round_num = state["round_number"]
        wave_idx = state.get("current_wave", 0)
        _tag_round(f"round-{round_num}-wave-{wave_idx}-pre-merge")

        # Stufe 2: Merge
        main_branch = git_current_branch()
        if main_branch.startswith("agent-"):
            main_branch = "main"

        if batch and len(validated) > 1:
            _batch_merge(validated, main_branch, state, bisect)
        else:
            _serial_merge(validated, main_branch, state)

        # Git-Tag nach Merge
        _tag_round(f"round-{round_num}-wave-{wave_idx}-post-merge")

    finally:
        # Signal-Handler wiederherstellen
        signal.signal(signal.SIGINT, old_handler)

    save_state(state)
    print()


def _batch_merge(
    validated: list[dict[str, Any]],
    main_branch: str,
    state: dict[str, Any],
    bisect: bool,
) -> None:
    """Batch-Merge mit Pfad-Exklusivitaets-Check."""
    print(Color.c(Color.CYAN, f"\nBatch-Merge: {len(validated)} Agents auf einmal..."))
    branches_to_merge = [a["branch"] for a in validated]

    # Pfad-Exklusivitaet nochmal pruefen (untereinander)
    all_paths: dict[str, str] = {}
    overlap = False
    for a in validated:
        p = a["path"].rstrip("/")
        if p in all_paths:
            print(Color.c(Color.RED, f"  ✗ Pfad-Ueberlappung: {p} ({all_paths[p]} vs {a['agent_id']})"))
            print("  → Fallback auf seriellen Merge")
            overlap = True
            break
        all_paths[p] = a["agent_id"]

    if overlap:
        _serial_merge(validated, main_branch, state)
        return

    git("checkout", main_branch, check=False)
    result = git("merge", *branches_to_merge, "--no-edit", check=False)

    if result.returncode != 0:
        print(Color.c(Color.RED, "  ✗ Batch-Merge fehlgeschlagen"))
        if bisect:
            print(Color.c(Color.YELLOW, "  → Starte Bisect..."))
            _bisect_merge(validated, main_branch)
        else:
            print("  Tipp: --bisect-on-failure fuer automatisches Bisecting")
            git("merge", "--abort", check=False)
    else:
        print(Color.c(Color.GREEN, f"  ✓ Batch-Merge erfolgreich: {len(validated)} Agents"))
        for a in validated:
            a["status"] = AgentStatus.MERGED.value
            state["budget_spent"] = state.get("budget_spent", 0) + a.get("estimated_cost", 0)

        _post_merge_impact(state)

        # Affected Tests
        test_paths = list({a["path"].rstrip("/") for a in validated})
        test_dirs = [f"tests/{p.split('/')[-1]}/" for p in test_paths if p]
        existing_dirs = [d for d in test_dirs if Path(d).exists()]

        if existing_dirs:
            _run_tests([*existing_dirs, "-q", "--tb=short"], label="Affected Tests")
        else:
            print(Color.c(Color.GRAY, "  (Keine passenden Test-Verzeichnisse gefunden)"))


def _serial_merge(agents: list[dict[str, Any]], main_branch: str, state: dict[str, Any]) -> None:
    """Merged Agents einzeln (Fallback oder wenige Agents)."""
    git("checkout", main_branch, check=False)
    for a in agents:
        if _merge_interrupted:
            print(Color.c(Color.YELLOW, f"\n  Merge abgebrochen (Ctrl+C). Verbleibende Agents unveraendert."))
            break

        result = git("merge", a["branch"], "--no-edit", check=False)
        if result.returncode == 0:
            print(f"  {Color.c(Color.GREEN, '✓')} {a['agent_id']} gemerged")
            a["status"] = AgentStatus.MERGED.value
            state["budget_spent"] = state.get("budget_spent", 0) + a.get("estimated_cost", 0)
        else:
            print(f"  {Color.c(Color.RED, '✗')} {a['agent_id']} Merge-Konflikt")
            git("merge", "--abort", check=False)
            a["status"] = AgentStatus.FAILED.value

    _post_merge_impact(state)


def _bisect_merge(agents: list[dict[str, Any]], main_branch: str) -> None:
    """Binary Search nach dem Agent der den Merge bricht. Nicht-destruktiv."""
    git("merge", "--abort", check=False)

    if _merge_interrupted:
        print(Color.c(Color.YELLOW, "  Bisect abgebrochen (Ctrl+C)."))
        return

    if len(agents) <= 1:
        print(f"  Bisect: {agents[0]['agent_id']} ist der Schuldige.")
        agents[0]["status"] = AgentStatus.FAILED.value
        return

    mid = len(agents) // 2
    first_half = agents[:mid]
    second_half = agents[mid:]

    # Teste erste Haelfte mit temporaerem Merge (kein reset --hard!)
    branches = [a["branch"] for a in first_half]
    git("checkout", main_branch, check=False)
    result = git("merge", *branches, "--no-edit", check=False)

    if result.returncode == 0:
        print(f"  Bisect: Erste Haelfte OK ({len(first_half)} Agents). Problem in zweiter Haelfte.")
        # Merge rueckgaengig machen ohne Datenverlust
        git("merge", "--abort", check=False)
        # Falls merge erfolgreich war, muessen wir den Merge-Commit zuruecksetzen
        # Nutze revert statt reset --hard
        git("reset", "--soft", "HEAD~1", check=False)
        git("checkout", ".", check=False)
        _bisect_merge(second_half, main_branch)
    else:
        print(f"  Bisect: Problem in erster Haelfte ({len(first_half)} Agents).")
        git("merge", "--abort", check=False)
        _bisect_merge(first_half, main_branch)


def _post_merge_impact(state: dict[str, Any]) -> None:
    """GitNexus Post-Merge Impact-Analyse. Graceful skip wenn nicht verfuegbar."""
    gn_cfg = _gitnexus_config()
    if not gn_cfg.get("post_merge_impact", True):
        return
    if not _gitnexus_available:
        logger.debug("GitNexus nicht verfuegbar — ueberspringe Post-Merge Impact.")
        return

    round_num = state.get("round_number", 1)
    wave_idx = state.get("current_wave", 0)
    base_ref = f"round-{round_num}-wave-{wave_idx}-pre-merge"

    # Pruefen ob das Pre-Merge Tag existiert
    tag_check = git("rev-parse", "--verify", base_ref, check=False)
    if tag_check.returncode != 0:
        logger.debug("Pre-Merge Tag '%s' nicht gefunden — ueberspringe Impact.", base_ref)
        return

    print(Color.c(Color.CYAN, "\n  GitNexus Post-Merge Impact:"))

    result = _run_gitnexus([
        "detect_changes",
        "--scope", "compare",
        "--base-ref", base_ref,
    ])
    if not result:
        print(Color.c(Color.GRAY, "    (GitNexus detect_changes nicht verfuegbar)"))
        return

    risk = result.get("risk_level", "unknown")
    changed_symbols = result.get("changed_symbols", [])
    affected_processes = result.get("affected_processes", [])

    # Farbe nach Risiko
    risk_colors = {"low": Color.GREEN, "medium": Color.YELLOW, "high": Color.RED, "critical": Color.RED}
    risk_color = risk_colors.get(risk, Color.GRAY)

    sym_count = len(changed_symbols)
    proc_count = len(affected_processes)
    print(f"    Risk: {Color.c(risk_color, risk)} | "
          f"{sym_count} Symbole geaendert | "
          f"{proc_count} Prozesse betroffen")

    for proc in affected_processes[:5]:
        proc_name = proc.get("name", "unbekannt")
        steps_changed = proc.get("steps_changed", 0)
        print(f"    {Color.c(Color.YELLOW, '⚠')} Betroffener Prozess: "
              f"\"{proc_name}\" ({steps_changed} Steps geaendert)")

    if risk == "critical":
        print(Color.c(Color.RED, "\n    ⚠ KRITISCHES Risiko — Full Test Suite empfohlen!"))
        print("    -> orchestrate test --full")

    # Im State speichern
    state["merge_impact"] = {
        "risk_level": risk,
        "changed_symbols_count": sym_count,
        "affected_processes_count": proc_count,
        "affected_processes": [p.get("name", "") for p in affected_processes[:10]],
    }


def cmd_next(args: argparse.Namespace) -> None:
    """orchestrate next — Naechste Wave dispatchen."""
    state = load_state()
    if not state:
        print("Keine aktive Runde.")
        return

    agents = state["agents"]
    waves = state.get("waves", [])
    current_wave_idx = state.get("current_wave", 0)

    if current_wave_idx >= len(waves) - 1:
        all_done = all(a["status"] in (AgentStatus.MERGED.value, AgentStatus.SKIPPED.value) for a in agents)
        if all_done:
            print(Color.c(Color.GREEN, "Alle Waves abgeschlossen! → orchestrate report"))
        else:
            print("Letzte Wave, aber nicht alle Agents fertig/gemerged.")
            pending = [a for a in agents if a["status"] in (AgentStatus.RUNNING.value, AgentStatus.DONE.value)]
            for a in pending:
                print(f"  {a['agent_id']}: {a['status']}")
        return

    # Pruefe: Sind required_agents der naechsten Wave gemerged?
    next_wave = waves[current_wave_idx + 1]
    required = next_wave.get("required_agents", [])

    if required:
        merged_ids = {a["agent_id"] for a in agents if a["status"] == AgentStatus.MERGED.value}
        missing = [r for r in required if r not in merged_ids]
        if missing:
            print(f"Naechste Wave ({next_wave['name']}) wartet auf required_agents:")
            for m in missing:
                matching = [a for a in agents if a["agent_id"] == m]
                st = matching[0]["status"] if matching else "UNKNOWN"
                print(f"  {m}: {st}")
            return

    # Naechste Wave starten
    current_wave_idx += 1
    state["current_wave"] = current_wave_idx
    next_wave_name = next_wave["name"]
    round_num = state["round_number"]
    prompt_dir = Path(PROMPTS_DIR) / f"round{round_num}"

    wave_agents = [a for a in agents if a["wave"] == next_wave_name]

    print(Color.c(Color.BOLD, f"\n=== {next_wave_name} ===\n"))
    for a in wave_agents:
        a["status"] = AgentStatus.RUNNING.value
        a["started_at"] = _now_iso()
        prompt_path = prompt_dir / a["file"]
        print(f"  {Color.c(Color.CYAN, '→')} {a['agent_id']}")
        print(f"    Branch: {a['branch']} | Tier: {a['tier']} | Prompt: {prompt_path}")

        # Branch erstellen OHNE Working Tree zu wechseln
        if not git_branch_exists(a["branch"]):
            _create_branch(a["branch"])

    save_state(state)
    print(Color.c(Color.GREEN, f"\n✓ {len(wave_agents)} Agents gestartet."))
    print("  Prompts in Terminals kopieren.\n")


def cmd_validate(args: argparse.Namespace) -> None:
    """orchestrate validate <prompt-dir> — Prompt-Validierung."""
    prompt_dir = Path(args.prompt_dir)
    if not prompt_dir.exists():
        print(f"Verzeichnis nicht gefunden: {prompt_dir}")
        sys.exit(1)

    prompt_files = sorted(prompt_dir.glob("*.md"))
    if not prompt_files:
        print(f"Keine .md Dateien in {prompt_dir}")
        sys.exit(1)

    print(Color.c(Color.BOLD, f"\nPrompt-Validierung: {prompt_dir}\n"))

    total_pass = 0
    total_fail = 0

    for pf in prompt_files:
        results = validate_prompt(pf)
        passed = [r for r in results if r["passed"]]
        failed = [r for r in results if not r["passed"]]
        total_pass += len(passed)
        total_fail += len(failed)

        if failed:
            print(f"  {Color.c(Color.RED, '✗')} {pf.name} ({len(passed)}/{len(results)} Checks)")
            for r in failed:
                print(f"    {Color.c(Color.RED, '✗')} {r['check']}: {r['description']}")
        else:
            print(f"  {Color.c(Color.GREEN, '✓')} {pf.name} ({len(passed)}/{len(results)} Checks)")

    # Cross-Prompt Checks
    print(Color.c(Color.CYAN, "\nCross-Prompt Checks:"))
    cross = validate_cross_prompts(prompt_files)
    for r in cross:
        if r["passed"]:
            print(f"  {Color.c(Color.GREEN, '✓')} {r['description']}")
        else:
            print(f"  {Color.c(Color.RED, '✗')} {r['description']}: {r.get('files', [])}")
            total_fail += 1

    print(f"\n{'─' * 50}")
    print(f"  Gesamt: {total_pass} PASS, {total_fail} FAIL")
    if total_fail == 0:
        print(Color.c(Color.GREEN, "  ✓ Alle Checks bestanden → orchestrate start freigegeben"))
    else:
        print(Color.c(Color.YELLOW, "  ⚠ Fixes noetig bevor Start"))
    print()


def cmd_preflight(args: argparse.Namespace) -> None:
    """orchestrate preflight [prompt-dir] — GitNexus Impact-Analyse vor Start."""
    if not _gitnexus_available:
        print(Color.c(Color.GRAY, "GitNexus nicht gefunden. Ueberspringe Impact-Analyse."))
        print("  Installiere GitNexus und fuehre 'gitnexus analyze .' aus.")
        print("  Alternativ: grep -r 'from MODULE import\\|import MODULE' src/")
        return

    prompt_dir = Path(args.prompt_dir) if args.prompt_dir else _find_prompt_dir()
    if not prompt_dir or not prompt_dir.exists():
        print(f"Prompt-Verzeichnis nicht gefunden: {prompt_dir}")
        sys.exit(1)

    gn_cfg = _gitnexus_config()
    depth = getattr(args, "depth", None) or gn_cfg.get("impact_depth", 2)

    prompt_files = sorted(prompt_dir.glob("*.md"))
    if not prompt_files:
        print(f"Keine .md Dateien in {prompt_dir}")
        return

    print(Color.c(Color.BOLD, f"\nPre-flight Impact-Analyse: {prompt_dir}\n"))

    # Schritt 1: Pfade und Agent-IDs aus Prompts extrahieren
    agent_paths: dict[str, str] = {}  # path -> agent_id
    for pf in prompt_files:
        fm_content = pf.read_text(encoding="utf-8")
        fm = _parse_frontmatter(fm_content)
        if fm:
            path = str(fm.get("exclusive_path", "")).rstrip("/")
            agent_id = fm.get("branch", pf.stem)
            if path:
                agent_paths[path] = agent_id

    if not agent_paths:
        print(Color.c(Color.YELLOW, "  Keine exclusive_path Eintraege in Prompts gefunden."))
        return

    # Schritt 2: Fuer jeden Pfad GitNexus query + impact
    warnings: list[str] = []
    for path, agent_id in agent_paths.items():
        print(f"  Analysiere {Color.c(Color.CYAN, path)} ({agent_id})...")

        # Query: Welche Execution Flows beruehren diesen Pfad?
        query_result = _run_gitnexus(["query", path])
        if not query_result:
            print(Color.c(Color.GRAY, f"    (keine GitNexus-Daten fuer {path})"))
            continue

        # Symbole an der Pfadgrenze finden
        symbols = query_result.get("symbols", [])
        boundary_symbols = [
            s for s in symbols
            if s.get("file", "").startswith(path + "/")
        ]

        for sym in boundary_symbols:
            sym_name = sym.get("name", sym.get("qualified_name", ""))
            if not sym_name:
                continue

            # Impact-Analyse: Was haengt von diesem Symbol ab?
            impact = _run_gitnexus([
                "impact", sym_name,
                "--direction", "downstream",
                "--depth", str(depth),
            ])
            if not impact:
                continue

            affected = impact.get("affected", [])
            for dep in affected:
                dep_file = dep.get("file", "")
                dep_name = dep.get("name", "")

                # Liegt die Abhaengigkeit AUSSERHALB dieses Pfads?
                if dep_file and not dep_file.startswith(path + "/"):
                    # Gehoert sie zu einem ANDEREN Agent?
                    other_agent = None
                    for other_path, other_id in agent_paths.items():
                        if other_path != path and dep_file.startswith(other_path + "/"):
                            other_agent = other_id
                            break

                    warning = f"  {Color.c(Color.YELLOW, '⚠')} {sym.get('file', '')}:{sym_name}"
                    warning += f"\n    -> wird genutzt von {dep_file}"
                    if dep_name:
                        warning += f":{dep_name}"
                    if other_agent:
                        warning += f" (Agent: {other_agent})"
                        warning += f"\n    -> Empfehlung: Pfad erweitern ODER gemeinsames Interface"
                    warnings.append(warning)

    # Schritt 3: Zusammenfassung
    separator = "─" * 60
    print(f"\n{separator}")
    if warnings:
        print(Color.c(Color.YELLOW, f"  {len(warnings)} Cross-Path Abhaengigkeit(en) gefunden:\n"))
        for w in warnings:
            print(w)
            print()
        print(Color.c(Color.YELLOW, "  Empfehlung: Pfade anpassen oder Interfaces einfuegen."))
    else:
        print(Color.c(Color.GREEN, "  -> Keine Cross-Path Abhaengigkeiten gefunden."))
    print()


def _find_prompt_dir() -> Path | None:
    """Versucht das aktuelle Prompt-Verzeichnis zu finden."""
    state = load_state()
    if state:
        round_num = state.get("round_number", 1)
        candidate = Path(PROMPTS_DIR) / f"round{round_num}"
        if candidate.exists():
            return candidate
    # Fallback: erstes Verzeichnis in prompts/
    prompts = Path(PROMPTS_DIR)
    if prompts.exists():
        dirs = sorted(d for d in prompts.iterdir() if d.is_dir())
        return dirs[0] if dirs else None
    return None


def cmd_report(args: argparse.Namespace) -> None:
    """orchestrate report — Generiert Post-Runde Report."""
    state = load_state()
    if not state:
        print("Keine aktive Runde.")
        return

    round_num = state["round_number"]
    agents = state["agents"]
    budget_cap = state["budget_cap"]
    budget_spent = state.get("budget_spent", 0)

    total = len(agents)
    merged = sum(1 for a in agents if a["status"] == AgentStatus.MERGED.value)
    failed = sum(1 for a in agents if a["status"] == AgentStatus.FAILED.value)
    skipped = sum(1 for a in agents if a["status"] == AgentStatus.SKIPPED.value)

    # Kosten nach Tier
    tier_costs: dict[str, float] = {}
    for a in agents:
        t = a.get("tier", "sonnet")
        tier_costs[t] = tier_costs.get(t, 0) + a.get("estimated_cost", 0)

    # Report generieren
    report_lines = [
        f"# Round {round_num} Report",
        f"**Datum:** {_now_iso()[:10]}",
        f"**Modus:** {state['mode']}",
        f"**Budget:** ${budget_spent:.0f} / ${budget_cap} ({budget_spent / budget_cap * 100:.0f}%)" if budget_cap else "",
        "",
        "## Agents",
        f"- Gesamt: {total}",
        f"- Gemerged: {merged}",
        f"- Failed: {failed}",
        f"- Skipped: {skipped}",
        f"- Erfolgsrate: {merged / total * 100:.0f}%" if total > 0 else "",
        "",
        "## Kosten nach Tier",
        "*(Hinweis: Heuristische Schaetzwerte — mit echten Abrechnungsdaten kalibrieren)*",
    ]
    for tier, cost in sorted(tier_costs.items()):
        report_lines.append(f"- {tier}: ${cost:.1f}")

    report_lines.extend([
        "",
        "## Agent Details",
        "| Agent | Status | Health | Tier | Retries |",
        "|-------|--------|--------|------|---------|",
    ])
    for a in agents:
        report_lines.append(
            f"| {a['agent_id'][:30]} | {a['status']} | {a.get('health', '?')} | {a['tier']} | {a['retry_count']} |"
        )

    # Health-Metriken
    health_counts: dict[str, int] = {}
    for a in agents:
        h = a.get("health", "UNKNOWN")
        health_counts[h] = health_counts.get(h, 0) + 1

    report_lines.extend([
        "",
        "## Health-Metriken",
    ])
    for h, c in sorted(health_counts.items()):
        report_lines.append(f"- {h}: {c}")

    # Failure-Analyse
    failures = [a for a in agents if a["status"] == AgentStatus.FAILED.value]
    if failures:
        report_lines.extend([
            "",
            "## Failure-Analyse",
        ])
        for a in failures:
            fc = a.get("failure_class", "?")
            report_lines.append(f"- {a['agent_id']}: Klasse {fc} ({a.get('health', '?')})")

    report_content = "\n".join(report_lines)

    # Speichern
    reports_path = Path(REPORTS_DIR)
    reports_path.mkdir(parents=True, exist_ok=True)
    report_file = reports_path / f"round{round_num:02d}.md"
    report_file.write_text(report_content, encoding="utf-8")

    # Ausgabe
    print(Color.c(Color.BOLD, f"\n=== Round {round_num} Report ===\n"))
    if total > 0:
        print(f"  Agents:     {merged}/{total} gemerged ({merged / total * 100:.0f}%)")
    print(f"  Failed:     {failed}")
    print(f"  Budget:     ${budget_spent:.0f} / ${budget_cap}")
    print(f"  Kosten/Tier: {', '.join(f'{t}: ${c:.0f}' for t, c in sorted(tier_costs.items()))}")
    print()

    if failures:
        print(Color.c(Color.YELLOW, "  Failures:"))
        for a in failures:
            print(f"    {a['agent_id']}: {a.get('health', '?')} (Klasse {a.get('failure_class', '?')})")
        print()

    print(f"  Report gespeichert: {report_file}")
    print()

    # State aktualisieren
    state["finished_at"] = _now_iso()
    save_state(state)

    print(Color.c(Color.GRAY, "  → Bitte .ai/learnings.md mit Erkenntnissen aktualisieren"))
    print(Color.c(Color.GRAY, "  → Naechste Runde: orchestrate start <round+1>\n"))


def cmd_retry(args: argparse.Namespace) -> None:
    """orchestrate retry <agent-id> [--with-context 'hint']"""
    state = load_state()
    if not state:
        print("Keine aktive Runde.")
        return

    agent_id = args.agent_id
    hint = getattr(args, "with_context", None)
    agents = state["agents"]

    target = _find_agent(agents, agent_id)

    if not target:
        print(f"Agent nicht gefunden: {agent_id}")
        print("Verfuegbare Agents:")
        for a in agents:
            print(f"  {a['agent_id']} ({a['status']})")
        return

    if target["retry_count"] >= 2:
        print(Color.c(Color.RED, f"Max Retries (2) erreicht fuer {target['agent_id']}."))
        print(f"  → orchestrate skip {target['agent_id']}")
        return

    target["retry_count"] += 1
    target["status"] = AgentStatus.RUNNING.value
    target["health"] = HealthStatus.UNKNOWN.value
    target["started_at"] = _now_iso()

    save_state(state)

    print(Color.c(Color.CYAN, f"\nRetry #{target['retry_count']} fuer {target['agent_id']}"))
    print(f"  Branch:  {target['branch']}")
    print(f"  Prompt:  prompts/round{state['round_number']}/{target['file']}")
    if hint:
        print(f"  Kontext: {hint}")
    print()
    print("  Prompt mit Fehler-Kontext in neues Terminal kopieren.")
    if hint:
        print(f"  Zusaetzlicher Hint: \"{hint}\"")
    print()


def cmd_skip(args: argparse.Namespace) -> None:
    """orchestrate skip <agent-id>"""
    state = load_state()
    if not state:
        print("Keine aktive Runde.")
        return

    agent_id = args.agent_id
    agents = state["agents"]

    target = _find_agent(agents, agent_id)

    if not target:
        print(f"Agent nicht gefunden: {agent_id}")
        return

    target["status"] = AgentStatus.SKIPPED.value
    save_state(state)

    print(Color.c(Color.YELLOW, f"\nAgent {target['agent_id']} uebersprungen."))
    print("  Task wird in naechste Wave/Runde verschoben.")

    # Pruefe Abhaengigkeiten
    waves = state.get("waves", [])
    for wave in waves:
        required = wave.get("required_agents", [])
        if target["agent_id"] in required:
            print(Color.c(Color.RED, f"  ⚠ WARNUNG: {target['agent_id']} ist required_agent fuer {wave['name']}!"))
            print(f"    Wave {wave['name']} kann nicht starten ohne diesen Agent.")
            print("    → Entweder retry oder manifest.yaml anpassen.")
    print()


def cmd_test_full(args: argparse.Namespace) -> None:
    """orchestrate test --full — Volle Test-Suite nach letzter Wave."""
    print(Color.c(Color.BOLD, "\nFull Test Suite...\n"))
    cmd = TEST_RUNNER + ["--tb=short", "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode == 0:
        print(Color.c(Color.GREEN, "✓ Full Suite bestanden → Runde clean"))
    else:
        print(Color.c(Color.RED, "✗ Full Suite fehlgeschlagen"))
        print("  → git log --oneline zeigt Wave-Grenzen")
        print("  → Bisect zwischen Waves (nicht zwischen Agents)")
    print()


# ---------------------------------------------------------------------------
# Convenience: Mark agent as done (manuell)
# ---------------------------------------------------------------------------

def cmd_done(args: argparse.Namespace) -> None:
    """Markiert einen Agent manuell als DONE (wenn er fertig ist)."""
    state = load_state()
    if not state:
        print("Keine aktive Runde.")
        return

    agent_id = args.agent_id
    target = _find_agent(state["agents"], agent_id)

    if not target:
        print(f"Agent nicht gefunden: {agent_id}")
        return

    target["status"] = AgentStatus.DONE.value
    target["finished_at"] = _now_iso()

    # Health-Check
    health = check_agent_health(target)
    target["health"] = health.value

    save_state(state)
    print(f"  {Color.c(Color.GREEN, '✓')} {target['agent_id']} → DONE ({health.value})")


# ---------------------------------------------------------------------------
# Neue Commands: reset, abort
# ---------------------------------------------------------------------------

def cmd_reset(args: argparse.Namespace) -> None:
    """orchestrate reset [--hard] — Setzt aktuelle Runde zurueck."""
    state = load_state()
    if not state:
        print("Keine aktive Runde zum Zuruecksetzen.")
        return

    round_num = state["round_number"]
    hard = getattr(args, "hard", False)

    if hard:
        # Hard Reset: State loeschen, Branches behalten (zum manuellen Aufraeuemen)
        print(Color.c(Color.YELLOW, f"\nHard-Reset Runde {round_num}:"))
        print("  State-Datei wird geloescht.")
        print("  Agent-Branches bleiben erhalten (manuell aufraeuemen bei Bedarf).")
        _state_path().unlink(missing_ok=True)
        lock_path = _state_path().with_suffix(".lock")
        lock_path.unlink(missing_ok=True)
        print(Color.c(Color.GREEN, "  ✓ State zurueckgesetzt."))
    else:
        # Soft Reset: Alle RUNNING/FAILED → PENDING, Budget reset
        print(Color.c(Color.CYAN, f"\nSoft-Reset Runde {round_num}:"))
        reset_count = 0
        for a in state["agents"]:
            if a["status"] in (AgentStatus.RUNNING.value, AgentStatus.FAILED.value):
                a["status"] = AgentStatus.PENDING.value
                a["health"] = HealthStatus.UNKNOWN.value
                a["retry_count"] = 0
                a["started_at"] = None
                a["finished_at"] = None
                reset_count += 1

        state["current_wave"] = 0
        state["budget_spent"] = 0.0
        save_state(state)
        print(f"  {reset_count} Agents zurueckgesetzt → PENDING")
        print(Color.c(Color.GREEN, "  ✓ Bereit fuer orchestrate start (gleiche Runde)."))
    print()


def cmd_abort(args: argparse.Namespace) -> None:
    """orchestrate abort — Bricht laufende Runde ab, setzt Tag."""
    state = load_state()
    if not state:
        print("Keine aktive Runde.")
        return

    round_num = state["round_number"]

    # Alle laufenden Agents stoppen
    stopped = 0
    for a in state["agents"]:
        if a["status"] == AgentStatus.RUNNING.value:
            a["status"] = AgentStatus.FAILED.value
            a["failure_class"] = FailureClass.B.value
            a["finished_at"] = _now_iso()
            stopped += 1

    state["finished_at"] = _now_iso()
    save_state(state)

    # Abort-Tag setzen
    _tag_round(f"round-{round_num}-aborted")

    print(Color.c(Color.YELLOW, f"\nRunde {round_num} abgebrochen."))
    print(f"  {stopped} laufende Agents gestoppt.")
    print(f"  Tag: round-{round_num}-aborted")
    print()
    print("  Naechste Schritte:")
    print("    orchestrate report  — Report der abgebrochenen Runde")
    print("    orchestrate reset   — State zuruecksetzen")
    print("    orchestrate start   — Neue Runde starten")
    print()


# ---------------------------------------------------------------------------
# CLI Setup
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orchestrate",
        description="AI-Orchestrated Parallel Development — CLI Tool",
    )
    sub = parser.add_subparsers(dest="command")

    # start
    p_start = sub.add_parser("start", help="Runde starten")
    p_start.add_argument("round", type=int, help="Rundennummer")
    p_start.add_argument("--mode", choices=["A", "B", "C"], default="B")
    p_start.add_argument("--budget", choices=list(BUDGET_CAPS.keys()), default="MEDIUM")
    p_start.add_argument("--force", action="store_true", help="Validierungsfehler ignorieren")

    # status
    sub.add_parser("status", help="Dashboard anzeigen")

    # health
    sub.add_parser("health", help="Health-Checks aller Agents")

    # merge
    p_merge = sub.add_parser("merge", help="Agents mergen")
    p_merge.add_argument("--batch", action="store_true", help="Batch-Merge aller fertigen Agents")
    p_merge.add_argument("--bisect-on-failure", action="store_true", help="Binary Search bei Failure")
    p_merge.add_argument("--dry-run", action="store_true", help="Nur validieren, nicht mergen")

    # next
    sub.add_parser("next", help="Naechste Wave dispatchen")

    # validate
    p_val = sub.add_parser("validate", help="Prompts validieren")
    p_val.add_argument("prompt_dir", help="Pfad zum Prompt-Verzeichnis")

    # preflight
    p_pre = sub.add_parser("preflight", help="GitNexus Impact-Analyse vor Start")
    p_pre.add_argument("prompt_dir", nargs="?", default=None, help="Pfad zum Prompt-Verzeichnis")
    p_pre.add_argument("--depth", type=int, default=2, help="Impact-Analyse Tiefe")

    # report
    sub.add_parser("report", help="Post-Runde Report generieren")

    # retry
    p_retry = sub.add_parser("retry", help="Agent re-dispatchen")
    p_retry.add_argument("agent_id", help="Agent-ID")
    p_retry.add_argument("--with-context", help="Zusaetzlicher Hint fuer Retry")

    # skip
    p_skip = sub.add_parser("skip", help="Agent ueberspringen")
    p_skip.add_argument("agent_id", help="Agent-ID")

    # test
    p_test = sub.add_parser("test", help="Tests laufen lassen")
    p_test.add_argument("--full", action="store_true", help="Volle Test-Suite")

    # done (convenience)
    p_done = sub.add_parser("done", help="Agent manuell als fertig markieren")
    p_done.add_argument("agent_id", help="Agent-ID")

    # reset
    p_reset = sub.add_parser("reset", help="Runde zuruecksetzen")
    p_reset.add_argument("--hard", action="store_true", help="State komplett loeschen")

    # abort
    sub.add_parser("abort", help="Laufende Runde abbrechen")

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Konfiguration laden
    _load_config()

    parser = build_parser()
    args = parser.parse_args()

    commands: dict[str, Any] = {
        "start": cmd_start,
        "status": cmd_status,
        "health": cmd_health,
        "merge": cmd_merge,
        "next": cmd_next,
        "validate": cmd_validate,
        "preflight": cmd_preflight,
        "report": cmd_report,
        "retry": cmd_retry,
        "skip": cmd_skip,
        "test": cmd_test_full,
        "done": cmd_done,
        "reset": cmd_reset,
        "abort": cmd_abort,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
