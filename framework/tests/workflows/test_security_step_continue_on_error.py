"""Guard: no security-relevant step in ci.yml swallows its own failure.

Issue #288: the "Run detect-secrets" step in the `security-scan` job carried
`continue-on-error: true` on top of a task that was already broken (its
`--exclude-files` arguments were shell globs, not regexes, so `detect-secrets
scan` raised `re.error` on every invocation and never actually completed a
scan). `continue-on-error: true` hid that: the step turned red in the logs
but green in the job result, so nothing failed CI and nothing forced a fix.

This guard generalizes the lesson rather than re-encoding the single step
name or line number #288 was found at (the #255-shaped failure mode every
other guard in this directory exists to avoid): it walks every job/step in
ci.yml, classifies each step as security-relevant by *what it actually runs*
- a `pixi run` invocation that resolves to a known secret/vulnerability/SAST
tool, or a `uses:` referencing a known security Action - and asserts none of
them carry `continue-on-error: true`. A step swallowing a security finding is
exactly the shape of bug #288 was.

The pixi-manifest and ci.yml parsing primitives live in
`framework/tests/utils/pixi_meta.py`, shared with `test_yaml_lint_scope.py`
and `test_workflow_lint_scope.py`.

`_KNOWN_UNFIXED` below is a DOCUMENTED, tracked exception to the rule above:
the pip-audit and Bandit steps in `security-scan` still carry
`continue-on-error: true` because, unlike the detect-secrets step #288 fixed,
they each fail for a real, pre-existing reason today (bandit: one High B602
finding at `framework/actions/quality_gates.py:250`; pip-audit: transitive
CVEs in current dependencies) and un-exempting them without fixing those
findings would just break CI. This is a hole, not a design choice - tracked
by issue #301. Closing #301 means fixing those findings and deleting the
`_KNOWN_UNFIXED` entries, not widening them.
"""

from __future__ import annotations

import yaml

from framework.tests.utils.pixi_meta import (
    CI_WORKFLOW,
    PIXI_RUN_TASK_RE,
    load_tasks,
    logical_run_lines,
    resolve_task_commands,
)

# `uses:` references that are themselves security tooling, matched by
# substring so a version pin (`@v4`, `@vX.Y.Z`) never breaks the match.
SECURITY_ACTION_MARKERS = (
    "codeql-action",
    "trufflehog",
    "gitleaks",
    "semgrep",
    "dependency-review-action",
)

# Substrings of a *resolved* pixi task command that mark it as invoking a
# secret/vulnerability/SAST scanner. Matched against the leaf command (after
# following the `pixi run -e <env> <impl>` indirection), not the task name,
# so a task rename can't accidentally opt a step out of this guard.
SECURITY_TOOL_MARKERS = (
    "bandit",
    "pip-audit",
    "detect-secrets",
    "safety",
    "trufflehog",
    "gitleaks",
    "semgrep",
)

# `job::step` identifiers exempted from `test_no_security_step_swallows_its_own_failure`.
# This is a DOCUMENTED hole, not a silent one: both steps carry
# `continue-on-error: true` today because the tool each invokes reports a
# real, pre-existing finding (bandit: one High B602 at
# framework/actions/quality_gates.py:250; pip-audit: transitive CVEs in
# current dependencies), and simply removing `continue-on-error: true` would
# break CI without fixing anything. Tracked by issue #301. Every entry here
# requires a tracked issue - do not add one to silence a new finding without
# opening one. Closing #301 means fixing the underlying findings and deleting
# these two entries, not adding to them.
_KNOWN_UNFIXED: set[str] = {
    "security-scan::Run pip-audit (dependency vulnerabilities)",
    "security-scan::Run Bandit (static analysis)",
}


def invoked_task_names(run_body: str) -> list[str]:
    """Every pixi task name a `run:` body invokes, across all its lines.

    Unlike `pixi_meta.ci_invokes_task` (which only needs to know whether one
    specific task is present), this collects every invocation in the body so
    a step running several `pixi run ...` commands is fully classified.
    """
    names = []
    for raw_line in logical_run_lines(run_body):
        line = raw_line.strip()
        if "pixi run" not in line:
            continue
        match = PIXI_RUN_TASK_RE.search(line)
        if match is not None:
            names.append(match.group(1))
    return names


def is_security_relevant_step(step: dict, tasks: dict) -> bool:
    """True when `step` invokes a known secret/vulnerability/SAST scanner.

    Two independent ways a step can qualify:
      - `uses:` names a security Action directly (e.g. CodeQL).
      - `run:` invokes a `pixi run` task whose resolved leaf command contains
        a known scanner binary/task name.
    """
    uses = step.get("uses")
    if isinstance(uses, str) and any(
        marker in uses.lower() for marker in SECURITY_ACTION_MARKERS
    ):
        return True

    run = step.get("run")
    if isinstance(run, str):
        for name in invoked_task_names(run):
            for cmd in resolve_task_commands(tasks, name):
                if any(marker in cmd.lower() for marker in SECURITY_TOOL_MARKERS):
                    return True
    return False


