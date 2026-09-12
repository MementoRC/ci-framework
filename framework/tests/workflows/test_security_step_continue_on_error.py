"""Guard: no security-relevant step in a shipped workflow swallows its failure.

Issue #288: the "Run detect-secrets" step in `ci.yml`'s `security-scan` job
carried `continue-on-error: true` on top of a task that was already broken (its
`--exclude-files` arguments were shell globs, not regexes, so `detect-secrets
scan` raised `re.error` on every invocation and never actually completed a
scan). `continue-on-error: true` hid that: the step turned red in the logs but
green in the job result, so nothing failed CI and nothing forced a fix.

Issue #304 found that the guard written for that lesson had two blind spots,
and that a green run could not be told apart from a clean bill of health - it
reported "no security step is exempted" while 18 of them were:

  1. It walked only `ci.yml`. `standalone-ci.yml`, `reusable-ci.yml` and
     `reusable-security.yml` were outside its blast radius entirely. It now
     walks every file GitHub would actually run from `.github/workflows/`, and
     `test_anchor_workflows_each_yield_a_security_step` keeps that walk
     non-vacuous per file rather than only in aggregate.

  2. Its classifier recognised a scanner only when it was reached through a
     `pixi run <task>` indirection, so a step shelling straight out to
     `semgrep ci` or `npm audit`, or a `uses:` not on its marker list
     (`actions-rust-lang/audit`), was invisible to it. Several of #304's
     findings were exactly that shape; `DIRECT_SCANNER_RE` closes it.

What this guard does NOT assert is a blanket ban on `continue-on-error: true`
for security steps, which is what #304 assumed the fix would be. Both reusable
workflows pair each exempted scanner with a step that re-raises its failure:

    - name: TruffleHog scan
      id: trufflehog
      continue-on-error: true
    - name: Fail on verified secrets
      if: inputs.fail-on-secrets && steps.trufflehog.outcome == 'failure'
      run: exit 1

There the `continue-on-error: true` is load-bearing: it is precisely what makes
the `fail-on-secrets` input mean anything to a consumer. Stripping it would not
harden the scan, it would break a documented opt-out. So the real invariant,
asserted by `test_exempted_security_step_has_a_downstream_failure_gate`, is:

    a security-relevant step may carry `continue-on-error: true` only if some
    later step in the same job fails the job on its `outcome == 'failure'`

and, separately, that any such gate hanging off a `workflow_call` input has
that input defaulting to `true` - a gate defaulting to `false` is a scanner
that is advisory until a consumer opts in, which is #288's silence moved up one
level. `fail-on-sast` is exactly that, and is tracked in #305.

SARIF upload steps are classified as non-scanner infrastructure and are not
gated at all: an upload failing is a permissions or API problem, not a finding.
That classification is only honest while #306 - which suspects those uploads
have been failing silently in every job whose `permissions:` block omits
`security-events: write` - stays open and visible.

The two exemption maps below (`_KNOWN_UNGATED`, `_GATE_DEFAULTS_OFF`) are the
DOCUMENTED, tracked mechanism inherited from #290/#292/#301: every entry must
cite an issue, and `test_documented_exemptions_are_not_stale` forces deletion
once the entry's subject stops matching.

The pixi-manifest and workflow parsing primitives live in
`framework/tests/utils/pixi_meta.py`, shared with `test_yaml_lint_scope.py`,
`test_workflow_lint_scope.py` and `test_pre_commit_ci_gate.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from framework.tests.utils.pixi_meta import (
    PIXI_RUN_TASK_RE,
    WORKFLOWS_DIR,
    load_tasks,
    logical_run_lines,
    resolve_task_commands,
    shipped_workflow_files,
)

# `uses:` references that are themselves security tooling, matched by substring
# so a version pin (`@v4`, `@vX.Y.Z`) never breaks the match.
SECURITY_ACTION_MARKERS = (
    "codeql-action",
    "trufflehog",
    "gitleaks",
    "semgrep",
    "dependency-review-action",
    # cargo-audit ships only as an Action, so no pixi task resolution can ever
    # reach it and SECURITY_TOOL_MARKERS below cannot see it (#304).
    "actions-rust-lang/audit",
)

# `uses:` references matching a marker above that are NOT scanners: they ship an
# already-computed result somewhere else. Checked BEFORE
# SECURITY_ACTION_MARKERS, because `github/codeql-action/upload-sarif` contains
# `codeql-action` and would otherwise classify as a scanner.
#
# An upload failing is an infrastructure problem - a missing
# `security-events: write`, a rate-limited API - not a security finding, so
# `continue-on-error: true` on one hides nothing about the code under test.
# #306 suspects these uploads have in fact been failing silently; that is a
# reason to fix the permissions, not a reason to fail CI on an upload.
NON_SCANNER_ACTION_MARKERS = ("upload-sarif",)

# Substrings of a *resolved* pixi task command that mark it as invoking a
# secret/vulnerability/SAST scanner. Matched against the leaf command (after
# following the `pixi run -e <env> <impl>` indirection), not the task name, so a
# task rename can't accidentally opt a step out of this guard.
SECURITY_TOOL_MARKERS = (
    "bandit",
    "pip-audit",
    "detect-secrets",
    "safety",
    "trufflehog",
    "gitleaks",
    "semgrep",
)

# Scanners invoked as a bare command in a `run:` body rather than through a
# `pixi run <task>` indirection (#304).
DIRECT_SCANNER_COMMANDS = (
    "bandit",
    "cargo audit",
    "cargo-audit",
    "detect-secrets",
    "gitleaks",
    "npm audit",
    "pip-audit",
    "safety",
    "semgrep",
    "trufflehog",
)

# A scanner name only counts in *command position*: the start of a logical line,
# or straight after a `|`, `&&`, `||`, `;` or `(`, optionally behind `sudo`.
# Matching anywhere in the body would classify the dependency-audit steps' own
# `echo "::notice::No safety-check pixi task found"` as a scanner invocation.
DIRECT_SCANNER_RE = re.compile(
    r"(?:^|[|&;(])\s*(?:sudo\s+)?(?:"
    + "|".join(re.escape(command) for command in DIRECT_SCANNER_COMMANDS)
    + r")\b"
)

# Workflows that must each yield at least one security-relevant step. Naming
# them keeps the walk honest per file: a renamed directory, a typo'd suffix
# filter or a classifier regression would otherwise report green across every
# file at once, which is the exact failure mode #304 was filed about.
ANCHOR_WORKFLOWS = (
    "ci.yml",
    "reusable-ci.yml",
    "reusable-security.yml",
    "standalone-ci.yml",
)

# Identifier -> reason, for security steps carrying `continue-on-error: true`
# with no downstream step re-raising the failure. Empty: #304 fixed all three
# that existed (both scanners in standalone-ci.yml's `security` job, and
# reusable-security.yml's CodeQL `analyze`, split so the analysis gates and only
# the SARIF upload stays tolerant). Kept as the documented mechanism - every
# entry needs its own tracked issue.
_KNOWN_UNGATED: dict[str, str] = {}

# Identifier -> reason, for security steps whose downstream gate exists but
# hangs off a `workflow_call` input defaulting to `false`, making the scanner
# advisory until a consumer opts in.
_GATE_DEFAULTS_OFF: dict[str, str] = {
    "reusable-ci.yml::sast-semgrep::Run Semgrep": (
        "fail-on-sast defaults to false. SEMGREP_RULES is p/python plus "
        "p/security-audit, an audit ruleset tuned for review breadth rather "
        "than gating, so defaulting it true would turn adopters' pipelines red "
        "on advisory findings. Policy call tracked in #305."
    ),
    "reusable-security.yml::sast-semgrep::Run Semgrep": (
        "fail-on-sast defaults to false - the same step as the reusable-ci.yml "
        "entry above, duplicated verbatim between the two workflows. Tracked "
        "in #305."
    ),
}

_ISSUE_REF_RE = re.compile(r"#\d+")
_INPUT_REF_RE = re.compile(r"inputs\.([A-Za-z0-9_-]+)")


def workflow_call_inputs(doc: object) -> dict:
    """The `on.workflow_call.inputs` table of a parsed workflow, or `{}`.

    YAML 1.1 resolves a bare `on:` key to the boolean `True`, which is what
    `yaml.safe_load` hands back, so reading `doc["on"]` alone returns nothing
    and every default-checking assertion would pass vacuously.
    `test_reusable_workflow_inputs_parse` pins that down.
    """
    if not isinstance(doc, dict):
        return {}
    on_block = doc.get("on", doc.get(True)) or {}
    if not isinstance(on_block, dict):
        return {}
    workflow_call = on_block.get("workflow_call") or {}
    if not isinstance(workflow_call, dict):
        return {}
    inputs = workflow_call.get("inputs") or {}
    return inputs if isinstance(inputs, dict) else {}


def invoked_task_names(run_body: str) -> list[str]:
    """Every pixi task name a `run:` body invokes, across all its lines."""
    names = []
    for raw_line in logical_run_lines(run_body):
        line = raw_line.strip()
        if "pixi run" not in line:
            continue
        match = PIXI_RUN_TASK_RE.search(line)
        if match is not None:
            names.append(match.group(1))
    return names


def is_non_scanner_step(step: dict) -> bool:
    """True when `step` ships an already-computed result rather than scanning."""
    uses = step.get("uses")
    return isinstance(uses, str) and any(
        marker in uses.lower() for marker in NON_SCANNER_ACTION_MARKERS
    )


def uses_security_action(step: dict) -> bool:
    """True when `step`'s `uses:` names a known security Action."""
    uses = step.get("uses")
    return isinstance(uses, str) and any(
        marker in uses.lower() for marker in SECURITY_ACTION_MARKERS
    )


