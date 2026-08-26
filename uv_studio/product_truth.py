"""Machine-readable Product Truth contract validation for UV Studio.

D-067 deliberately avoids fuzzy documentation parsing. Ready user-visible
features instead publish small JSON contracts whose source references must
resolve to real backend, frontend and user-outcome evidence.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

PRODUCT_TRUTH_SCHEMA_VERSION = 1
PRODUCT_TRUTH_DIRECTORY = Path("docs/architecture/product-truth")
_FEATURE_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_FRONTEND_SYMBOL_TEMPLATE = r"\b(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+{symbol}\b|\b(?:export\s+)?const\s+{symbol}\b"
_FRONTEND_ROUTE_PARAMETER_RE = re.compile(r"\{[^{}]+\}")
_REQUIRED_VISIBLE_STATES = frozenset(
    {"model_choice", "queued", "running", "succeeded", "failed", "cancelled", "take_candidate"}
)


class ProductTruthError(ValueError):
    """A Product Truth contract is malformed or points at missing product surface."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProductTruthError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> Any:
    raise ProductTruthError(f"non-standard JSON constant: {value}")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
        )
    except ProductTruthError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProductTruthError(f"cannot read Product Truth JSON {path}: {exc}") from exc


def _object(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProductTruthError(f"{location} must be a JSON object")
    return value


def _exact_keys(value: Mapping[str, Any], *, location: str, expected: set[str]) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing={missing!r}")
        if unknown:
            details.append(f"unknown={unknown!r}")
        raise ProductTruthError(f"{location} has invalid keys ({', '.join(details)})")


def _text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ProductTruthError(f"{location} must be a trimmed nonblank string")
    return value


def _string_list(value: Any, location: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ProductTruthError(f"{location} must be a nonempty JSON array")
    parsed = tuple(_text(item, f"{location}[{index}]") for index, item in enumerate(value))
    if len(parsed) != len(set(parsed)):
        raise ProductTruthError(f"{location} must not contain duplicates")
    return parsed


def _repo_file(root: Path, value: Any, location: str) -> Path:
    relative = _text(value, location)
    if "\\" in relative or relative.startswith("/") or relative.endswith("/"):
        raise ProductTruthError(f"{location} must be a portable repository-relative file path")
    parts = PurePosixPath(relative).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ProductTruthError(f"{location} contains an invalid path segment")
    candidate = root.joinpath(*parts)
    try:
        resolved_root = root.resolve()
        resolved = candidate.resolve()
        resolved.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise ProductTruthError(f"{location} escapes repository root") from exc
    if not resolved.is_file():
        raise ProductTruthError(f"{location} does not resolve to a file: {relative!r}")
    return resolved


def _python_tree(path: Path) -> ast.Module:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ProductTruthError(f"cannot parse Python reference {path}: {exc}") from exc


def _top_level_class(tree: ast.Module, class_name: str, location: str) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise ProductTruthError(f"{location} class does not resolve: {class_name!r}")


def _require_class_method(path: Path, class_name: str, method_name: str, location: str) -> None:
    class_node = _top_level_class(_python_tree(path), class_name, location)
    if not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name
        for node in class_node.body
    ):
        raise ProductTruthError(
            f"{location} method does not resolve: {class_name}.{method_name}"
        )


def _require_python_symbol(path: Path, symbol: str, location: str) -> None:
    tree = _python_tree(path)
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            return
    raise ProductTruthError(f"{location} symbol does not resolve: {symbol!r}")


def _router_prefix(tree: ast.Module) -> str:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "router" for target in node.targets):
            continue
        call = node.value
        if not isinstance(call, ast.Call):
            continue
        function = call.func
        if not isinstance(function, ast.Name) or function.id != "APIRouter":
            continue
        for keyword in call.keywords:
            if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    return keyword.value.value
    return ""


