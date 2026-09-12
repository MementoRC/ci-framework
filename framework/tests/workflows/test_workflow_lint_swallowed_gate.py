"""Guards that a CI quality gate cannot silently discard its exit code.

Issue #278: `.github/workflows/ci.yml` ran

    pixi run -e quality typecheck || echo "Type check completed with issues"

The `|| echo` made the step exit 0 whatever mypy returned, so a type error
could not fail CI - while `pixi run quality`, which hard-depends on
`typecheck`, failed locally. CI was strictly weaker than the local gate it
is supposed to mirror, and the green check read as though it were not.

The rule lives in `framework.workflow_lint` (`swallowed-gate-exit`) rather
than in a ci.yml-specific test, so it covers every file
`discover_workflow_files` finds (#279).

These tests deliberately keep the pre-fix shape as a synthetic fixture. A
guard that only ever sees an already-clean tree passes vacuously - the #281
review found exactly that failure mode in a first-draft classifier - so
every "does not fire" case here is paired with a sample the rule MUST
reject.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from framework.workflow_lint import (
    ALL_CHECKS,
    GATE_ROOT_TASK,
    LintError,
    check_swallowed_gate_exit,
    discover_workflow_files,
    gate_tasks,
    lint_workflow,
)

RULE = "swallowed-gate-exit"
CI_WORKFLOW = Path(".github/workflows/ci.yml")
PYPROJECT = Path("pyproject.toml")

# What `pixi run quality` transitively depends on in THIS repo. Asserted
# rather than derived, so a silent change to the task graph - or a resolver
# that degrades to the empty set - fails here instead of quietly turning the
# whole rule into a no-op.
EXPECTED_GATE_TASKS = frozenset(
    {
        "quality",
        "test",
        "test-impl",
        "lint-full",
        "lint-full-impl",
        "format-check",
        "format-check-impl",
        "typecheck",
        "typecheck-impl",
    }
)

SYNTHETIC_PYPROJECT = """\
[tool.pixi.tasks]
typecheck = "pixi run -e quality typecheck-impl"
typecheck-impl = "mypy framework/"
quality = { depends-on = ["typecheck"] }
"""


def _write_repo(
    tmp_path: Path,
    run_body: str,
    *,
    step_extra: str = "",
    pyproject: str = SYNTHETIC_PYPROJECT,
) -> Path:
    """Write a minimal repo - one pyproject, one workflow - and return the workflow.

    The rule resolves its gate set by walking up from the workflow file to a
    pyproject.toml, so a fixture has to supply both to exercise it honestly.
    """
    (tmp_path / "pyproject.toml").write_text(pyproject)
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)

    body = textwrap.indent(textwrap.dedent(run_body).strip("\n"), " " * 10)
    extra = f"        {step_extra}\n" if step_extra else ""
    path = workflows / "ci.yml"
    path.write_text(
        "name: Synthetic\n"
        "on: [push]\n"
        "jobs:\n"
        "  lint-and-format:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        '      - name: "Run Type Check"\n'
        f"{extra}"
        "        run: |\n"
        f"{body}\n"
    )
    return path


def _findings(workflow: Path) -> list[LintError]:
    """Only this rule's findings - a synthetic workflow may trip other checks."""
    return [e for e in lint_workflow(workflow).errors if e.rule == RULE]


def test_rule_is_registered():
    assert check_swallowed_gate_exit in ALL_CHECKS


def test_gate_task_closure_is_not_vacuous():
    """An empty closure would make every assertion below pass for free."""
    resolved = gate_tasks(PYPROJECT.resolve())
    assert resolved, "gate closure is empty - the rule would cover nothing"
    assert GATE_ROOT_TASK in resolved
    missing = EXPECTED_GATE_TASKS - resolved
    assert not missing, f"gate closure no longer reaches: {sorted(missing)}"


def test_guard_detects_the_pre_fix_shape(tmp_path):
    """The literal ci.yml:72 line #278 was filed about."""
    workflow = _write_repo(
        tmp_path,
        """
        echo "Running type check..."
        pixi run -e quality typecheck || echo "Type check completed with issues"
        """,
    )
    findings = _findings(workflow)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.severity == "error"
    assert finding.line > 0
    assert "typecheck" in finding.message
    assert "continue-on-error" in finding.message


def test_guard_detects_a_swallow_across_a_line_continuation(tmp_path):
    """reusable-ci.yml splits exactly this way; a physical-line scan misses it."""
    workflow = _write_repo(
        tmp_path,
        """
        pixi run -e quality typecheck \\
          || echo "ignored"
        """,
    )
    assert len(_findings(workflow)) == 1


