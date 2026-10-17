"""Layer boundaries (CLAUDE.md §6, ARCHITECTURE §3), checked by parsing imports with `ast`."""

import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"
SIM = BACKEND / "sim"

DOMAIN_FORBIDDEN = (
    "sqlalchemy",
    "fastapi",
    "starlette",
    "httpx",
    "anthropic",
    "os",
    "yaml",
    "random",
    "app.services",
    "app.repositories",
    "app.models",
    "app.integrations",
    "app.api",
    "app.core",
    "app.db",
)
API_FORBIDDEN = ("app.repositories", "app.models")
SIM_FORBIDDEN = ("app.domain", "app.services", "app.repositories", "app.integrations", "app.api")
SIM_ALLOWED_APP_IMPORTS = {
    "seed.py": ("app.models", "app.core.settings", "app.core.security", "app.db"),
    "evaluate.py": ("app.main", "app.core.settings"),
    "bench.py": ("app.core.settings",),
}


def _python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def _matches(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(module == p or module.startswith(p + ".") for p in prefixes)


@pytest.mark.parametrize("path", _python_files(APP / "domain"), ids=lambda p: p.name)
def test_domain_is_pure(path: Path) -> None:
    bad = sorted(m for m in _imports(path) if _matches(m, DOMAIN_FORBIDDEN))
    assert not bad, f"{path.name} imports {bad}"
    source = path.read_text(encoding="utf-8")
    for call in ("datetime.now(", "date.today(", "time.time(", "datetime.utcnow("):
        assert call not in source, f"{path.name} reads the wall clock ({call})"


@pytest.mark.parametrize("path", _python_files(APP / "api"), ids=lambda p: p.name)
def test_api_goes_through_services(path: Path) -> None:
    bad = sorted(m for m in _imports(path) if _matches(m, API_FORBIDDEN))
    assert not bad, f"{path.name} imports {bad}"


@pytest.mark.parametrize("path", _python_files(SIM), ids=lambda p: p.name)
def test_sim_talks_http_only(path: Path) -> None:
    imports = _imports(path)
    bad = sorted(m for m in imports if _matches(m, SIM_FORBIDDEN))
    assert not bad, f"{path.name} imports {bad}"
    # ARCHITECTURE §3: any sim module may read configuration through app.core.settings.
    allowed = (*SIM_ALLOWED_APP_IMPORTS.get(path.name, ()), "app.core.settings")
    app_imports = sorted(m for m in imports if _matches(m, ("app",)) and not _matches(m, allowed))
    assert not app_imports, f"{path.name} may not import {app_imports}"


def test_engine_never_reads_scenario_label() -> None:
    for path in _python_files(APP / "domain"):
        assert "scenario_label" not in path.read_text(encoding="utf-8"), path.name


def test_no_print_in_app() -> None:
    for path in _python_files(APP):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "print":
                pytest.fail(f"print() in {path.relative_to(BACKEND)}")


def test_os_getenv_only_in_settings() -> None:
    for path in _python_files(APP):
        if path.name == "settings.py":
            continue
        source = path.read_text(encoding="utf-8")
        assert "os.getenv" not in source and "os.environ" not in source, path.name
