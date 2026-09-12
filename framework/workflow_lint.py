"""Custom workflow linter for GitHub Actions anti-patterns.

Catches issues that actionlint misses:
- Double ${{ }} wrapping in job-level if: conditions
- Cross-repo checkout steps without error handling
- Undeclared workflow_call inputs referenced in jobs
- Hardcoded versions that should be parameterized
- dependency-review-action without event guard
- Gate tasks whose exit code is swallowed by `|| echo` / `|| true`
"""

from __future__ import annotations

import functools
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

GATE_ROOT_TASK = "quality"

# `pixi run [-e/--environment <env>] <task>` - same shape as the regex in
# framework/tests/utils/pixi_meta.py, kept separate because the linter must
# not import from the test tree.
_PIXI_RUN_TASK_RE = re.compile(
    r"pixi\s+run\s+(?:(?:-e|--environment)\s+[\w.-]+\s+)?([\w.-]+)"
)

# `|| echo ...`, `|| true`, `|| :` - the three ways a shell line discards a
# non-zero exit without saying so anywhere a reviewer can see it. `\s*`
# accepts `||true` and `||   true` alike. Each alternative ends on a
# word-boundary-ish assertion rather than requiring whitespace, so a
# trailing `;` does not hide the swallow: `||:;` is caught, as `|| true;`
# and `|| echo;` already were via `\b`.
_SWALLOW_RE = re.compile(r"\|\|\s*(?:echo\b|true\b|:(?![\w.-]))")

# A single- or double-quoted shell argument, and a `#` comment introduced at
# a word boundary.
_QUOTED_SPAN_RE = re.compile(r"'[^']*'|\"[^\"]*\"")
_TRAILING_COMMENT_RE = re.compile(r"(?:^|\s)#")


@dataclass
class LintError:
    file: str
    line: int
    rule: str
    message: str
    severity: str = "error"

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: [{self.severity}] {self.rule}: {self.message}"


@dataclass
class LintResult:
    errors: list[LintError] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(e.severity == "error" for e in self.errors)

    @property
    def error_count(self) -> int:
        return sum(1 for e in self.errors if e.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for e in self.errors if e.severity == "warning")


def _find_line_number(raw_lines: list[str], pattern: str, start: int = 0) -> int:
    """Find line number (1-indexed) containing pattern."""
    for i, line in enumerate(raw_lines[start:], start=start):
        if pattern in line:
            return i + 1
    return 0


def _find_line_number_re(raw_lines: list[str], regex: str, start: int = 0) -> int:
    """Find line number (1-indexed) matching regex."""
    compiled = re.compile(regex)
    for i, line in enumerate(raw_lines[start:], start=start):
        if compiled.search(line):
            return i + 1
    return 0


def _logical_run_lines(body: str) -> list[str]:
    """Split a `run:` body into logical (shell-continuation-joined) lines.

    reusable-ci.yml puts the `||` swallow on a different physical line from
    the `pixi run` invocation whose exit code it discards, so a physical-line
    scan would miss exactly the case this rule exists to catch (#278).
    """
    return body.replace("\\\n", " ").splitlines()


def _strip_shell_noise(line: str) -> str:
    """Blank quoted arguments and any trailing `#` comment before matching.

    Without this, a step that merely *mentions* the anti-pattern would be
    reported as committing it - `echo "pass || true to skip"`, or one of the
    explanatory comments this repo's house style puts inside `run:` bodies.
    ci.yml's own "Run Type Check" step now carries a comment quoting
    `|| echo`, and is safe today only because that comment happens to sit on
    a different line from the invocation.

    A real `|| echo "..."` still matches: only the quoted argument is
    blanked, not the `echo` token that precedes it.

    `#` opens a comment only at a word boundary, so `foo#bar` - not a shell
    comment - survives. A swallow hidden after a literal `#` in an unquoted
    URL would be missed, but that is a false negative in a shape that does
    not occur, and it is the safer direction to err for a rule whose job is
    to fail CI.
    """
    line = _QUOTED_SPAN_RE.sub(" ", line)
    comment = _TRAILING_COMMENT_RE.search(line)
    return line[: comment.start()] if comment else line


def _find_pyproject(start: Path) -> Path | None:
    """Walk `start.resolve()` and its parents looking for a pyproject.toml."""
    current = start.resolve()
    for directory in (current, *current.parents):
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


