"""Tests guarding the consistency of this repo's declared Python floor.

Issue #281: `tomllib` is stdlib only from Python 3.11, and this repo imports
it in fifteen places - including two shipped composite actions
(`actions/quality-gates/action.yml`, `actions/performance-benchmark/action.yml`)
whose inline Python runs on the *consumer's* runner, not ours. Nothing
declared that floor: `[project]` had no `requires-python`, and
`[tool.pixi.dependencies]` pins `python = "3.12.*"`, so no local or CI run
ever exercises 3.10. Per #251, the `python-versions` matrix would not catch
it either, because every leg tests the same interpreter.

This repo takes option 1 from #281: declare 3.11+ and leave every
`import tomllib` bare. These tests keep the two halves consistent, in
whichever direction a future change moves them:

  - every `tomllib` site is bare **and** `requires-python` admits nothing
    below 3.11, or
  - every site carries a `tomli` fallback **and** `tomli` is in the manifest.

The failure mode #281 calls out is a *subset* fix: guarding some files and
not others leaves the framework equally broken on 3.10 while reading as
protected. When this guard was written the tree was in exactly that state -
ten bare sites and five guarded ones - so a mixed result is an explicit
failure here, not a tolerated middle ground.

Sites are discovered by walking the tree (the #255/#261-shaped guard) rather
than from a hand-written file list, so a new import in a new file is caught
rather than silently shipped.

Issue #284 widened this guard: `test_python_floor_is_declared` checked only
that `[project] requires-python` existed, but `[tool.ruff] target-version`
and `[tool.mypy] python_version` were both pinned to 3.10 regardless - one
third of "the python floor" was covered while the test's name claimed
authority over the whole thing. `test_tool_configs_track_the_declared_floor`
below now compares all three declarations against each other.

Issue #286 widened this file again: `discover_version_declarations` walks
three corpora - every `*.toml` at the repo root and under `templates/`,
every `.github/workflows/*.yml` and `*.yml.template`, and the literal
`py3XX` / `>=3.Y` defaults `framework/migration/migrator.py` emits into
migrated projects - and checks every Python-version declaration found there
against the `[project] requires-python` floor. It deliberately EXCLUDES
`docs/` and `README.md` (~70 sites still pinned to 3.10 at the time this
was written): those are fixed in a separate PR (#286 PR-C), and including
them here would fail this guard until that PR lands. Doc drift is
therefore NOT currently guarded by this file.

Issue #286 PR-B added a fourth corpus: `discover_framework_version_declarations`
walks every `*.py` under `framework/` for version-spec literals (`py3XX`,
`>=3.Y`/`^3.Y`/`~=3.Y`, `3.Y.*`, version-string list literals) and
`sys.version_info >= (3, N)`-shaped comparisons, checked against the same
declared floor. Sites that are deliberately below the floor - consumer-project
fixtures, and this file's own classifier self-test samples - carry an
in-place `# python-floor-exempt: <reason>` (or, for a whole file that is
entirely such fixtures, a module-level `# python-floor-exempt-module:
<reason>`) rather than being tracked in a central list, for the same reason
`EXCLUDED_DIR_NAMES` above stays short: a hand-maintained inventory of exempt
sites is the exact artefact #250/#255/#261/#286 keep going stale on. A bare
version string with no spec syntax around it (`"3.10"` as a dict key, say) is
out of scope for this corpus - see the corpus's own docstring below.
"""

# python-floor-exempt-module: this file's samples are classifier self-test
# input; they must spell out sub-floor versions to prove the walk catches them.

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(".")
PYPROJECT = Path("pyproject.toml")

# VCS internals, the pixi environment cache, JS deps, caches, and gitignored
# agent-worktree scratch space. `templates/` is deliberately NOT excluded
# here (unlike in `test_yaml_lint_scope.py`): template files are copied into
# consumer projects, so their interpreter floor matters exactly as much as
# our own.
EXCLUDED_DIR_NAMES = {
    ".git",
    ".pixi",
    "node_modules",
    ".claude",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache",
}

# File types that can carry Python source: real modules, and the inline
# `run:` Python embedded in composite actions and workflows.
SCANNED_SUFFIXES = {".py", ".yml", ".yaml"}

IMPORT_TOMLLIB_LINE_RE = re.compile(r"^[ \t]*import[ \t]+tomllib\b")
IMPORT_TOMLI_RE = re.compile(r"\bimport[ \t]+tomli\b")

# How far below a YAML-embedded `import tomllib` to look for a fallback.
# Inline `run:` Python cannot be parsed with `ast`, so those sites fall back
# to a line window; the idiom sits within a few lines when present at all.
YAML_FALLBACK_WINDOW = 8

