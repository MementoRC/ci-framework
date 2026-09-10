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

import ast
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
CHANGE_DETECTION_PY = REPO_ROOT / "framework" / "actions" / "change_detection.py"
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


_CHANGE_DETECTION_EXPECTED_KWARGS = (
    "project_dir",
    "reports_dir",
    "detection_level",
    "base_ref",
    "head_ref",
    "enable_test_optimization",
    "enable_job_skipping",
    "monorepo_mode",
    "pattern_config",
)


def _change_detection_constructor_violations(text: str) -> list[str]:
    """AST-based signature-parity check for `ChangeDetectionAction(...)` (#291).

    Walks every python3 heredoc in `text`, and for each one that calls
    `ChangeDetectionAction(...)`:
      - asserts the call passes exactly the nine expected keywords (no
        fewer - that was the #291 bug - and no unexpected extras),
      - asserts none of those keyword values is a hardcoded literal (each
        must be threaded from the environment, i.e. a Name or Call), and
      - if the same heredoc also defines a fallback `class
        ChangeDetectionAction`, asserts its `__init__` accepts every
        keyword passed at the call site (named explicitly or absorbed by
        `**kwargs`), so the import path and the fallback path cannot drift.

    Shared by the real guard and its own vacuity self-test below, so
    neither can duplicate (and thereby desync from) the other's logic.
    Returns a list of violation messages; empty means clean.
    """
    violations: list[str] = []
    for body in _heredoc_bodies(text):
        try:
            tree = ast.parse(textwrap.dedent(body))
        except SyntaxError as exc:
            violations.append(f"failed to parse python3 heredoc body: {exc}")
            continue

        call_node = next(
            (
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "ChangeDetectionAction"
            ),
            None,
        )
        if call_node is None:
            continue

        call_kwargs = {kw.arg: kw.value for kw in call_node.keywords if kw.arg}

        missing = sorted(
            name
            for name in _CHANGE_DETECTION_EXPECTED_KWARGS
            if name not in call_kwargs
        )
        if missing:
            violations.append(
                "ChangeDetectionAction(...) call is missing expected keyword(s): "
                f"{missing}"
            )

        extra = sorted(
            name
            for name in call_kwargs
            if name not in _CHANGE_DETECTION_EXPECTED_KWARGS
        )
        if extra:
            violations.append(
                f"ChangeDetectionAction(...) call has unexpected keyword(s): {extra}"
            )

        for name, value_node in call_kwargs.items():
            if isinstance(value_node, ast.Constant):
                violations.append(
                    f"ChangeDetectionAction(...) keyword '{name}' is a hardcoded "
                    f"literal ({value_node.value!r}) instead of being threaded "
                    "from the environment"
                )

        class_node = next(
            (
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef)
                and node.name == "ChangeDetectionAction"
            ),
            None,
        )
        if class_node is None:
            continue

        init_node = next(
            (
                node
                for node in class_node.body
                if isinstance(node, ast.FunctionDef) and node.name == "__init__"
            ),
            None,
        )
        if init_node is None:
            violations.append("fallback ChangeDetectionAction class has no __init__")
            continue

        accepted = {a.arg for a in init_node.args.args} | {
            a.arg for a in init_node.args.kwonlyargs
        }
        accepted.discard("self")
        accepts_kwargs = init_node.args.kwarg is not None

        unaccepted = sorted(
            name for name in call_kwargs if name not in accepted and not accepts_kwargs
        )
        if unaccepted:
            violations.append(
                "fallback ChangeDetectionAction.__init__ does not accept "
                f"keyword(s) passed at the call site (and has no **kwargs): {unaccepted}"
            )

    return violations


