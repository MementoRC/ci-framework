"""Tests for pixi task quality-gate conventions in pyproject.toml.

These tests validate that the `quality` aggregate task and its members
follow the env-self-contained delegation convention used throughout this
project (a user-facing task like `lint` delegates to `pixi run -e quality
lint-impl`, rather than being a bare command that only works if the caller
happens to pass `-e quality`). A bare command silently falls back to the
default env and fails with "command not found" instead of running the
intended tool.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

PYPROJECT = Path("pyproject.toml")
TEMPLATE_PYPROJECT = Path("templates/pyproject-tiered-template.toml")

# Env-delegation guards accept both the short (`-e`) and long
# (`--environment`) pixi flag forms, and tolerate extra whitespace.
ENV_DELEGATION_RE = re.compile(r"^pixi\s+run\s+(?:-e|--environment)\s+[\w.-]+\s")
QUALITY_ENV_DELEGATION_RE = re.compile(
    r"^pixi\s+run\s+(?:-e|--environment)\s+quality(?:\s|$)"
)
# Captures (env, target-task) from a `pixi run -e/--environment <env> <task> ...` command.
DELEGATION_TARGET_RE = re.compile(
    r"^pixi\s+run\s+(?:-e|--environment)\s+([\w.-]+)\s+([\w.-]+)"
)


CI_WORKFLOWS_DIR = Path(".github/workflows")

# `ruff check` invoked as a command — at the start of a command or right after
# a shell separator. Never matches `ruff format`, nor `ruff` as an argument.
RUFF_CHECK_RE = re.compile(r"(?:^|&&|\|\||\||;)\s*ruff\s+check\b")
# Value of `--select=X,Y` or `--select X,Y`.
RUFF_SELECT_RE = re.compile(r"--select[=\s]+([A-Za-z0-9,]+)")
# Task name from `pixi run [-e <env>] <task>`.
PIXI_RUN_TASK_RE = re.compile(
    r"pixi\s+run\s+(?:(?:-e|--environment)\s+[\w.-]+\s+)?([\w.-]+)"
)

# Sentinel for `ruff check` with no `--select`: the full configured ruleset,
# which by definition covers every narrower selection.
FULL_RULESET = None


def resolve_task_commands(
    tasks: dict, name: str, _seen: frozenset[str] = frozenset()
) -> list[str]:
    """Expand a pixi task into every concrete command it actually runs.

    Follows `depends-on` edges and `pixi run -e <env> <target>` delegations
    transitively, so callers see the commands at the leaves rather than the
    one-line indirection at the top. Cycles terminate via `_seen`.
    """
    if name in _seen or name not in tasks:
        return []
    _seen = _seen | {name}
    task = tasks[name]
    commands: list[str] = []
    for dep in task_depends_on(task):
        commands.extend(resolve_task_commands(tasks, dep, _seen))
    cmd = task_cmd(task)
    if cmd is None:
        return commands
    match = PIXI_RUN_TASK_RE.match(cmd.strip())
    if match is not None and match.group(1) in tasks:
        commands.extend(resolve_task_commands(tasks, match.group(1), _seen))
    else:
        commands.append(cmd)
    return commands


def ruff_check_rulesets(commands: list[str]) -> list[frozenset[str] | None]:
    """Return one ruleset per `ruff check` command in `commands`.

    A ruleset is the frozenset of `--select` rule prefixes, or FULL_RULESET
    when nothing narrows the invocation.
    """
    rulesets: list[frozenset[str] | None] = []
    for cmd in commands:
        if not RUFF_CHECK_RE.search(cmd):
            continue
        select = RUFF_SELECT_RE.search(cmd)
        if select is None:
            rulesets.append(FULL_RULESET)
        else:
            rulesets.append(frozenset(p for p in select.group(1).split(",") if p))
    return rulesets


def ruleset_covers(local: frozenset[str] | None, ci: frozenset[str] | None) -> bool:
    """True when `local` checks at least everything `ci` checks."""
    if local is FULL_RULESET:
        return True
    if ci is FULL_RULESET:
        return False
    return ci <= local


def describe_ruleset(ruleset: frozenset[str] | None) -> str:
    """Render a ruleset for assertion messages."""
    if ruleset is FULL_RULESET:
        return "full configured ruleset"
    return "--select=" + ",".join(sorted(ruleset))


def iter_workflow_run_bodies(doc: object) -> Iterator[str]:
    """Yield every `run:` body in a parsed workflow or action document.

    Covers workflow jobs and composite-action steps alike, so a `run:` body
    is found wherever it lives rather than wherever a regex happened to look.
    """
    if not isinstance(doc, dict):
        return
    for job in (doc.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                yield step["run"]
    runs = doc.get("runs")
    if isinstance(runs, dict):
        for step in runs.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                yield step["run"]


def workflow_ruff_check_commands(path: Path, tasks: dict) -> list[str]:
    """Every `ruff check` command a workflow file causes to run.

    Parses the YAML structurally rather than scanning lines: the body of a
    `run:` block is a plain shell script once the document is parsed, so a
    bare `ruff check .` written as a single-line `run:` value is found the
    same way as one inside a block scalar. Line scanning missed the former.
    """
    commands: list[str] = []
    for body in iter_workflow_run_bodies(yaml.safe_load(path.read_text())):
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if "pixi run" in line:
                for match in PIXI_RUN_TASK_RE.finditer(line):
                    if match.group(1) in tasks:
                        commands.extend(resolve_task_commands(tasks, match.group(1)))
            elif RUFF_CHECK_RE.search(line):
                commands.append(line)
    return commands


def load_tasks() -> dict:
    """Load the [tool.pixi.tasks] table from pyproject.toml."""
    data = tomllib.loads(PYPROJECT.read_text())
    return data["tool"]["pixi"]["tasks"]


def task_depends_on(task: dict | str) -> list[str]:
    """Return the depends-on list for a task, or an empty list if none."""
    if isinstance(task, dict):
        depends = task.get("depends-on", [])
        return list(depends) if depends else []
    return []


def task_cmd(task: dict | str) -> str | None:
    """Return the command string for a task, or None if it has no cmd."""
    if isinstance(task, str):
        return task
    if isinstance(task, dict):
        cmd = task.get("cmd")
        return cmd if isinstance(cmd, str) else None
    return None


def load_template_tasks() -> dict:
    """Load the [tool.pixi.tasks] table from the tiered pyproject template."""
    data = tomllib.loads(TEMPLATE_PYPROJECT.read_text())
    return data["tool"]["pixi"]["tasks"]


def load_template_manifest() -> dict:
    """Load the full parsed template manifest (for feature/environment tables)."""
    return tomllib.loads(TEMPLATE_PYPROJECT.read_text())


def build_tool_to_feature_map(manifest: dict) -> dict[str, str]:
    """Map each tool/binary name to the pixi feature that declares it.

    Parses every `[tool.pixi.feature.<name>.dependencies]` table directly
    from the manifest, so the tracked tool universe reflects whatever the
    template actually declares instead of a hand-maintained literal list —
    the exact staleness failure mode this guard exists to prevent (#255,
    #261). There is no exclusion list: every tool declared under a feature
    is tracked, and any task that bare-invokes one must earn its exemption
    structurally by being an `-impl` leaf.
    """
    features = manifest.get("tool", {}).get("pixi", {}).get("feature", {})
    tool_to_feature: dict[str, str] = {}
    for feature_name, feature_table in features.items():
        deps = (
            feature_table.get("dependencies", {})
            if isinstance(feature_table, dict)
            else {}
        )
        for dep_name in deps:
            tool_to_feature.setdefault(dep_name, feature_name)
    return tool_to_feature


def build_feature_to_environments_map(manifest: dict) -> dict[str, set]:
    """Map each pixi feature to the set of environments that include it."""
    environments = manifest.get("tool", {}).get("pixi", {}).get("environments", {})
    feature_to_envs: dict[str, set] = {}
    for env_name, env_table in environments.items():
        if not isinstance(env_table, dict):
            continue
        for feature_name in env_table.get("features", []):
            feature_to_envs.setdefault(feature_name, set()).add(env_name)
    return feature_to_envs


def find_direct_tool_invocation(cmd: str, tool_to_feature: dict) -> str | None:
    """Return the tracked tool name `cmd` directly invokes, or None.

    Matches a tool name only when it is the command being run — at the very
    start of `cmd`, or immediately after a shell separator (&&, |, ;) — never
    when it merely appears as an argument. A `pixi run ...` delegation is
    never a direct invocation, since it only references a task name.
    """
    if not tool_to_feature or cmd.strip().startswith("pixi run"):
        return None
    pattern = re.compile(
        r"(?:^|&&|\||;)\s*(" + "|".join(re.escape(t) for t in tool_to_feature) + r")\b"
    )
    match = pattern.search(cmd)
    return match.group(1) if match else None


@pytest.fixture(scope="module")
def template_manifest() -> dict:
    """Parse the template manifest once per module, not once per parametrized case."""
    return load_template_manifest()


@pytest.fixture(scope="module")
def template_tool_to_feature(template_manifest: dict) -> dict:
    return build_tool_to_feature_map(template_manifest)


@pytest.fixture(scope="module")
def template_feature_to_envs(template_manifest: dict) -> dict:
    return build_feature_to_environments_map(template_manifest)


class TestQualityGateTasksAreEnvSelfContained:
    """Validate that the `quality` aggregate and its members are env-self-contained.

    Follows the convention seen in `lint`/`lint-impl` and
    `typecheck`/`typecheck-impl`: a user-facing task delegates to an
    `-impl` task run in the `quality` env via `pixi run -e quality
    <name>-impl`, so it works from any starting env. `format-check` used
    to break this convention as a bare `ruff format --check framework/`
    command, which exits 127 "command not found" unless the caller
    happens to pass `-e quality` themselves.
    """

    def test_quality_task_was_actually_found(self):
        """Vacuity guard: a silently-empty parse would make the other tests trivially pass."""
        tasks = load_tasks()
        assert tasks, "Parsed pixi tasks table is empty — parse likely failed silently"
        assert "quality" in tasks, "'quality' task not found in pyproject.toml"
        depends_on = task_depends_on(tasks["quality"])
        assert len(depends_on) >= 4, (
            f"'quality' depends-on has only {len(depends_on)} entries "
            f"({depends_on!r}) — expected at least 4"
        )

    def test_quality_aggregate_includes_format_check(self):
        """`format-check` must be a member of the mandatory pre-commit `quality` gate.

        Without this, formatting was silently absent from the mandatory
        pre-commit gate: `pixi run quality` could pass while unformatted
        code slipped through, since nothing in the aggregate ever ran
        `ruff format --check`.
        """
        tasks = load_tasks()
        depends_on = task_depends_on(tasks["quality"])
        assert "format-check" in depends_on, (
            f"'quality' depends-on {depends_on!r} is missing 'format-check'"
        )

    def test_quality_gate_members_are_env_self_contained(self):
        """Every task the `quality` gate depends on must be env-self-contained.

        A task is self-contained if its command delegates to an explicit env
        via `pixi run -e <env>` or `pixi run --environment <env>`, or if it
        is itself a depends-on aggregate with no `cmd` of its own. A bare
        tool invocation like `ruff format --check framework/` fails this
        check because it only works if the caller happens to already be in
        the right env.
        """
        tasks = load_tasks()
        depends_on = task_depends_on(tasks["quality"])
        offenders = []
        for name in depends_on:
            assert name in tasks, (
                f"'{name}' listed in quality depends-on but not defined"
            )
            task = tasks[name]
            cmd = task_cmd(task)
            if cmd is None:
                # Aggregate task with no cmd of its own (e.g. depends-on only).
                continue
            if not ENV_DELEGATION_RE.match(cmd):
                offenders.append(f"{name!r}: {cmd!r}")
        assert not offenders, (
            "these quality-gate members are not env-self-contained "
            "(command must delegate via 'pixi run -e <env>' or "
            "'pixi run --environment <env>'): " + "; ".join(offenders)
        )

    def test_ci_format_check_delegates_to_quality_env(self):
        """`ci-format-check` must delegate to the quality env, not run bare."""
        tasks = load_tasks()
        assert "ci-format-check" in tasks, "'ci-format-check' task not found"
        cmd = task_cmd(tasks["ci-format-check"])
        assert cmd is not None, "'ci-format-check' has no command"
        assert QUALITY_ENV_DELEGATION_RE.match(cmd), (
            f"'ci-format-check' command {cmd!r} does not delegate to the quality env"
        )


class TestTemplateFormatCheckTasksAreEnvSelfContained:
    """Guard the tiered pyproject template against the same #267 regression.

    `templates/pyproject-tiered-template.toml` is copied into every project
    scaffolded from it, so a bare `ruff format --check {{ source_path }}`
    there reproduces the exit-127 "command not found" bug for every
    generated project, not just this repo.
    """

    def test_template_tasks_were_actually_found(self):
        """Vacuity guard: a silently-empty parse would make the other tests trivially pass."""
        tasks = load_template_tasks()
        assert tasks, (
            "Parsed template pixi tasks table is empty — parse likely failed silently"
        )
        assert "format-check" in tasks, "'format-check' task not found in template"
        assert "ci-format-check" in tasks, (
            "'ci-format-check' task not found in template"
        )

    def test_template_format_check_delegates_to_quality_env(self):
        """`format-check` in the template must delegate, not run bare."""
        tasks = load_template_tasks()
        cmd = task_cmd(tasks["format-check"])
        assert cmd is not None, "'format-check' has no command"
        assert QUALITY_ENV_DELEGATION_RE.match(cmd), (
            f"'format-check' command {cmd!r} does not delegate to the quality env"
        )

    def test_template_ci_format_check_delegates_to_quality_env(self):
        """`ci-format-check` in the template must delegate, not run bare."""
        tasks = load_template_tasks()
        cmd = task_cmd(tasks["ci-format-check"])
        assert cmd is not None, "'ci-format-check' has no command"
        assert QUALITY_ENV_DELEGATION_RE.match(cmd), (
            f"'ci-format-check' command {cmd!r} does not delegate to the quality env"
        )

    def test_template_quality_aggregate_includes_format_check(self):
        """`format-check` must be a member of the template's mandatory quality gate."""
        tasks = load_template_tasks()
        depends_on = task_depends_on(tasks["quality"])
        assert "format-check" in depends_on, (
            f"template 'quality' depends-on {depends_on!r} is missing 'format-check'"
        )


class TestTemplateToolInvokingTasksFollowDelegationConvention:
    """Data-driven guard for the #267/#268 defect class across ALL template tasks.

    Hand-listing "the tasks this applies to" (as the class above does for
    `format-check`/`ci-format-check`) goes stale whenever a new bare
    tool-invoking task is added — see #255, #261. This derives the tracked
    tool universe from the manifest itself (every dependency declared under
    `[tool.pixi.feature.*.dependencies]`, mapped to the smallest
    `[tool.pixi.environments]` entries that provide each feature) and walks
    every task in the template's `[tool.pixi.tasks]`:

    - if a task's command directly bare-invokes a tracked tool, its name
      must end in `-impl` (bare tool invocations only belong in `-impl`
      leaf tasks, run inside an env that provides the tool);
    - if a task delegates (`pixi run -e/--environment <env> <target>`) to a
      target task that itself directly bare-invokes a tracked tool, the
      delegation's env must actually provide the feature that declares that
      tool — not just any env.
    """

    def test_template_task_table_was_actually_found(self):
        """Vacuity guard: a silently-empty parse would make the other tests trivially pass."""
        tasks = load_template_tasks()
        assert tasks, (
            "Parsed template pixi tasks table is empty — parse likely failed silently"
        )

    def test_template_tool_and_environment_maps_were_actually_found(
        self, template_tool_to_feature, template_feature_to_envs
    ):
        """Vacuity guard: empty derived maps would make the other tests trivially pass."""
        tool_to_feature = template_tool_to_feature
        feature_to_envs = template_feature_to_envs
        assert tool_to_feature, (
            "Parsed template tool→feature map is empty — parse likely failed silently"
        )
        assert "bandit" in tool_to_feature, (
            "'bandit' not found in template's tool→feature map"
        )
        assert feature_to_envs, (
            "Parsed template feature→environments map is empty — parse likely failed silently"
        )
        assert "quality" in feature_to_envs, (
            "'quality' feature not found in template's feature→environments map"
        )

    @pytest.mark.parametrize("name", sorted(load_template_tasks()))
    def test_template_task_tool_delegation_convention(
        self,
        name,
        template_manifest,
        template_tool_to_feature,
        template_feature_to_envs,
    ):
        tasks = template_manifest["tool"]["pixi"]["tasks"]
        tool_to_feature = template_tool_to_feature
        feature_to_envs = template_feature_to_envs

        cmd = task_cmd(tasks[name])
        if cmd is None:
            pytest.skip(f"{name!r} has no cmd (depends-on aggregate)")

        tool = find_direct_tool_invocation(cmd, tool_to_feature)
        if tool is not None:
            assert name.endswith("-impl"), (
                f"{name!r} directly invokes {tool!r} ({cmd!r}), a tool declared "
                f"in the {tool_to_feature[tool]!r} feature, but its name does "
                "not end in '-impl' — bare tool invocations must live in an "
                "'-impl' leaf task"
            )
            return

        match = DELEGATION_TARGET_RE.match(cmd.strip())
        if match is None:
            return
        env, target = match.group(1), match.group(2)
        target_task = tasks.get(target)
        if target_task is None:
            return
        target_cmd = task_cmd(target_task)
        if target_cmd is None:
            return
        target_tool = find_direct_tool_invocation(target_cmd, tool_to_feature)
        if target_tool is None:
            return
        required_feature = tool_to_feature[target_tool]
        providing_envs = feature_to_envs.get(required_feature, set())
        assert env in providing_envs, (
            f"{name!r} delegates to {target!r} (which directly invokes "
            f"{target_tool!r}, declared in the {required_feature!r} feature) "
            f"via env {env!r}, but {env!r} does not provide the "
            f"{required_feature!r} feature — provided by: {sorted(providing_envs)!r}"
        )


class TestLocalQualityGateCoversCiLintRuleset:
    """Guard #271: the mandatory local gate must not be weaker than CI.

    `quality` used to depend on `lint` (`ruff check --select=F,E9`) while CI
    ran `lint-full` (the full configured ruleset). Every rule outside `F` and
    `E9` — the whole `UP`/`I`/`B`/`C4`/`W` surface — was therefore unchecked
    locally and enforced in CI, so a clean `pixi run quality` was not evidence
    a PR would pass. It cost a full push cycle per violation, twice (#266,
    #270) before being named.

    This compares *rulesets only*, not the paths each invocation targets:
    CI's `ruff check .` and the local `ruff check framework/` legitimately
    differ in scope, and widening local scope is a separate question from
    ruleset drift.
    """

    def test_ci_workflows_were_actually_found(self):
        """Vacuity guard: no workflow files would make the comparison trivial."""
        assert CI_WORKFLOWS_DIR.is_dir(), (
            f"{CI_WORKFLOWS_DIR} not found — run tests from the repo root"
        )
        workflows = sorted(CI_WORKFLOWS_DIR.glob("*.yml"))
        assert workflows, f"no workflow files found in {CI_WORKFLOWS_DIR}"

    def test_ci_runs_at_least_one_ruff_check(self):
        """Vacuity guard: finding zero CI ruff checks would pass the gate test for free."""
        tasks = load_tasks()
        found = [
            (path.name, cmd)
            for path in sorted(CI_WORKFLOWS_DIR.glob("*.yml"))
            for cmd in workflow_ruff_check_commands(path, tasks)
        ]
        assert found, (
            "no `ruff check` invocation discovered in any workflow — the "
            "ruleset-drift guard would pass vacuously"
        )

    def test_bare_ruff_check_in_run_block_is_discovered(self):
        """A bare `ruff check` in a `run:` block must be found, not only `pixi run` tasks.

        reusable-quality.yml runs `ruff check .` directly rather than through a
        pixi task. An earlier version of `workflow_ruff_check_commands` missed
        it because `ruff` sat after the `run:` key, so the guard covered less
        than its docstring claimed — the exact defect class this file exists
        to prevent.
        """
        tasks = load_tasks()
        bare = [
            cmd
            for path in sorted(CI_WORKFLOWS_DIR.glob("*.yml"))
            for cmd in workflow_ruff_check_commands(path, tasks)
            if cmd.startswith("ruff check")
        ]
        assert bare, (
            "no bare `ruff check` command discovered in any workflow `run:` "
            "block — YAML `run:` prefix stripping has regressed"
        )

    def test_quality_gate_runs_at_least_one_ruff_check(self):
        """Vacuity guard: the gate must actually lint, or coverage is meaningless."""
        tasks = load_tasks()
        rulesets = ruff_check_rulesets(resolve_task_commands(tasks, "quality"))
        assert rulesets, (
            "the `quality` gate resolves to no `ruff check` command at all — "
            "it cannot cover CI's lint job"
        )

    def test_quality_gate_ruleset_covers_every_ci_ruff_check(self):
        """Every ruleset CI enforces must be a subset of one the local gate runs.

        This is the assertion that stops #271 recurring: narrowing the gate,
        or widening CI, fails here instead of on a push.
        """
        tasks = load_tasks()
        local_rulesets = ruff_check_rulesets(resolve_task_commands(tasks, "quality"))
        offenders = []
        for path in sorted(CI_WORKFLOWS_DIR.glob("*.yml")):
            for cmd in workflow_ruff_check_commands(path, tasks):
                for ci_ruleset in ruff_check_rulesets([cmd]):
                    if any(
                        ruleset_covers(local, ci_ruleset) for local in local_rulesets
                    ):
                        continue
                    offenders.append(
                        f"{path.name}: CI runs {describe_ruleset(ci_ruleset)}, "
                        f"local `quality` gate only runs "
                        f"{[describe_ruleset(r) for r in local_rulesets]}"
                    )
        assert not offenders, (
            "the mandatory local `quality` gate is weaker than CI, so a clean "
            "local run does not predict CI: " + "; ".join(offenders)
        )


class TestTemplateQualityGateCoversTemplateCiLintRuleset:
    """Same #271 guard for the tiered template every scaffolded project inherits."""

    def test_template_quality_gate_runs_at_least_one_ruff_check(self):
        """Vacuity guard: an empty resolution would make the coverage test trivial."""
        tasks = load_template_tasks()
        rulesets = ruff_check_rulesets(resolve_task_commands(tasks, "quality"))
        assert rulesets, (
            "the template's `quality` gate resolves to no `ruff check` command"
        )

    def test_template_quality_gate_covers_template_ci_lint(self):
        """The template's gate must not be weaker than the `ci-lint` it ships."""
        tasks = load_template_tasks()
        local_rulesets = ruff_check_rulesets(resolve_task_commands(tasks, "quality"))
        ci_rulesets = ruff_check_rulesets(resolve_task_commands(tasks, "ci-lint"))
        assert ci_rulesets, "the template's `ci-lint` resolves to no `ruff check`"
        offenders = [
            describe_ruleset(ci)
            for ci in ci_rulesets
            if not any(ruleset_covers(local, ci) for local in local_rulesets)
        ]
        assert not offenders, (
            "the template's `quality` gate is weaker than its own `ci-lint`: "
            f"ci-lint runs {offenders}, gate runs "
            f"{[describe_ruleset(r) for r in local_rulesets]}"
        )


# ===== #268: direct-task binary resolves in the `default` pixi env =====
#
# `pixi run <task>` with no `-e` resolves `<task>` in the `default`
# environment. Every task fixed in #268 bare-invoked a quality/security/dev
# only tool and therefore 127'd unless the caller happened to already be in
# the right env; each was converted to the `<task> = "pixi run -e <env>
# <task>-impl"` delegation pattern already used by `lint`/`format-check`/etc.
# This section guards the defect class from recurring, built by DISCOVERY
# over `[tool.pixi.tasks]` rather than a hand-maintained task list — the
# #255/#261 failure mode (a narrower list than reality) this whole file
# exists to avoid.

# Binary -> conda package name, for every binary this manifest's tasks
# directly invoke. An unmapped binary must fail the guard loudly (see
# `resolve_binary_package`) rather than be silently skipped — silently
# skipping unknowns is exactly the #255/#261 failure this guard exists to
# prevent.
BINARY_TO_PACKAGE = {
    "ruff": "ruff",
    "mypy": "mypy",
    "pytest": "pytest",
    "radon": "radon",
    "vulture": "vulture",
    "bandit": "bandit",
    "pip-audit": "pip-audit",
    "pre-commit": "pre-commit",
    "detect-secrets": "bc-detect-secrets",
    "cyclonedx-py": "cyclonedx-bom",
    "yamllint": "yamllint",
    "actionlint": "actionlint",
    "shellcheck": "shellcheck",
    "python -m build": "python-build",
}

# Shell/OS-level utilities that are never pixi-managed packages: they are on
# PATH regardless of which pixi environment is active (coreutils, and `pixi`
# itself — the tool orchestrating the whole task graph, invoked bare by
# `emergency-fix`). Treated the same as "no package needed".
ALWAYS_AVAILABLE_BINARIES = frozenset({"echo", "rm", "pixi"})

# Sentinel returned by `resolve_binary_package` for a binary that needs no
# pixi package: an `ALWAYS_AVAILABLE_BINARIES` entry, or one of this repo's
# own `python -m framework.*` modules (stdlib-only, never pip/conda-installed
# — see `install-editable`).
NO_PACKAGE_NEEDED = "<no-package-needed>"


def load_manifest() -> dict:
    """Load the full parsed pyproject.toml manifest."""
    return tomllib.loads(PYPROJECT.read_text())


def classify_task(task: dict | str) -> str:
    """Classify a pixi task as 'delegating', 'depends-only', or 'direct'.

    - 'delegating': the command is a `pixi run -e/--environment <env> ...`
      indirection to another task — always resolves, whatever env the
      caller started from.
    - 'depends-only': a dict with no `cmd` of its own (a `depends-on`
      aggregate like `quality` or `static-analysis`).
    - 'direct': any other command string — a bare tool invocation that
      resolves in whatever env the caller happens to already be in.
    """
    cmd = task_cmd(task)
    if cmd is None:
        return "depends-only"
    if ENV_DELEGATION_RE.match(cmd.strip()):
        return "delegating"
    return "direct"


def extract_invoked_binary(cmd: str) -> str:
    """Return the binary a 'direct' task command invokes.

    Takes the first shell token, except for `python -m <module>`, which
    returns `"python -m <module>"` verbatim — the module is what determines
    the providing package (e.g. `python -m build` -> the `python-build`
    package), not the interpreter.
    """
    tokens = cmd.strip().split()
    if len(tokens) >= 3 and tokens[0] == "python" and tokens[1] == "-m":
        return f"python -m {tokens[2]}"
    return tokens[0]


def resolve_binary_package(task_name: str, binary: str) -> str:
    """Map an invoked binary to its providing conda package name.

    Returns `NO_PACKAGE_NEEDED` for shell utilities and this repo's own
    `python -m framework.*` modules. Raises for anything else not in
    `BINARY_TO_PACKAGE` — an unmapped binary must fail loudly, naming the
    task and the binary, so a maintainer adds a mapping entry instead of the
    guard silently skipping a task it does not understand (#255, #261).
    """
    if binary in ALWAYS_AVAILABLE_BINARIES:
        return NO_PACKAGE_NEEDED
    if binary.startswith("python -m framework."):
        return NO_PACKAGE_NEEDED
    if binary in BINARY_TO_PACKAGE:
        return BINARY_TO_PACKAGE[binary]
    raise AssertionError(
        f"task {task_name!r} directly invokes unmapped binary {binary!r} — "
        "add a BINARY_TO_PACKAGE entry (or an ALWAYS_AVAILABLE_BINARIES / "
        "python-module-prefix exemption) in test_pixi_quality_tasks.py "
        "before this guard can classify it"
    )


def build_env_to_features(manifest: dict) -> dict[str, list[str]]:
    """Map each `[tool.pixi.environments]` entry to its feature list.

    `default` has no `features` key at all — it gets the base
    `[tool.pixi.dependencies]` only, by pixi's own convention.
    """
    environments = manifest.get("tool", {}).get("pixi", {}).get("environments", {})
    env_to_features: dict[str, list[str]] = {}
    for env_name, env_table in environments.items():
        features = env_table.get("features", []) if isinstance(env_table, dict) else []
        env_to_features[env_name] = list(features)
    return env_to_features


def build_env_to_packages(manifest: dict) -> dict[str, set]:
    """Map each pixi environment to the union of package names it provides.

    An environment's package set is the base `[tool.pixi.dependencies]`
    table plus every `[tool.pixi.feature.<f>.dependencies]` table for each
    feature listed under it in `[tool.pixi.environments]` — mirroring how
    pixi itself resolves an environment, so "available in an env" here means
    what it means to pixi, not an approximation of it.
    """
    pixi = manifest.get("tool", {}).get("pixi", {})
    base_packages = set(pixi.get("dependencies", {}))
    features = pixi.get("feature", {})
    env_to_packages: dict[str, set] = {}
    for env_name, feature_names in build_env_to_features(manifest).items():
        packages = set(base_packages)
        for feature_name in feature_names:
            feature_table = features.get(feature_name, {})
            if isinstance(feature_table, dict):
                packages |= set(feature_table.get("dependencies", {}))
        env_to_packages[env_name] = packages
    return env_to_packages


class TestPixiTaskClassifier:
    """Self-test for `classify_task`/`extract_invoked_binary`.

    A classifier that mislabelled everything as 'delegating' would make
    `TestDirectTasksResolveInDefaultEnv`'s main assertion pass for free —
    this pins the classifier against literal, known-shape samples so that
    can't happen silently.
    """

    def test_classifies_delegating_command(self):
        assert classify_task("pixi run -e quality lint-impl") == "delegating"

    def test_classifies_direct_command(self):
        assert classify_task("ruff check framework/") == "direct"

    def test_classifies_depends_only_table(self):
        assert classify_task({"depends-on": ["a", "b"]}) == "depends-only"

    def test_classifies_python_module_form_as_direct(self):
        cmd = "python -m build"
        assert classify_task(cmd) == "direct"
        assert extract_invoked_binary(cmd) == "python -m build"


class TestPixiTaskDiscoveryIsNonVacuous:
    """Guard the discovery walk itself: an empty or broken walk must fail,
    not silently pass every downstream assertion for free.
    """

    def test_discovery_found_a_non_trivial_task_set_with_every_class(self):
        tasks = load_tasks()
        classes = {name: classify_task(task) for name, task in tasks.items()}
        assert len(classes) > 20, (
            f"only {len(classes)} tasks discovered in [tool.pixi.tasks] — "
            "the discovery walk is likely broken"
        )
        found_classes = set(classes.values())
        assert found_classes == {"delegating", "depends-only", "direct"}, (
            f"expected all three task classes present, found only {found_classes}"
        )


class TestEnvPackageResolution:
    """Guard `build_env_to_packages` itself.

    Pins the very fact that makes the #268 guard meaningful: `ruff` is a
    `quality`-feature dependency, not a base one, so it is genuinely absent
    from `default`. If this ever stopped being true, the whole delegation
    convention would be unnecessary — this test would be the one to notice.
    """

    def test_ruff_absent_from_default_present_in_quality(self):
        env_to_packages = build_env_to_packages(load_manifest())
        assert "ruff" not in env_to_packages["default"], (
            "'ruff' unexpectedly present in the default env's package set — "
            "either the manifest changed or build_env_to_packages is wrong"
        )
        assert "ruff" in env_to_packages["quality"], (
            "'ruff' expected in the quality env's package set via the quality feature"
        )


class TestDirectTasksResolveInDefaultEnv:
    """The #268 guard: every bare, user-invocable pixi task must actually run.

    `pixi run <task>` with no `-e` resolves `<task>` in the `default`
    environment. A 'direct' task (see `classify_task`) whose invoked binary
    is not a `default`-env package will 127 for any caller who runs it that
    way — the exact defect class Parts 1-3 of #268 fixed. `-impl` tasks are
    exempt by convention: they are leaf tasks only ever reached through a
    `pixi run -e <env> <name>-impl` delegation, never invoked bare by a
    human (the delegating wrapper is what a caller actually runs).
    """

    def test_every_direct_task_binary_has_a_package_mapping(self):
        """Anti-vacuity: an unknown binary must fail loudly here — for
        every direct task, `-impl` or not — rather than being silently
        skipped.
        """
        tasks = load_tasks()
        for name, task in tasks.items():
            if classify_task(task) != "direct":
                continue
            binary = extract_invoked_binary(task_cmd(task))
            resolve_binary_package(name, binary)  # raises AssertionError if unmapped

    def test_every_non_impl_direct_task_resolves_in_default_env(self):
        manifest = load_manifest()
        tasks = load_tasks()
        default_packages = build_env_to_packages(manifest)["default"]

        offenders = []
        for name, task in tasks.items():
            if name.endswith("-impl"):
                continue
            if classify_task(task) != "direct":
                continue
            binary = extract_invoked_binary(task_cmd(task))
            package = resolve_binary_package(name, binary)
            if package == NO_PACKAGE_NEEDED:
                continue
            if package not in default_packages:
                offenders.append(
                    f"{name!r} bare-invokes {binary!r} (package {package!r}), "
                    "not present in the default env's package set"
                )
        assert not offenders, (
            "these tasks are directly invocable via `pixi run <task>` (no "
            "-e) but bare-invoke a tool the default env does not provide, "
            "so they 127 for any caller who is not already in the right "
            "env: " + "; ".join(offenders)
        )