def runs_security_tool_via_pixi(run_body: str, tasks: dict) -> bool:
    """True when a `run:` body reaches a scanner through a pixi task."""
    for name in invoked_task_names(run_body):
        for cmd in resolve_task_commands(tasks, name):
            if any(marker in cmd.lower() for marker in SECURITY_TOOL_MARKERS):
                return True
    return False


def runs_security_tool_directly(run_body: str) -> bool:
    """True when a `run:` body invokes a scanner binary in command position."""
    return any(
        DIRECT_SCANNER_RE.search(raw_line.strip().lower())
        for raw_line in logical_run_lines(run_body)
    )


def is_security_relevant_step(step: dict, tasks: dict) -> bool:
    """True when `step` invokes a known secret/vulnerability/SAST scanner."""
    if is_non_scanner_step(step):
        return False
    if uses_security_action(step):
        return True
    run = step.get("run")
    if not isinstance(run, str):
        return False
    return runs_security_tool_via_pixi(run, tasks) or runs_security_tool_directly(run)


def step_label(step: dict, index: int) -> str:
    """A stable human-readable label for a step.

    Prefers `name`, then `id`, then `uses`: an unnamed `uses:` step is better
    identified by what it runs than by a positional index that shifts whenever a
    step is inserted above it - which is what an exemption entry would otherwise
    be pinned to.
    """
    for key in ("name", "id", "uses"):
        value = step.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return f"<step {index}>"