def _value_references_config_surface(node: ast.expr, param_names: set[str]) -> bool:
    """True iff `node` (an assigned value) is threaded from the constructor.

    An attribute belongs to the config surface iff its assigned value
    either names one of `__init__`'s own parameters (e.g. `project_dir or
    Path.cwd()`) or calls `kwargs.get(...)` (e.g. `kwargs.get("base_ref",
    ...)`). Everything else in `ChangeDetectionAction.__init__` - the
    component-construction block (`self.pattern_matcher =
    FilePatternMatcher(...)`, etc.) - only ever reads those values back via
    `self.xxx`, never the bare parameter name or `kwargs` directly, so this
    single rule isolates the nine config attributes without needing to
    hard-code the component attribute names or a line-number cutoff that
    would silently drift out of sync with the source.
    """
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id in param_names:
            return True
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr == "get"
            and isinstance(sub.func.value, ast.Name)
            and sub.func.value.id == "kwargs"
        ):
            return True
    return False


def _config_surface_attrs(tree: ast.AST) -> set[str]:
    """The `self.X` names in `ChangeDetectionAction.__init__`'s config surface.

    Finds the `ChangeDetectionAction` class and its `__init__` in `tree`,
    then collects every `self.X = ...` assignment (anywhere in the method,
    not just top-level, so it also reaches assignments inside conditionals)
    whose value satisfies `_value_references_config_surface`. Returns an
    empty set if no such class/`__init__` is found.
    """
    class_node = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "ChangeDetectionAction"
        ),
        None,
    )
    if class_node is None:
        return set()

    init_node = next(
        (
            node
            for node in class_node.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        ),
        None,
    )
    if init_node is None:
        return set()

    param_names = (
        {a.arg for a in init_node.args.args}
        | {a.arg for a in init_node.args.posonlyargs}
        | {a.arg for a in init_node.args.kwonlyargs}
    )
    param_names.discard("self")

    attrs: set[str] = set()
    for node in ast.walk(init_node):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
                and _value_references_config_surface(node.value, param_names)
            ):
                attrs.add(target.attr)
    return attrs


def _change_detection_attribute_parity_violations(
    packaged_source: str | None = None,
    fallback_source: str | None = None,
) -> list[str]:
    """AST-based attribute-parity check between the packaged and fallback
    `ChangeDetectionAction.__init__` (#291 follow-up).

    `_change_detection_constructor_violations` above only checks that both
    constructors *accept* the same keywords - it never looks at what each
    `__init__` actually assigns to `self`. That gap is exactly how the
    enable_test_opt/enable_test_optimization split (and the matching
    enable_job_skip/enable_job_skipping split) went unnoticed: both
    constructors accepted `enable_test_optimization` as a kwarg, but only
    the packaged class stored it under that name.

    Of the two attribute-collection strategies discussed for this guard - a
    "stop before the first `self.X_matcher`/`_analyzer`/`_handler`/
    `_engine`/`_generator` assignment" cutoff, versus "collect only
    `self.X` assigned from a parameter name or a `kwargs.get(...)` call" -
    this uses the latter (`_config_surface_attrs` /
    `_value_references_config_surface`). The cutoff approach is asymmetric:
    the packaged class's component-construction block starts with
    `self.pattern_matcher = ...`, but the fallback class has no such block
    at all (it builds its `self.patterns` dict inline instead), so a
    cutoff tuned for one class's shape does not stop at the right place -
    or at all - in the other. The parameter/`kwargs.get(...)` rule instead
    asks the same structural question of every assignment regardless of
    which class it is in, and naturally excludes the packaged class's
    component attributes (they are built from `self.xxx`, i.e. attribute
    reads, not from the parameter names or `kwargs` directly) without
    needing to know their names.

    Defaults to reading the real packaged module and the real fallback
    class out of `action.yml`; accepts explicit source strings so the
    vacuity self-test below can exercise the exact same logic against a
    synthetic pair.
    """
    if packaged_source is None:
        packaged_source = CHANGE_DETECTION_PY.read_text()
    if fallback_source is None:
        fallback_source = CHANGE_DETECTION_YML.read_text()

    packaged_attrs = _config_surface_attrs(ast.parse(packaged_source))

    fallback_attrs: set[str] = set()
    found_fallback_class = False
    for body in _heredoc_bodies(fallback_source):
        try:
            tree = ast.parse(textwrap.dedent(body))
        except SyntaxError:
            continue
        if not any(
            isinstance(node, ast.ClassDef) and node.name == "ChangeDetectionAction"
            for node in ast.walk(tree)
        ):
            continue
        found_fallback_class = True
        fallback_attrs |= _config_surface_attrs(tree)

    if not found_fallback_class:
        return ["no fallback ChangeDetectionAction class found in any heredoc body"]

    violations: list[str] = []
    only_in_packaged = sorted(packaged_attrs - fallback_attrs)
    only_in_fallback = sorted(fallback_attrs - packaged_attrs)
    if only_in_packaged:
        violations.append(
            "attribute(s) set by the packaged ChangeDetectionAction.__init__ "
            f"but not by the fallback's: {only_in_packaged}"
        )
    if only_in_fallback:
        violations.append(
            "attribute(s) set by the fallback ChangeDetectionAction.__init__ "
            f"but not by the packaged class's: {only_in_fallback}"
        )
    return violations


