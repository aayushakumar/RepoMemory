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
            "bug",
            "fix",
            "error",
            "exception",
            "crash",
            "fail",
            "issue",
            "broken",
            "traceback",
            "stack trace",
            "TypeError",
            "ValueError",
            "KeyError",
            "undefined",
            "null",
            "NoneType",
            "segfault",
            "panic",
        ],
        weight_overrides={
            "lexical": 0.28,
            "semantic": 0.23,
            "path_match": 0.09,
            "symbol_match": 0.14,
            "memory_frecency": 0.09,
            "git_recency": 0.09,
            "dependency_graph": 0.08,
        },
    ),
    "trace_flow": TaskMode(
        name="trace_flow",
        description="Trace an endpoint, function, or feature through the codebase",
        keywords=[
            "trace",
            "flow",
            "route",
            "endpoint",
            "path of",
            "call chain",
            "handler",
            "middleware",
            "pipeline",
            "from.*to",
            "end to end",
            "how does.*work",
        ],
        weight_overrides={
            "lexical": 0.18,
            "semantic": 0.30,
            "path_match": 0.08,
            "symbol_match": 0.17,
            "memory_frecency": 0.08,
            "git_recency": 0.04,
            "dependency_graph": 0.15,
        },
    ),
    "test_lookup": TaskMode(
        name="test_lookup",
        description="Find the most relevant tests for a feature, bug, or function",
        keywords=[
            "test",
            "spec",
            "coverage",
            "assert",
            "mock",
            "fixture",
            "unit test",
            "integration test",
            "e2e",
        ],
        weight_overrides={
            "lexical": 0.19,
            "semantic": 0.23,
            "path_match": 0.23,
            "symbol_match": 0.18,
            "memory_frecency": 0.05,
            "git_recency": 0.05,
            "dependency_graph": 0.07,
        },
    ),
    "config_lookup": TaskMode(
        name="config_lookup",
        description="Find configuration files, environment settings, flags, or parameters",
        keywords=[
            "config",
            "setting",
            "env",
            "environment",
            "flag",
            "parameter",
            "yaml",
            "toml",
            "ini",
            "json",
            ".env",
            "variable",
            "constant",
        ],
        weight_overrides={
            "lexical": 0.23,
            "semantic": 0.18,
            "path_match": 0.28,
            "symbol_match": 0.09,
            "memory_frecency": 0.09,
            "git_recency": 0.05,
            "dependency_graph": 0.08,
        },
        extension_filters=[
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".json",
            ".env",
            ".env.example",
        ],
    ),
    "general": TaskMode(
        name="general",
        description="General code search and navigation",
        keywords=[],
        weight_overrides={
            "lexical": 0.22,
            "semantic": 0.27,
            "path_match": 0.13,
            "symbol_match": 0.13,
            "memory_frecency": 0.09,
            "git_recency": 0.05,
            "dependency_graph": 0.11,
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
        return dict(TASK_MODES[mode].weight_overrides)
    return dict(DEFAULT_WEIGHTS)