MINIMUM_FLOOR = (3, 11)

# Samples for the classifier self-test below. The guarded one mirrors the
# real shape found in `framework/actions/quality_gates.py`: a nested `try`,
# comments between the keyword and the import, and an unaliased `import
# tomli` in the handler.
_GUARDED_SAMPLE = """
try:
    # For Python 3.11+, use tomllib
    import tomllib

    data = tomllib.loads("")
except ImportError:
    # Fallback for older Python versions
    import tomli

    data = tomli.loads("")
"""

_BARE_SAMPLE = "import tomllib\n\ndata = tomllib.loads('')\n"


def _catches_import_error(handler: ast.ExceptHandler) -> bool:
    """True for `except ImportError`, `except (ImportError, ...)`, or bare `except`."""
    if handler.type is None:
        return True
    candidates = (
        handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    )
    return any(
        isinstance(node, ast.Name) and node.id in ("ImportError", "ModuleNotFoundError")
        for node in candidates
    )


def _handler_imports_tomli(handler: ast.ExceptHandler) -> bool:
    """True when the except-branch pulls in `tomli`, aliased or not."""
    for node in ast.walk(handler):
        if isinstance(node, ast.Import) and any(
            alias.name == "tomli" for alias in node.names
        ):
            return True
        if isinstance(node, ast.ImportFrom) and node.module == "tomli":
            return True
    return False


def _guarded_line_ranges(tree: ast.AST) -> list[tuple[int, int]]:
    """Line spans of every `try` body whose handler falls back to `tomli`."""
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        if not any(
            _catches_import_error(handler) and _handler_imports_tomli(handler)
            for handler in node.handlers
        ):
            continue
        spans = [
            (stmt.lineno, getattr(stmt, "end_lineno", None) or stmt.lineno)
            for stmt in node.body
        ]
        if spans:
            ranges.append((min(s for s, _ in spans), max(e for _, e in spans)))
    return ranges


