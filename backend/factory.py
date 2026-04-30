from __future__ import annotations
from typing import Any
import importlib
import pkgutil
import pathlib

from backend import registry as reg
from backend.interfaces import PipelineAdapter


def _auto_import_adapters() -> None:
    """Walk adapters/ and import every module so @register decorators fire."""
    adapters_path = pathlib.Path(__file__).parent / "adapters"
    for finder, name, _ in pkgutil.walk_packages(
        [str(adapters_path)], prefix="backend.adapters."
    ):
        importlib.import_module(name)


_auto_import_adapters()


def build_pipeline(config: dict[str, Any]) -> PipelineAdapter:
    pipeline_name = config["pipeline"]
    return reg.build("pipeline", pipeline_name, config)


def build_chunker(name: str, config: dict[str, Any]):
    return reg.build("chunker", name, config)


def build_embedder(name: str, config: dict[str, Any]):
    return reg.build("embedder", name, config)
