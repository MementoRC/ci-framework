"""Behavioural tests for the three inputs wired up by #273.

`config-file`, `fail-fast` (security-scan) and `pattern-config`
(change-detection) were declared, read into a shell variable, and never
referenced again. These tests execute the *actual* text extracted from
`action.yml` at test time (not a hand-copied mirror of it) so that reverting
any of the three back to "assign but never use" makes the corresponding test
fail - recreating a decorative test here would recreate #273 itself.

The shell-variable-unused guard requested for #273 is not duplicated here:
`framework/tests/workflows/test_action_shellcheck.py::test_repo_composite_actions_are_clean`
already runs shellcheck (which includes SC2034, "variable appears unused")
over every `runs.steps[].run` body in every action on disk, so any *future*
inert input is caught by that existing gate. `TestShellcheckCatchesUnusedVariable`
below proves SC2034 is actually live in that pipeline (a guard that never
fires is worth nothing), rather than re-implementing discovery.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import textwrap
import types
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
SECURITY_SCAN_YML = REPO_ROOT / "actions" / "security-scan" / "action.yml"
CHANGE_DETECTION_YML = REPO_ROOT / "actions" / "change-detection" / "action.yml"


def _pinned_shellcheck() -> str | None:
    """The shellcheck inside the active pixi environment, if there is one.

    Mirrors `test_action_shellcheck.py`'s own check: a PATH shellcheck from
    the runner is a different build and is deliberately not used (see that
    module for why - it silently produced zero findings for every input).
    """
    found = shutil.which("shellcheck")
    if found is None:
        return None
    prefix = os.environ.get("CONDA_PREFIX")
    if prefix and Path(found).is_relative_to(Path(prefix)):
        return found
    return None


requires_shellcheck = pytest.mark.skipif(
    _pinned_shellcheck() is None,
    reason="no pixi-pinned shellcheck in this environment",
)


def _extract(text: str, start_marker: str, end_marker: str) -> str:
    """The exact source between two literal markers, dedented.

    Extracting from the real file (not copying it into the test) is what
    makes the mutation-testing requirement meaningful: revert the action.yml
    wiring and this text changes, so the behaviour under exec() changes too.
    """
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return textwrap.dedent(text[start:end])


# ===== security-scan: config-file =====


class TestSecurityScanConfigFile:
    """`config-file` must reach bandit's and semgrep's command line."""

    @pytest.fixture
    def run_bandit(self):
        source = SECURITY_SCAN_YML.read_text()
        snippet = _extract(source, "def run_bandit(self)", "def run_safety(self)")
        captured: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured.append(cmd)
            if "-o" in cmd:
                out_path = Path(cmd[cmd.index("-o") + 1])
                out_path.write_text(json.dumps({"results": []}))
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        fake_subprocess = types.SimpleNamespace(
            run=fake_run, TimeoutExpired=subprocess.TimeoutExpired
        )
        namespace: dict[str, Any] = {
            "subprocess": fake_subprocess,
            "json": json,
            "Path": Path,
            "Dict": dict,
            "Any": object,
        }
        exec(snippet, namespace)  # noqa: S102 - exercising real action.yml source
        return namespace["run_bandit"], captured

    def _self_stub(self, tmp_path: Path) -> types.SimpleNamespace:
        return types.SimpleNamespace(
            project_dir=tmp_path,
            reports_dir=tmp_path,
            config={"bandit_severity": "medium", "timeout_per_tool": 5},
            failed_tools=[],
            tools_executed=[],
            vulnerabilities={"critical": 0, "high": 0, "medium": 0, "low": 0},
        )

    def test_unset_matches_prior_bandit_invocation(self, run_bandit, tmp_path):
        """No config-file -> no `-c` flag, exactly as before #273."""
        fn, captured = run_bandit
        namespace_globals = fn.__globals__
        namespace_globals["CONFIG_FILE"] = ""

        fn(self._self_stub(tmp_path))

        json_cmd = captured[0]
        assert "-c" not in json_cmd, json_cmd

    def test_set_adds_configfile_flag_to_bandit(self, run_bandit, tmp_path):
        """A config-file input must actually reach bandit's argv."""
        fn, captured = run_bandit
        config_path = str(tmp_path / "bandit.yaml")
        fn.__globals__["CONFIG_FILE"] = config_path

        fn(self._self_stub(tmp_path))

        json_cmd = captured[0]
        assert "-c" in json_cmd, json_cmd
        assert json_cmd[json_cmd.index("-c") + 1] == config_path


# ===== security-scan: fail-fast =====