def classify_python(label: str, text: str) -> tuple[list[str], list[str]] | None:
    """Split `import tomllib` sites in Python source into (bare, guarded).

    Returns None when the text will not parse, so the caller can fall back to
    the line-window classifier.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    ranges = _guarded_line_ranges(tree)
    bare: list[str] = []
    guarded: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue
        if not any(alias.name == "tomllib" for alias in node.names):
            continue
        site = f"{label}:{node.lineno}"
        inside = any(lo <= node.lineno <= hi for lo, hi in ranges)
        (guarded if inside else bare).append(site)
    return bare, guarded


def classify_text(label: str, text: str) -> tuple[list[str], list[str]]:
    """Line-window classifier for sources `ast` cannot parse (inline YAML Python)."""
    lines = text.splitlines()
    bare: list[str] = []
    guarded: list[str] = []
    for index, line in enumerate(lines):
        if not IMPORT_TOMLLIB_LINE_RE.match(line):
            continue
        window = "\n".join(lines[index : index + YAML_FALLBACK_WINDOW])
        site = f"{label}:{index + 1}"
        has_fallback = "except ImportError" in window and IMPORT_TOMLI_RE.search(window)
        (guarded if has_fallback else bare).append(site)
    return bare, guarded


def _iter_candidate_files() -> list[Path]:
    """Every file in the repo that could contain a `tomllib` import."""
    found: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        found.append(path)
    return found


def discover_tomllib_sites() -> tuple[list[str], list[str]]:
    """Walk the tree and split every `import tomllib` site into (bare, guarded)."""
    bare: list[str] = []
    guarded: list[str] = []
    for path in _iter_candidate_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "tomllib" not in text:
            continue
        result = classify_python(str(path), text) if path.suffix == ".py" else None
        if result is None:
            result = classify_text(str(path), text)
        bare.extend(result[0])
        guarded.extend(result[1])
    return bare, guarded


def _pyproject_data() -> dict[str, Any]:
    """Parse pyproject.toml once; every other TOML-reading helper builds on this."""
    return tomllib.loads(PYPROJECT.read_text())


def declared_floor() -> str | None:
    """The `[project] requires-python` string, or None when undeclared."""
    data = _pyproject_data()
    value = data.get("project", {}).get("requires-python")
    return value if isinstance(value, str) else None


def floor_admits_below(spec: str, version: tuple[int, int]) -> bool:
    """True when `spec` permits an interpreter older than `version`.

    Only the `>=X.Y` form is understood. Anything else is reported as
    admitting older interpreters, so an unparseable floor fails loudly
    rather than passing vacuously.
    """
    match = re.match(r"^>=\s*(\d+)\.(\d+)", spec.strip())
    if match is None:
        return True
    return (int(match.group(1)), int(match.group(2))) < version


def tomli_in_manifest() -> bool:
    """True when the read-side `tomli` package is a pixi dependency.

    `tomli-w` is a writer and does not provide the `tomli` read module, so it
    deliberately does not satisfy this.
    """
    data = _pyproject_data()
    pixi = data.get("tool", {}).get("pixi", {})
    tables = [pixi.get("dependencies", {}) or {}]
    for feature in (pixi.get("feature", {}) or {}).values():
        if isinstance(feature, dict):
            tables.append(feature.get("dependencies", {}) or {})
    return any("tomli" in table for table in tables)


# All three `_parse_*` helpers below take `value: object` rather than `str`.
# TOML can hand back a non-string for these keys - `python_version = 3.11`
# written *without* quotes parses as a float, not a string - so each parser
# is a total function over whatever TOML yields, and a non-string fails
# loudly via the wrapper's `is not None` assertion rather than raising
# TypeError deep inside a regex match.


def _parse_requires_python_floor(value: object) -> tuple[int, int] | None:
    """Parse the `>=X.Y` floor out of a `requires-python` value.

    Mirrors the regex `floor_admits_below` uses. Only the `>=X.Y` form is
    understood; anything else (including a non-string value) yields None
    rather than guessing.
    """
    if not isinstance(value, str):
        return None
    match = re.match(r"^>=\s*(\d+)\.(\d+)", value.strip())
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)))


def requires_python_floor() -> tuple[int, int] | None:
    """The `[project] requires-python` floor as a (major, minor) tuple."""
    spec = declared_floor()
    if spec is None:
        return None
    return _parse_requires_python_floor(spec)


def _parse_ruff_target_version(value: object) -> tuple[int, int] | None:
    """Parse a ruff `target-version` value like "py311" into (3, 11).

    Accepts the `py<major><minor>` form where minor may be 1 or 2 digits
    (py39, py310, py311). Returns None when the value doesn't match that
    shape, or isn't a string at all.
    """
    if not isinstance(value, str):
        return None
    match = re.match(r"^py(\d)(\d{1,2})$", value.strip())
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)))


def ruff_target_version() -> tuple[int, int] | None:
    """The `[tool.ruff] target-version` floor as a (major, minor) tuple."""
    data = _pyproject_data()
    value = data.get("tool", {}).get("ruff", {}).get("target-version")
    return _parse_ruff_target_version(value)


def _parse_mypy_python_version(value: object) -> tuple[int, int] | None:
    """Parse a mypy `python_version` value like "3.11" into (3, 11).

    TOML may hand this back as a string; only that form is handled here, so
    a non-string value (or an unparseable string) yields None.
    """
    if not isinstance(value, str):
        return None
    match = re.match(r"^(\d+)\.(\d+)$", value.strip())
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)))


def mypy_python_version() -> tuple[int, int] | None:
    """The `[tool.mypy] python_version` floor as a (major, minor) tuple."""
    data = _pyproject_data()
    value = data.get("tool", {}).get("mypy", {}).get("python_version")
    return _parse_mypy_python_version(value)


def test_classifier_detects_the_fallback_idiom():
    """Meta-guard: the classifier must actually recognise a guarded site.

    A classifier that silently labels everything 'bare' would make the
    mixed-state test below pass for free. That is not hypothetical: the
    first draft of this file used a literal-idiom regex, and it reported a
    clean bill of health against a tree that had five guarded sites in it.
    """
    bare, guarded = classify_python("<guarded-sample>", _GUARDED_SAMPLE)
    assert guarded and not bare, (
        "classifier failed to recognise the try/except ImportError fallback "
        f"idiom (bare={bare}, guarded={guarded}) - every other test in this "
        "file is vacuous until this passes"
    )

    bare, guarded = classify_python("<bare-sample>", _BARE_SAMPLE)
    assert bare and not guarded, (
        "classifier mislabelled an unguarded `import tomllib` as guarded "
        f"(bare={bare}, guarded={guarded})"
    )


def test_tomllib_site_discovery_is_not_vacuous():
    """Vacuity guard: an empty walk would pass every other test for free."""
    bare, guarded = discover_tomllib_sites()
    assert bare or guarded, (
        "no `import tomllib` sites discovered anywhere in the repo - the "
        "tree walk is broken, and the consistency tests below are vacuous"
    )


def test_python_floor_is_declared():
    """`requires-python` must state the floor the code already requires."""
    spec = declared_floor()
    assert spec is not None, (
        "[project] in pyproject.toml declares no `requires-python`, so "
        "nothing states the interpreter range this framework supports - "
        "while `import tomllib` already requires 3.11+ (#281)"
    )


def test_tool_configs_track_the_declared_floor():
    """`[tool.ruff]`, `[tool.mypy]`, and `[project] requires-python` must agree.

    #284: ruff's `target-version` and mypy's `python_version` were both
    pinned to 3.10 while `requires-python` declared 3.11+, so both tools
    checked the code against an interpreter the repo does not support -
    and 3.10 is exactly where `import tomllib` (#281) fails. The three
    values are discovered independently from the parsed TOML and compared
    against *each other*, not against a hardcoded (3, 11), so this also
    fails if the floor is raised in the future and the tool configs are
    left behind.
    """
    requires_python = requires_python_floor()
    ruff = ruff_target_version()
    mypy = mypy_python_version()
    assert requires_python is not None, "could not parse [project] requires-python"
    assert ruff is not None, "could not parse [tool.ruff] target-version"
    assert mypy is not None, "could not parse [tool.mypy] python_version"
    assert requires_python == ruff == mypy, (
        "tool configs have drifted from the declared Python floor (#284): "
        f"requires-python={requires_python}, ruff target-version={ruff}, "
        f"mypy python_version={mypy} - a tool configured below the floor "
        "checks the code against a Python version the repo does not "
        "support"
    )


def test_floor_parsers_are_not_vacuous():
    """Meta-guard: the three parsers must return the *correct* tuple, not just *a* tuple.

    A parser that returned a constant `(3, 11)` for every input would make
    `test_tool_configs_track_the_declared_floor` pass for free, the same way
    an always-'bare' classifier would make the tomllib consistency tests
    above pass for free. Each parser is fed a known-good literal (must yield
    the expected tuple) and a malformed one (must yield None).
    """
    assert _parse_requires_python_floor(">=3.11") == (3, 11)
    assert _parse_requires_python_floor(">=3.9") == (3, 9)
    assert _parse_requires_python_floor("not-a-spec") is None
    # No `$` anchor in the regex: it matches the `>=X.Y` prefix and ignores
    # whatever follows, so comma-separated upper bounds are understood too.
    assert _parse_requires_python_floor(">=3.11,<4.0") == (3, 11)
    assert _parse_requires_python_floor(">=3.11, <4.0") == (3, 11)
    # Deliberate: an exact pin is not the `>=X.Y` form the guard reasons
    # about, so it fails loudly via the "could not parse" assertion instead
    # of being silently guessed at - mirrors `floor_admits_below`'s contract.
    assert _parse_requires_python_floor("==3.11") is None
    assert _parse_requires_python_floor(None) is None
    assert _parse_requires_python_floor(3.11) is None

    assert _parse_ruff_target_version("py311") == (3, 11)
    assert _parse_ruff_target_version("py39") == (3, 9)
    assert _parse_ruff_target_version("not-a-version") is None
    assert _parse_ruff_target_version(None) is None
    assert _parse_ruff_target_version(3.11) is None

    assert _parse_mypy_python_version("3.11") == (3, 11)
    assert _parse_mypy_python_version("3.9") == (3, 9)
    assert _parse_mypy_python_version(None) is None
    assert _parse_mypy_python_version("not-a-version") is None
    assert _parse_mypy_python_version(3.11) is None


def test_tomllib_sites_are_not_mixed():
    """Every site must be guarded the same way; a subset fix is the #281 bug."""
    bare, guarded = discover_tomllib_sites()
    assert not (bare and guarded), (
        "`tomllib` import sites are inconsistently guarded, which leaves the "
        "framework broken on 3.10 while reading as protected (#281). "
        f"guarded: {sorted(guarded)}; bare: {sorted(bare)}"
    )


def test_declared_floor_matches_tomllib_usage():
    """The declared floor and the import style must agree."""
    bare, guarded = discover_tomllib_sites()
    spec = declared_floor()
    assert spec is not None, "no `requires-python` declared (see #281)"

    if bare:
        assert not floor_admits_below(spec, MINIMUM_FLOOR), (
            f"`requires-python = {spec!r}` admits interpreters older than "
            f"{MINIMUM_FLOOR[0]}.{MINIMUM_FLOOR[1]}, but these `import "
            "tomllib` sites are bare and would raise ModuleNotFoundError "
            f"there: {sorted(bare)}"
        )
    else:
        assert tomli_in_manifest(), (
            "every `import tomllib` site carries a `tomli` fallback, but "
            "`tomli` is not a pixi dependency, so the fallback import fails "
            "at runtime (`tomli-w` is a writer and does not provide it)"
        )


# ============================================================================
# #286: version-declaration discovery across TOML / workflow / migrator
# corpora. See the module docstring for the docs/ and README.md exclusion.
# ============================================================================

DeclarationRecord = tuple[Path, str, str, tuple[int, int] | None]

TEMPLATES_DIR = REPO_ROOT / "templates"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
MIGRATOR_PATH = REPO_ROOT / "framework" / "migration" / "migrator.py"

# Any "X.Y" pair, used to pull a floor out of loosely-formatted specs
# (pixi's `python = ">=3.11"` / `"3.12.*"`, workflow matrix arrays) that
# don't follow one single fixed grammar.
VERSION_TOKEN_RE = re.compile(r"(\d+)\.(\d+)")
JSON_ARRAY_RE = re.compile(r"\[[^\]]*\]")

# Matches a `python-version`/`python-versions` key whether written as a YAML
# `key: value` pair or a shell `key=value` assignment (the standalone-ci.yml
# `echo 'python-versions=[...]'` idiom), with or without a leading `#`
# (the reusable-ci.yml usage-example comment). Not anchored to line start so
# it also matches inside a quoted shell string.
VERSION_KEY_RE = re.compile(r"['\"]?(python-versions?)['\"]?\s*[:=]\s*(.*)$")

# How far below a bare `python-versions:` key to look for its `default:`
# entry in a `workflow_call` input block (key and value live on separate
# lines when the key also carries a multi-line `description: >-`). Mirrors
# the `YAML_FALLBACK_WINDOW` idiom above.
WORKFLOW_LOOKAHEAD_WINDOW = 10
DEFAULT_VALUE_RE = re.compile(r"default:\s*['\"]?(\[[^\]\n]*\])")

# `framework/migration/migrator.py` literals: quote-agnostic so either
# quote style is caught, using a backreference to match the same quote on
# both sides.
PY3_LITERAL_RE = re.compile(r"""(['"])(py3\d+)\1""")
GTE_LITERAL_RE = re.compile(r"""(['"])(>=3\.\d+)\1""")


def _parse_version_floor_loose(value: object) -> tuple[int, int] | None:
    """Extract the lowest `(major, minor)` token from a loosely-formatted spec.

    Handles forms `_parse_requires_python_floor`/`_parse_mypy_python_version`
    don't: pixi's `">=3.11"` or `"3.12.*"`, and a Jinja-templated default
    embedding a concrete fallback (`"{{ python_version | default('3.12.*')
    }}"` - the template's own `[tool.pixi.dependencies]` value). Every `X.Y`
    token in the string is a candidate; the minimum is treated as the floor,
    matching the policy applied to workflow matrix arrays below. Returns
    None when the value carries no version token at all, rather than
    guessing.
    """
    if not isinstance(value, str):
        return None
    matches = [
        (int(major), int(minor)) for major, minor in VERSION_TOKEN_RE.findall(value)
    ]
    return min(matches) if matches else None


def _iter_toml_candidate_files() -> list[Path]:
    """Every `*.toml` at the repo root (non-recursive) and under `templates/`."""
    root_files = [path for path in REPO_ROOT.glob("*.toml") if path.is_file()]
    template_files = (
        list(TEMPLATES_DIR.rglob("*.toml")) if TEMPLATES_DIR.is_dir() else []
    )
    return root_files + template_files


def discover_toml_version_declarations() -> list[DeclarationRecord]:
    """`[tool.ruff] target-version`, `[tool.mypy] python_version`, and
    `[tool.pixi.dependencies] python`, across every `*.toml` at the repo
    root and under `templates/` (templates ship into consumer projects, so
    their floor matters exactly as much as our own)."""
    records: list[DeclarationRecord] = []
    for path in _iter_toml_candidate_files():
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError):
            continue
        tool = data.get("tool", {})
        ruff_value = tool.get("ruff", {}).get("target-version")
        if ruff_value is not None:
            records.append(
                (
                    path,
                    "toml-ruff-target-version",
                    str(ruff_value),
                    _parse_ruff_target_version(ruff_value),
                )
            )
        mypy_value = tool.get("mypy", {}).get("python_version")
        if mypy_value is not None:
            records.append(
                (
                    path,
                    "toml-mypy-python-version",
                    str(mypy_value),
                    _parse_mypy_python_version(mypy_value),
                )
            )
        pixi_value = tool.get("pixi", {}).get("dependencies", {}).get("python")
        if pixi_value is not None:
            records.append(
                (
                    path,
                    "toml-pixi-python",
                    str(pixi_value),
                    _parse_version_floor_loose(pixi_value),
                )
            )
    return records