def _find_init_node(tree: ast.AST, class_name: str) -> ast.FunctionDef | None:
    """The `__init__` `FunctionDef` of `class_name` in `tree`, if any."""
    class_node = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ),
        None,
    )
    if class_node is None:
        return None
    return next(
        (
            node
            for node in class_node.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        ),
        None,
    )


def _init_param_names(node: ast.FunctionDef) -> set[str]:
    """Parameter names an `__init__` node accepts, excluding `self`."""
    names = {a.arg for a in node.args.args} | {a.arg for a in node.args.kwonlyargs}
    names.discard("self")
    return names


def _change_detection_signature_parity_violations(
    packaged_source: str | None = None,
    fallback_source: str | None = None,
) -> list[str]:
    """Parameter-name-parity check between the two `ChangeDetectionAction`
    constructors (#291 follow-up).

    Both constructors used to collapse everything but `project_dir` /
    `reports_dir` / `detection_level` into `**kwargs`, so
    `_change_detection_constructor_violations`'s `accepts_kwargs` escape
    hatch made an unaccepted-keyword drift invisible on either side.  Now
    that both declare their nine parameters explicitly, nothing checks that
    the *names* of those parameters actually still match between the
    packaged class and the standalone fallback - a rename on one side would
    go unnoticed by every other guard in this file.  This asserts the two
    parameter-name sets (excluding `self`) are identical and reports the
    symmetric difference in both directions when they are not.

    Defaults to reading the real packaged module and the real fallback
    class out of `action.yml`; accepts explicit source strings so the
    vacuity self-test below can exercise the exact same logic against a
    synthetic pair.
    """
    if packaged_source is None:
        packaged_source = CHANGE_DETECTION_PY.read_text()
    if fallback_source is None:
        fallback_source = CHANGE_DETECTION_YML.read_text()

    packaged_init = _find_init_node(ast.parse(packaged_source), "ChangeDetectionAction")
    if packaged_init is None:
        return ["no packaged ChangeDetectionAction.__init__ found"]
    packaged_params = _init_param_names(packaged_init)

    fallback_init = None
    for body in _heredoc_bodies(fallback_source):
        try:
            tree = ast.parse(textwrap.dedent(body))
        except SyntaxError:
            continue
        candidate = _find_init_node(tree, "ChangeDetectionAction")
        if candidate is not None:
            fallback_init = candidate
            break
    if fallback_init is None:
        return ["no fallback ChangeDetectionAction.__init__ found in any heredoc body"]
    fallback_params = _init_param_names(fallback_init)

    violations: list[str] = []
    only_in_packaged = sorted(packaged_params - fallback_params)
    only_in_fallback = sorted(fallback_params - packaged_params)
    if only_in_packaged:
        violations.append(
            "parameter(s) accepted by the packaged ChangeDetectionAction.__init__ "
            f"but not by the fallback's: {only_in_packaged}"
        )
    if only_in_fallback:
        violations.append(
            "parameter(s) accepted by the fallback ChangeDetectionAction.__init__ "
            f"but not by the packaged class's: {only_in_fallback}"
        )
    return violations


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

    def test_constructor_call_site_was_actually_found(self):
        """Vacuity guard: `_change_detection_constructor_violations` skips any
        heredoc body that does not contain a `ChangeDetectionAction(` call. If
        `_heredoc_bodies` ever stopped extracting bodies from the real
        `action.yml` (regex drift, YAML restructure), it would return zero
        violations and the wiring test would pass trivially. This asserts the
        real file is actually being scanned. Follows the same convention as
        the existing `test_template_task_table_was_actually_found`-style
        vacuity guards elsewhere in the suite.
        """
        source = CHANGE_DETECTION_YML.read_text()
        bodies = _heredoc_bodies(source)
        assert bodies, (
            "No python3 heredoc bodies were extracted from change-detection/action.yml"
        )
        assert any("ChangeDetectionAction(" in body for body in bodies), (
            "The constructor call site was not found in any extracted "
            "heredoc body, so the wiring guard would pass vacuously"
        )
        parsed_any = False
        for body in bodies:
            try:
                ast.parse(textwrap.dedent(body))
            except SyntaxError:
                continue
            parsed_any = True
        assert parsed_any, (
            "No extracted heredoc body could be ast.parse'd, so the wiring "
            "guard would pass vacuously"
        )

    def test_wiring_reaches_the_constructor_call(self):
        """Static guard against reverting to the original inert pattern.

        Before #273 the standalone class was instantiated with zero
        arguments (`ChangeDetectionAction()`), so PATTERN_CONFIG was read
        into a shell variable and never referenced again. Before #291 the
        call site passed only `pattern_config`, silently dropping the other
        eight declared inputs on the packaged-class import path (the
        fallback path happened to work because it read module globals
        directly). A literal substring match on the pre-#291 call proved
        text presence, not that every value actually reaches the
        constructor - this is why #291 was missed. This now uses an
        AST-based check (`_change_detection_constructor_violations`) that
        fails if any of the nine expected keywords go missing, are
        hardcoded literals, or diverge between the import path and the
        fallback class's `__init__`.
        """
        source = CHANGE_DETECTION_YML.read_text()
        # PATTERN_CONFIG is now read from the environment rather than
        # spliced as "$PATTERN_CONFIG" into the python3 heredoc source - see
        # the #273-follow-up injection fix. The wiring guard is updated to
        # match, but still fails if the pattern_config plumbing regresses.
        assert re.search(r"pattern_config\s*=\s*PATTERN_CONFIG\s+or\s+None", source), (
            "pattern_config is no longer read from the PATTERN_CONFIG environment variable"
        )
        violations = _change_detection_constructor_violations(source)
        assert not violations, violations

    def test_discovery_would_have_caught_the_dropped_constructor_arguments(self):
        """Sanity check on the parser itself: it must actually flag the
        exact shape of the #291 bug (only `pattern_config` reaching the
        constructor) on a minimal reproduction, so a broken AST walk can't
        make the real test above pass vacuously.
        """
        sample = (
            "        python3 << 'EOF'\n"
            "        import os\n"
            "        from pathlib import Path\n"
            '        PROJECT_DIR = os.environ.get("PROJECT_DIR") or "."\n'
            "        try:\n"
            "            from actions.change_detection import ChangeDetectionAction\n"
            "        except ImportError:\n"
            "            class ChangeDetectionAction:\n"
            "                def __init__(self, pattern_config=None):\n"
            "                    self.pattern_config = pattern_config\n"
            "        pattern_config = PATTERN_CONFIG or None\n"
            "        detector = ChangeDetectionAction(pattern_config=pattern_config)\n"
            "        EOF\n"
        )

        violations = _change_detection_constructor_violations(sample)

        assert violations, "parser failed to flag the pre-#291 inert wiring"
        expected_missing = {
            "project_dir",
            "reports_dir",
            "detection_level",
            "base_ref",
            "head_ref",
            "enable_test_optimization",
            "enable_job_skipping",
            "monorepo_mode",
        }
        missing_message = next(
            (
                v
                for v in violations
                if v.startswith("ChangeDetectionAction(...) call is missing")
            ),
            "",
        )
        assert missing_message, violations
        for name in expected_missing:
            assert name in missing_message, (name, missing_message)
        # pattern_config *is* passed, so it must not show up as missing.
        assert "'pattern_config'" not in missing_message, missing_message

    def test_fallback_class_attribute_names_match_the_packaged_class(self):
        """Attribute-parity guard for #291's actual failure mode.

        `test_wiring_reaches_the_constructor_call` (via
        `_change_detection_constructor_violations`) only proves both
        constructors *accept* the same nine keywords - it says nothing
        about what each `__init__` stores them under. That gap let the
        fallback keep `self.enable_test_opt`/`self.enable_job_skip` while
        the packaged class used `self.enable_test_optimization`/
        `self.enable_job_skipping`, unnoticed. This closes it directly.
        """
        packaged_attrs = _config_surface_attrs(
            ast.parse(CHANGE_DETECTION_PY.read_text())
        )
        fallback_attrs: set[str] = set()
        for body in _heredoc_bodies(CHANGE_DETECTION_YML.read_text()):
            try:
                tree = ast.parse(textwrap.dedent(body))
            except SyntaxError:
                continue
            fallback_attrs |= _config_surface_attrs(tree)

        # Vacuity guard: a failed parse on either side would make the
        # symmetric-difference check below pass trivially (empty == empty).
        assert packaged_attrs, (
            "no config-surface attributes were parsed from the packaged "
            "ChangeDetectionAction.__init__ - the parity check below would "
            "pass vacuously"
        )
        assert fallback_attrs, (
            "no config-surface attributes were parsed from the fallback "
            "ChangeDetectionAction.__init__ - the parity check below would "
            "pass vacuously"
        )

        violations = _change_detection_attribute_parity_violations()
        assert not violations, violations

    def test_attribute_parity_check_would_have_caught_the_short_names(self):
        """Sanity check on the parity parser itself: it must actually flag
        the exact shape of the enable_test_opt/enable_job_skip drift on a
        minimal reproduction, so a broken AST walk can't make the real test
        above pass vacuously. Exercises
        `_change_detection_attribute_parity_violations` directly (via its
        optional source-string parameters), not a copy of its logic.
        """
        packaged_source = textwrap.dedent(
            """
            class ChangeDetectionAction:
                def __init__(self, project_dir=None, reports_dir=None, detection_level="standard", **kwargs):
                    self.project_dir = project_dir or Path.cwd()
                    self.reports_dir = reports_dir or (self.project_dir / "change-reports")
                    self.detection_level = detection_level
                    self.base_ref = kwargs.get("base_ref", "HEAD~1")
                    self.head_ref = kwargs.get("head_ref", "HEAD")
                    self.enable_test_optimization = kwargs.get("enable_test_optimization", True)
                    self.enable_job_skipping = kwargs.get("enable_job_skipping", True)
                    self.monorepo_mode = kwargs.get("monorepo_mode", False)
                    self.pattern_config = kwargs.get("pattern_config")
                    self.pattern_matcher = FilePatternMatcher()
            """
        )
        fallback_source = (
            "        python3 << 'EOF'\n"
            "        class ChangeDetectionAction:\n"
            "            def __init__(self, project_dir=None, reports_dir=None, detection_level='standard', **kwargs):\n"
            "                self.project_dir = project_dir or Path.cwd()\n"
            "                self.reports_dir = reports_dir or Path.cwd()\n"
            "                self.detection_level = detection_level\n"
            "                self.base_ref = kwargs.get('base_ref', 'HEAD~1')\n"
            "                self.head_ref = kwargs.get('head_ref', 'HEAD')\n"
            "                self.enable_test_opt = kwargs.get('enable_test_optimization', True)\n"
            "                self.enable_job_skip = kwargs.get('enable_job_skipping', True)\n"
            "                self.monorepo_mode = kwargs.get('monorepo_mode', False)\n"
            "                self.pattern_config = kwargs.get('pattern_config')\n"
            "        EOF\n"
        )

        violations = _change_detection_attribute_parity_violations(
            packaged_source, fallback_source
        )

        assert violations, (
            "parser failed to flag the enable_test_opt/enable_job_skip drift"
        )
        joined = " ".join(violations)
        for name in ("enable_test_optimization", "enable_job_skipping"):
            assert name in joined, (name, violations)
        for name in ("enable_test_opt", "enable_job_skip"):
            assert name in joined, (name, violations)

    def test_fallback_class_parameter_names_match_the_packaged_class(self):
        """Signature-name-parity guard for the post-#291 explicit-parameter
        constructors.

        `_change_detection_constructor_violations`'s `accepted`/
        `accepts_kwargs` check only proves the fallback `__init__` does not
        *reject* a keyword the call site passes - with `**kwargs` gone from
        both classes, it says nothing about whether the two `__init__`
        signatures still name the same nine parameters. This asserts they
        do, independently of `_change_detection_attribute_parity_violations`
        (which checks what each side stores `self.X` under, not what the
        parameters are named).
        """
        packaged_params = _init_param_names(
            _find_init_node(
                ast.parse(CHANGE_DETECTION_PY.read_text()), "ChangeDetectionAction"
            )
        )
        fallback_init = None
        for body in _heredoc_bodies(CHANGE_DETECTION_YML.read_text()):
            try:
                tree = ast.parse(textwrap.dedent(body))
            except SyntaxError:
                continue
            candidate = _find_init_node(tree, "ChangeDetectionAction")
            if candidate is not None:
                fallback_init = candidate
                break

        # Vacuity guard: a failed lookup on either side would make the
        # symmetric-difference check below pass trivially (empty == empty).
        assert packaged_params, (
            "no parameters were parsed from the packaged "
            "ChangeDetectionAction.__init__ - the parity check below would "
            "pass vacuously"
        )
        assert fallback_init is not None, (
            "no fallback ChangeDetectionAction.__init__ was found in any "
            "heredoc body - the parity check below would pass vacuously"
        )

        violations = _change_detection_signature_parity_violations()
        assert not violations, violations

    def test_parameter_parity_check_would_have_caught_a_dropped_parameter(self):
        """Sanity check on the signature-parity parser itself: it must
        actually flag a fallback `__init__` that drops a parameter the
        packaged class still accepts, so a broken AST walk can't make the
        real test above pass vacuously. Exercises
        `_change_detection_signature_parity_violations` directly (via its
        optional source-string parameters), not a copy of its logic.
        """
        packaged_source = textwrap.dedent(
            """
            class ChangeDetectionAction:
                def __init__(
                    self,
                    project_dir=None,
                    reports_dir=None,
                    detection_level="standard",
                    base_ref="HEAD~1",
                    head_ref="HEAD",
                    enable_test_optimization=True,
                    enable_job_skipping=True,
                    monorepo_mode=False,
                    pattern_config=None,
                ):
                    self.project_dir = project_dir or Path.cwd()
            """
        )
        fallback_source = (
            "        python3 << 'EOF'\n"
            "        class ChangeDetectionAction:\n"
            "            def __init__(\n"
            "              self,\n"
            "              project_dir=None,\n"
            "              reports_dir=None,\n"
            "              detection_level=None,\n"
            "              base_ref=None,\n"
            "              enable_test_optimization=None,\n"
            "              enable_job_skipping=None,\n"
            "              monorepo_mode=None,\n"
            "              pattern_config=None,\n"
            "            ):\n"
            "                self.project_dir = Path(project_dir or PROJECT_DIR)\n"
            "        EOF\n"
        )

        violations = _change_detection_signature_parity_violations(
            packaged_source, fallback_source
        )

        assert violations, "parser failed to flag the dropped head_ref parameter"
        joined = " ".join(violations)
        assert "head_ref" in joined, violations

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