@pytest.mark.parametrize(
    "swallow",
    [
        '|| echo "x"',
        "|| true",
        "|| :",
        # Spacing is not part of the idiom: `\s*` has to accept none or many.
        '||echo "x"',
        "||true",
        "||   true",
        "||\t\ttrue",
        # A trailing `;` must not hide the swallow. `|| true;` and `|| echo;`
        # were already caught by `\b`; `||:;` needed the `:` alternative to
        # end on a negative lookahead rather than on whitespace-or-end.
        "|| true;",
        '|| echo "x";',
        "||:;",
        "|| : ;",
    ],
)
def test_guard_detects_every_swallow_form(tmp_path, swallow):
    """Spacing and trailing separators are incidental - the swallow is the point."""
    workflow = _write_repo(tmp_path, f"pixi run -e quality typecheck {swallow}")
    assert len(_findings(workflow)) == 1


def test_guard_does_not_fire_on_the_fixed_shape(tmp_path):
    workflow = _write_repo(
        tmp_path,
        """
        echo "Running type check..."
        pixi run -e quality typecheck
        """,
    )
    assert _findings(workflow) == []


@pytest.mark.parametrize(
    "run_body",
    [
        # Not `pixi run` at all.
        'pixi info || echo "Pixi info failed"',
        # `which` is not a declared task, so not a gate.
        'pixi run -e ci which pytest || echo "Pytest not found in CI environment"',
        # A bare pytest invocation, not a gate task - the benchmark steps in
        # reusable-ci.yml and standalone-ci.yml have this shape.
        "pixi run -e dev pytest tests/performance/ \\\n"
        "  --benchmark-only \\\n"
        '  || echo "No benchmark tests found or benchmarks failed"',
        # The swallow precedes the gate, so it discards nothing of the gate's.
        'echo "warming up" || true\npixi run -e quality typecheck',
        # A same-line comment that mentions the anti-pattern is not the
        # anti-pattern. This repo's run: bodies are full of such comments.
        "pixi run -e quality typecheck  # never use || true here",
        # Same, for a quoted argument that merely talks about it.
        'pixi run -e quality typecheck && echo "pass || true to skip"',
        # A commented-out swallow is not a live one.
        '# pixi run -e quality typecheck || echo "disabled"',
    ],
)
def test_guard_does_not_fire_on_non_gate_commands(tmp_path, run_body):
    assert _findings(_write_repo(tmp_path, run_body)) == []


def test_stripping_comments_does_not_blind_the_guard(tmp_path):
    """`#` mid-word is not a comment, so a swallow after it is still caught."""
    workflow = _write_repo(
        tmp_path,
        'pixi run -e quality typecheck --tag=v1#rc || echo "ignored"',
    )
    assert len(_findings(workflow)) == 1


def test_continue_on_error_is_the_sanctioned_advisory_form(tmp_path):
    """Explicit and visible in the job summary, unlike a shell-level swallow."""
    workflow = _write_repo(
        tmp_path,
        "pixi run -e quality typecheck",
        step_extra="continue-on-error: true",
    )
    assert _findings(workflow) == []


def test_rule_is_silent_for_a_repo_without_a_quality_gate(tmp_path):
    """A consumer with a different task layout gets no findings, not false ones."""
    workflow = _write_repo(
        tmp_path,
        'pixi run -e quality typecheck || echo "ignored"',
        pyproject='[tool.pixi.tasks]\ntypecheck = "mypy ."\n',
    )
    assert gate_tasks((tmp_path / "pyproject.toml").resolve()) == frozenset()
    assert _findings(workflow) == []


def test_ci_type_check_step_propagates_mypy_exit_code():
    """The #278 regression guard, asserted against the real ci.yml."""
    doc = yaml.safe_load(CI_WORKFLOW.read_text())
    steps = [
        step
        for job in doc["jobs"].values()
        for step in (job.get("steps") or [])
        if isinstance(step, dict) and step.get("name") == "Run Type Check"
    ]
    assert len(steps) == 1
    step = steps[0]
    assert step.get("continue-on-error") is not True

    # Comments in this step mention `|| echo` by name, so judge the commands.
    commands = [
        line.strip()
        for line in step["run"].replace("\\\n", " ").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert "pixi run -e quality typecheck" in commands
    assert not any("||" in line for line in commands)


def test_no_shipped_workflow_swallows_a_gate_exit():
    workflows = discover_workflow_files()
    assert workflows, "no workflows discovered - this guard would pass vacuously"
    offenders = [
        str(error)
        for workflow in workflows
        for error in lint_workflow(workflow).errors
        if error.rule == RULE
    ]
    assert offenders == []