def discover_security_steps(
    path: Path, doc: object, tasks: dict
) -> list[tuple[str, dict, list, int]]:
    """Every security-relevant step in one parsed workflow.

    Returns `(identifier, step, sibling_steps, index)`. The sibling list and
    index come along so a caller can look *forward* in the same job for a step
    re-raising this one's failure, without re-walking the document.
    """
    if not isinstance(doc, dict):
        return []
    found: list[tuple[str, dict, list, int]] = []
    for job_name, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps") or []
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            if not is_security_relevant_step(step, tasks):
                continue
            identifier = f"{path.name}::{job_name}::{step_label(step, index)}"
            found.append((identifier, step, steps, index))
    return found


def security_steps_by_workflow() -> dict[str, list[tuple[str, dict, list, int]]]:
    """Every security-relevant step in every shipped workflow, keyed by filename."""
    tasks = load_tasks()
    discovered: dict[str, list[tuple[str, dict, list, int]]] = {}
    for path in shipped_workflow_files():
        doc = yaml.safe_load(path.read_text())
        discovered[path.name] = discover_security_steps(path, doc, tasks)
    return discovered


def exempted_security_steps() -> list[tuple[str, dict, list, int]]:
    """Only the security-relevant steps carrying `continue-on-error: true`."""
    return [
        entry
        for entries in security_steps_by_workflow().values()
        for entry in entries
        if entry[1].get("continue-on-error") is True
    ]


def downstream_failure_gates(steps: list, index: int, step_id: str | None) -> list[str]:
    """`if:` expressions of later steps in the job re-raising `step_id`'s failure."""
    if not step_id:
        return []
    pattern = re.compile(
        r"steps\." + re.escape(step_id) + r"\.outcome\s*==\s*'failure'"
    )
    gates = []
    for later in steps[index + 1 :]:
        if not isinstance(later, dict):
            continue
        condition = later.get("if")
        if isinstance(condition, str) and pattern.search(condition):
            gates.append(condition)
    return gates


def test_every_shipped_workflow_parses():
    """A workflow failing to parse would contribute zero steps, silently."""
    files = shipped_workflow_files()
    assert files, "no workflow files discovered - the walk is broken"
    unparsed = [
        path.name
        for path in files
        if not isinstance(yaml.safe_load(path.read_text()), dict)
    ]
    assert not unparsed, (
        "these workflow files did not parse as a mapping, so every check in "
        f"this module silently skipped them: {unparsed}"
    )


