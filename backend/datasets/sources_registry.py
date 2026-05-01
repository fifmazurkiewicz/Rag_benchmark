"""
Dataset source registry.
Each source is a function: build(config) -> {documents, qa_pairs}
registered with @source("name").
"""
from __future__ import annotations
from typing import Callable, Any

_sources: dict[str, Callable] = {}


def source(name: str):
    def decorator(fn: Callable) -> Callable:
        _sources[name] = fn
        return fn
    return decorator


def available() -> list[dict]:
    import importlib, pkgutil, pathlib
    pkg = pathlib.Path(__file__).parent / "sources"
    for _, mod_name, _ in pkgutil.iter_modules([str(pkg)]):
        importlib.import_module(f"backend.datasets.sources.{mod_name}")
    return [{"name": k, "description": fn.__doc__ or ""} for k, fn in _sources.items()]


def build(name: str, config: dict[str, Any]) -> dict:
    import importlib, pkgutil, pathlib
    pkg = pathlib.Path(__file__).parent / "sources"
    for _, mod_name, _ in pkgutil.iter_modules([str(pkg)]):
        importlib.import_module(f"backend.datasets.sources.{mod_name}")
    if name not in _sources:
        raise ValueError(f"Unknown source '{name}'. Available: {list(_sources.keys())}")
    return _sources[name](config)