def _extract_array_versions(fragment: str) -> list[tuple[int, int]] | None:
    """Pull `[..., ...]` version tokens out of `fragment`, or None if no array is present.

    None (not an empty list) distinguishes "this value isn't an array at
    all" (a scalar default, or a `${{ expression }}` reference) from "an
    array with nothing recognisable in it", so a caller can tell the two
    apart.
    """
    array_match = JSON_ARRAY_RE.search(fragment)
    if array_match is None:
        return None
    return [
        (int(major), int(minor))
        for major, minor in VERSION_TOKEN_RE.findall(array_match.group(0))
    ]


def _iter_workflow_candidate_files() -> list[Path]:
    """Every `*.yml` and `*.yml.template` under `.github/workflows/`."""
    if not WORKFLOWS_DIR.is_dir():
        return []
    return sorted(
        set(WORKFLOWS_DIR.glob("*.yml")) | set(WORKFLOWS_DIR.glob("*.yml.template"))
    )


def discover_workflow_version_declarations() -> list[DeclarationRecord]:
    """`python-version`/`python-versions` matrix values under `.github/workflows/`.

    Only JSON-array-string or YAML-list values count: a scalar default like
    `python-version: '3.12'` or a reference like `${{ matrix.python-version
    }}` is not a floor declaration and is skipped. For a `workflow_call`
    input whose key and `default:` live on separate lines, the default is
    found by looking a few lines below the bare key.
    """
    records: list[DeclarationRecord] = []
    for path in _iter_workflow_candidate_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for index, line in enumerate(lines):
            match = VERSION_KEY_RE.search(line)
            if match is None:
                continue
            rest = match.group(2).strip()
            if rest:
                raw = rest
                versions = _extract_array_versions(rest)
            else:
                window = "\n".join(
                    lines[index + 1 : index + 1 + WORKFLOW_LOOKAHEAD_WINDOW]
                )
                default_match = DEFAULT_VALUE_RE.search(window)
                raw = default_match.group(1) if default_match else ""
                versions = _extract_array_versions(raw) if default_match else None
            if not versions:
                continue
            records.append((path, "workflow-python-version-min", raw, min(versions)))
    return records


