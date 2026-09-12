"""Shellcheck the bash embedded in composite action definitions (#261).

Neither existing lint gate looks at composite actions: `actionlint` inspects
`.github/workflows/` and has no composite-action support, and `yaml-lint` was
scoped to `.github/workflows/` by its own command. So the `run:` bodies in
every `action.yml` in this repo had never been checked by anything, despite
composite actions being a shipped product surface that consumers invoke
directly.

This module extracts every `runs.steps[].run` body from every action
definition, neutralises the `${{ ... }}` expressions the runner substitutes
before bash ever sees them, and runs shellcheck over the result, mapping each
finding back to its line in the original `action.yml`.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml

# Composite actions live in both trees. Discovery walks them rather than
# reading a fixed list: a hand-maintained file list is exactly what silently
# drifted out of sync in #255, letting real findings go unnoticed.
ACTION_DIRS = (Path("actions"), Path(".github/actions"))
ACTION_FILENAMES = ("action.yml", "action.yaml")

# Shells shellcheck understands. Anything else is reported as skipped rather
# than silently dropped.
SHELLCHECK_SHELLS = {"bash", "sh"}
DEFAULT_SHELL = "bash"

# A GitHub Actions expression. The runner substitutes these before bash ever
# sees them, so they are not shell syntax and would otherwise produce spurious
# parse errors.
GHA_EXPRESSION_RE = re.compile(r"\$\{\{.*?\}\}", re.DOTALL)

# The placeholder substituted for an expression must be a variable EXPANSION,
# never a literal. Substituting a literal makes shellcheck reason about a
# constant the runner will never actually produce, fabricating SC2050
# ("expression is constant"), SC2157 ("-n is always true due to literal
# strings") and SC2194 for every `if [ "${{ inputs.x }}" = "true" ]` in the
# repo - findings that would push a reader to "fix" correct code.
PLACEHOLDER_STEM = "GHA_EXPR"

# A finding whose position falls ON a substituted expression is describing the
# placeholder, not the author's shell: `$(( ${{ inputs.n }} * 60 ))` reports
# SC2004 ("unnecessary $ on arithmetic variable") and `'${{ inputs.json }}'`
# reports SC2016 ("expressions don't expand in single quotes") - yet the
# single-quoting there is correct, because GitHub substitutes before bash
# runs. SC2086 is exempt: an unquoted `${{ }}` really is the defect class this
# gate exists to catch.
EXPRESSION_AWARE_CODES = frozenset({"SC2086"})

# The `[SCxxxx]` code trailing a shellcheck message.
FINDING_CODE_RE = re.compile(r"\[(SC\d+)\]")

# A `shellcheck --format=gcc` line: file:line:col: level: message [SCxxxx]
GCC_FINDING_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s*(?P<level>\w+):\s*(?P<message>.*)$"
)


@dataclass(frozen=True)
class RunStep:
    """One `run:` body lifted out of a composite action definition."""

    path: Path
    step_name: str
    shell: str
    body: str
    start_line: int


@dataclass(frozen=True)
class Finding:
    """A shellcheck finding, mapped back to the action file it came from."""

    path: Path
    line: int
    column: int
    level: str
    message: str
    step_name: str

    def __str__(self) -> str:
        return (
            f"{self.path}:{self.line}:{self.column}: {self.level}: "
            f"{self.message}  (step: {self.step_name})"
        )


def discover_action_files(roots: tuple[Path, ...] = ACTION_DIRS) -> list[Path]:
    """Every composite action definition, found by walking the action trees."""
    found: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for name in ACTION_FILENAMES:
            found.update(root.rglob(name))
    return sorted(found)


def _placeholder_name(length: int) -> str:
    """A valid shell identifier of exactly `length` characters."""
    if length <= 0:
        return ""
    repeats = length // len(PLACEHOLDER_STEM) + 1
    return (PLACEHOLDER_STEM * repeats)[:length]


def neutralize_expressions(body: str) -> tuple[str, set[str]]:
    """Replace each `${{ ... }}` with a same-length variable expansion.

    Each expression becomes a braced `${NAME}` expansion of identical width.
    Returns the rewritten body and the set of placeholder names used, so the
    caller can declare them and keep SC2154 meaningful for genuinely
    undefined variables. Length and newlines are preserved so shellcheck's
    reported line and column still map back to the original file.

    A multi-line expression keeps its first line as the expansion and turns
    its continuation lines into comments; that preserves the line count, at
    the cost of masking anything sharing a continuation line - rare enough in
    a `run:` body to be worth the accurate line numbers.
    """
    names: set[str] = set()

    def _replace(match: re.Match[str]) -> str:
        first, *rest = match.group(0).split("\n")
        # Braced form: `${NAME}` cannot merge with a following identifier
        # character. A bare `$NAME` in `${{ x }}s` becomes `$NAMEs`, which
        # shellcheck reads as a different variable - reporting the declared
        # name unused and the merged name unassigned, both fabricated.
        name = _placeholder_name(len(first) - 3)
        if name:
            names.add(name)
        out = ["${" + name + "}" if name else ""]
        out.extend(("#" + "x" * (len(line) - 1)) if line else "" for line in rest)
        return "\n".join(out)

    return GHA_EXPRESSION_RE.sub(_replace, body), names


def placeholder_spans(script: str, names: set[str]) -> dict[int, list[tuple[int, int]]]:
    """Map each 1-based line to the column spans its placeholders occupy."""
    spans: dict[int, list[tuple[int, int]]] = {}
    if not names:
        return spans
    pattern = re.compile(
        "|".join(
            re.escape("${" + name + "}")
            for name in sorted(names, key=len, reverse=True)
        )
    )
    for index, line in enumerate(script.splitlines(), start=1):
        for match in pattern.finditer(line):
            spans.setdefault(index, []).append((match.start() + 1, match.end()))
    return spans


def _quoted_span(line: str, column: int) -> tuple[int, int] | None:
    """Span of the quoted string that OPENS at `column`, if one does.

    shellcheck reports SC2016 against the opening quote rather than the
    expression inside, so the placeholder-span test alone does not see it.
    """
    index = column - 1
    if not 0 <= index < len(line) or line[index] not in "'\"":
        return None
    end = line.find(line[index], index + 1)
    if end == -1:
        return None
    return column, end + 1


def _is_expression_artifact(
    line: str, column: int, spans: list[tuple[int, int]]
) -> bool:
    """True when a finding describes a substituted expression, not the source.

    Either the finding points directly at a placeholder, or it points at a
    quoted string that encloses one.
    """
    if any(start <= column <= end for start, end in spans):
        return True
    quoted = _quoted_span(line, column)
    if quoted is None:
        return False
    return any(quoted[0] <= start and end <= quoted[1] for start, end in spans)


def build_script(step: RunStep) -> tuple[str, int, dict[int, list[tuple[int, int]]]]:
    """Return the shellcheck-ready script, its preamble line count, and spans.

    Placeholders are declared up front so an expression standing in for a
    value does not read as an unassigned variable. The preamble line count is
    subtracted back out when mapping findings to the source file, and the
    spans let the caller discard findings aimed at a placeholder.
    """
    script, names = neutralize_expressions(step.body)
    preamble = "".join(f'{name}=""\n' for name in sorted(names)) if names else ""
    full_script = preamble + script
    return full_script, preamble.count("\n"), placeholder_spans(full_script, names)


def block_indent(step: RunStep) -> int:
    """Columns are body-relative once YAML strips the block indentation.

    Recover the stripped width by comparing the body's first line with the
    same line as it appears in the file, so reported columns point at the
    right character in `action.yml`.
    """
    body_lines = step.body.splitlines()
    if not body_lines:
        return 0
    file_lines = step.path.read_text().splitlines()
    index = step.start_line - 1
    if not 0 <= index < len(file_lines):
        return 0
    file_line = file_lines[index]
    body_line = body_lines[0]
    return (len(file_line) - len(file_line.lstrip())) - (
        len(body_line) - len(body_line.lstrip())
    )


def _mapping_items(node: yaml.Node) -> Iterator[tuple[str, yaml.Node]]:
    """Yield (key, value_node) for a MappingNode; nothing for anything else."""
    if not isinstance(node, yaml.MappingNode):
        return
    for key_node, value_node in node.value:
        if isinstance(key_node, yaml.ScalarNode):
            yield key_node.value, value_node


def body_start_line(run_node: yaml.ScalarNode) -> int:
    """1-based line in the file where the run body's first line lives.

    For a block scalar (`run: |`) the node's mark points at the indicator, and
    the content starts on the following line; for a plain scalar it already
    points at the content.
    """
    line = run_node.start_mark.line + 1
    if run_node.style in ("|", ">"):
        return line + 1
    return line


def iter_run_steps(path: Path) -> Iterator[RunStep]:
    """Yield every `runs.steps[].run` body in one action definition."""
    node = yaml.compose(path.read_text())
    if node is None:
        return
    for key, value in _mapping_items(node):
        if key != "runs":
            continue
        for runs_key, runs_value in _mapping_items(value):
            if runs_key != "steps" or not isinstance(runs_value, yaml.SequenceNode):
                continue
            for step_node in runs_value.value:
                items = dict(_mapping_items(step_node))
                run_node = items.get("run")
                if not isinstance(run_node, yaml.ScalarNode):
                    continue
                name_node = items.get("name")
                shell_node = items.get("shell")
                yield RunStep(
                    path=path,
                    step_name=(
                        name_node.value
                        if isinstance(name_node, yaml.ScalarNode)
                        else "<unnamed>"
                    ),
                    shell=(
                        shell_node.value
                        if isinstance(shell_node, yaml.ScalarNode)
                        else DEFAULT_SHELL
                    ),
                    body=run_node.value,
                    start_line=body_start_line(run_node),
                )


def shellcheck_step(step: RunStep, severity: str = "style") -> list[Finding]:
    """Run shellcheck over one extracted body, mapping findings back to source."""
    script, preamble_lines, spans = build_script(step)
    script_lines = script.splitlines()
    indent = block_indent(step)
    with tempfile.NamedTemporaryFile(
        "w", suffix=".sh", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(script)
        temp_path = Path(handle.name)
    try:
        completed = subprocess.run(
            [
                "shellcheck",
                f"--shell={step.shell}",
                f"--severity={severity}",
                "--format=gcc",
                str(temp_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    # shellcheck exits 0 with no findings and 1 with findings, and writes
    # nothing to stderr in normal operation. Any other exit code, or any
    # stderr output, means the invocation itself failed - and stdout will be
    # empty. Parsing that as "no findings" would report the gate clean
    # precisely when it is blind.
    if completed.returncode not in (0, 1) or completed.stderr.strip():
        raise RuntimeError(
            f"shellcheck exited {completed.returncode} for {step.path} "
            f"(step: {step.step_name}); it did not run. "
            f"stderr: {completed.stderr.strip() or '<empty>'}"
        )

    findings: list[Finding] = []
    parsed = 0
    for line in completed.stdout.splitlines():
        match = GCC_FINDING_RE.match(line.strip())
        if match is None:
            continue
        parsed += 1
        # A finding on the synthetic preamble describes the scaffolding, not
        # the action. Mapping it back would point at a line before the body.
        script_line = int(match.group("line"))
        if script_line <= preamble_lines:
            continue
        # A finding aimed at a substituted expression describes the
        # placeholder rather than the author's shell.
        code_match = FINDING_CODE_RE.search(match.group("message"))
        column = int(match.group("col"))
        if code_match is not None and code_match.group(1) not in EXPRESSION_AWARE_CODES:
            source_line = (
                script_lines[script_line - 1]
                if 0 <= script_line - 1 < len(script_lines)
                else ""
            )
            if _is_expression_artifact(source_line, column, spans.get(script_line, [])):
                continue
        findings.append(
            Finding(
                path=step.path,
                line=step.start_line + int(match.group("line")) - preamble_lines - 1,
                column=int(match.group("col")) + indent,
                level=match.group("level"),
                message=match.group("message"),
                step_name=step.step_name,
            )
        )

    # Exit 1 means shellcheck reported something. Reaching here having parsed
    # NOTHING means it wrote in a form this code cannot read - a silent blind
    # spot rather than a clean file. Note the test is on lines parsed, not on
    # findings kept: an invocation whose every finding is filtered out as an
    # expression artifact is a working invocation with an empty result.
    if completed.returncode == 1 and parsed == 0:
        raise RuntimeError(
            f"shellcheck exited 1 for {step.path} (step: {step.step_name}) "
            "but no line of its output could be parsed; the gate cannot trust "
            f"this result. stdout: {completed.stdout.strip()[:400]!r}"
        )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Shellcheck the bash embedded in composite action definitions"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Action files to check (default: discover under actions/ and .github/actions/)",
    )
    parser.add_argument(
        "--severity",
        default="style",
        choices=("error", "warning", "info", "style"),
        help="Minimum shellcheck severity to report (default: style, i.e. everything)",
    )
    args = parser.parse_args(argv)

    if shutil.which("shellcheck") is None:
        print(
            "shellcheck not found on PATH - run this via the `dev` pixi env",
            file=sys.stderr,
        )
        return 2

    paths = list(args.paths) or discover_action_files()
    if not paths:
        print(
            "no composite action definitions found - refusing to report success, "
            "since a check that cannot fail reads exactly like a check that passes",
            file=sys.stderr,
        )
        return 2

    steps: list[RunStep] = []
    skipped: list[str] = []
    for path in paths:
        for step in iter_run_steps(path):
            if step.shell not in SHELLCHECK_SHELLS:
                skipped.append(f"{path} (step: {step.step_name}) shell={step.shell}")
                continue
            steps.append(step)

    if not steps:
        print(
            "no shellcheckable run: bodies found in "
            f"{len(paths)} action file(s) - refusing to report success",
            file=sys.stderr,
        )
        return 2

    try:
        findings = [
            finding
            for step in steps
            for finding in shellcheck_step(step, args.severity)
        ]
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 2
    for finding in sorted(findings, key=lambda f: (str(f.path), f.line, f.column)):
        print(finding)
    for note in skipped:
        print(f"skipped (shellcheck cannot check this shell): {note}")
    print(
        f"\n{len(steps)} run block(s) across {len(paths)} action file(s), "
        f"{len(findings)} finding(s)"
    )
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
