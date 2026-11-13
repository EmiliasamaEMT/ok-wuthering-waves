"""Check fork release identity without importing application code."""

import argparse
import ast
from pathlib import Path
import re
import tomllib

import yaml


REPOSITORY = "https://github.com/EmiliasamaEMT/ok-wuthering-waves"
UPDATE_PINS = {"dulwich": "1.2.21", "pyappify": "1.0.20", "ok-script": "3.0.5b7"}


def check_identity(root):
    root = Path(root)
    errors = []

    def read(relative):
        try:
            return (root / relative).read_text(encoding="utf-8-sig")
        except OSError as error:
            errors.append(f"{relative}: {error.strerror}")
            return ""

    def require(condition, message):
        if not condition:
            errors.append(message)

    def tree(relative):
        try:
            return ast.parse(read(relative), filename=relative)
        except SyntaxError as error:
            errors.append(f"{relative}: {error.msg} at line {error.lineno}")
            return ast.Module(body=[], type_ignores=[])

    try:
        app = yaml.safe_load(read("pyappify.yml")) or {}
        require(app.get("name") == "mc-helper", "pyappify.yml: name must be mc-helper")
        require(app.get("website") == REPOSITORY, "pyappify.yml: website must point to the fork")
        profiles = app.get("profiles", [])
        require(isinstance(profiles, list), "pyappify.yml: profiles must be a list")
        if isinstance(profiles, list):
            require(len(profiles) == 2 and {p.get("name") for p in profiles} == {"China", "Global"},
                    "pyappify.yml: require the China and Global profiles")
            for profile in profiles:
                require(profile.get("git_url") == REPOSITORY + ".git",
                        f"pyappify.yml: {profile.get('name')} update source must point to the fork")
    except (yaml.YAMLError, AttributeError, TypeError) as error:
        errors.append(f"pyappify.yml: invalid configuration ({error})")

    try:
        project = tomllib.loads(read("pyproject.toml"))
        require(project.get("project", {}).get("name") == "mc-helper", "pyproject.toml: project name must be mc-helper")
    except tomllib.TOMLDecodeError as error:
        errors.append(f"pyproject.toml: {error}")

    config_tree = tree("config.py")
    expected = {"gui_title": "mc小帮手", "log_file": "logs/mc-helper.log",
                "error_log_file": "logs/mc-helper_error.log", "github": REPOSITORY}
    found = {key: [] for key in expected}
    for node in ast.walk(config_tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value in expected:
                    found[key.value].append(value.value if isinstance(value, ast.Constant) else None)
    for key, value in expected.items():
        require(bool(found[key]) and all(item == value for item in found[key]),
                f"config.py: {key} must remain {value!r}")

    hooks = {"prepare_update_repository", "install_prerelease_comparison"}
    for relative in ["main.py", "main_debug.py"]:
        module = tree(relative)
        imports = [node.lineno for node in ast.walk(module)
                   if isinstance(node, ast.ImportFrom) and node.module in {"config", "ok"}]
        boundary = min(imports, default=0)
        for hook in hooks:
            calls = [node.lineno for node in ast.walk(module) if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name) and node.func.id == hook]
            require(bool(calls) and boundary > min(calls),
                    f"{relative}: {hook} must run before importing config/ok")

    for relative, symbol in [("src/update_repo.py", "prepare_update_repository"),
                             ("src/pyappify_compat.py", "install_prerelease_comparison")]:
        require(any(isinstance(node, ast.FunctionDef) and node.name == symbol for node in tree(relative).body),
                f"{relative}: missing {symbol}")
    for relative in ["tests/test_update_repo.py", "tests/test_pyappify_compat.py"]:
        require(any(isinstance(node, ast.ClassDef) for node in tree(relative).body),
                f"{relative}: update regression tests must be retained")

    pins = dict((name.lower().replace("_", "-"), version) for name, version in re.findall(
        r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?==([^\s;]+)", read("requirements.txt"), re.MULTILINE))
    for name, version in UPDATE_PINS.items():
        require(pins.get(name) == version,
                f"requirements.txt: {name} changed from tested {version}; review update compatibility and this guard")

    build = read(".github/workflows/build.yml")
    for script in ["fix_portable_versions.py", "stage_release_assets.py"]:
        require(script in build, f"build.yml: retain {script}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    errors = check_identity(args.root)
    for error in errors:
        print(f"ERROR: {error}")
    if not errors:
        print("Fork identity, update sources, startup hooks and tested update dependencies: OK")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