def discover_migrator_version_declarations() -> list[DeclarationRecord]:
    """`py3\\d+` and `>=3\\.\\d+` string literals in `framework/migration/migrator.py`.

    These are the Python-version defaults the migrator writes INTO
    consumer projects' `pyproject.toml`/ruff config during a migration, so a
    stale literal here ships a stale floor outward to every project this
    tool touches.
    """
    records: list[DeclarationRecord] = []
    try:
        text = MIGRATOR_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return records
    for match in PY3_LITERAL_RE.finditer(text):
        value = match.group(2)
        records.append(
            (
                MIGRATOR_PATH,
                "migrator-py3-literal",
                value,
                _parse_ruff_target_version(value),
            )
        )
    for match in GTE_LITERAL_RE.finditer(text):
        value = match.group(2)
        records.append(
            (
                MIGRATOR_PATH,
                "migrator-gte-literal",
                value,
                _parse_requires_python_floor(value),
            )
        )
    return records


def discover_version_declarations() -> list[DeclarationRecord]:
    """Every Python-version declaration across all three corpora.

    See the module docstring: `docs/` and `README.md` are deliberately
    excluded (PR-C's scope), so doc drift is not covered by this check.
    """
    return (
        discover_toml_version_declarations()
        + discover_workflow_version_declarations()
        + discover_migrator_version_declarations()
        + discover_framework_version_declarations()
    )


