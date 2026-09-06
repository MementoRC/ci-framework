"""Tests for the #277 blocking pre-commit CI gate.

`.pre-commit-config.yaml` has always declared hooks, and #268/PR #287 fixed
`pre-commit`/`install-pre-commit` to delegate to the `quality-extended` env
(`pixi run -e quality-extended <impl>`) instead of bare-invoking a tool the
caller's current env might not provide. But nothing in CI ever ran the
hooks: a contributor who never ran `pixi run install-pre-commit` locally
could merge code the hooks would have rejected. The hooks were reachable in
principle and nothing made them actually run - two independent halves of
the same defect, and this file guards both:

- reachability: `pre-commit`/`install-pre-commit` resolve to an env that
  actually provides the `pre-commit` package (not just any env) - reuses
  the env->package map (`build_env_to_packages`) built for #268's
  `test_pixi_quality_tasks.py` rather than duplicating it.
- invocation: at least one CI workflow actually runs the hooks, discovered
  by walking every `.github/workflows/*.yml` rather than naming one file -
  the exact staleness failure mode named in #255/#261/#279.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from framework.tests.utils.pixi_meta import WORKFLOWS_DIR, ci_invokes_task
from framework.tests.workflows.test_pixi_quality_tasks import (
    DELEGATION_TARGET_RE,
    build_env_to_packages,
    load_manifest,
    load_tasks,
    task_cmd,
)

PRE_COMMIT_CONFIG = Path(".pre-commit-config.yaml")


def load_pre_commit_hook_ids() -> list[str]:
    """Return every hook id declared across every repo in .pre-commit-config.yaml."""
    doc = yaml.safe_load(PRE_COMMIT_CONFIG.read_text())
    hook_ids: list[str] = []
    for repo in doc.get("repos", []) if isinstance(doc, dict) else []:
        if not isinstance(repo, dict):
            continue
        for hook in repo.get("hooks", []) or []:
            if isinstance(hook, dict) and "id" in hook:
                hook_ids.append(hook["id"])
    return hook_ids


def resolve_delegated_env(cmd: str) -> str | None:
    """Return the env a `pixi run -e <env> <target>` command delegates to, or None."""
    match = DELEGATION_TARGET_RE.match(cmd.strip())
    return match.group(1) if match is not None else None


class TestPreCommitConfigIsNonVacuous:
    """Anti-vacuity: an empty hook parse would make every other test meaningless."""

    def test_pre_commit_config_was_actually_found(self):
        assert PRE_COMMIT_CONFIG.is_file(), (
            f"{PRE_COMMIT_CONFIG} not found — run tests from the repo root"
        )

    def test_pre_commit_config_declares_at_least_one_hook(self):
        hook_ids = load_pre_commit_hook_ids()
        assert hook_ids, (
            ".pre-commit-config.yaml declares no hooks — the reachability "
            "and invocation guards in this file would be meaningless"
        )


class TestPreCommitTasksReachAnEnvWithThePackage:
    """`pre-commit`/`install-pre-commit` must resolve to an env that
    actually provides the `pre-commit` package, not just any env - the
    #268 defect class where a delegation to an env lacking the tool 127s.
    """

    def test_pre_commit_task_delegates_to_env_providing_pre_commit(self):
        tasks = load_tasks()
        assert "pre-commit" in tasks, "'pre-commit' task not found in pyproject.toml"
        cmd = task_cmd(tasks["pre-commit"])
        assert cmd is not None, "'pre-commit' has no command"
        env = resolve_delegated_env(cmd)
        assert env is not None, (
            f"'pre-commit' command {cmd!r} does not delegate via "
            "'pixi run -e <env> <target>'"
        )
        packages = build_env_to_packages(load_manifest())
        assert "pre-commit" in packages.get(env, set()), (
            f"'pre-commit' task delegates to env {env!r}, which does not "
            "provide the 'pre-commit' package"
        )

    def test_install_pre_commit_task_delegates_to_env_providing_pre_commit(self):
        tasks = load_tasks()
        assert "install-pre-commit" in tasks, (
            "'install-pre-commit' task not found in pyproject.toml"
        )
        cmd = task_cmd(tasks["install-pre-commit"])
        assert cmd is not None, "'install-pre-commit' has no command"
        env = resolve_delegated_env(cmd)
        assert env is not None, (
            f"'install-pre-commit' command {cmd!r} does not delegate via "
            "'pixi run -e <env> <target>'"
        )
        packages = build_env_to_packages(load_manifest())
        assert "pre-commit" in packages.get(env, set()), (
            f"'install-pre-commit' task delegates to env {env!r}, which "
            "does not provide the 'pre-commit' package"
        )


class TestCiActuallyRunsPreCommit:
    """The other half of #277: the hooks existed, but nothing in CI ran them."""

    def test_workflow_files_were_actually_found(self):
        """Vacuity guard: no workflow files would make the walk trivial."""
        assert WORKFLOWS_DIR.is_dir(), f"{WORKFLOWS_DIR} not found"
        workflows = sorted(WORKFLOWS_DIR.glob("*.yml"))
        assert workflows, f"no workflow files found in {WORKFLOWS_DIR}"

    def test_discoverer_does_not_find_a_nonexistent_task(self):
        """Anti-vacuity: a discoverer that always returns True would make
        the positive assertion below pass for free, whether or not any
        workflow actually invokes pre-commit.
        """
        workflows = sorted(WORKFLOWS_DIR.glob("*.yml"))
        assert not any(
            ci_invokes_task("this-task-does-not-exist-277", workflow=path)
            for path in workflows
        ), "discoverer reported a nonexistent task as invoked — it is broken"

    def test_some_ci_workflow_invokes_pre_commit(self):
        """Walks every workflow file rather than naming one - the #255/#261/#279 shape.

        A hand-named single file (e.g. only checking ci.yml) would silently
        stop covering a future workflow reorganisation the same way a
        hand-maintained file list did for #279.
        """
        workflows = sorted(WORKFLOWS_DIR.glob("*.yml"))
        found = [
            path.name
            for path in workflows
            if ci_invokes_task("pre-commit", workflow=path)
        ]
        assert found, (
            "no `run:` step in any .github/workflows/*.yml invokes `pixi "
            "run [-e <env>] pre-commit` — the pre-commit hooks are "
            "declared in .pre-commit-config.yaml but nothing in CI runs them"
        )
