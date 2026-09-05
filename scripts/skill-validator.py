#!/usr/bin/env python3
"""Validate strict skill metadata, names, visibility, and local references."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote, urlsplit
from typing import Any

try:
    import yaml
except ImportError:  # CI and contributor setup install the pinned dependency.
    yaml = None

try:
    from markdown_it import MarkdownIt
except ImportError:
    MarkdownIt = None

BASE = Path(__file__).resolve().parents[1]
SKILLS = Path(os.environ.get("SKILLS_ROOT", str(BASE / "skills")))
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
INVOCATIONS = {"entry", "internal", "manual", "vendor"}
FOUNDATION_KIND = "foundation"
LEGACY_FOUNDATIONS = BASE / ("foundation" + "-pack")
STRING_FIELDS = {"name", "description", "invocation", "kind", "setup", "compatibility"}
BOOL_FIELDS = {"disable-model-invocation", "x-manual-only"}


class FrontmatterError(ValueError):
    pass


if yaml is not None:
    class UniqueKeyLoader(yaml.SafeLoader):
        """Safe YAML loader that rejects duplicate mapping keys."""


    def _construct_unique_mapping(loader, node, deep=False):
        direct_keys = set()
        for key_node, _value_node in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                continue
            key = loader.construct_object(key_node, deep=deep)
            try:
                duplicate = key in direct_keys
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable key",
                    key_node.start_mark,
                ) from exc
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"duplicate key: {key!r}",
                    key_node.start_mark,
                )
            direct_keys.add(key)
        loader.flatten_mapping(node)
        return yaml.constructor.SafeConstructor.construct_mapping(
            loader, node, deep=deep
        )


    UniqueKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_unique_mapping,
    )
else:
    UniqueKeyLoader = None


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse the opening YAML document strictly; never guess from lines."""
    if not text.startswith("---\n"):
        raise FrontmatterError("opening --- delimiter missing")
    match = re.search(r"^---[ \t]*$", text[4:], re.MULTILINE)
    if match is None:
        raise FrontmatterError("closing --- delimiter missing")
    source = text[4:4 + match.start()]
    if yaml is None:
        raise FrontmatterError("PyYAML is required for strict frontmatter parsing")
    try:
        value = yaml.load(source, Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"invalid YAML: {exc}") from exc
    if not isinstance(value, dict):
        raise FrontmatterError("frontmatter must be a YAML mapping")
    if not all(isinstance(key, str) for key in value):
        raise FrontmatterError("frontmatter keys must be strings")
    return value