def test_anchor_workflows_each_yield_a_security_step():
    """Non-vacuity, per file: each anchor must contribute at least one step."""
    discovered = security_steps_by_workflow()
    empty = [name for name in ANCHOR_WORKFLOWS if not discovered.get(name)]
    assert not empty, (
        "these workflows contain scanners but the walk found none in them - "
        f"the walk or the classifier is broken, not the workflows: {empty}"
    )


def test_direct_scanner_classification_fires_on_the_real_tree():
    """At least one real step must be classified by the direct-command path.

    #288's classifier only followed `pixi run <task>`. If a regex edit ever
    breaks `DIRECT_SCANNER_RE`, this fails here rather than quietly reverting
    the guard to its old blind spot (#304).
    """
    direct = [
        identifier
        for entries in security_steps_by_workflow().values()
        for identifier, step, _steps, _index in entries
        if isinstance(step.get("run"), str) and runs_security_tool_directly(step["run"])
    ]
    assert direct, (
        "no step was classified by the direct-command path - DIRECT_SCANNER_RE "
        "matches nothing, so bare `semgrep ci` / `npm audit` invocations are "
        "invisible to this guard again (#304)"
    )


def test_exempted_security_step_has_a_downstream_failure_gate():
    """Every `continue-on-error: true` scanner must have its failure re-raised.

    This is the real #288 invariant. A scanner whose failure nothing reacts to
    is green-when-red; a scanner paired with a `Fail on ...` step is a
    consumer-facing policy switch, and `continue-on-error: true` is what makes
    that switch work. Collects every violation before asserting once, so a
    failure names all of them in a single run.
    """
    ungated = []
    for identifier, step, steps, index in exempted_security_steps():
        if identifier in _KNOWN_UNGATED:
            continue
        if not downstream_failure_gates(steps, index, step.get("id")):
            ungated.append(identifier)
    assert not ungated, (
        "these security-relevant steps carry `continue-on-error: true` with no "
        "later step in the same job failing on their `outcome == 'failure'`, so "
        "a real finding passes the job (and therefore CI) silently: "
        f"{'; '.join(sorted(ungated))}"
    )


def test_downstream_gate_inputs_default_to_failing():
    """A gate controlled by a `workflow_call` input must default to failing.

    `if: inputs.fail-on-cve && steps.audit.outcome == 'failure'` only gates
    anything when `fail-on-cve` defaults to true. Defaulting it false ships a
    scanner that runs, reports, and fails nothing unless a consumer goes looking
    for the input - #288's silence one level up.
    """
    tasks = load_tasks()
    advisory = []
    for path in shipped_workflow_files():
        doc = yaml.safe_load(path.read_text())
        inputs = workflow_call_inputs(doc)
        for identifier, step, steps, index in discover_security_steps(path, doc, tasks):
            if step.get("continue-on-error") is not True:
                continue
            if identifier in _GATE_DEFAULTS_OFF:
                continue
            for condition in downstream_failure_gates(steps, index, step.get("id")):
                for input_name in _INPUT_REF_RE.findall(condition):
                    declared = inputs.get(input_name)
                    if isinstance(declared, dict) and declared.get("default") is False:
                        advisory.append(f"{identifier} (inputs.{input_name})")
    assert not advisory, (
        "these security scanners are gated on a workflow_call input that "
        "defaults to false, so they report findings and fail nothing unless a "
        f"consumer opts in: {'; '.join(sorted(advisory))}"
    )


def test_reusable_workflow_inputs_parse():
    """Non-vacuity for the defaults check: `on:` is the YAML 1.1 boolean True.

    If `workflow_call_inputs` ever stops finding the inputs table,
    `test_downstream_gate_inputs_default_to_failing` would pass for free on
    every workflow.
    """
    for name in ("reusable-ci.yml", "reusable-security.yml"):
        inputs = workflow_call_inputs(
            yaml.safe_load((WORKFLOWS_DIR / name).read_text())
        )
        assert "fail-on-cve" in inputs, (
            f"{name}: workflow_call inputs did not parse - every default "
            "assertion in this module is vacuous"
        )


