"""Tests for reusable-ci.yml and standalone-ci.yml quality.

These tests validate the actual workflow files that consumer repos depend on,
catching anti-patterns that actionlint misses (double ${{ }}, cross-repo
checkout fragility, missing event guards, etc.).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS_DIR = Path(".github/workflows")
REUSABLE_CI = WORKFLOWS_DIR / "reusable-ci.yml"
REUSABLE_RELEASE = WORKFLOWS_DIR / "reusable-release.yml"
REUSABLE_SECURITY = WORKFLOWS_DIR / "reusable-security.yml"
STANDALONE_CI = WORKFLOWS_DIR / "standalone-ci.yml"
CI_YML = WORKFLOWS_DIR / "ci.yml"

# Matches a `pixi-version:` site that carries a value on the same line (i.e.
# excludes the bare `pixi-version:` key that introduces the input definition,
# whose `default:` lives on a following line).
PIXI_VERSION_SITE_RE = re.compile(r"pixi-version:\s*(\S.*?)\s*$")
HARDCODED_PIXI_VERSION_RE = re.compile(r"pixi-version:\s*(v[0-9]\S*)")


def load_workflow(path: Path) -> tuple[dict, list[str]]:
    """Load a workflow file, returning parsed YAML and raw lines."""
    text = path.read_text()
    return yaml.safe_load(text), text.splitlines()


# ============================================================================
# Custom linter integration tests
# ============================================================================


class TestWorkflowLinter:
    """Test that the custom linter catches known anti-patterns."""

    def test_reusable_ci_has_no_lint_errors(self):
        """reusable-ci.yml must pass custom lint with zero errors."""
        from framework.workflow_lint import lint_workflow

        result = lint_workflow(REUSABLE_CI)
        errors = [e for e in result.errors if e.severity == "error"]
        assert not errors, "Lint errors in reusable-ci.yml:\n" + "\n".join(
            str(e) for e in errors
        )

    def test_standalone_ci_has_no_lint_errors(self):
        """standalone-ci.yml must pass custom lint with zero errors."""
        from framework.workflow_lint import lint_workflow

        result = lint_workflow(STANDALONE_CI)
        errors = [e for e in result.errors if e.severity == "error"]
        assert not errors, "Lint errors in standalone-ci.yml:\n" + "\n".join(
            str(e) for e in errors
        )

    def test_ci_yml_has_no_lint_errors(self):
        """ci.yml must pass custom lint with zero errors."""
        from framework.workflow_lint import lint_workflow

        result = lint_workflow(CI_YML)
        errors = [e for e in result.errors if e.severity == "error"]
        assert not errors, "Lint errors in ci.yml:\n" + "\n".join(
            str(e) for e in errors
        )


# ============================================================================
# Structural validation for reusable-ci.yml
# ============================================================================


class TestReusableCIStructure:
    """Validate reusable-ci.yml structure and correctness."""

    @pytest.fixture()
    def workflow(self) -> dict:
        wf, _ = load_workflow(REUSABLE_CI)
        return wf

    def test_is_workflow_call_trigger(self, workflow):
        """Must use workflow_call trigger for reusable pattern."""
        trigger = workflow.get("on", workflow.get(True, {}))
        assert "workflow_call" in trigger

    def test_all_inputs_have_defaults(self, workflow):
        """All inputs must have defaults so consumers can call with zero config."""
        trigger = workflow.get("on", workflow.get(True, {}))
        inputs = trigger["workflow_call"]["inputs"]
        for name, config in inputs.items():
            assert "default" in config, f"Input '{name}' missing default value"

    def test_has_expected_jobs(self, workflow):
        """Check that all core jobs exist (allows additional language-specific jobs)."""
        jobs = set(workflow["jobs"].keys())
        core_jobs = {"detect-changes", "hygiene", "test", "summary"}
        assert core_jobs.issubset(jobs), f"Missing core jobs: {core_jobs - jobs}"

    def test_no_double_expression_wrap_in_job_if(self, workflow):
        """No job-level if: should contain explicit ${{ }}.

        Job-level if: already implicitly wraps in ${{ }}, so explicit wrapping
        causes startup_failure — the exact bug that motivated this test suite.
        """
        for job_name, job_config in workflow["jobs"].items():
            if not isinstance(job_config, dict):
                continue
            job_if = job_config.get("if")
            if job_if and isinstance(job_if, str):
                assert "${{" not in job_if, (
                    f"Job '{job_name}' has double ${{{{ }}}} in if: '{job_if}'. "
                    "Remove the explicit ${{{{ }}}} — job-level if: wraps implicitly."
                )

    def test_no_cross_repo_checkout(self, workflow):
        """No job should checkout external repos — makes workflow fragile."""
        for job_name, job_config in workflow["jobs"].items():
            if not isinstance(job_config, dict):
                continue
            for step in job_config.get("steps", []):
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses", "")
                with_config = step.get("with", {})
                if "actions/checkout" in uses and isinstance(with_config, dict):
                    repo = with_config.get("repository", "")
                    assert not repo or repo == "${{ github.repository }}", (
                        f"Job '{job_name}' checks out external repo '{repo}'. "
                        "Reusable workflow must be self-contained."
                    )

    def test_dependency_review_has_event_guard(self, workflow):
        """dependency-review-action must have pull_request event guard."""
        for job_name, job_config in workflow["jobs"].items():
            if not isinstance(job_config, dict):
                continue
            for step in job_config.get("steps", []):
                if not isinstance(step, dict):
                    continue
                if "dependency-review-action" in step.get("uses", ""):
                    step_if = str(step.get("if", ""))
                    assert "pull_request" in step_if, (
                        f"Job '{job_name}' uses dependency-review-action without "
                        "pull_request event guard. It only works on PR events."
                    )

    def test_summary_job_always_runs(self, workflow):
        """Summary job must use if: always() to run even on failures."""
        summary = workflow["jobs"]["summary"]
        assert summary.get("if") == "always()" or "always()" in str(
            summary.get("if", "")
        )

    def test_summary_needs_all_jobs(self, workflow):
        """Summary job must depend on all other jobs except detect-changes and configure."""
        upstream_only = {"detect-changes", "configure"}
        all_jobs = set(workflow["jobs"].keys()) - {"summary"} - upstream_only
        summary_needs = workflow["jobs"]["summary"].get("needs", [])
        if isinstance(summary_needs, str):
            summary_needs = [summary_needs]
        missing = all_jobs - set(summary_needs)
        assert not missing, f"Summary missing needs: {sorted(missing)}"


# ============================================================================
# pixi-version input: no hardcoded drift, all sites reference the input
# ============================================================================


class TestPixiVersionInput:
    """Validate the pixi-version workflow_call input across reusable workflows.

    reusable-ci.yml and reusable-security.yml both take a `pixi-version`
    input so the pinned pixi CLI version can be overridden per-caller
    (issue #250). These tests replace the old test_consistent_pixi_version,
    which became vacuous once every site was rewritten to the literal string
    `${{ inputs.pixi-version }}` (a single-element set no matter what the
    input's actual default is).
    """

    @pytest.mark.parametrize("path", [REUSABLE_CI, REUSABLE_SECURITY])
    def test_no_hardcoded_pixi_version_literal(self, path):
        """No pixi-version site may hardcode a literal version like v0.74.0."""
        _, raw_lines = load_workflow(path)
        for lineno, line in enumerate(raw_lines, start=1):
            if line.strip().startswith("default:"):
                continue
            match = HARDCODED_PIXI_VERSION_RE.search(line)
            assert not match, (
                f"{path}:{lineno} hardcodes pixi-version '{match.group(1)}' "
                "instead of using ${{ inputs.pixi-version }}"
            )

    @pytest.mark.parametrize("path", [REUSABLE_CI, REUSABLE_SECURITY])
    def test_setup_pixi_steps_reference_input(self, path):
        """Every setup-pixi pixi-version: site must resolve to the input expression."""
        _, raw_lines = load_workflow(path)
        sites = [
            (lineno, match.group(1))
            for lineno, line in enumerate(raw_lines, start=1)
            if (match := PIXI_VERSION_SITE_RE.search(line))
        ]
        assert sites, f"No pixi-version: sites with a value found in {path}"
        for lineno, value in sites:
            assert value == "${{ inputs.pixi-version }}", (
                f"{path}:{lineno} pixi-version does not reference the input: '{value}'"
            )

    @pytest.mark.parametrize("path", [REUSABLE_CI, REUSABLE_SECURITY])
    def test_pixi_version_input_is_well_formed(self, path):
        """The pixi-version input must exist, be an optional string with a vX.Y.Z default."""
        workflow, _ = load_workflow(path)
        trigger = workflow.get("on", workflow.get(True, {}))
        inputs = trigger["workflow_call"]["inputs"]
        assert "pixi-version" in inputs, f"{path} is missing the 'pixi-version' input"
        config = inputs["pixi-version"]
        assert config.get("type") == "string", (
            f"{path} pixi-version input type must be 'string', got {config.get('type')!r}"
        )
        assert config.get("required") is False, (
            f"{path} pixi-version input must be optional (required: false)"
        )
        default = config.get("default")
        assert default and re.match(r"^v\d+\.\d+\.\d+$", default), (
            f"{path} pixi-version default {default!r} is not a valid vX.Y.Z version"
        )

    def test_pixi_version_default_matches_across_reusable_workflows(self):
        """The default pixi-version must be identical in both reusable workflows."""
        ci_workflow, _ = load_workflow(REUSABLE_CI)
        security_workflow, _ = load_workflow(REUSABLE_SECURITY)
        ci_trigger = ci_workflow.get("on", ci_workflow.get(True, {}))
        security_trigger = security_workflow.get("on", security_workflow.get(True, {}))
        ci_default = ci_trigger["workflow_call"]["inputs"]["pixi-version"]["default"]
        security_default = security_trigger["workflow_call"]["inputs"]["pixi-version"][
            "default"
        ]
        assert ci_default == security_default, (
            f"pixi-version default mismatch: reusable-ci={ci_default!r}, "
            f"reusable-security={security_default!r}"
        )


# ============================================================================
# python-version-env-pattern / strict-python-matrix inputs (issue #251)
# ============================================================================


class TestPythonVersionMatrix:
    """Validate the per-Python-version pixi environment resolution (issue #251).

    reusable-ci.yml's `test` and `test-postgres` jobs resolve a per-version
    pixi environment (e.g. `py311`) instead of always using the single
    `pixi-environment` input, and optionally fail the leg when the resolved
    interpreter doesn't match the matrix's declared python-version.
    """

    MATRIX_JOB_NAMES = ["test", "test-postgres"]

    RESOLVE_STEP_NAME = "Resolve pixi environment for this matrix leg"
    VERIFY_STEP_NAME = "Verify interpreter matches this matrix leg"
    INSTALL_STEP_NAME = "Install Dependencies"

    @pytest.fixture()
    def workflow(self) -> dict:
        wf, _ = load_workflow(REUSABLE_CI)
        return wf

    def _step_index(self, steps: list[dict], predicate) -> int:
        for i, step in enumerate(steps):
            if isinstance(step, dict) and predicate(step):
                return i
        raise AssertionError("No matching step found")

    def test_python_version_env_pattern_input_is_well_formed(self, workflow):
        """python-version-env-pattern must be optional string, default 'py{nodot}'."""
        trigger = workflow.get("on", workflow.get(True, {}))
        inputs = trigger["workflow_call"]["inputs"]
        assert "python-version-env-pattern" in inputs, (
            "reusable-ci.yml is missing the 'python-version-env-pattern' input"
        )
        config = inputs["python-version-env-pattern"]
        assert config.get("type") == "string", (
            f"python-version-env-pattern type must be 'string', got {config.get('type')!r}"
        )
        assert config.get("required") is False, (
            "python-version-env-pattern input must be optional (required: false)"
        )
        assert config.get("default") == "py{nodot}", (
            f"python-version-env-pattern default must be 'py{{nodot}}', "
            f"got {config.get('default')!r}"
        )

    def test_strict_python_matrix_input_is_well_formed(self, workflow):
        """strict-python-matrix must be optional boolean, default false."""
        trigger = workflow.get("on", workflow.get(True, {}))
        inputs = trigger["workflow_call"]["inputs"]
        assert "strict-python-matrix" in inputs, (
            "reusable-ci.yml is missing the 'strict-python-matrix' input"
        )
        config = inputs["strict-python-matrix"]
        assert config.get("type") == "boolean", (
            f"strict-python-matrix type must be 'boolean', got {config.get('type')!r}"
        )
        assert config.get("required") is False, (
            "strict-python-matrix input must be optional (required: false)"
        )
        assert config.get("default") is False, (
            f"strict-python-matrix default must be False, got {config.get('default')!r}"
        )

    @pytest.mark.parametrize("job_name", MATRIX_JOB_NAMES)
    def test_resolve_and_verify_steps_exist_in_order(self, workflow, job_name):
        """Resolve must precede install; verify must precede the test-suite step."""
        steps = workflow["jobs"][job_name]["steps"]
        resolve_idx = self._step_index(
            steps, lambda s: s.get("name") == self.RESOLVE_STEP_NAME
        )
        verify_idx = self._step_index(
            steps, lambda s: s.get("name") == self.VERIFY_STEP_NAME
        )
        install_idx = self._step_index(
            steps, lambda s: s.get("name") == self.INSTALL_STEP_NAME
        )
        run_suite_idx = self._step_index(
            steps, lambda s: str(s.get("name", "")).startswith("Run Test Suite")
        )
        assert resolve_idx < install_idx, (
            f"Job '{job_name}': '{self.RESOLVE_STEP_NAME}' must come before "
            f"'{self.INSTALL_STEP_NAME}'"
        )
        assert verify_idx < run_suite_idx, (
            f"Job '{job_name}': '{self.VERIFY_STEP_NAME}' must come before "
            "the 'Run Test Suite' step"
        )

    @pytest.mark.parametrize("job_name", MATRIX_JOB_NAMES)
    def test_no_pixi_environment_input_in_matrix_job_run_bodies(
        self, workflow, job_name
    ):
        """Install/editable-install/test steps must use $RESOLVED_PIXI_ENV, not the raw input."""
        steps = workflow["jobs"][job_name]["steps"]
        target_names = {
            self.INSTALL_STEP_NAME,
            "Editable Install (pixi-only)",
        }
        checked_any = False
        for step in steps:
            if not isinstance(step, dict):
                continue
            name = str(step.get("name", ""))
            is_target = name in target_names or name.startswith("Run Test Suite")
            run_body = step.get("run")
            if not is_target or not isinstance(run_body, str):
                continue
            checked_any = True
            assert "${{ inputs.pixi-environment }}" not in run_body, (
                f"Job '{job_name}' step '{name}' still references "
                "${{ inputs.pixi-environment }} instead of $RESOLVED_PIXI_ENV"
            )
            assert "RESOLVED_PIXI_ENV" in run_body, (
                f"Job '{job_name}' step '{name}' must reference RESOLVED_PIXI_ENV"
            )
        assert checked_any, f"No install/test steps found to check in job '{job_name}'"

    @pytest.mark.parametrize("job_name", MATRIX_JOB_NAMES)
    def test_resolve_step_writes_expected_env_vars(self, workflow, job_name):
        """The resolve step must export RESOLVED_PIXI_ENV and MATRIX_PY_VERSION."""
        steps = workflow["jobs"][job_name]["steps"]
        resolve_step = next(
            s
            for s in steps
            if isinstance(s, dict) and s.get("name") == self.RESOLVE_STEP_NAME
        )
        run_body = resolve_step.get("run", "")
        assert "RESOLVED_PIXI_ENV=" in run_body and '>> "$GITHUB_ENV"' in run_body, (
            f"Job '{job_name}' resolve step must write RESOLVED_PIXI_ENV to $GITHUB_ENV"
        )
        assert "MATRIX_PY_VERSION=" in run_body, (
            f"Job '{job_name}' resolve step must write MATRIX_PY_VERSION to $GITHUB_ENV"
        )

    @pytest.mark.parametrize("job_name", MATRIX_JOB_NAMES)
    def test_matrix_jobs_do_not_use_setup_python(self, workflow, job_name):
        """The matrix jobs must not run actions/setup-python.

        `pixi run` always executes with the pixi environment's own
        interpreter, never the runner-installed one, so a setup-python step
        in these jobs would just reintroduce the false-assurance illusion
        from issue #251 (a job named for Python X.Y that silently tests a
        different interpreter).
        """
        steps = workflow["jobs"][job_name]["steps"]
        assert steps, f"Job '{job_name}' has no steps"
        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = str(step.get("uses", ""))
            assert not uses.startswith("actions/setup-python"), (
                f"Job '{job_name}' step '{step.get('name', '<unnamed>')}' uses "
                f"'{uses}' — actions/setup-python must not appear in the pixi "
                "matrix jobs (see #251)"
            )


# ============================================================================
# Repo-wide invariant: run: bodies never contain raw GHA expressions
# ============================================================================


class TestNoExpressionInterpolationInRunBodies:
    """Lock in the convention that `run:` shell bodies never embed ${{ }}.

    Any value a step needs from inputs/matrix/etc. must be threaded in via
    `env:` and read as a shell variable — never interpolated directly into
    the script text, which is fragile (quoting, injection) and was the root
    cause class behind issues #250/#251.
    """

    @pytest.mark.parametrize("path", [REUSABLE_CI, REUSABLE_SECURITY])
    def test_no_expression_interpolation_in_run_bodies(self, path):
        workflow, _ = load_workflow(path)
        violations = []
        for job_name, job_config in workflow["jobs"].items():
            if not isinstance(job_config, dict):
                continue
            for step in job_config.get("steps", []):
                if not isinstance(step, dict):
                    continue
                run_body = step.get("run")
                if not isinstance(run_body, str):
                    continue
                idx = run_body.find("${{")
                if idx == -1:
                    continue
                end = run_body.find("}}", idx)
                snippet = (
                    run_body[idx : end + 2] if end != -1 else run_body[idx : idx + 30]
                )
                step_name = step.get("name", "<unnamed>")
                violations.append(f"{job_name}/{step_name}: {snippet}")
        assert not violations, (
            f"{path} has run: bodies with raw GHA expression interpolation "
            "(should be threaded via env: instead):\n" + "\n".join(violations)
        )


# ============================================================================
# Structural validation for standalone-ci.yml
# ============================================================================


class TestStandaloneCIStructure:
    """Validate standalone-ci.yml structure and correctness."""

    @pytest.fixture()
    def workflow(self) -> dict:
        wf, _ = load_workflow(STANDALONE_CI)
        return wf

    def test_is_not_workflow_call(self, workflow):
        """Standalone must NOT use workflow_call — it's a direct trigger template."""
        trigger = workflow.get("on", workflow.get(True, {}))
        if isinstance(trigger, dict):
            assert "workflow_call" not in trigger

    def test_has_dispatch_trigger(self, workflow):
        """Must have at least workflow_dispatch trigger.

        In ci-framework repo, standalone uses workflow_dispatch only to avoid
        running against the framework itself. The comments instruct consumers
        to add push/pull_request triggers when copying.
        """
        trigger = workflow.get("on", workflow.get(True, {}))
        # trigger can be a string "workflow_dispatch" or dict
        if isinstance(trigger, str):
            assert trigger == "workflow_dispatch"
        else:
            assert "workflow_dispatch" in trigger

    def test_has_configure_job(self, workflow):
        """Must have configure job for job-level settings."""
        assert "configure" in workflow["jobs"]
        outputs = workflow["jobs"]["configure"].get("outputs", {})
        assert "python-versions" in outputs
        assert "os-matrix" in outputs

    def test_has_expected_jobs(self, workflow):
        """Must have expected content jobs (same as reusable) plus configure."""
        expected = {
            "configure",
            "detect-changes",
            "hygiene",
            "quality",
            "test",
            "security",
            "performance",
            "build",
            "self-heal",
            "summary",
        }
        actual = set(workflow["jobs"].keys())
        assert expected == actual

    def test_no_cross_repo_checkout(self, workflow):
        """Standalone must have zero external dependencies."""
        for job_name, job_config in workflow["jobs"].items():
            if not isinstance(job_config, dict):
                continue
            for step in job_config.get("steps", []):
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses", "")
                with_config = step.get("with", {})
                if "actions/checkout" in uses and isinstance(with_config, dict):
                    repo = with_config.get("repository", "")
                    assert not repo, (
                        f"Job '{job_name}' checks out external repo '{repo}'. "
                        "Standalone template must be fully self-contained."
                    )

    def test_has_top_level_permissions(self, workflow):
        """Must declare top-level permissions for security."""
        assert "permissions" in workflow

    def test_has_env_block(self, workflow):
        """Must have env block for step-level configuration."""
        assert "env" in workflow
        env = workflow["env"]
        assert "PIXI_VERSION" in env
        assert "PIXI_ENVIRONMENT" in env
        assert "PACKAGE_PATH" in env


# ============================================================================
# Structural validation for reusable-release.yml
# ============================================================================


class TestReusableReleaseStructure:
    """Validate reusable-release.yml structure and correctness."""

    @pytest.fixture()
    def workflow(self) -> dict:
        wf, _ = load_workflow(REUSABLE_RELEASE)
        return wf

    def test_is_workflow_call_trigger(self, workflow):
        """Must use workflow_call trigger for reusable pattern."""
        trigger = workflow.get("on", workflow.get(True, {}))
        assert "workflow_call" in trigger

    def test_no_permissions_declared(self, workflow):
        """Must NOT declare top-level or job-level permissions.

        The caller must provide id-token: write and contents: write at the
        calling job level. If the reusable workflow declares these permissions
        itself, it causes startup_failure for callers whose token scope
        cannot satisfy them.
        """
        # No top-level permissions
        assert "permissions" not in workflow, (
            "reusable-release.yml must not declare top-level permissions — "
            "the caller provides them"
        )
        # No job-level permissions
        for job_name, job_config in workflow["jobs"].items():
            if isinstance(job_config, dict):
                assert "permissions" not in job_config, (
                    f"Job '{job_name}' must not declare permissions — "
                    "the caller provides them"
                )

    def test_has_event_guard(self, workflow):
        """Publish job must guard against non-push events."""
        publish = workflow["jobs"]["publish"]
        job_if = str(publish.get("if", ""))
        assert "push" in job_if, (
            "Publish job must guard on push event to prevent accidental "
            "publishing on PRs"
        )

    def test_downloads_artifact(self, workflow):
        """Must download the build artifact from the CI pipeline."""
        publish = workflow["jobs"]["publish"]
        download_steps = [
            s
            for s in publish.get("steps", [])
            if isinstance(s, dict) and "download-artifact" in s.get("uses", "")
        ]
        assert download_steps, "Publish job must download build artifact"

    def test_no_double_expression_wrap(self, workflow):
        """No job-level if: should contain explicit ${{ }}."""
        for job_name, job_config in workflow["jobs"].items():
            if not isinstance(job_config, dict):
                continue
            job_if = job_config.get("if")
            if job_if and isinstance(job_if, str):
                assert "${{" not in job_if, (
                    f"Job '{job_name}' has double ${{{{ }}}} in if: '{job_if}'"
                )


# ============================================================================
# Cross-file consistency
# ============================================================================


class TestCrossFileConsistency:
    """Validate consistency between reusable and standalone workflows."""

    def test_same_content_jobs(self):
        """Core jobs should match between reusable and standalone (security/quality may differ)."""
        reusable, _ = load_workflow(REUSABLE_CI)
        standalone, _ = load_workflow(STANDALONE_CI)

        reusable_jobs = set(reusable["jobs"].keys())
        standalone_jobs = set(standalone["jobs"].keys())
        # These jobs differ: reusable has multi-lang, standalone has Python-only
        multi_lang_jobs = {
            "python-dep-audit",
            "rust-dep-audit",
            "rust-deny",
            "js-dep-audit",
            "sast-semgrep",
            "sast-codeql",
            "secret-scan",
            "scorecard",
            "python-quality",
            "python-lint",
            "python-format",
            "python-types",
            "rust-lint",
            "rust-format",
            "c-cpp-lint",
            "cython-lint",
            "js-lint",
        }
        old_jobs = {"security", "quality"}
        # Optional service-container jobs only in reusable workflow
        optional_service_jobs = {"test-postgres"}
        reusable_core = (
            reusable_jobs - multi_lang_jobs - old_jobs - optional_service_jobs
        )
        standalone_core = standalone_jobs - multi_lang_jobs - old_jobs - {"configure"}
        assert reusable_core == standalone_core, (
            f"Core job mismatch: reusable={sorted(reusable_core)}, standalone={sorted(standalone_core)}"
        )

    def test_action_versions_match(self):
        """Action versions should be consistent across workflows."""
        reusable_text = REUSABLE_CI.read_text()
        standalone_text = STANDALONE_CI.read_text()

        # Extract action@version pairs
        action_re = re.compile(r"uses:\s*([\w/-]+)@(v\d+)")

        reusable_actions = {}
        for match in action_re.finditer(reusable_text):
            reusable_actions[match.group(1)] = match.group(2)

        standalone_actions = {}
        for match in action_re.finditer(standalone_text):
            standalone_actions[match.group(1)] = match.group(2)

        # Check common actions have same versions
        common = set(reusable_actions.keys()) & set(standalone_actions.keys())
        mismatches = []
        for action in sorted(common):
            if reusable_actions[action] != standalone_actions[action]:
                mismatches.append(
                    f"  {action}: reusable={reusable_actions[action]}, "
                    f"standalone={standalone_actions[action]}"
                )

        assert not mismatches, "Action version mismatches:\n" + "\n".join(mismatches)


class TestOwnCiUsesCommittedLockfile:
    """Guards for #257: this framework must dogfood the lockfile it demands.

    `.gitignore` used to ignore this repo's own `pixi.lock`. setup-pixi runs
    `pixi install --locked` only when a lockfile is present and a plain,
    re-solving `pixi install` otherwise, so ignoring the lock made every CI run
    here non-reproducible — while the hygiene job in reusable-ci.yml fails any
    consumer lacking a lock and docs/ci-workflow-guide.md recommends `--locked`.
    """

    def test_gitignore_does_not_ignore_pixi_lock(self):
        """A committed pixi.lock is what makes setup-pixi install --locked."""
        entries = [
            line.strip()
            for line in Path(".gitignore").read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        assert "pixi.lock" not in entries, (
            "`.gitignore` ignores pixi.lock. setup-pixi only runs "
            "`pixi install --locked` when a lockfile is present, so ignoring "
            "the lock silently makes this repo's own CI non-reproducible (#257)"
        )

    def test_pixi_lock_is_present(self):
        """The lockfile this framework requires of consumers must exist here."""
        assert Path("pixi.lock").is_file(), (
            "pixi.lock is missing from the repo root; #257 requires this "
            "framework to ship the lockfile it demands of its consumers"
        )

    def test_own_ci_installs_are_locked(self):
        """Every `pixi install` in ci.yml must pass --locked.

        Deliberately scoped to ci.yml, which installs THIS repo's environments.
        reusable-ci.yml, standalone-ci.yml and actions/* install the consumer's
        environment, where --locked would be a breaking change (#257).
        """
        _, lines = load_workflow(CI_YML)
        installs = [line for line in lines if "pixi install" in line]
        assert installs, "ci.yml has no `pixi install` lines — test is vacuous"
        offenders = [
            f"line {n}: {line.strip()}"
            for n, line in enumerate(lines, start=1)
            if "pixi install" in line and "--locked" not in line
        ]
        assert not offenders, (
            "these `pixi install` sites in ci.yml omit --locked: "
            + "; ".join(offenders)
        )
