"""Guards against secrets reaching a shell command line (#258).

A `${{ secrets.X }}` expression inside a `run:` body is substituted into the
script text the runner executes, so the secret value ends up in the rendered
script. Passing it through a step-level `env:` block instead keeps it off the
command line.

#255 fixed one instance of this and silently missed two more - one of them in a
file the issue did not know existed. That is what duplicated secret handling
invites, and it is why this guard is repo-wide rather than a list of the files
known to be affected today.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS_DIR = Path(".github/workflows")
ACTION_DIRS = (Path(".github/actions"), Path("actions"))
GPG_ACTION = Path(".github/actions/gpg-signing-setup/action.yml")

# A BARE secret interpolation - the value itself. Deliberately does NOT match
# comparisons such as `${{ secrets.X != '' }}`, which evaluate to a boolean
# rather than the secret and are safe to print.
BARE_SECRET_RE = re.compile(r"\$\{\{\s*secrets\.[A-Za-z_][A-Za-z0-9_]*\s*\}\}")


def _yaml_files() -> list[Path]:
    """Every workflow and composite action definition in the repo."""
    files = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    for directory in ACTION_DIRS:
        files += sorted(directory.glob("*/action.yml"))
        files += sorted(directory.glob("*/action.yaml"))
    return files


def _iter_run_bodies(doc):
    """Yield (owner, step_name, run_body) for every step carrying a run: block."""
    if not isinstance(doc, dict):
        return
    for job_name, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                yield job_name, step.get("name", "<unnamed>"), step["run"]
    runs = doc.get("runs")
    if isinstance(runs, dict):
        for step in runs.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                yield "runs", step.get("name", "<unnamed>"), step["run"]


@pytest.mark.parametrize("path", _yaml_files(), ids=str)
def test_no_bare_secret_in_run_body(path):
    """No workflow or action may interpolate a secret value into a run: body."""
    offenders = [
        f"{owner} / {step}: {match}"
        for owner, step, body in _iter_run_bodies(yaml.safe_load(path.read_text()))
        for match in BARE_SECRET_RE.findall(body)
    ]
    assert not offenders, (
        f"{path} interpolates a secret directly into a run: body, which renders "
        "the secret into the executed script text. Pass it through a step-level "
        "env: block and reference it as a quoted shell variable (#258). "
        "Offenders: " + "; ".join(offenders)
    )


def test_secret_guard_is_not_vacuous():
    """The parametrization must cover real files, or the guard proves nothing."""
    files = _yaml_files()
    assert len(files) > 5, f"expected many workflow/action files, found {files}"
    assert any(f.name == "action.yml" for f in files), (
        "no composite action files were scanned; the guard would miss them"
    )


class TestGpgSigningSetupAction:
    """The composite action #258 consolidates GPG handling into.

    Nothing else lints this file - actionlint only inspects .github/workflows/
    and the yaml-lint task is scoped to that directory too - so its structure is
    asserted here rather than assumed.
    """

    def test_action_file_exists_and_parses(self):
        assert GPG_ACTION.is_file(), f"{GPG_ACTION} is missing"
        assert yaml.safe_load(GPG_ACTION.read_text()), "action.yml parsed as empty"

    def test_is_a_composite_action_with_expected_interface(self):
        doc = yaml.safe_load(GPG_ACTION.read_text())
        assert doc["runs"]["using"] == "composite"
        expected_inputs = {
            "gpg-private-key",
            "gpg-key-id",
            "git-user-name",
            "git-user-email",
            "config-scope",
        }
        assert set(doc["inputs"]) == expected_inputs
        assert "signing-enabled" in doc.get("outputs", {})

    def test_secrets_are_passed_through_env_not_the_script_body(self):
        """The whole point of the action: the key never hits the command line."""
        step = yaml.safe_load(GPG_ACTION.read_text())["runs"]["steps"][0]
        assert "GPG_PRIVATE_KEY" in step["env"], (
            "the private key must be exposed to the script through env:"
        )
        assert "${{ inputs.gpg-private-key }}" not in step["run"], (
            "the private key must not be interpolated into the script body"
        )
