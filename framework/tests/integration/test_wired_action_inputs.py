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
PERFORMANCE_BENCHMARK_YML = (
    REPO_ROOT / "actions" / "performance-benchmark" / "action.yml"
)
QUALITY_GATES_YML = REPO_ROOT / "actions" / "quality-gates" / "action.yml"


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


_HEREDOC_START = re.compile(r"^\s*(\S*python3?\S*)\s*<<-?\s*(['\"]?)(\w+)\2\s*$")


def _heredoc_bodies(text: str) -> list[str]:
    """The body of every `python3 << 'EOF' ... EOF` heredoc in `text`.

    Shared by every "walk every action.yml" discovery test below, so the
    heredoc-boundary parsing logic exists exactly once.
    """
    lines = text.splitlines()
    bodies = []
    i = 0
    while i < len(lines):
        match = _HEREDOC_START.match(lines[i])
        if match:
            delimiter = match.group(3)
            body: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() != delimiter:
                body.append(lines[i])
                i += 1
        else:
            i += 1
            continue
        bodies.append("\n".join(body))
    return bodies


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

    def test_nonexistent_config_file_fails_fast_in_bash(self):
        """A typo'd config-file must abort before the python3 heredoc ever runs.

        This is bash logic (`exit 1`), not Python, so it is executed for
        real via `bash -c` against the exact text extracted from
        action.yml, rather than mirrored by hand or exercised through the
        Python-only exec() fixtures above.
        """
        source = SECURITY_SCAN_YML.read_text()
        snippet = _extract(
            source, 'if [[ -n "$CONFIG_FILE"', "# Create reports directory"
        )

        result = subprocess.run(
            ["bash", "-c", snippet],
            env={**os.environ, "CONFIG_FILE": "/nonexistent/does-not-exist.yaml"},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1, result.stderr
        assert "config-file not found" in result.stderr

    def test_existing_config_file_does_not_abort_in_bash(self, tmp_path):
        """The same bash guard must be a no-op once the file actually exists."""
        source = SECURITY_SCAN_YML.read_text()
        snippet = _extract(
            source, 'if [[ -n "$CONFIG_FILE"', "# Create reports directory"
        )
        config_path = tmp_path / "bandit.yaml"
        config_path.write_text("")

        result = subprocess.run(
            ["bash", "-c", snippet],
            env={**os.environ, "CONFIG_FILE": str(config_path)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr


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
        # PATTERN_CONFIG is now read from the environment rather than
        # spliced as "$PATTERN_CONFIG" into the python3 heredoc source - see
        # the #273-follow-up injection fix. The wiring guard is updated to
        # match, but still fails if the pattern_config plumbing regresses.
        assert re.search(r"pattern_config\s*=\s*PATTERN_CONFIG\s+or\s+None", source), (
            "pattern_config is no longer read from the PATTERN_CONFIG environment variable"
        )
        assert "ChangeDetectionAction(pattern_config=pattern_config)" in source, (
            "pattern_config is no longer passed into ChangeDetectionAction()"
        )

    def test_nonexistent_pattern_config_fails_fast_in_bash(self):
        """A typo'd pattern-config must abort before the python3 heredoc ever runs.

        Same rationale as the security-scan config-file test: this is a
        bash `exit 1` guard, so it is executed for real via `bash -c`
        against the exact text extracted from action.yml.
        """
        source = CHANGE_DETECTION_YML.read_text()
        snippet = _extract(
            source, 'if [[ -n "$PATTERN_CONFIG"', "# Create reports directory"
        )

        result = subprocess.run(
            ["bash", "-c", snippet],
            env={**os.environ, "PATTERN_CONFIG": "/nonexistent/does-not-exist.toml"},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1, result.stderr
        assert "pattern-config not found" in result.stderr

    def test_existing_pattern_config_does_not_abort_in_bash(self, tmp_path):
        """The same bash guard must be a no-op once the file actually exists."""
        source = CHANGE_DETECTION_YML.read_text()
        snippet = _extract(
            source, 'if [[ -n "$PATTERN_CONFIG"', "# Create reports directory"
        )
        config_path = tmp_path / "patterns.toml"
        config_path.write_text("")

        result = subprocess.run(
            ["bash", "-c", snippet],
            env={**os.environ, "PATTERN_CONFIG": str(config_path)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr

    @pytest.fixture
    def action_class(self):
        source = CHANGE_DETECTION_YML.read_text()
        snippet = _extract(
            source,
            "class ChangeDetectionAction:",
            "def get_changed_files(self)",
        )
        # __init__ now reads these as bare names resolved from os.environ at
        # module scope (see the injection fix), rather than as literal
        # "$VAR" strings baked into the source. Provide the same defaults
        # the real heredoc's os.environ.get(...) calls use.
        namespace: dict[str, Any] = {
            "Path": Path,
            "PROJECT_DIR": ".",
            "REPORTS_DIR": "change-reports",
            "DETECTION_LEVEL": "standard",
            "BASE_REF": "",
            "HEAD_REF": "",
            "ENABLE_TEST_OPT": True,
            "ENABLE_JOB_SKIP": True,
            "MONOREPO_MODE": False,
        }
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


# ===== change-detection: env-var injection regression (#273 follow-up) =====


class TestChangeDetectionEnvVarInjectionRegression:
    """Before this fix, HEAD_REF/PROJECT_DIR/PATTERN_CONFIG (and others) were
    spliced directly into the python3 heredoc's *source text* as `"$VAR"`
    inside an unquoted (`<< EOF`) heredoc. Bash performs no escaping when
    expanding a variable inside a double-quoted context, so a value
    containing a `"` followed by a newline and code breaks out of the Python
    string literal and runs arbitrary code - e.g. a fork PR's branch name
    flowing into `head-ref: ${{ github.event.pull_request.head.ref }}`.

    The fix reads these values via `os.environ.get(...)` instead, so a
    malicious value can only ever become a Python *string value*, never
    Python *source*. These tests feed such a value through the real
    action.yml source (extracted, not hand-copied) and assert it comes out
    the other end as inert data.
    """

    MALICIOUS = 'foo"\nimport os\nos.system("touch /tmp/pwned")\n#'

    def _instantiate(self, monkeypatch: pytest.MonkeyPatch, **env: str):
        defaults = {
            "PROJECT_DIR": ".",
            "REPORTS_DIR": "change-reports",
            "DETECTION_LEVEL": "standard",
            "BASE_REF": "",
            "HEAD_REF": "",
            "ENABLE_TEST_OPT": "true",
            "ENABLE_JOB_SKIP": "true",
            "MONOREPO_MODE": "false",
            "PATTERN_CONFIG": "",
            "FAIL_FAST": "false",
        }
        defaults.update(env)
        for key, value in defaults.items():
            monkeypatch.setenv(key, value)

        source = CHANGE_DETECTION_YML.read_text()
        # The leading "\n        " keeps the first extracted line's own
        # indentation intact (a bare mid-line marker would otherwise strip
        # just that line's leading whitespace, leaving it at column 0 while
        # every other line stays at column 8 - an IndentationError once
        # dedented and exec'd).
        env_reads = _extract(
            source,
            "\n        PROJECT_DIR = os.environ.get(",
            "# Add framework to path",
        )
        class_def = _extract(
            source,
            "class ChangeDetectionAction:",
            "def get_changed_files(self)",
        )
        namespace: dict[str, Any] = {"os": os, "Path": Path}
        exec(env_reads, namespace)  # noqa: S102 - exercising real action.yml source
        exec(class_def, namespace)  # noqa: S102 - exercising real action.yml source
        pattern_config = namespace["PATTERN_CONFIG"] or None
        return namespace["ChangeDetectionAction"](pattern_config=pattern_config)

    def test_head_ref_injection_is_treated_as_data(self, monkeypatch):
        detector = self._instantiate(monkeypatch, HEAD_REF=self.MALICIOUS)

        assert detector.head_ref == self.MALICIOUS

    def test_project_dir_injection_is_treated_as_data(self, monkeypatch):
        detector = self._instantiate(monkeypatch, PROJECT_DIR=self.MALICIOUS)

        assert detector.project_dir == Path(self.MALICIOUS)

    def test_pattern_config_injection_is_treated_as_data(self, monkeypatch):
        """A truthy pattern_config is opened as a file by __init__, so the
        proof here is stronger than an attribute check: the malicious string
        must surface as a literal, unparsed *filename* in a real filesystem
        error, never as executed code.
        """
        with pytest.raises(FileNotFoundError) as exc_info:
            self._instantiate(monkeypatch, PATTERN_CONFIG=self.MALICIOUS)

        assert exc_info.value.filename == self.MALICIOUS

    def test_no_injected_code_actually_executes(self, tmp_path, monkeypatch):
        """No file is created by the injected `os.system("touch ...")` payload."""
        marker = tmp_path / "pwned"
        payload = f'foo"\nimport pathlib\npathlib.Path(r"{marker}").touch()\n#'

        self._instantiate(monkeypatch, HEAD_REF=payload)

        assert not marker.exists(), (
            "injected code executed - the env-var read is no longer safe"
        )

    def test_bash_style_splicing_would_have_executed_injected_code(self, tmp_path):
        """Proves the vulnerability class the fix above closes is real.

        Reproduces - by hand, not by reading it back out of action.yml, since
        the fix means it no longer exists there - exactly what bash does
        when expanding a variable inside a double-quoted heredoc line: the
        value is spliced into the *source text* verbatim, with no escaping.
        This is what `self.head_ref = "$HEAD_REF"` compiled down to before
        the fix, for a malicious HEAD_REF.
        """
        marker = tmp_path / "pwned"
        payload = f'foo"\nimport pathlib\npathlib.Path(r"{marker}").touch()\n#'
        vulnerable_source = f'value = "{payload}"\n'

        exec(vulnerable_source, {})  # noqa: S102 - demonstrating the vulnerability class

        assert marker.exists(), (
            "simulated bash-style splicing should have executed injected code"
        )


# ===== performance-benchmark: env-var injection regression (#292) =====


class TestPerformanceBenchmarkEnvVarInjectionRegression:
    """Same vulnerability class as change-detection's #273 follow-up, closed
    for this action by #292: SUITE/BASELINE_BRANCH/CONFIG_FILE and friends
    were spliced directly into the python3 heredoc's *source text* as
    `"$VAR"` inside an unquoted (`<< EOF`) heredoc - a value containing a
    `"` followed by a newline and code broke out of the Python string
    literal and ran arbitrary code, e.g. a malicious `baseline-branch` or
    `suite` input. The fix reads these values via `os.environ.get(...)`
    instead, so a malicious value can only ever become a Python *string
    value*, never Python *source*.
    """

    MALICIOUS = 'foo"\nimport os\nos.system("touch /tmp/pwned")\n#'

    def _read_env(self, monkeypatch: pytest.MonkeyPatch, **env: str) -> dict[str, Any]:
        defaults = {
            "SUITE": "quick",
            "BASELINE_BRANCH": "main",
            "REGRESSION_THRESHOLD": "10.0",
            "TIMEOUT": "1800",
            "PROJECT_DIR": ".",
            "CONFIG_FILE": "",
            "STORE_RESULTS": "true",
            "RESULTS_DIR": "benchmark-results",
            "COMPARE_BASELINE": "true",
            "FAIL_ON_REGRESSION": "true",
            "PARALLEL": "false",
        }
        defaults.update(env)
        for key, value in defaults.items():
            monkeypatch.setenv(key, value)

        source = PERFORMANCE_BENCHMARK_YML.read_text()
        # The leading "\n        " keeps the first extracted line's own
        # indentation intact - see the identical note on the
        # change-detection version of this helper above.
        env_reads = _extract(
            source,
            "\n        SUITE = os.environ.get(",
            "# Add framework to path",
        )
        namespace: dict[str, Any] = {"os": os}
        exec(env_reads, namespace)  # noqa: S102 - exercising real action.yml source
        return namespace

    def test_suite_injection_is_treated_as_data(self, monkeypatch):
        namespace = self._read_env(monkeypatch, SUITE=self.MALICIOUS)

        assert namespace["SUITE"] == self.MALICIOUS

    def test_baseline_branch_injection_is_treated_as_data(self, monkeypatch):
        namespace = self._read_env(monkeypatch, BASELINE_BRANCH=self.MALICIOUS)

        assert namespace["BASELINE_BRANCH"] == self.MALICIOUS

    def test_config_file_injection_is_treated_as_data(self, monkeypatch):
        namespace = self._read_env(monkeypatch, CONFIG_FILE=self.MALICIOUS)

        assert namespace["CONFIG_FILE"] == self.MALICIOUS

    def test_no_injected_code_actually_executes(self, tmp_path, monkeypatch):
        """No file is created by the injected `os.system("touch ...")` payload."""
        marker = tmp_path / "pwned"
        payload = f'foo"\nimport pathlib\npathlib.Path(r"{marker}").touch()\n#'

        self._read_env(monkeypatch, SUITE=payload)

        assert not marker.exists(), (
            "injected code executed - the env-var read is no longer safe"
        )


# ===== quality-gates: env-var injection regression (#292) =====


class TestQualityGatesEnvVarInjectionRegression:
    """Same vulnerability class as change-detection's #273 follow-up, closed
    for this action by #292: TIER/CONFIG_FILE and friends were spliced
    directly into the python3 heredoc's *source text* as `"$VAR"` inside an
    unquoted (`<< EOF`) heredoc - a value containing a `"` followed by a
    newline and code broke out of the Python string literal and ran
    arbitrary code, e.g. a malicious `tier` or `config-file` input. The fix
    reads these values via `os.environ.get(...)` instead, so a malicious
    value can only ever become a Python *string value*, never Python
    *source*.
    """

    MALICIOUS = 'foo"\nimport os\nos.system("touch /tmp/pwned")\n#'

    def _read_env(self, monkeypatch: pytest.MonkeyPatch, **env: str) -> dict[str, Any]:
        defaults = {
            "TIER": "essential",
            "TIMEOUT": "300",
            "PARALLEL": "true",
            "PROJECT_DIR": ".",
            "CONFIG_FILE": "",
            "FAIL_FAST": "true",
            "REPORTS_DIR": "reports",
        }
        defaults.update(env)
        for key, value in defaults.items():
            monkeypatch.setenv(key, value)

        source = QUALITY_GATES_YML.read_text()
        env_reads = _extract(
            source,
            "\n        TIER = os.environ.get(",
            "# Add framework to path",
        )
        namespace: dict[str, Any] = {"os": os}
        exec(env_reads, namespace)  # noqa: S102 - exercising real action.yml source
        return namespace

    def test_tier_injection_is_treated_as_data(self, monkeypatch):
        namespace = self._read_env(monkeypatch, TIER=self.MALICIOUS)

        assert namespace["TIER"] == self.MALICIOUS

    def test_config_file_injection_is_treated_as_data(self, monkeypatch):
        namespace = self._read_env(monkeypatch, CONFIG_FILE=self.MALICIOUS)

        assert namespace["CONFIG_FILE"] == self.MALICIOUS

    def test_no_injected_code_actually_executes(self, tmp_path, monkeypatch):
        """No file is created by the injected `os.system("touch ...")` payload."""
        marker = tmp_path / "pwned"
        payload = f'foo"\nimport pathlib\npathlib.Path(r"{marker}").touch()\n#'

        self._read_env(monkeypatch, TIER=payload)

        assert not marker.exists(), (
            "injected code executed - the env-var read is no longer safe"
        )


# ===== guard by discovery: no python3 heredoc may splice a shell $VAR =====


class TestNoShellInterpolationInsidePythonHeredocs:
    """General form of the #273 follow-up fix.

    Rather than relying on a hand-maintained list of sites, walk every
    action.yml under `actions/` and every `python3 << ...` heredoc within
    it, and fail loudly on any line that embeds a `$UPPERCASE_VAR`-shaped
    shell variable reference. That is exactly the pattern that made the ten
    (really fourteen) sites in change-detection/action.yml, and the three
    in security-scan/action.yml, exploitable or silently broken - and it
    would catch the next one automatically.
    """

    _SHELL_VAR = re.compile(r"\$[A-Z_][A-Z0-9_]*")

    # Must stay empty. #292 closed the last two entries (performance-benchmark,
    # quality-gates); every action.yml is now covered with no exclusions. Any
    # new entry here needs a tracked issue - do not add one to make this
    # guard pass; fix the site instead.
    _KNOWN_UNFIXED: set[str] = set()

    def test_discovery_would_have_caught_the_original_sites(self):
        """Sanity check on the parser itself: it must actually find the
        heredoc and detect the pattern on a minimal reproduction, so a
        broken regex can't make the real test below pass vacuously.
        """
        sample = (
            "        python3 << 'EOF'\n"
            '        self.head_ref = "$HEAD_REF"\n'
            "        EOF\n"
        )
        bodies = _heredoc_bodies(sample)
        assert len(bodies) == 1
        assert self._SHELL_VAR.search(bodies[0])

    def test_no_action_yml_splices_shell_vars_into_python_heredocs(self):
        actions_dir = REPO_ROOT / "actions"
        offenders: dict[str, list[str]] = {}
        for action_yml in sorted(actions_dir.rglob("action.yml")):
            rel = str(action_yml.relative_to(REPO_ROOT))
            if rel in self._KNOWN_UNFIXED:
                continue
            text = action_yml.read_text()
            for body in _heredoc_bodies(text):
                bad_lines = [
                    line for line in body.splitlines() if self._SHELL_VAR.search(line)
                ]
                if bad_lines:
                    offenders.setdefault(rel, []).extend(bad_lines)

        assert not offenders, (
            "shell variable spliced directly into python3 heredoc source "
            f"(arbitrary code injection risk if the heredoc is ever "
            f"unquoted): {offenders}"
        )


# ===== guard by discovery: two-arg os.environ.get() must not gate a
# boolean or numeric cast (#292 follow-up: security-scan, change-detection) =====


class TestEnvGetTwoArgFormNotUsedForBoolOrNumericCasts:
    """General form of the empty-but-set env var fix.

    `os.environ.get(key, default)` only falls back to `default` when `key`
    is *absent* from the environment. A composite action always exports
    every declared input (see the `export` comments throughout action.yml),
    so an empty-but-explicitly-set input (e.g. `fail-fast: ''`) reads back
    as `""`, not the declared default - silently flipping a `true`-by-default
    flag to `False`, or feeding a numeric cast a value that crashes or
    coerces unpredictably. security-scan's FAIL_FAST was exactly this: an
    empty `fail-fast` input made the scan exit 0 on findings - the same
    silent-disable failure mode #290 fixed via a different mechanism.

    This walks every `python3 << ...` heredoc in every action.yml under
    `actions/` (discovery, not a hand-maintained site list) and flags any
    two-arg `VAR = os.environ.get("VAR", "default")` assignment where `VAR`
    is later:
      - cast to bool via a `.lower() == "true"`/`"false"` comparison chained
        directly onto the assignment (the pattern used everywhere in this
        codebase), or
      - passed to `int(...)`/`float(...)` anywhere else in the same heredoc
        body - UNLESS that body also guards the cast with a `VAR.isdigit()`
        check (as quality-gates' TIMEOUT does: `""` already fails
        `.isdigit()` and falls back correctly, so the two-arg form there is
        not a bug).

    What this does NOT cover - a static regex, not full data-flow analysis:
    variables read via `os.environ.get(VAR, default)` and used only as
    plain strings (e.g. a directory or git ref passed to `Path(...)`) are
    never flagged, even where an empty value could in principle differ from
    the declared default. Judging whether "empty" is a valid value for a
    plain string requires the kind of semantic call several sibling tests
    in this file document by hand (CONFIG_FILE, PATTERN_CONFIG, BASE_REF,
    HEAD_REF are all intentionally left two-arg). It also only looks inside
    the extracted heredoc body text, so a cast reached through indirection
    (e.g. assigning `int` to a variable first) would not be detected.
    """

    _ENV_GET_TWO_ARG = re.compile(
        r"^\s*(?P<var>[A-Z_][A-Z0-9_]*)\s*=\s*"
        r'os\.environ\.get\(\s*"(?P=var)"\s*,\s*"[^"]*"\s*\)'
        r"(?P<rest>.*)$"
    )
    _BOOL_CAST = re.compile(r'\.lower\(\)\s*==\s*["\'](?:true|false)["\']')

    @staticmethod
    def _numeric_cast_pattern(var: str) -> re.Pattern[str]:
        return re.compile(rf"\b(?:int|float)\(\s*{re.escape(var)}\s*\)")

    @staticmethod
    def _isdigit_guard_pattern(var: str) -> re.Pattern[str]:
        return re.compile(rf"\b{re.escape(var)}\.isdigit\(\)")

    @classmethod
    def _violations_in(cls, text: str) -> list[str]:
        violations = []
        for body in _heredoc_bodies(text):
            for line in body.splitlines():
                match = cls._ENV_GET_TWO_ARG.match(line)
                if not match:
                    continue
                var = match.group("var")
                if cls._BOOL_CAST.search(match.group("rest")):
                    violations.append(var)
                    continue
                if cls._numeric_cast_pattern(var).search(
                    body
                ) and not cls._isdigit_guard_pattern(var).search(body):
                    violations.append(var)
        return violations

    def test_discovery_would_have_caught_fail_fast(self):
        """Sanity check on the parser itself: it must actually flag the
        exact shape of the FAIL_FAST bug this suite fixed on a minimal
        reproduction, so a broken regex can't make the real test below pass
        vacuously.
        """
        sample = (
            "        python3 << 'EOF'\n"
            '        FAIL_FAST = os.environ.get("FAIL_FAST", "true").strip().lower() == "true"\n'
            "        EOF\n"
        )
        assert self._violations_in(sample) == ["FAIL_FAST"]

    def test_isdigit_guarded_numeric_cast_is_not_flagged(self):
        """Sanity check for the one deliberate exception (quality-gates'
        TIMEOUT): a two-arg get() feeding an `.isdigit()`-guarded int() cast
        must NOT be flagged, so the real test isn't over-strict either.
        """
        sample = (
            "        python3 << 'EOF'\n"
            '        TIMEOUT = os.environ.get("TIMEOUT", "300")\n'
            "        timeout = int(TIMEOUT) if TIMEOUT.isdigit() else 300\n"
            "        EOF\n"
        )
        assert self._violations_in(sample) == []

    def test_no_action_yml_uses_two_arg_get_for_a_bool_or_numeric_cast(self):
        actions_dir = REPO_ROOT / "actions"
        offenders: dict[str, list[str]] = {}
        for action_yml in sorted(actions_dir.rglob("action.yml")):
            rel = str(action_yml.relative_to(REPO_ROOT))
            violations = self._violations_in(action_yml.read_text())
            if violations:
                offenders[rel] = violations

        assert not offenders, (
            "os.environ.get(key, default) two-arg form feeds a boolean or "
            "numeric cast: an empty-but-set input (which every composite "
            "action input becomes once exported) silently bypasses the "
            "declared default instead of falling back to it - use "
            f"`os.environ.get(key) or default` instead: {offenders}"
        )


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