def test_version_declaration_discovery_is_not_vacuous():
    """Per-corpus vacuity guard: an empty walk in any one corpus would make
    `test_no_declaration_is_below_the_project_floor` pass for free for it."""
    toml_records = discover_toml_version_declarations()
    assert toml_records, (
        "no [tool.ruff]/[tool.mypy]/[tool.pixi.dependencies] python "
        "declarations found in any *.toml at the repo root or under "
        "templates/ - the TOML walker is broken"
    )

    workflow_records = discover_workflow_version_declarations()
    assert workflow_records, (
        "no python-version(s) matrix declarations found under "
        ".github/workflows/ (*.yml or *.yml.template) - the workflow "
        "walker is broken"
    )

    migrator_records = discover_migrator_version_declarations()
    assert migrator_records, (
        "no py3XX / >=3.Y string literals found in "
        "framework/migration/migrator.py - the migrator walker is broken"
    )


def test_no_declaration_is_below_the_project_floor():
    """Every discovered declaration must admit nothing older than the
    `[project] requires-python` floor (#286)."""
    floor = requires_python_floor()
    assert floor is not None, "could not parse [project] requires-python"
    for path, kind, raw_value, parsed_floor in discover_version_declarations():
        if parsed_floor is None:
            # Nothing concrete to compare (no version token at all in the
            # raw value); such a value isn't a floor declaration in its own
            # right, so it can't violate one.
            continue
        assert parsed_floor >= floor, (
            f"{path}: {kind} declares {raw_value!r} (parsed floor "
            f"{parsed_floor}), below the project floor {floor} required by "
            "[project] requires-python (#286)"
        )


