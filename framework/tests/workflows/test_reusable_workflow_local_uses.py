"""Guards against `./`-relative `uses:` refs in reusable workflows (#262).

Inside a workflow triggered by `workflow_call`, a `./`-relative `uses:` value
resolves against the CALLER's checkout, not this repo. Reusable workflows are
by definition only ever invoked by external consumers, so a `./`-relative
action reference in one can never resolve and is dead on arrival - it just
happens to go unnoticed because nothing in this repo's own CI calls its own
reusable workflows.

This guard is data-driven: it walks every workflow file and classifies it as
reusable by checking for `workflow_call` under `on:`, rather than hardcoding
which workflows are reusable. A hand-maintained list is exactly the kind of
thing that goes stale (#255, #261).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS_DIR = Path(".github/workflows")


def _workflow_files() -> list[Path]:
    return sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))


def _get_on(doc: dict):
    """Return the `on:` trigger mapping.

    YAML parses an unquoted `on:` key as the boolean `True`, not the string
    "on" (YAML 1.1 boolean-word rule), so the key actually present in the
    parsed dict depends on how the file spells it. Handle both forms.
    """
    if "on" in doc:
        return doc["on"]
    return doc.get(True, {})


def _is_reusable(doc: dict) -> bool:
    """A workflow is reusable if `workflow_call` appears under its `on:` key."""
    trigger = _get_on(doc)
    if isinstance(trigger, dict):
        return "workflow_call" in trigger
    if isinstance(trigger, list | str):
        return "workflow_call" in trigger
    return False


def _iter_uses_values(node):
    """Recursively yield every `uses:` value found anywhere in the document."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "uses" and isinstance(value, str):
                yield value
            else:
                yield from _iter_uses_values(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_uses_values(item)


def _reusable_workflow_paths() -> list[Path]:
    reusable = []
    for path in _workflow_files():
        doc = yaml.safe_load(path.read_text())
        if isinstance(doc, dict) and _is_reusable(doc):
            reusable.append(path)
    return reusable


@pytest.mark.parametrize("path", _workflow_files(), ids=str)
def test_reusable_workflows_have_no_relative_local_uses(path):
    """A `workflow_call` workflow must not reference actions via `./`-relative uses:.

    `./`-relative refs resolve against the CALLER's checkout inside a reusable
    workflow, not this repo, so they can never resolve for any consumer.
    """
    doc = yaml.safe_load(path.read_text())
    if not isinstance(doc, dict) or not _is_reusable(doc):
        pytest.skip(f"{path} is not a reusable (workflow_call) workflow")

    offenders = [uses for uses in _iter_uses_values(doc) if uses.startswith("./")]
    assert not offenders, (
        f"{path} is a reusable workflow (workflow_call) but references "
        f"local action(s) via ./-relative uses:, which cannot resolve for "
        f"any external consumer (#262): {offenders}. Use a pinned remote "
        "ref instead, e.g. "
        "'Claire-s-Monster/ci-framework/actions/<name>@vX.Y.Z "
        "# x-release-please-version'."
    )


def test_guard_is_not_vacuous():
    """The parametrization must cover real files, and at least one reusable one."""
    files = _workflow_files()
    assert len(files) > 5, f"expected many workflow files, found {files}"
    reusable = _reusable_workflow_paths()
    assert reusable, (
        "no workflow classified as reusable (workflow_call) - the guard "
        "would silently check nothing"
    )


def test_guard_detects_the_pre_fix_shape():
    """This is the guard's own regression test (#262).

    `test_guard_is_not_vacuous` only proves the parametrization covers real
    reusable files - it never proves an actual offender would be caught. A
    bug in `_is_reusable` or `_iter_uses_values` (e.g. mishandling the
    `on:` -> `True` key parsing quirk) would make every parametrized case
    silently pass. This test reproduces the PRE-FIX shape of
    self-healing.yml in-memory, via `yaml.safe_load` (so the same `on:`
    parsing path real files take is exercised), and asserts the helpers
    both classify it as reusable and flag its `./`-relative `uses:` as an
    offender.
    """
    doc = yaml.safe_load(
        """
        on:
          workflow_call:
        jobs:
          heal:
            steps:
              - uses: ./actions/self-healing
        """
    )

    assert _is_reusable(doc), (
        "pre-fix self-healing.yml shape (workflow_call trigger) was not "
        "classified as reusable - the guard would never have fired"
    )

    offenders = [uses for uses in _iter_uses_values(doc) if uses.startswith("./")]
    assert offenders == ["./actions/self-healing"], (
        f"expected the ./-relative uses: to be flagged as an offender, got {offenders}"
    )


def test_guard_does_not_over_fire_on_non_reusable_relative_uses():
    """A non-reusable workflow with a legitimate `./`-relative `uses:` must pass.

    Mirrors the shape of ci.yml / gemini-ai-analysis.yml / release-please.yml,
    which use `./`-relative refs but are never workflow_call triggered, so the
    ref resolves fine against their own checkout. The guard must not flag
    these.
    """
    doc = yaml.safe_load(
        """
        on:
          push:
            branches: [main]
        jobs:
          build:
            steps:
              - uses: ./
        """
    )

    assert not _is_reusable(doc), (
        "a push-triggered workflow was misclassified as reusable - the "
        "guard would over-fire on legitimate ./-relative uses:"
    )
