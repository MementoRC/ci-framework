"""Shared helpers for the meta-tests that inspect this repo's own build.

`test_yaml_lint_scope.py` (#274) and `test_workflow_lint_scope.py` (#279)
both answer the same shape of question - "does the gate named in
pyproject.toml actually cover what it claims, and does CI actually run it?"
- so they need the same three primitives: read `[tool.pixi.tasks]`, resolve
a task through its `pixi run -e <env> <impl>` indirection to the leaf
command, and scan `ci.yml`'s `run:` bodies for a task invocation.

Those primitives were duplicated in both files. They live here instead so a
fix in one is a fix in both.

These are meta-tests about the build system, so they parse `pixi` command
strings directly. If this project ever moves off pixi as its task runner,
this module is the single place that has to move with it - it will fail
loudly rather than pass vacuously, but the failure will point here rather
than at the real change.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterator
from pathlib import Path

import yaml

PYPROJECT = Path("pyproject.toml")
CI_WORKFLOW = Path(".github/workflows/ci.yml")
WORKFLOWS_DIR = Path(".github/workflows")

# Task name from `pixi run [-e/--environment <env>] <task>`. Matched against a
# single logical line: YAML block/folded scalars are already resolved by the
# parser before this regex sees anything, and `logical_run_lines` rejoins
# shell `\` continuations, so the only text reaching it is plain shell.
PIXI_RUN_TASK_RE = re.compile(
    r"pixi\s+run\s+(?:(?:-e|--environment)\s+[\w.-]+\s+)?([\w.-]+)"
)


def load_tasks() -> dict:
    """Load the [tool.pixi.tasks] table from pyproject.toml."""
    data = tomllib.loads(PYPROJECT.read_text())
    return data["tool"]["pixi"]["tasks"]


def task_cmd(task: dict | str) -> str | None:
    """Return the command string for a task, or None if it has no cmd."""
    if isinstance(task, str):
        return task
    if isinstance(task, dict):
        cmd = task.get("cmd")
        return cmd if isinstance(cmd, str) else None
    return None


def resolve_task_commands(
    tasks: dict, name: str, _seen: frozenset[str] = frozenset()
) -> list[str]:
    """Expand a pixi task into every concrete command it actually runs.

    Follows a single `pixi run -e <env> <target>` delegation transitively (the
    convention used by `yaml-lint` -> `yaml-lint-impl` and `workflow-lint` ->
    `workflow-lint-impl`), so callers see the leaf command rather than the
    one-line indirection at the top. Cycles terminate via `_seen`.
    """
    if name in _seen or name not in tasks:
        return []
    _seen = _seen | {name}
    cmd = task_cmd(tasks[name])
    if cmd is None:
        return []
    match = PIXI_RUN_TASK_RE.match(cmd.strip())
    if match is not None and match.group(1) in tasks:
        return resolve_task_commands(tasks, match.group(1), _seen)
    return [cmd]


def iter_workflow_run_bodies(doc: object) -> Iterator[str]:
    """Yield every job step's `run:` body in a parsed workflow document."""
    if not isinstance(doc, dict):
        return
    for job in (doc.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                yield step["run"]


def logical_run_lines(body: str) -> list[str]:
    """Split a `run:` body into logical lines, rejoining shell continuations.

    A trailing `\\` splits one logical command across two physical lines,
    which would otherwise hide a `pixi run <task>` invocation from a
    line-oriented regex - the very formatting #279's six-file invocation used.
    """
    return body.replace("\\\n", " ").splitlines()


def ci_invokes_task(task_name: str, workflow: Path = CI_WORKFLOW) -> bool:
    """True when some `run:` step in `workflow` runs `pixi run [-e <env>] <task>`."""
    doc = yaml.safe_load(workflow.read_text())
    for body in iter_workflow_run_bodies(doc):
        for raw_line in logical_run_lines(body):
            line = raw_line.strip()
            if "pixi run" not in line:
                continue
            match = PIXI_RUN_TASK_RE.search(line)
            if match is not None and match.group(1) == task_name:
                return True
    return False