def test_declaration_classifier_would_have_caught_py310():
    """Classifier self-test: replay the exact #286 regression as synthetic
    input and confirm every declaration shape is both detected and
    classified as below the 3.11 floor. Without this, a classifier that
    silently ignored everything would make the test above pass vacuously,
    the same way an always-'bare' tomllib classifier would above."""
    ruff_floor = _parse_ruff_target_version("py310")
    assert ruff_floor is not None and ruff_floor < MINIMUM_FLOOR, (
        f"ruff target-version classifier failed to catch 'py310' (got {ruff_floor})"
    )

    mypy_floor = _parse_mypy_python_version("3.10")
    assert mypy_floor is not None and mypy_floor < MINIMUM_FLOOR, (
        f"mypy python_version classifier failed to catch '3.10' (got {mypy_floor})"
    )

    pixi_floor = _parse_version_floor_loose(">=3.10")
    assert pixi_floor is not None and pixi_floor < MINIMUM_FLOOR, (
        f"pixi python classifier failed to catch '>=3.10' (got {pixi_floor})"
    )

    matrix_versions = _extract_array_versions('\'["3.10", "3.11"]\'')
    assert matrix_versions is not None, (
        'workflow matrix classifier failed to find an array in \'["3.10", "3.11"]\''
    )
    matrix_floor = min(matrix_versions)
    assert matrix_floor < MINIMUM_FLOOR, (
        f'workflow matrix classifier failed to catch \'["3.10", "3.11"]\' '
        f"(got minimum {matrix_floor})"
    )


# ============================================================================
# #286 PR-B: version declarations inside `framework/` (source and tests)
#
# The three corpora above cover what this repo SHIPS (templates, workflows,
# the migrator's emitted literals). They do not cover `framework/` itself,
# which is how `test_compatibility_matrix.py` came to assert
# `sys.version_info >= (3, 10)` and publish `"3.10": "✅ Supported"` while
# `[project] requires-python` said 3.11.
#
# SCOPE LIMIT, stated plainly so this is not read as broader than it is:
# only version-SPEC shapes are matched - `py3XX`, `>=3.Y` / `^3.Y` / `~=3.Y`,
# `3.Y.*`, list literals of version strings, and `... >= (3, N)`
# comparisons. A BARE `"3.10"` string (a dict key in a free-form
# version->status table, say) is deliberately NOT matched: it occurs in far
# too many innocent contexts to flag usefully. The `compatibility_matrix`
# table in test_compatibility_matrix.py is guarded by its own test against
# the declared floor, not by this walk.
# ============================================================================

FRAMEWORK_DIR = REPO_ROOT / "framework"

# Some version literals below the floor are CORRECT and must stay: the
# classifier self-test samples in this very file, and synthetic fixtures
# modelling CONSUMER projects (a real consumer may well still declare
# ">=3.10" - this framework has to parse that, and testing it means writing
# it down). Exemptions therefore live AT the site and carry a reason, rather
# than in a central list here: a hand-maintained inventory of exempt sites is
# the exact artefact #250/#255/#261/#286 keep going stale on. The trailing
# `\S` means a marker with no reason does not count.
EXEMPT_LINE_RE = re.compile(r"#\s*python-floor-exempt:\s*\S")
EXEMPT_MODULE_RE = re.compile(r"#\s*python-floor-exempt-module:\s*\S")

FRAMEWORK_SPEC_RES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("framework-py3-literal", re.compile(r"""(['"])(py3\d+)\1""")),
    (
        "framework-spec-literal",
        re.compile(r"""(['"])((?:>=|\^|~=)\s*3\.\d+[^'"]*)\1"""),
    ),
    ("framework-pin-literal", re.compile(r"""(['"])(3\.\d+\.\*)\1""")),
)

# `sys.version_info >= (3, 10)`, including the black-formatted multi-line
# spelling `>= (\n    3,\n    10,\n)` - `\s` matches newlines, so both forms
# are caught.
VERSION_INFO_CMP_RE = re.compile(r">=\s*\(\s*3\s*,\s*(\d+)\s*,?\s*\)")

# A list literal of version strings: `["3.10", "3.11", "3.12"]`. Requires a
# second element so a lone `["3.11"]` - far more likely to be something
# unrelated - is not swept in.
VERSION_LIST_RE = re.compile(r"""\[\s*(['"])3\.\d+\1\s*,\s*[^\]]*\]""")


def _line_of(text: str, offset: int) -> int:
    """1-based line number containing `offset` within `text`."""
    return text.count("\n", 0, offset) + 1


