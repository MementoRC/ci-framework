"""Guards for the composite-action shellcheck gate (#261).

`actionlint` has no composite-action support and `yaml-lint` was scoped to
`.github/workflows/` by its own command, so the bash embedded in nine
`action.yml` files was checked by nothing at all. These tests guard the gate
that closed that hole - principally that its discovery cannot quietly narrow
to a subset, which is how #255's hand-maintained workflow list went stale
without anyone noticing.

They also pin the expression-neutralisation rules. Both naive substitutions
fabricate findings: a literal makes shellcheck evaluate a constant the runner
never produces (SC2050/SC2157), and a bare `$NAME` merges with a following
identifier character into a different variable (SC2034/SC2154). A fabricated
finding names the placeholder rather than anything in the source.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from framework.action_shellcheck import (
    SHELLCHECK_SHELLS,
    RunStep,
    discover_action_files,
    iter_run_steps,
    neutralize_expressions,
    shellcheck_step,
)


# These tests shell out to shellcheck, so they are only meaningful against the
# binary pixi pins. GitHub-hosted runners ship their own shellcheck on PATH
# (see the shellcheck dependency comment in pyproject.toml), and that build
# behaves differently: in CI it emitted no output at all for every input, so
# every "must not find" assertion passed vacuously while the two that require
# a finding failed. Running against whatever happens to be on PATH therefore
# produces both false failures and, worse, false passes.
#
# Enforcement is not weakened by skipping here: ci.yml's `action-shellcheck`
# step runs the gate over every action in the `dev` env, with this pinned
# binary. These tests are a second opinion on that same code.
def _pinned_shellcheck() -> str | None:
    """The shellcheck inside the active pixi environment, if there is one."""
    found = shutil.which("shellcheck")
    if found is None:
        return None
    prefix = os.environ.get("CONDA_PREFIX")
    if prefix and Path(found).is_relative_to(Path(prefix)):
        return found
    return None


requires_shellcheck = pytest.mark.skipif(
    _pinned_shellcheck() is None,
    reason="no pixi-pinned shellcheck in this environment (a PATH binary from "
    "the runner is a different build and is deliberately not used)",
)


def _all_action_files_on_disk() -> list[Path]:
    """Independent discovery that deliberately does not reuse the module's."""
    found: set[Path] = set()
    for root in (Path("actions"), Path(".github/actions")):
        if root.is_dir():
            found.update(root.rglob("action.yml"))
            found.update(root.rglob("action.yaml"))
    return sorted(found)


def _step(tmp_path: Path, body: str) -> RunStep:
    """A RunStep whose file contains exactly the body, so offsets are trivial."""
    path = tmp_path / "action.yml"
    path.write_text(body)
    return RunStep(path=path, step_name="test", shell="bash", body=body, start_line=1)


class TestDiscoveryCannotNarrow:
    """The gate must cover every action on disk, found by walking - never a list."""

    def test_action_files_were_actually_found(self):
        """Vacuity guard: discovering nothing would make the others pass free."""
        assert _all_action_files_on_disk(), (
            "no action definitions found on disk - run tests from the repo root"
        )

    def test_discovery_matches_disk_exactly(self):
        """Every action.yml on disk is discovered: no subset, no exclusions."""
        assert discover_action_files() == _all_action_files_on_disk()

    def test_discovery_covers_both_action_trees(self):
        """`actions/` and `.github/actions/` must both be in scope."""
        roots = {path.parts[0] for path in discover_action_files()}
        assert "actions" in roots, f"actions/ not covered, roots={roots}"
        assert ".github" in roots, f".github/actions/ not covered, roots={roots}"

    def test_run_bodies_were_actually_found(self):
        """Vacuity guard: extracting no bodies would make the gate hollow."""
        steps = [
            step for path in discover_action_files() for step in iter_run_steps(path)
        ]
        assert steps, "no runs.steps[].run bodies extracted from any action"