@functools.lru_cache
def gate_tasks(pyproject: Path) -> frozenset[str]:
    """Transitive closure of pixi tasks that `pixi run quality` depends on.

    Returns `frozenset()` on any failure to read/parse the file, or if
    `GATE_ROOT_TASK` is not declared, so a consumer repo without this task
    layout gets no findings from `check_swallowed_gate_exit` rather than
    spurious ones. Follows both a task's `depends-on` list and a single
    `pixi run [-e <env>] <target>` delegation (the `typecheck ->
    typecheck-impl` convention used throughout pyproject.toml).
    """
    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return frozenset()

    tasks = data.get("tool", {}).get("pixi", {}).get("tasks", {})
    if not isinstance(tasks, dict) or GATE_ROOT_TASK not in tasks:
        return frozenset()

    seen: set[str] = set()
    stack = [GATE_ROOT_TASK]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        entry = tasks.get(name)
        if entry is None:
            continue
        seen.add(name)

        cmd: str | None
        if isinstance(entry, str):
            cmd = entry
            depends_on = []
        elif isinstance(entry, dict):
            cmd = entry.get("cmd")
            depends_on = entry.get("depends-on", [])
        else:
            continue

        if isinstance(depends_on, list):
            for dep in depends_on:
                if isinstance(dep, str):
                    stack.append(dep)
                elif isinstance(dep, dict) and isinstance(dep.get("task"), str):
                    stack.append(dep["task"])

        if isinstance(cmd, str):
            delegate = _PIXI_RUN_TASK_RE.match(cmd.strip())
            if delegate and delegate.group(1) in tasks:
                stack.append(delegate.group(1))

    return frozenset(seen)


def check_double_expression_wrap(
    filepath: str, raw_lines: list[str], workflow: dict
) -> list[LintError]:
    """Detect double ${{ }} wrapping in job-level if: conditions.

    Job-level if: already implicitly wraps in ${{ }}, so explicit wrapping
    causes the expression to be evaluated as a string literal first, producing
    unexpected behavior or startup_failure.
    """
    errors = []
    jobs = workflow.get("jobs", {})
    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue
        job_if = job_config.get("if")
        if job_if and isinstance(job_if, str):
            # Check for explicit ${{ }} in job-level if
            if "${{" in job_if and "}}" in job_if:
                line = _find_line_number(raw_lines, "if:")
                # Search more precisely near the job definition
                job_line = _find_line_number(raw_lines, f"  {job_name}:")
                if job_line:
                    line = _find_line_number(raw_lines, "if:", start=job_line - 1)
                errors.append(
                    LintError(
                        file=filepath,
                        line=line,
                        rule="double-expression-wrap",
                        message=(
                            f"Job '{job_name}' has explicit ${{{{ }}}} in if: condition. "
                            "Job-level if: already implicitly wraps expressions. "
                            "This can cause startup_failure."
                        ),
                    )
                )
    return errors


def check_cross_repo_checkout(
    filepath: str, raw_lines: list[str], workflow: dict
) -> list[LintError]:
    """Detect cross-repo checkout steps that add fragile external dependencies.

    In reusable workflows called remotely, cross-repo checkouts add failure
    modes: permission issues, network failures, missing paths. Prefer
    self-contained steps using pixi/pip.
    """
    errors = []
    jobs = workflow.get("jobs", {})
    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue
        steps = job_config.get("steps", [])
        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses", "")
            with_config = step.get("with", {})
            if "actions/checkout" in uses and isinstance(with_config, dict):
                repo = with_config.get("repository", "")
                if repo and repo != "${{ github.repository }}":
                    step_name = step.get("name", uses)
                    line = _find_line_number(raw_lines, f"repository: {repo}")
                    errors.append(
                        LintError(
                            file=filepath,
                            line=line,
                            rule="cross-repo-checkout",
                            message=(
                                f"Job '{job_name}' checks out external repo '{repo}' "
                                f"in step '{step_name}'. This adds a fragile runtime "
                                "dependency. Prefer self-contained pixi/pip commands."
                            ),
                            severity="warning",
                        )
                    )
    return errors


def check_dependency_review_guard(
    filepath: str, raw_lines: list[str], workflow: dict
) -> list[LintError]:
    """Detect dependency-review-action without pull_request event guard.

    dependency-review-action only works on pull_request, pull_request_target,
    or merge_group events. Running it on push causes failures.
    """
    errors = []
    jobs = workflow.get("jobs", {})
    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue
        steps = job_config.get("steps", [])
        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses", "")
            if "dependency-review-action" in uses:
                step_if = step.get("if", "")
                if not step_if or "pull_request" not in str(step_if):
                    step_name = step.get("name", uses)
                    line = _find_line_number(raw_lines, "dependency-review-action")
                    errors.append(
                        LintError(
                            file=filepath,
                            line=line,
                            rule="dependency-review-unguarded",
                            message=(
                                f"Job '{job_name}' uses dependency-review-action "
                                f"in step '{step_name}' without a pull_request event "
                                "guard. This action only works on PR events and will "
                                "fail on push."
                            ),
                        )
                    )
    return errors