def test_documented_exemptions_cite_a_tracked_issue():
    """Every exemption entry must name the issue tracking its removal."""
    uncited = [
        identifier
        for mapping in (_KNOWN_UNGATED, _GATE_DEFAULTS_OFF)
        for identifier, reason in mapping.items()
        if not _ISSUE_REF_RE.search(reason)
    ]
    assert not uncited, (
        "these exemption entries cite no tracked issue - an exemption without "
        f"one is a silent hole, which is what #304 was about: {uncited}"
    )


def test_documented_exemptions_are_not_stale():
    """Exemptions must name steps that still exist and are still exempt.

    Guards the lists in both directions: a renamed, removed or no-longer-exempt
    step must have its entry deleted rather than left to silently over-broaden
    the exemption for whatever moves into its place.
    """
    exempt = {
        identifier for identifier, _step, _steps, _index in exempted_security_steps()
    }
    stale = [
        identifier
        for mapping in (_KNOWN_UNGATED, _GATE_DEFAULTS_OFF)
        for identifier in mapping
        if identifier not in exempt
    ]
    assert not stale, (
        "these exemption entries name steps that no longer exist, are no longer "
        "security-relevant, or no longer carry `continue-on-error: true` - "
        "delete them; the issue each cites may already be fixed: "
        f"{sorted(stale)}"
    )


def test_classifier_flags_a_pixi_task_scanner():
    """Self-test: the `pixi run <task>` classification path fires."""
    doc = yaml.safe_load(
        """
        jobs:
          fake-security-job:
            steps:
              - name: "Run Bandit (synthetic)"
                run: pixi run -e quality-extended security-scan
                continue-on-error: true
        """
    )
    discovered = discover_security_steps(Path("synthetic.yml"), doc, load_tasks())
    assert [identifier for identifier, *_rest in discovered] == [
        "synthetic.yml::fake-security-job::Run Bandit (synthetic)"
    ]


def test_classifier_flags_a_direct_scanner_invocation():
    """Self-test: a bare `npm audit` is classified with no pixi task involved."""
    doc = yaml.safe_load(
        """
        jobs:
          fake-js-job:
            steps:
              - name: npm audit
                run: npm audit --audit-level=high
                continue-on-error: true
        """
    )
    assert discover_security_steps(Path("synthetic.yml"), doc, load_tasks()), (
        "direct-command classification failed on `npm audit` (#304)"
    )


def test_classifier_ignores_a_notice_mentioning_a_scanner():
    """Self-test: a scanner name outside command position is not an invocation."""
    doc = yaml.safe_load(
        """
        jobs:
          fake-job:
            steps:
              - name: Say something
                run: echo "::notice::No safety-check pixi task found"
                continue-on-error: true
        """
    )
    assert not discover_security_steps(Path("synthetic.yml"), doc, load_tasks()), (
        "an `echo` mentioning a scanner classified as a scanner invocation - "
        "DIRECT_SCANNER_RE is not anchored to command position"
    )


def test_classifier_ignores_a_sarif_upload_step():
    """Self-test: `upload-sarif` is infrastructure, not a scanner (#306)."""
    doc = yaml.safe_load(
        """
        jobs:
          fake-upload-job:
            steps:
              - name: Upload SARIF
                uses: github/codeql-action/upload-sarif@v4
                continue-on-error: true
        """
    )
    assert not discover_security_steps(Path("synthetic.yml"), doc, load_tasks()), (
        "a SARIF upload classified as a scanner - NON_SCANNER_ACTION_MARKERS "
        "must be checked before SECURITY_ACTION_MARKERS, since "
        "`codeql-action/upload-sarif` contains `codeql-action`"
    )


def test_gate_detection_separates_a_gated_step_from_an_ungated_one():
    """Self-test: `downstream_failure_gates` actually distinguishes the two."""
    doc = yaml.safe_load(
        """
        jobs:
          gated:
            steps:
              - name: TruffleHog scan
                id: trufflehog
                uses: trufflesecurity/trufflehog@v3.97.4
                continue-on-error: true
              - name: Fail on verified secrets
                if: inputs.fail-on-secrets && steps.trufflehog.outcome == 'failure'
                run: exit 1
          ungated:
            steps:
              - name: TruffleHog scan
                id: trufflehog
                uses: trufflesecurity/trufflehog@v3.97.4
                continue-on-error: true
        """
    )
    results = {
        identifier.split("::")[1]: downstream_failure_gates(
            steps, index, step.get("id")
        )
        for identifier, step, steps, index in discover_security_steps(
            Path("synthetic.yml"), doc, load_tasks()
        )
    }
    assert results["gated"], "a gated step was reported as ungated"
    assert not results["ungated"], "an ungated step was reported as gated"