def metadata_type_errors(skill: Path, metadata: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in STRING_FIELDS & metadata.keys():
        if not isinstance(metadata[key], str):
            errors.append(f"{skill}: {key} must be a string")
    for key in BOOL_FIELDS & metadata.keys():
        if not isinstance(metadata[key], bool):
            errors.append(f"{skill}: {key} must be a boolean")
    return errors


def git_ignored_dirs(root: Path) -> set[str]:
    if not root.is_dir():
        return set()
    names = [entry.name for entry in root.iterdir() if entry.is_dir()]
    if not names:
        return set()
    try:
        result = subprocess.run(
            ["git", "-C", str(root.parent), "check-ignore", "--stdin", "--no-index"],
            input="".join(f"{root.name}/{name}\n" for name in names),
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return set()
    if result.returncode not in (0, 1):
        return set()
    return {line.rsplit("/", 1)[-1] for line in result.stdout.splitlines()}


def git_untracked_dirs(root: Path) -> set[str]:
    """Return top-level skill dirs whose SKILL.md is not in the Git index."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root.parent), "ls-files", "--", f"{root.name}/*/SKILL.md"],
            capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    tracked = {Path(line).parent.name for line in result.stdout.splitlines()}
    return {entry.name for entry in root.iterdir() if entry.is_dir() and entry.name not in tracked}


def referenced_files(skill: Path, text: str) -> list[str]:
    errors: list[str] = []
    for relative in sorted(set(re.findall(r"`(references/[A-Za-z0-9][A-Za-z0-9._/-]*)`", text))):
        target = (skill.parent / relative).resolve()
        try:
            target.relative_to(skill.parent.resolve())
        except ValueError:
            errors.append(f"{skill}: reference escapes skill directory: {relative}")
            continue
        if not target.is_file():
            errors.append(f"{skill}: referenced file missing: {relative}")
    return errors


def markdown_link_errors(source: Path, text: str, boundary: Path) -> list[str]:
    """Check rendered CommonMark links/images, not code examples or HTML."""
    if MarkdownIt is None:
        return [f"{source}: markdown-it-py is required for local Markdown links"]
    if text.startswith("---\n"):
        closing = re.search(r"^---[ \t]*$", text[4:], re.MULTILINE)
        if closing is not None:
            text = text[4 + closing.end():]
    destinations = set()
    for token in MarkdownIt("commonmark").parse(text):
        for child in token.children or []:
            attribute = {"link_open": "href", "image": "src"}.get(child.type)
            if attribute:
                destination = child.attrGet(attribute)
                if destination:
                    destinations.add(destination)
    errors = []
    boundary = boundary.resolve()
    for destination in sorted(destinations):
        try:
            parsed = urlsplit(destination)
            if parsed.scheme.lower() == "file":
                errors.append(f"{source}: absolute Markdown target not allowed: {destination}")
                continue
            if parsed.netloc:
                continue  # Protocol-relative external URL, not a filesystem UNC path.
            if PureWindowsPath(destination).drive:
                errors.append(f"{source}: absolute Markdown target not allowed: {destination}")
                continue
            if parsed.scheme or not parsed.path:
                continue  # External URI, network URL, or same-document fragment/query.
            relative = unquote(parsed.path)
            if Path(relative).is_absolute() or PureWindowsPath(relative).drive:
                errors.append(f"{source}: absolute Markdown target not allowed: {destination}")
                continue
            target = (source.parent / relative).resolve()
            if not target.is_relative_to(boundary):
                errors.append(f"{source}: Markdown target escapes permitted root: {destination}")
            elif not target.is_file():
                errors.append(f"{source}: Markdown target missing or not a file: {destination}")
        except (OSError, ValueError, RuntimeError) as exc:
            errors.append(f"{source}: invalid Markdown target {destination!r}: {exc}")
    return errors


def validate_foundation_index(skill: Path) -> list[str]:
    references = skill.parent / "references"
    index = references / "index.md"
    if not index.is_file():
        return [f"{skill}: foundation references/index.md missing"]
    text = index.read_text(encoding="utf-8")
    linked = set(re.findall(r"\]\((?:\./)?([A-Za-z0-9][A-Za-z0-9._-]*\.md)\)", text))
    on_disk = {path.name for path in references.glob("*.md") if path.name != "index.md"}
    errors = [f"{index}: reference file absent from inventory: {name}" for name in sorted(on_disk - linked)]
    errors += [f"{index}: inventory target missing: {name}" for name in sorted(linked - on_disk)]
    return errors


def validate_skill(
    skill: Path, require_invocation: bool = True, link_root: Path | None = None,
) -> tuple[str | None, list[str]]:
    try:
        text = skill.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"{skill}: unreadable: {exc}"]
    try:
        metadata = parse_frontmatter(text)
    except FrontmatterError as exc:
        return None, [f"{skill}: frontmatter unparseable: {exc}"]
    errors = metadata_type_errors(skill, metadata)
    name_value = metadata.get("name")
    name = name_value if isinstance(name_value, str) else None
    if name is None:
        errors.append(f"{skill}: name missing")
    elif not NAME_RE.fullmatch(name):
        errors.append(f"{skill}: invalid skill name: {name!r}")
    elif name != skill.parent.name:
        errors.append(f"{skill}: name {name!r} != directory {skill.parent.name!r}")
    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{skill}: description missing")
    if require_invocation:
        invocation = metadata.get("invocation")
        if invocation not in INVOCATIONS:
            errors.append(f"{skill}: invocation must be one of {sorted(INVOCATIONS)}, got {invocation!r}")
        hidden_value = metadata.get("disable-model-invocation", False)
        hidden = hidden_value is True
        if invocation == "entry" and hidden:
            errors.append(f"{skill}: entry invocation contradicts hidden visibility")
        if invocation in {"internal", "manual"} and not hidden:
            errors.append(f"{skill}: {invocation} invocation requires hidden visibility")
        kind = metadata.get("kind")
        foundation_name = bool(name and name.endswith("-foundation"))
        if foundation_name and kind != FOUNDATION_KIND:
            errors.append(f"{skill}: *-foundation requires kind: foundation")
        if kind == FOUNDATION_KIND and not foundation_name:
            errors.append(f"{skill}: kind: foundation requires a *-foundation name")
        if kind not in {None, FOUNDATION_KIND}:
            errors.append(f"{skill}: unsupported kind: {kind!r}")
        if kind == FOUNDATION_KIND:
            if invocation != "manual":
                errors.append(f"{skill}: foundation invocation must be manual")
            if not hidden:
                errors.append(f"{skill}: foundations must disable model invocation")
            errors.extend(validate_foundation_index(skill))
    errors.extend(referenced_files(skill, text))
    errors.extend(markdown_link_errors(skill, text, link_root or skill.parent))
    return name, errors


def validate_tree(
    root: Path, require_invocation: bool = True, ignored: set[str] | None = None,
    link_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    if not root.is_dir():
        return [f"required directory missing: {root}"]
    ignored = ignored or set()
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or directory.name.startswith(".") or directory.name in ignored:
            continue
        if directory.is_symlink():
            errors.append(f"{directory}: skill directories must not be symlinks")
            continue
        skill = directory / "SKILL.md"
        if skill.is_symlink():
            errors.append(f"{skill}: SKILL.md must not be a symlink")
            continue
        if not skill.is_file():
            errors.append(f"{directory}: SKILL.md missing")
            continue
        name, skill_errors = validate_skill(skill, require_invocation, link_root or root)
        errors.extend(skill_errors)
        if name in seen:
            errors.append(f"{skill}: duplicate skill name: {name}")
        elif name:
            seen.add(name)
    return errors


def selftest() -> int:
    with tempfile.TemporaryDirectory(prefix="skill-validator-") as temp:
        root = Path(temp) / "skills"
        valid = root / "demo-foundation"
        (valid / "references").mkdir(parents=True)
        (valid / "references" / "capsule.md").write_text("evidence\n", encoding="utf-8")
        (valid / "references" / "index.md").write_text(
            "- [`capsule.md`](./capsule.md)\n", encoding="utf-8"
        )
        valid_text = (
            "---\nname: demo-foundation\ndescription: cold evidence\n"
            "kind: foundation\ninvocation: manual\n"
            "disable-model-invocation: true\n---\n"
            "# Demo\n\nSee `references/index.md`.\n"
        )
        (valid / "SKILL.md").write_text(valid_text, encoding="utf-8")
        if validate_tree(root):
            print("selftest: valid foundation rejected", file=sys.stderr)
            return 1
        (valid / "LOGIC.md").write_text("# Logic\n", encoding="utf-8")
        (valid / "space name.md").write_text("# Space\n", encoding="utf-8")
        (valid / "paren(one).md").write_text("# Parens\n", encoding="utf-8")
        (root / "shared.md").write_text("# Shared\n", encoding="utf-8")
        outside = Path(temp) / "outside.md"
        outside.write_text("outside the permitted skill collection\n", encoding="utf-8")
        (valid / "escape.md").symlink_to(outside)
        link_cases = [
            ("[logic](LOGIC.md#section)", False),
            ("[shared](../shared.md)", False),
            ("[space](<space name.md>)", False),
            ("[space](space%20name.md?raw=1#section)", False),
            ("[paren](paren(one).md)", False),
            ("[ref][logic]\n\n[logic]: LOGIC.md", False),
            ("[site](https://example.com/missing.md) [mail](mailto:a@example.com)", False),
            ("[anchor](#missing-heading)", False),
            ("[network](//example.com/missing.md)", False),
            # markdown-it-py declines file:/javascript: as links and parses them
            # as literal text; no destination is emitted. These pin that behavior:
            # if the parser changes, the explicit file: rejection in
            # markdown_link_errors turns them into failures.
            ("[file-uri](file:///etc/passwd)", False),
            ("[file-host](file://host/etc/passwd)", False),
            ("[windows](C:/outside.md)", True),
            ("[nul](%00.md)", True),
            ("`[example](missing.md)`\n\n```md\n[x](missing.md)\n```", False),
            ("[missing](missing.md)", True),
            ("![image](missing.png)", True),
            ("[escape](../../outside.md)", True),
            ("[encoded](%2e%2e/%2e%2e/outside.md)", True),
            ("[absolute](/etc/passwd)", True),
            ("[symlink](escape.md)", True),
        ]
        for markdown, should_fail in link_cases:
            errors = markdown_link_errors(valid / "SKILL.md", markdown, root)
            if bool(errors) != should_fail:
                print(f"selftest: Markdown link {markdown!r}: {errors}", file=sys.stderr)
                return 1
        (valid / "SKILL.md").write_text(valid_text + "\n[broken](missing.md)\n", encoding="utf-8")
        errors = validate_tree(root)
        if not any("Markdown target missing" in error for error in errors):
            print("selftest: local Markdown check is not integrated into tree validation", file=sys.stderr)
            return 1
        metadata_example = valid_text.replace("description: cold evidence",
                                              'description: "[example](missing.md)"')
        (valid / "SKILL.md").write_text(metadata_example, encoding="utf-8")
        if validate_tree(root):
            print("selftest: frontmatter parsed as Markdown body", file=sys.stderr)
            return 1
        (valid / "SKILL.md").write_text(valid_text, encoding="utf-8")
        typed = parse_frontmatter(
            "---\nname: 'quoted-name'\ndescription: |\n"
            "  first line\n  second line\n"
            "disable-model-invocation: true\n---\n"
        )
        if typed["description"] != "first line\nsecond line\n" or typed["disable-model-invocation"] is not True:
            print("selftest: valid YAML scalar typing changed", file=sys.stderr)
            return 1
        merged = parse_frontmatter(
            "---\ndefaults: &defaults\n  invocation: manual\n"
            "  disable-model-invocation: true\n<<: *defaults\n"
            "name: merged\ndescription: merged values\n---\n"
        )
        if (
            merged["invocation"] != "manual"
            or merged["disable-model-invocation"] is not True
        ):
            print("selftest: valid YAML merge rejected", file=sys.stderr)
            return 1
        overridden = parse_frontmatter(
            "---\ndefaults: &defaults\n  invocation: manual\n<<: *defaults\n"
            "name: override\ndescription: explicit override\ninvocation: entry\n---\n"
        )
        if overridden["invocation"] != "entry":
            print("selftest: explicit merge override changed", file=sys.stderr)
            return 1
        try:
            parse_frontmatter(
                "---\nname: nested\ndescription: nested duplicate\n"
                "extra:\n  key: first\n  key: second\n---\n"
            )
        except FrontmatterError as exc:
            if "duplicate key: 'key'" not in str(exc):
                print(f"selftest: nested duplicate error changed: {exc}", file=sys.stderr)
                return 1
        else:
            print("selftest: nested duplicate key accepted", file=sys.stderr)
            return 1
        cases = [
            (valid_text.replace("invocation: manual", "invocation: entry"), "foundation invocation must be manual"),
            (valid_text.replace("kind: foundation\n", ""), "*-foundation requires kind: foundation"),
            (valid_text.replace("disable-model-invocation: true", 'disable-model-invocation: "true"'), "must be a boolean"),
            (valid_text.replace("description: cold evidence", "description:\n  nested: value"), "description must be a string"),
            (valid_text.replace("kind: foundation", "kind: [foundation"), "frontmatter unparseable"),
            (
                valid_text.replace("name: demo-foundation", "name: first\nname: second"),
                "duplicate key: 'name'",
            ),
            (
                valid_text.replace("invocation: manual", "invocation: entry\ninvocation: manual"),
                "duplicate key: 'invocation'",
            ),
        ]
        for bad, expected in cases:
            (valid / "SKILL.md").write_text(bad, encoding="utf-8")
            errors = validate_tree(root)
            if not any(expected in error for error in errors):
                print(f"selftest: {expected!r} not caught: {errors}", file=sys.stderr)
                return 1
    print("SKILL VALIDATOR SELFTEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--link-root", type=Path, help="explicit permitted root for local Markdown targets")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    ignored = git_ignored_dirs(SKILLS) if SKILLS == BASE / "skills" else set()
    if MarkdownIt is None:
        print("FAIL  markdown-it-py is required; install requirements-dev.txt")
        return 1
    link_root = args.link_root or (BASE if SKILLS.resolve() == (BASE / "skills").resolve() else SKILLS)
    errors = validate_tree(SKILLS, True, ignored, link_root)
    if SKILLS == BASE / "skills" and (LEGACY_FOUNDATIONS.exists() or LEGACY_FOUNDATIONS.is_symlink()):
        errors.append("retired foundation directory must not exist (including symlinks)")
    for error in errors:
        print(f"FAIL  {error}")
    print(f"SKILL CONTRACTS: {len(errors)} fail")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