def _is_exempt(lines: list[str], lineno: int) -> bool:
    """True when an exemption marker sits on line `lineno` or the line above.

    `lines` is 0-indexed; `lineno` is 1-based.
    """
    for candidate in (lineno - 1, lineno - 2):
        if 0 <= candidate < len(lines) and EXEMPT_LINE_RE.search(lines[candidate]):
            return True
    return False


def _iter_framework_python_files() -> list[Path]:
    """Every `*.py` under `framework/`, minus the usual excluded directories."""
    if not FRAMEWORK_DIR.is_dir():
        return []
    return sorted(
        path
        for path in FRAMEWORK_DIR.rglob("*.py")
        if not any(part in EXCLUDED_DIR_NAMES for part in path.parts)
    )


def discover_framework_version_declarations() -> list[DeclarationRecord]:
    """Version-spec literals and floor comparisons under `framework/`."""
    records: list[DeclarationRecord] = []
    for path in _iter_framework_python_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if EXEMPT_MODULE_RE.search(text):
            continue
        lines = text.splitlines()

        for kind, pattern in FRAMEWORK_SPEC_RES:
            for match in pattern.finditer(text):
                lineno = _line_of(text, match.start())
                if _is_exempt(lines, lineno):
                    continue
                value = match.group(2)
                parsed = (
                    _parse_ruff_target_version(value)
                    if kind == "framework-py3-literal"
                    else _parse_version_floor_loose(value)
                )
                records.append((path, f"{kind}:{lineno}", value, parsed))

        for match in VERSION_INFO_CMP_RE.finditer(text):
            lineno = _line_of(text, match.start())
            if _is_exempt(lines, lineno):
                continue
            records.append(
                (
                    path,
                    f"framework-version-info-cmp:{lineno}",
                    match.group(0),
                    (3, int(match.group(1))),
                )
            )

        for match in VERSION_LIST_RE.finditer(text):
            lineno = _line_of(text, match.start())
            if _is_exempt(lines, lineno):
                continue
            versions = _extract_array_versions(match.group(0))
            if not versions:
                continue
            records.append(
                (
                    path,
                    f"framework-version-list:{lineno}",
                    match.group(0),
                    min(versions),
                )
            )
    return records


def test_framework_corpus_is_not_vacuous():
    """Vacuity guard, matching the three corpora above."""
    assert discover_framework_version_declarations(), (
        "no version-spec literals or floor comparisons found anywhere under "
        "framework/ - the framework walker is broken, and every site in it "
        "is silently unguarded"
    )


def test_framework_exemption_markers_are_honoured_and_required():
    """Meta-guard on the exemption mechanism itself.

    An `_is_exempt` that returned True unconditionally would silence this
    entire corpus while every test above still passed - the same failure
    shape as an always-'bare' tomllib classifier.
    """
    assert _is_exempt(['python = ">=3.10"  # python-floor-exempt: fixture'], 1)
    assert _is_exempt(["# python-floor-exempt: fixture", 'python = ">=3.10"'], 2)
    assert not _is_exempt(['python = ">=3.10"'], 1)
    # A marker with no reason after the colon does not count.
    assert not _is_exempt(['python = ">=3.10"  # python-floor-exempt:'], 1)


def test_framework_classifier_would_have_caught_the_286_sites():
    """Replay the real #286 `framework/` sites as synthetic input."""
    for raw, parser in (
        ("py310", _parse_ruff_target_version),
        (">=3.10", _parse_version_floor_loose),
        ("^3.10", _parse_version_floor_loose),
        ("3.10.*", _parse_version_floor_loose),
    ):
        parsed = parser(raw)
        assert parsed is not None and parsed < MINIMUM_FLOOR, (
            f"framework spec classifier failed to catch {raw!r} (got {parsed})"
        )

    # `sys.version_info >= (3, 10)` - the test_compatibility_matrix.py shape.
    single_line = VERSION_INFO_CMP_RE.search("assert sys.version_info >= (3, 10)")
    assert single_line is not None
    assert (3, int(single_line.group(1))) < MINIMUM_FLOOR
    # ...and its black-formatted multi-line spelling.
    assert VERSION_INFO_CMP_RE.search("current_version >= (\n    3,\n    10,\n)")

    # `["3.10", "3.11", "3.12"]` - the analyzer.py shape.
    list_match = VERSION_LIST_RE.search('versions = ["3.10", "3.11", "3.12"]')
    assert list_match is not None
    list_versions = _extract_array_versions(list_match.group(0))
    assert list_versions is not None and min(list_versions) < MINIMUM_FLOOR

    # The documented scope limit: a bare version string must NOT be swept in.
    assert not any(
        pattern.search('matrix = {"3.10": "not supported"}')
        for _, pattern in FRAMEWORK_SPEC_RES
    )
