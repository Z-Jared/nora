from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Callable

from mini_agent.registry import ToolRegistry


def load_plugins(registry: ToolRegistry, plugins_dir: Path) -> list[str]:
    if not plugins_dir.is_dir():
        return []

    loaded = []
    for plugin_path in sorted(plugins_dir.glob("*.py")):
        if plugin_path.name.startswith("_"):
            continue
        try:
            _load_plugin(registry, plugin_path)
            loaded.append(plugin_path.stem)
        except Exception as error:
            print(f"Warning: failed to load plugin {plugin_path.name}: {error}")

    return loaded


def _load_plugin(registry: ToolRegistry, path: Path) -> None:
    spec = importlib.util.spec_from_file_location(f"nora_plugin_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    register_fn = getattr(module, "register", None)
    if not callable(register_fn):
        raise AttributeError(f"plugin {path.name} must export a callable 'register' function")

    register_fn(registry)