def discover_security_steps(doc: object, tasks: dict) -> list[tuple[str, str, dict]]:
    """Walk every job/step in a parsed workflow doc, returning the security-relevant ones.

    Returns `(job_name, step_name, step)` triples rather than just the step,
    so a failure message can name where a violation lives without the walk
    itself depending on any particular job/step name.
    """
    if not isinstance(doc, dict):
        return []
    found: list[tuple[str, str, dict]] = []
    for job_name, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        for index, step in enumerate(job.get("steps") or []):
            if not isinstance(step, dict):
                continue
            if is_security_relevant_step(step, tasks):
                step_name = step.get("name", f"<step {index}>")
                found.append((job_name, step_name, step))
    return found


def test_security_step_discovery_is_not_vacuous():
    """Non-vacuity guard: an empty discovery would pass the real check for free."""
    tasks = load_tasks()
    doc = yaml.safe_load(CI_WORKFLOW.read_text())
    discovered = discover_security_steps(doc, tasks)
    assert discovered, (
        "no security-relevant steps discovered in ci.yml - the walk or the "
        "classifier is broken, not the workflow"
    )


def test_no_security_step_swallows_its_own_failure():
    """No security-relevant step may carry `continue-on-error: true`.

    Skips the `_KNOWN_UNFIXED` entries (tracked by #301) but must still fail
    on any non-exempted step, so a new step slipping in with
    `continue-on-error: true` is caught even though the two documented holes
    are not.

    Collects every violation before asserting once, rather than asserting
    inside the loop, so a failure names every offending step in one run
    instead of the first one masking the rest.
    """
    tasks = load_tasks()
    doc = yaml.safe_load(CI_WORKFLOW.read_text())
    violations = [
        f"{job_name}::{step_name}"
        for job_name, step_name, step in discover_security_steps(doc, tasks)
        if step.get("continue-on-error") is True
        and f"{job_name}::{step_name}" not in _KNOWN_UNFIXED
    ]
    assert not violations, (
        "these security-relevant steps in ci.yml carry `continue-on-error: "
        "true`, which lets a real finding pass the job (and therefore CI) "
        f"silently: {'; '.join(violations)}"
    )


def test_known_unfixed_exemptions_are_not_stale():
    """`_KNOWN_UNFIXED` must name real, currently-exempt steps - nothing else.

    Guards the exemption list itself against going stale in either
    direction: if a step is renamed, removed, or has its
    `continue-on-error: true` removed (i.e. #301 gets fixed), the matching
    entry must be deleted from `_KNOWN_UNFIXED` rather than left to linger
    and silently over-broaden the exemption for whatever moves into its
    place.
    """
    tasks = load_tasks()
    doc = yaml.safe_load(CI_WORKFLOW.read_text())
    discovered = {
        f"{job_name}::{step_name}": step
        for job_name, step_name, step in discover_security_steps(doc, tasks)
    }

    stale = [
        identifier
        for identifier in _KNOWN_UNFIXED
        if identifier not in discovered
        or discovered[identifier].get("continue-on-error") is not True
    ]
    assert not stale, (
        "_KNOWN_UNFIXED names steps that no longer exist, are no longer "
        "security-relevant, or no longer carry `continue-on-error: true` - "
        f"delete these stale entries (issue #301 may already be fixed): {stale}"
    )


def test_classifier_flags_a_synthetic_continue_on_error_step():
    """Self-test: prove the classifier and violation-collection actually fire.

    Builds a minimal synthetic workflow doc with one job/step that is
    security-relevant (invokes the real `security-scan` pixi task, which
    resolves to a `bandit` command) and carries `continue-on-error: true`,
    independent of anything in the real ci.yml. If this fails, the two tests
    above are not proving anything.
    """
    tasks = load_tasks()
    synthetic_doc = yaml.safe_load(
        """
        jobs:
          fake-security-job:
            steps:
              - name: "Run Bandit (synthetic)"
                run: pixi run -e quality-extended security-scan
                continue-on-error: true
        """
    )

    discovered = discover_security_steps(synthetic_doc, tasks)
    assert discovered, (
        "classifier failed to flag the synthetic security-relevant step - "
        "self-test cannot validate the real guard"
    )

    violations = [
        f"{job_name}::{step_name}"
        for job_name, step_name, step in discovered
        if step.get("continue-on-error") is True
    ]
    assert violations, (
        "violation-collection failed to flag the synthetic "
        "`continue-on-error: true` step - self-test cannot validate the "
        "real guard"
    )