class TestExpressionNeutralization:
    """Substitution must preserve geometry and never look like a literal."""

    def test_preserves_line_count_and_width(self):
        """Line and column numbers only map back if the shape is preserved."""
        body = 'echo "${{ inputs.name }}"\nrun ${{ steps.a.outputs.b }} x\n'
        script, _ = neutralize_expressions(body)
        original = body.splitlines()
        rewritten = script.splitlines()
        assert len(rewritten) == len(original)
        assert [len(line) for line in rewritten] == [len(line) for line in original]

    def test_placeholder_is_braced(self):
        """A bare `$NAME` in `${{ x }}s` becomes `$NAMEs` - a different variable."""
        script, names = neutralize_expressions("echo ${{ inputs.x }}s")
        assert names, "no placeholder recorded"
        for name in names:
            assert "${" + name + "}" in script, script

    def test_no_expression_survives(self):
        """Any surviving `${{` would reach shellcheck as a parse error."""
        script, _ = neutralize_expressions("a ${{ x }} b ${{ y }} c")
        assert "${{" not in script, script


@requires_shellcheck
class TestFabricatedFindingsAreSuppressed:
    """Artifacts of substitution must not reach the report."""

    def test_single_quoted_expression_is_not_reported(self, tmp_path):
        """`'${{ ... }}'` is correct - GitHub substitutes before bash runs.

        Reporting SC2016 would push a reader to switch to double quotes,
        exposing the substituted content to shell expansion.
        """
        step = _step(tmp_path, "PLATFORMS=$(echo '${{ inputs.matrix }}' | jq -r .)\n")
        messages = [finding.message for finding in shellcheck_step(step)]
        assert not any("SC2016" in message for message in messages), messages

    def test_constant_comparison_is_not_reported(self, tmp_path):
        """A literal placeholder made `[ "${{ x }}" = "true" ]` look constant."""
        step = _step(
            tmp_path, 'if [ "${{ inputs.flag }}" = "true" ]; then echo y; fi\n'
        )
        messages = [finding.message for finding in shellcheck_step(step)]
        assert not any(
            "SC2050" in message or "SC2157" in message for message in messages
        ), messages

    def test_placeholder_never_appears_in_a_finding(self, tmp_path):
        """A finding naming the placeholder is about the tool, not the action."""
        step = _step(tmp_path, 'echo "${{ inputs.a }}"\nx=${{ inputs.b }}s\n')
        messages = [finding.message for finding in shellcheck_step(step)]
        assert not any("GHA_EXPR" in message for message in messages), messages


@requires_shellcheck
class TestGateStillDetectsRealDefects:
    """The suppressions must not have blunted the gate."""

    def test_unquoted_expression_is_reported(self, tmp_path):
        """An unquoted `${{ }}` is the defect class this gate exists to catch."""
        step = _step(tmp_path, "pixi install -e ${{ inputs.env }}\n")
        messages = [finding.message for finding in shellcheck_step(step)]
        assert any("SC2086" in message for message in messages), messages

    def test_unquoted_shell_variable_is_reported(self, tmp_path):
        """Ordinary shell quoting defects are reported too."""
        step = _step(tmp_path, 'echo "x=1" >> $GITHUB_OUTPUT\n')
        messages = [finding.message for finding in shellcheck_step(step)]
        assert any("SC2086" in message for message in messages), messages


@requires_shellcheck
def test_repo_composite_actions_are_clean():
    """Every shellcheckable run body in the repo passes (#261's triage)."""
    findings = [
        finding
        for path in discover_action_files()
        for step in iter_run_steps(path)
        if step.shell in SHELLCHECK_SHELLS
        for finding in shellcheck_step(step)
    ]
    assert not findings, "\n".join(str(finding) for finding in findings)


class TestBrokenShellcheckIsNotSilentSuccess:
    """A shellcheck that fails to run must not read as a clean result."""

    def test_nonzero_exit_raises_instead_of_reporting_clean(
        self, tmp_path, monkeypatch
    ):
        """Exit codes other than 0/1 mean the tool did not run.

        Observed in CI: shellcheck produced no output in one environment, so
        every body parsed as clean. Silence from a broken tool is
        indistinguishable from a passing gate unless the exit code is checked.
        """
        import subprocess

        from framework import action_shellcheck

        def _fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0] if args else [],
                returncode=2,
                stdout="",
                stderr="shellcheck: unrecognized option",
            )

        monkeypatch.setattr(action_shellcheck.subprocess, "run", _fake_run)
        step = _step(tmp_path, "echo hi\n")
        with pytest.raises(RuntimeError, match="did not run"):
            action_shellcheck.shellcheck_step(step)
