from __future__ import annotations
from typing import Any

_registry: dict[str, dict[str, type]] = {}


def register(component_type: str, name: str):
    """Decorator: @register("chunker", "fixed") registers a class by type+name."""
    def decorator(cls: type) -> type:
        _registry.setdefault(component_type, {})[name] = cls
        return cls
    return decorator


def get(component_type: str, name: str) -> type:
    try:
        return _registry[component_type][name]
    except KeyError:
        available = list(_registry.get(component_type, {}).keys())
        raise ValueError(
            f"Unknown {component_type} '{name}'. Available: {available}"
        )


def available(component_type: str | None = None) -> dict[str, list[str]]:
    if component_type:
        return {component_type: list(_registry.get(component_type, {}).keys())}
    return {k: list(v.keys()) for k, v in _registry.items()}


def build(component_type: str, name: str, config: Any) -> Any:
    cls = get(component_type, name)
    return cls(config)
