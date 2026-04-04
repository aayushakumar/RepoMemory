"""Task router — classifies queries into task modes."""

import re
from dataclasses import dataclass, field


@dataclass
class TaskMode:
    name: str
    description: str
    keywords: list[str]
    weight_overrides: dict[str, float] = field(default_factory=dict)
    extension_filters: list[str] | None = None


TASK_MODES: dict[str, TaskMode] = {
    "bug_fix": TaskMode(
        name="bug_fix",
        description="Find likely files, symbols, tests, and configs involved in a bug",
        keywords=[
            "bug", "fix", "error", "exception", "crash", "fail", "issue", "broken",
            "traceback", "stack trace", "TypeError", "ValueError", "KeyError",
            "undefined", "null", "NoneType", "segfault", "panic",
        ],
        weight_overrides={
            "lexical": 0.30,
            "semantic": 0.25,
            "path_match": 0.10,
            "symbol_match": 0.15,
            "memory_frecency": 0.10,
            "git_recency": 0.10,
        },
    ),
    "trace_flow": TaskMode(
        name="trace_flow",
        description="Trace an endpoint, function, or feature through the codebase",
        keywords=[
            "trace", "flow", "route", "endpoint",
            "path of", "call chain", "handler", "middleware", "pipeline",
            "from.*to", "end to end", "how does.*work",
        ],
        weight_overrides={
            "lexical": 0.20,
            "semantic": 0.35,
            "path_match": 0.10,
            "symbol_match": 0.20,
            "memory_frecency": 0.10,
            "git_recency": 0.05,
        },
    ),
    "test_lookup": TaskMode(
        name="test_lookup",
        description="Find the most relevant tests for a feature, bug, or function",
        keywords=[
            "test", "spec", "coverage", "assert", "mock", "fixture",
            "unit test", "integration test", "e2e",
        ],
        weight_overrides={
            "lexical": 0.20,
            "semantic": 0.25,
            "path_match": 0.25,
            "symbol_match": 0.20,
            "memory_frecency": 0.05,
            "git_recency": 0.05,
        },
    ),
    "config_lookup": TaskMode(
        name="config_lookup",
        description="Find configuration files, environment settings, flags, or parameters",
        keywords=[
            "config", "setting", "env", "environment", "flag", "parameter",
            "yaml", "toml", "ini", "json", ".env", "variable", "constant",
        ],
        weight_overrides={
            "lexical": 0.25,
            "semantic": 0.20,
            "path_match": 0.30,
            "symbol_match": 0.10,
            "memory_frecency": 0.10,
            "git_recency": 0.05,
        },
        extension_filters=[
            ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
            ".json", ".env", ".env.example",
        ],
    ),
    "general": TaskMode(
        name="general",
        description="General code search and navigation",
        keywords=[],
        weight_overrides={
            "lexical": 0.25,
            "semantic": 0.30,
            "path_match": 0.15,
            "symbol_match": 0.15,
            "memory_frecency": 0.10,
            "git_recency": 0.05,
        },
    ),
}

DEFAULT_WEIGHTS = TASK_MODES["general"].weight_overrides


def classify_task(query: str) -> str:
    """Classify a query into a task mode. Returns mode name."""
    query_lower = query.lower()

    scores: dict[str, int] = {}
    for mode_name, mode in TASK_MODES.items():
        if mode_name == "general":
            continue
        score = 0
        for keyword in mode.keywords:
            kw = keyword.lower()
            if ".*" in kw:
                # Regex pattern keyword
                if re.search(kw, query_lower):
                    score += 2
            elif " " in kw:
                # Multi-word phrase — must appear as-is
                if kw in query_lower:
                    score += 2
            else:
                # Single word — require word boundary
                if re.search(r"\b" + re.escape(kw) + r"\b", query_lower):
                    score += 2
        scores[mode_name] = score

    if not scores or max(scores.values()) == 0:
        return "general"

    return max(scores, key=scores.get)


def get_weights(mode: str) -> dict[str, float]:
    """Get retrieval weights for a given mode."""
    if mode in TASK_MODES:
        return TASK_MODES[mode].weight_overrides
    return DEFAULT_WEIGHTS.copy()