def _require_fastapi_route(
    path: Path,
    *,
    function_name: str,
    method: str,
    route: str,
    location: str,
) -> None:
    tree = _python_tree(path)
    prefix = _router_prefix(tree)
    target: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            target = node
            break
    if target is None:
        raise ProductTruthError(f"{location} function does not resolve: {function_name!r}")

    for decorator in target.decorator_list:
        if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
            continue
        owner = decorator.func.value
        if not isinstance(owner, ast.Name) or owner.id != "router":
            continue
        if decorator.func.attr.upper() != method.upper() or not decorator.args:
            continue
        first = decorator.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            if f"{prefix}{first.value}" == route:
                return
    raise ProductTruthError(
        f"{location} route does not resolve: {method.upper()} {route} via {function_name}"
    )


def _read_frontend_text(path: Path, location: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ProductTruthError(f"cannot read frontend reference {path}: {exc}") from exc


def _require_frontend_symbol(path: Path, symbol: str, location: str) -> str:
    text = _read_frontend_text(path, location)
    pattern = re.compile(_FRONTEND_SYMBOL_TEMPLATE.format(symbol=re.escape(symbol)))
    if pattern.search(text) is None:
        raise ProductTruthError(f"{location} frontend symbol does not resolve: {symbol!r}")
    return text


def _require_frontend_surface(
    path: Path,
    *,
    symbol: str,
    controls: Sequence[str],
    location: str,
) -> None:
    text = _require_frontend_symbol(path, symbol, location)
    for control in controls:
        if control not in text:
            raise ProductTruthError(f"{location} declared control is absent from frontend: {control!r}")


def _normalized_declared_frontend_route(route: str, location: str) -> str:
    value = _text(route, location)
    if not value.startswith("/") or "?" in value or "#" in value:
        raise ProductTruthError(f"{location} must be an absolute product route without query/fragment")
    normalized = _FRONTEND_ROUTE_PARAMETER_RE.sub(":param", value)
    if "{" in normalized or "}" in normalized:
        raise ProductTruthError(f"{location} contains malformed route parameters")
    return normalized.rstrip("/") or "/"


def _next_route_for_entry(relative_path: str, location: str) -> str:
    parts = PurePosixPath(relative_path).parts
    prefix = ("frontend", "app")
    if parts[:2] != prefix or parts[-1] not in {"page.tsx", "page.ts", "page.jsx", "page.js"}:
        raise ProductTruthError(f"{location} must reference a Next app page under frontend/app")
    route_parts: list[str] = []
    for part in parts[2:-1]:
        if part.startswith("(") and part.endswith(")"):
            continue
        if part.startswith("@"):
            continue
        if part.startswith("[") and part.endswith("]"):
            route_parts.append(":param")
        else:
            route_parts.append(part)
    return "/" + "/".join(route_parts) if route_parts else "/"


def _validate_frontend_mount_chain(
    root: Path,
    value: Any,
    *,
    route: str,
    surface_path: Path,
    surface_symbol: str,
    location: str,
) -> None:
    if not isinstance(value, list) or not value:
        raise ProductTruthError(f"{location} must be a nonempty JSON array")
    resolved: list[tuple[str, Path, str, str]] = []
    for index, item in enumerate(value):
        item_location = f"{location}[{index}]"
        reference = _object(item, item_location)
        _exact_keys(reference, location=item_location, expected={"path", "symbol"})
        relative = _text(reference["path"], f"{item_location}.path")
        path = _repo_file(root, relative, f"{item_location}.path")
        symbol = _text(reference["symbol"], f"{item_location}.symbol")
        text = _require_frontend_symbol(path, symbol, item_location)
        resolved.append((relative, path, symbol, text))

    declared_route = _normalized_declared_frontend_route(route, f"{location}.route")
    actual_route = _next_route_for_entry(resolved[0][0], f"{location}[0].path")
    if actual_route != declared_route:
        raise ProductTruthError(
            f"{location} route entry resolves to {actual_route!r}, not declared {declared_route!r}"
        )

    for index, (_relative, _path, _symbol, text) in enumerate(resolved[:-1]):
        next_symbol = resolved[index + 1][2]
        if re.search(rf"\b{re.escape(next_symbol)}\b", text) is None:
            raise ProductTruthError(
                f"{location}[{index}] does not mount/reference next symbol {next_symbol!r}"
            )

    if resolved[-1][1] != surface_path or resolved[-1][2] != surface_symbol:
        raise ProductTruthError(
            f"{location} must terminate at the declared frontend surface {surface_symbol!r}"
        )


def _validate_dependency(root: Path, value: Any, location: str) -> None:
    dependency = _object(value, location)
    _exact_keys(dependency, location=location, expected={"name", "path", "symbol"})
    _text(dependency["name"], f"{location}.name")
    path = _repo_file(root, dependency["path"], f"{location}.path")
    symbol = _text(dependency["symbol"], f"{location}.symbol")
    if path.suffix != ".py":
        raise ProductTruthError(f"{location}.path must reference Python authority")
    _require_python_symbol(path, symbol, location)


def _validate_evidence(root: Path, value: Any, location: str) -> None:
    evidence = _object(value, location)
    _exact_keys(evidence, location=location, expected={"path", "class", "test"})
    path = _repo_file(root, evidence["path"], f"{location}.path")
    class_name = _text(evidence["class"], f"{location}.class")
    test_name = _text(evidence["test"], f"{location}.test")
    if not test_name.startswith("test_"):
        raise ProductTruthError(f"{location}.test must name a unittest test method")
    _require_class_method(path, class_name, test_name, location)


def validate_product_truth_contract(
    root: Path,
    raw: Any,
    *,
    location: str = "product-truth",
) -> dict[str, Any]:
    """Validate one contract and resolve all code/UI/evidence references."""

    document = _object(raw, location)
    _exact_keys(
        document,
        location=location,
        expected={
            "schema_version",
            "feature_id",
            "title",
            "user_visible",
            "readiness",
            "canonical",
            "dependencies",
            "visible_states",
            "availability",
            "evidence",
        },
    )
    if document["schema_version"] != PRODUCT_TRUTH_SCHEMA_VERSION or isinstance(
        document["schema_version"], bool
    ):
        raise ProductTruthError(
            f"{location}.schema_version must be integer {PRODUCT_TRUTH_SCHEMA_VERSION}"
        )
    feature_id = _text(document["feature_id"], f"{location}.feature_id")
    if _FEATURE_ID_RE.fullmatch(feature_id) is None:
        raise ProductTruthError(f"{location}.feature_id has invalid format")
    _text(document["title"], f"{location}.title")
    if not isinstance(document["user_visible"], bool):
        raise ProductTruthError(f"{location}.user_visible must be boolean")
    readiness = document["readiness"]
    if readiness not in {"ready", "not_ready", "internal"}:
        raise ProductTruthError(f"{location}.readiness is invalid: {readiness!r}")
    if readiness == "internal" and document["user_visible"]:
        raise ProductTruthError(f"{location} internal features cannot be user_visible")

    canonical = _object(document["canonical"], f"{location}.canonical")
    _exact_keys(
        canonical,
        location=f"{location}.canonical",
        expected={"domain", "backend", "frontend", "state"},
    )

    domain = _object(canonical["domain"], f"{location}.canonical.domain")
    _exact_keys(
        domain,
        location=f"{location}.canonical.domain",
        expected={"path", "class", "method"},
    )
    domain_path = _repo_file(root, domain["path"], f"{location}.canonical.domain.path")
    _require_class_method(
        domain_path,
        _text(domain["class"], f"{location}.canonical.domain.class"),
        _text(domain["method"], f"{location}.canonical.domain.method"),
        f"{location}.canonical.domain",
    )

    backend = _object(canonical["backend"], f"{location}.canonical.backend")
    _exact_keys(
        backend,
        location=f"{location}.canonical.backend",
        expected={"path", "function", "http_method", "route"},
    )
    backend_path = _repo_file(root, backend["path"], f"{location}.canonical.backend.path")
    method = _text(backend["http_method"], f"{location}.canonical.backend.http_method").upper()
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise ProductTruthError(f"{location}.canonical.backend.http_method is unsupported")
    _require_fastapi_route(
        backend_path,
        function_name=_text(backend["function"], f"{location}.canonical.backend.function"),
        method=method,
        route=_text(backend["route"], f"{location}.canonical.backend.route"),
        location=f"{location}.canonical.backend",
    )

    frontend = _object(canonical["frontend"], f"{location}.canonical.frontend")
    _exact_keys(
        frontend,
        location=f"{location}.canonical.frontend",
        expected={"path", "symbol", "route", "mount_chain", "controls"},
    )
    frontend_path = _repo_file(root, frontend["path"], f"{location}.canonical.frontend.path")
    frontend_symbol = _text(frontend["symbol"], f"{location}.canonical.frontend.symbol")
    controls = _string_list(frontend["controls"], f"{location}.canonical.frontend.controls")
    frontend_route = _text(frontend["route"], f"{location}.canonical.frontend.route")
    _require_frontend_surface(
        frontend_path,
        symbol=frontend_symbol,
        controls=controls,
        location=f"{location}.canonical.frontend",
    )
    _validate_frontend_mount_chain(
        root,
        frontend["mount_chain"],
        route=frontend_route,
        surface_path=frontend_path,
        surface_symbol=frontend_symbol,
        location=f"{location}.canonical.frontend.mount_chain",
    )

    _string_list(canonical["state"], f"{location}.canonical.state")

    dependencies = document["dependencies"]
    if not isinstance(dependencies, list) or not dependencies:
        raise ProductTruthError(f"{location}.dependencies must be a nonempty JSON array")
    names: list[str] = []
    for index, dependency in enumerate(dependencies):
        dep_location = f"{location}.dependencies[{index}]"
        _validate_dependency(root, dependency, dep_location)
        names.append(str(dependency["name"]))
    if len(names) != len(set(names)):
        raise ProductTruthError(f"{location}.dependencies names must be unique")

    visible_states = set(_string_list(document["visible_states"], f"{location}.visible_states"))
    if document["user_visible"] and readiness == "ready":
        missing_states = sorted(_REQUIRED_VISIBLE_STATES - visible_states)
        if missing_states:
            raise ProductTruthError(
                f"{location}.visible_states missing required ready-state surfaces: {missing_states!r}"
            )

    availability = _object(document["availability"], f"{location}.availability")
    _exact_keys(
        availability,
        location=f"{location}.availability",
        expected={"requires_available_offer", "default_behavior", "proof_transport"},
    )
    if not isinstance(availability["requires_available_offer"], bool):
        raise ProductTruthError(f"{location}.availability.requires_available_offer must be boolean")
    _text(availability["default_behavior"], f"{location}.availability.default_behavior")
    _text(availability["proof_transport"], f"{location}.availability.proof_transport")

    evidence = _object(document["evidence"], f"{location}.evidence")
    _exact_keys(
        evidence,
        location=f"{location}.evidence",
        expected={"browser_e2e", "api_integration"},
    )
    _validate_evidence(root, evidence["browser_e2e"], f"{location}.evidence.browser_e2e")
    _validate_evidence(root, evidence["api_integration"], f"{location}.evidence.api_integration")

    return dict(document)


def validate_product_truth_file(root: Path, path: Path) -> dict[str, Any]:
    return validate_product_truth_contract(root, _read_json(path), location=path.as_posix())


def validate_product_truth_registry(
    root: Path,
    directory: Path = PRODUCT_TRUTH_DIRECTORY,
) -> tuple[dict[str, Any], ...]:
    """Validate every registered Product Truth contract in deterministic order."""

    registry_dir = root / directory
    if not registry_dir.is_dir():
        raise ProductTruthError(f"Product Truth directory is missing: {directory.as_posix()}")
    paths = sorted(registry_dir.glob("*.json"))
    if not paths:
        raise ProductTruthError("Product Truth registry contains no contracts")
    contracts = tuple(validate_product_truth_file(root, path) for path in paths)
    feature_ids = [str(contract["feature_id"]) for contract in contracts]
    if len(feature_ids) != len(set(feature_ids)):
        raise ProductTruthError("Product Truth registry contains duplicate feature_id values")
    return contracts