def check_undeclared_inputs(
    filepath: str, raw_lines: list[str], workflow: dict
) -> list[LintError]:
    """Detect references to undeclared workflow_call inputs."""
    errors: list[LintError] = []
    trigger = workflow.get("on", workflow.get(True, {}))
    if not isinstance(trigger, dict):
        return errors

    # `workflow_dispatch` inputs are addressed through the same `inputs.`
    # context (and through `github.event.inputs.`), so a workflow declaring
    # them only under `workflow_dispatch:` is not referencing anything
    # undeclared. Consulting `workflow_call` alone reported
    # cleanup-dev-files.yml's legitimate `github.event.inputs.target_branch`
    # as an error the moment #279 widened this linter's scope.
    declared_inputs: set[str] = set()
    declares_any = False
    for trigger_name in ("workflow_call", "workflow_dispatch"):
        trigger_config = trigger.get(trigger_name)
        if not isinstance(trigger_config, dict):
            continue
        inputs_config = trigger_config.get("inputs")
        if isinstance(inputs_config, dict):
            declared_inputs |= set(inputs_config.keys())
            declares_any = True

    if not declares_any:
        return errors

    # Find all inputs.* references in the raw text
    input_refs = re.findall(r"inputs\.([a-zA-Z0-9_-]+)", "\n".join(raw_lines))
    for ref in set(input_refs):
        if ref not in declared_inputs:
            # Anchored on a non-name character so a report for
            # `inputs.target_branch` does not point at the line holding
            # `inputs.target_branches`.
            line = _find_line_number_re(
                raw_lines, rf"inputs\.{re.escape(ref)}(?![\w-])"
            )
            errors.append(
                LintError(
                    file=filepath,
                    line=line,
                    rule="undeclared-input",
                    message=(
                        f"Reference to undeclared input 'inputs.{ref}'. "
                        f"Declared inputs: {sorted(declared_inputs)}"
                    ),
                )
            )

    return errors


def check_hardcoded_versions(
    filepath: str, raw_lines: list[str], workflow: dict
) -> list[LintError]:
    """Detect hardcoded pixi versions that should use a single source of truth."""
    errors = []
    # Count pixi-version occurrences
    version_lines = []
    for i, line in enumerate(raw_lines):
        if "pixi-version:" in line and "#" not in line.split("pixi-version:")[0]:
            version_lines.append((i + 1, line.strip()))

    if len(version_lines) > 1:
        versions = set()
        for _, line in version_lines:
            match = re.search(r"pixi-version:\s*(\S+)", line)
            if match:
                versions.add(match.group(1))

        if len(versions) > 1:
            errors.append(
                LintError(
                    file=filepath,
                    line=version_lines[0][0],
                    rule="inconsistent-versions",
                    message=(
                        f"Multiple pixi versions found: {versions}. "
                        "Use a single source of truth (env var or input)."
                    ),
                )
            )

    return errors


def check_summary_needs_completeness(
    filepath: str, raw_lines: list[str], workflow: dict
) -> list[LintError]:
    """Check that the summary job's needs: lists all other jobs."""
    errors: list[LintError] = []
    jobs = workflow.get("jobs", {})
    if "summary" not in jobs:
        return errors

    summary_job = jobs["summary"]
    summary_needs = summary_job.get("needs", [])
    if isinstance(summary_needs, str):
        summary_needs = [summary_needs]

    # Exclude upstream-only jobs that are transitively covered
    upstream_only = {"detect-changes", "configure"}
    all_jobs = set(jobs.keys()) - {"summary"} - upstream_only
    missing = all_jobs - set(summary_needs)

    if missing:
        line = _find_line_number(raw_lines, "summary:")
        errors.append(
            LintError(
                file=filepath,
                line=line,
                rule="summary-missing-needs",
                message=(
                    f"Summary job is missing these jobs in needs: {sorted(missing)}. "
                    "It won't wait for them to complete."
                ),
                severity="warning",
            )
        )

    return errors