class TestSecurityScanFailFast:
    """`fail-fast` must stop the scan loop early, and be a no-op when false."""

    @pytest.fixture
    def run_all_scans(self):
        source = SECURITY_SCAN_YML.read_text()
        snippet = _extract(
            source,
            "def run_all_scans(self) -> Dict[str, Any]:",
            "execution_time = time.time() - start_time",
        )
        # The runner substitutes `${{ inputs.x }}` before bash ever sees it.
        # Neutralised here so tool gating is driven purely by
        # self.config["required_tools"] (which the test controls), and
        # `parallel` forced to "false" so the non-fail-fast branch is the
        # deterministic sequential one rather than a thread pool whose
        # completion order isn't guaranteed.
        overrides = {"parallel": "false"}
        snippet = re.sub(
            r'"\$\{\{ inputs\.([a-z-]+) \}\}"',
            lambda m: f'"{overrides.get(m.group(1), "true")}"',
            snippet,
        )
        import concurrent.futures

        namespace: dict[str, Any] = {
            "time": __import__("time"),
            "concurrent": concurrent,
        }
        exec(snippet, namespace)  # noqa: S102 - exercising real action.yml source
        return namespace["run_all_scans"]

    def _self_stub(self, order: list[str]) -> types.SimpleNamespace:
        def tool(name: str, success: bool = True):
            def _run():
                order.append(name)
                return {"success": success}

            return _run

        return types.SimpleNamespace(
            run_bandit=tool("bandit", success=False),
            run_safety=tool("safety"),
            run_pip_audit=tool("pip-audit"),
            run_semgrep=tool("semgrep"),
            run_trivy=tool("trivy"),
            config={"required_tools": ["bandit", "safety", "pip-audit"]},
            results={},
            failed_tools=[],
            tools_executed=[],
            vulnerabilities={"critical": 0, "high": 0, "medium": 0, "low": 0},
        )

    def test_unset_runs_every_enabled_tool(self, run_all_scans):
        """fail-fast=false is a no-op: every enabled tool still runs (today's behaviour)."""
        order: list[str] = []
        self_stub = self._self_stub(order)
        run_all_scans.__globals__["FAIL_FAST"] = False

        run_all_scans(self_stub)

        assert order == ["bandit", "safety", "pip-audit"], order

    def test_set_stops_after_first_failing_tool(self, run_all_scans):
        """fail-fast=true stops at the first failing scanner instead of aggregating."""
        order: list[str] = []
        self_stub = self._self_stub(order)
        run_all_scans.__globals__["FAIL_FAST"] = True

        run_all_scans(self_stub)

        assert order == ["bandit"], order

    def test_set_stops_on_first_critical_vulnerability(self, run_all_scans):
        """fail-fast=true also stops when a tool succeeds but finds a critical vuln."""

        def critical_bandit():
            order.append("bandit")
            self_stub.vulnerabilities["critical"] += 1
            return {"success": True}

        order: list[str] = []
        self_stub = self._self_stub(order)
        self_stub.run_bandit = critical_bandit
        run_all_scans.__globals__["FAIL_FAST"] = True

        run_all_scans(self_stub)

        assert order == ["bandit"], order


# ===== change-detection: pattern-config =====


class TestChangeDetectionPatternConfig:
    """`pattern-config` must reach both the instantiation and the classifier."""

    def test_wiring_reaches_the_constructor_call(self):
        """Static guard against reverting to the original inert pattern.

        Before #273 the standalone class was instantiated with zero
        arguments (`ChangeDetectionAction()`), so PATTERN_CONFIG was read
        into a shell variable and never referenced again. This fails if that
        reverts, even though the reverted code would still be syntactically
        valid Python.
        """
        source = CHANGE_DETECTION_YML.read_text()
        assert re.search(
            r'pattern_config\s*=\s*"\$PATTERN_CONFIG"\s+or\s+None', source
        ), "pattern_config is no longer read from the PATTERN_CONFIG shell variable"
        assert "ChangeDetectionAction(pattern_config=pattern_config)" in source, (
            "pattern_config is no longer passed into ChangeDetectionAction()"
        )

    @pytest.fixture
    def action_class(self):
        source = CHANGE_DETECTION_YML.read_text()
        snippet = _extract(
            source,
            "class ChangeDetectionAction:",
            "def get_changed_files(self)",
        )
        namespace: dict[str, Any] = {"Path": Path}
        exec(snippet, namespace)  # noqa: S102 - exercising real action.yml source
        return namespace["ChangeDetectionAction"]

    def test_unset_keeps_default_patterns(self, action_class):
        """No pattern-config -> built-in patterns, unchanged (today's behaviour)."""
        detector = action_class(pattern_config=None)

        assert detector.patterns["source"] == [
            "src/**",
            "**/*.py",
            "**/*.js",
            "**/*.ts",
            "framework/**",
        ]

    def test_set_overrides_only_the_categories_it_defines(self, action_class, tmp_path):
        """A pattern-config file overrides matching categories, merges the rest."""
        config_file = tmp_path / "patterns.toml"
        config_file.write_text('[patterns]\nsource = ["custom/**/*.py"]\n')

        detector = action_class(pattern_config=str(config_file))

        assert detector.patterns["source"] == ["custom/**/*.py"]
        # docs was not mentioned in the custom file - default is preserved.
        assert detector.patterns["docs"] == [
            "docs/**",
            "*.md",
            "*.rst",
            "*.txt",
            "README*",
        ]


# ===== shared guard: unused shell variables are caught by action-shellcheck =====


class TestShellcheckCatchesUnusedVariable:
    """Proves SC2034 is live in the existing gate, rather than adding a new one.

    #273's own defect pattern - `VAR="${{ inputs.x }}"` assigned and never
    referenced - is exactly what shellcheck's SC2034 detects. Extending
    `framework/action_shellcheck.py`'s existing, already-comprehensive
    discovery (see `test_repo_composite_actions_are_clean`, which walks every
    action on disk) is preferred over a second, parallel implementation of
    the same discovery logic.
    """

    @requires_shellcheck
    def test_sc2034_fires_on_an_inert_shell_variable(self, tmp_path):
        from framework.action_shellcheck import RunStep, shellcheck_step

        step = RunStep(
            path=tmp_path / "action.yml",
            step_name="test",
            shell="bash",
            body='INERT="${{ inputs.x }}"\necho "not using it"\n',
            start_line=1,
        )
        messages = [finding.message for finding in shellcheck_step(step)]
        assert any("SC2034" in message for message in messages), messages