# ===== change-detection: git ref option-injection (#291 follow-up) =====


class TestChangeDetectionRefOptionInjection:
    """A resolved base-ref/head-ref beginning with '-' is parsed by `git
    diff` as an OPTION, not a revision - e.g.
    base-ref="--output=/tmp/pwned" produces the single argument
    "--output=/tmp/pwned...HEAD", which git honours as an output-file
    option, giving arbitrary file write with diff content. This is git
    OPTION injection, a distinct vulnerability from the shell/Python source
    injection covered by `TestChangeDetectionEnvVarInjectionRegression`
    above: both call sites already use list-form `subprocess.run` with no
    `shell=True`, so no shell ever sees these values, and that existing
    class's tests do not exercise this path at all.

    The fix rejects any ref beginning with '-' before it reaches a git
    subprocess, both in the bash step (fail-fast, before the python3
    heredoc even runs) and in the packaged `ChangeDetectionAction` (which
    is also reachable directly via the module's `argparse` CLI, bypassing
    the bash step entirely).
    """

    MALICIOUS_REF = "--output=/tmp/pwned"

    def test_base_ref_option_injection_fails_fast_in_bash(self):
        """Model: `test_nonexistent_pattern_config_fails_fast_in_bash` above."""
        source = CHANGE_DETECTION_YML.read_text()
        snippet = _extract(
            source,
            'if [[ "$BASE_REF" == -*',
            "# Exported (after the defaulting above",
        )

        result = subprocess.run(
            ["bash", "-c", snippet],
            env={**os.environ, "BASE_REF": self.MALICIOUS_REF, "HEAD_REF": "HEAD"},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1, result.stderr
        assert "base-ref" in result.stderr
        assert "cannot begin with '-'" in result.stderr

    def test_head_ref_option_injection_fails_fast_in_bash(self):
        """Model: `test_nonexistent_pattern_config_fails_fast_in_bash` above."""
        source = CHANGE_DETECTION_YML.read_text()
        snippet = _extract(
            source,
            'if [[ "$BASE_REF" == -*',
            "# Exported (after the defaulting above",
        )

        result = subprocess.run(
            ["bash", "-c", snippet],
            env={**os.environ, "BASE_REF": "HEAD~1", "HEAD_REF": self.MALICIOUS_REF},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1, result.stderr
        assert "head-ref" in result.stderr
        assert "cannot begin with '-'" in result.stderr

    def test_packaged_base_ref_option_injection_raises_before_git(
        self, tmp_path, monkeypatch
    ):
        """The packaged class matters independently of the bash step: its
        `argparse` CLI (`python -m ... --base-ref ...`) takes refs straight
        from the command line and never passes through action.yml's bash
        guard.
        """
        from framework.actions import change_detection as cd_module

        def _fail_if_called(*args: object, **kwargs: object) -> None:
            raise AssertionError("git should not have been invoked")

        monkeypatch.setattr(cd_module.subprocess, "run", _fail_if_called)
        action = cd_module.ChangeDetectionAction(
            project_dir=tmp_path, base_ref=self.MALICIOUS_REF, head_ref="HEAD"
        )

        with pytest.raises(ValueError, match="base_ref"):
            action._get_changed_files()

    def test_packaged_head_ref_option_injection_raises_before_git(
        self, tmp_path, monkeypatch
    ):
        from framework.actions import change_detection as cd_module

        def _fail_if_called(*args: object, **kwargs: object) -> None:
            raise AssertionError("git should not have been invoked")

        monkeypatch.setattr(cd_module.subprocess, "run", _fail_if_called)
        action = cd_module.ChangeDetectionAction(
            project_dir=tmp_path, base_ref="HEAD~1", head_ref=self.MALICIOUS_REF
        )

        with pytest.raises(ValueError, match="head_ref"):
            action._get_changed_files()

    @pytest.mark.parametrize(
        "legit_ref",
        [
            "HEAD~1",
            "HEAD",
            "a" * 40,
            "refs/heads/feature/x",
            "origin/main",
        ],
    )
    def test_legitimate_refs_are_not_rejected(self, tmp_path, monkeypatch, legit_ref):
        """False-positive guard: a leading-dash-only check must never reject
        a real ref. Git itself forbids refnames beginning with '-', so this
        check cannot legitimately reject any of these.
        """
        from framework.actions import change_detection as cd_module

        def _fake_run(*args: object, **kwargs: object) -> types.SimpleNamespace:
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cd_module.subprocess, "run", _fake_run)
        action = cd_module.ChangeDetectionAction(
            project_dir=tmp_path, base_ref=legit_ref, head_ref=legit_ref
        )

        assert action._get_changed_files() == []


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