def check_swallowed_gate_exit(
    filepath: str, raw_lines: list[str], workflow: dict
) -> list[LintError]:
    """Detect a quality-gate task whose exit code is swallowed by `|| echo`/`|| true`.

    `pixi run -e quality typecheck || echo "..."` always exits 0, so a mypy
    failure could not fail this CI step even though `pixi run quality` --
    which hard-depends on `typecheck` -- fails locally (#278). CI ends up
    strictly weaker than the local gate it is supposed to mirror.

    `continue-on-error: true` is the sanctioned way to make a step advisory:
    it is visible in the workflow file and flagged in the job summary. A
    shell-level `|| echo`/`|| true`/`|| :` swallow is invisible unless a
    reviewer reads the embedded shell script.
    """
    errors: list[LintError] = []
    pyproject = _find_pyproject(Path(filepath))
    if pyproject is None:
        return errors
    tasks = gate_tasks(pyproject)
    if not tasks:
        return errors

    jobs = workflow.get("jobs", {})
    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue
        steps = job_config.get("steps", [])
        for step in steps:
            if not isinstance(step, dict):
                continue
            run_body = step.get("run")
            if not isinstance(run_body, str):
                continue
            step_name = step.get("name", "<unnamed>")
            reported: set[str] = set()

            for raw_logical_line in _logical_run_lines(run_body):
                logical_line = _strip_shell_noise(raw_logical_line)
                swallow_matches = list(_SWALLOW_RE.finditer(logical_line))
                for pixi_match in _PIXI_RUN_TASK_RE.finditer(logical_line):
                    task = pixi_match.group(1)
                    if task not in tasks or task in reported:
                        continue
                    swallow_match = next(
                        (m for m in swallow_matches if m.start() > pixi_match.end()),
                        None,
                    )
                    if swallow_match is None:
                        continue
                    reported.add(task)
                    swallowed_text = swallow_match.group(0).strip()
                    line = _find_line_number_re(
                        raw_lines,
                        rf"pixi\s+run\s+(?:(?:-e|--environment)\s+[\w.-]+\s+)?"
                        rf"{re.escape(task)}(?![\w.-])",
                    )
                    errors.append(
                        LintError(
                            file=filepath,
                            line=line,
                            rule="swallowed-gate-exit",
                            message=(
                                f"Job '{job_name}' step '{step_name}' runs gate task "
                                f"'{task}' but discards its "
                                f"exit code with '{swallowed_text}'. The step can "
                                "never fail, so this gate cannot "
                                f"fail CI while 'pixi run {GATE_ROOT_TASK}' fails "
                                "locally. Delete the swallow, or "
                                "set 'continue-on-error: true' on the step if it is "
                                "genuinely advisory."
                            ),
                        )
                    )

    return errors


ALL_CHECKS = [
    check_double_expression_wrap,
    check_cross_repo_checkout,
    check_dependency_review_guard,
    check_undeclared_inputs,
    check_hardcoded_versions,
    check_summary_needs_completeness,
    check_swallowed_gate_exit,
]


def lint_workflow(filepath: str | Path) -> LintResult:
    """Run all lint checks on a workflow file."""
    filepath = Path(filepath)
    result = LintResult()

    raw_text = filepath.read_text()
    raw_lines = raw_text.splitlines()

    try:
        workflow = yaml.safe_load(raw_text)
    except yaml.YAMLError as e:
        result.errors.append(
            LintError(
                file=str(filepath),
                line=0,
                rule="yaml-parse-error",
                message=f"Failed to parse YAML: {e}",
            )
        )
        return result

    if not isinstance(workflow, dict):
        return result

    for check in ALL_CHECKS:
        result.errors.extend(check(str(filepath), raw_lines, workflow))

    return result


def discover_workflow_files(
    workflow_dir: str | Path = ".github/workflows",
) -> list[Path]:
    """Every workflow file in `workflow_dir`, discovered rather than listed.

    Both suffixes: GitHub accepts `.yml` and `.yaml`. Exposed separately from
    `lint_all_workflows` so a test can assert the discovered set covers the
    whole directory (#279) — the hand-maintained six-file list this replaced
    covered 6 of 18 files and nothing noticed.
    """
    workflow_dir = Path(workflow_dir)
    return sorted(set(workflow_dir.glob("*.yml")) | set(workflow_dir.glob("*.yaml")))


def lint_all_workflows(workflow_dir: str | Path = ".github/workflows") -> LintResult:
    """Run all lint checks on all workflow files in a directory."""
    combined = LintResult()

    for workflow_file in discover_workflow_files(workflow_dir):
        file_result = lint_workflow(workflow_file)
        combined.errors.extend(file_result.errors)

    return combined


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Custom GitHub Actions workflow linter"
    )
    parser.add_argument(
        "files",
        nargs="*",
        default=[],
        help="Workflow files to lint (default: all in .github/workflows/)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    args = parser.parse_args()

    if args.files:
        result = LintResult()
        for f in args.files:
            file_result = lint_workflow(f)
            result.errors.extend(file_result.errors)
    else:
        result = lint_all_workflows()

    for error in result.errors:
        print(error)

    errors = result.error_count
    warnings = result.warning_count

    if args.strict:
        total = errors + warnings
    else:
        total = errors

    if total > 0:
        print(f"\n{errors} error(s), {warnings} warning(s)")
        return 1
    elif warnings > 0:
        print(f"\n0 errors, {warnings} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
