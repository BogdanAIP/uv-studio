from __future__ import annotations

import unittest

from uv_studio.recipes import (
    ExecutionCompatibility,
    build_builtin_registry,
    resolve_project_execution,
)
from uv_studio.server import app


class RecipeTargetMountingTests(unittest.TestCase):
    def test_any_advertised_base_execution_target_is_mounted(self) -> None:
        mounted_paths = {
            route.path
            for route in app.routes
            if isinstance(getattr(route, "path", None), str)
        }
        registry = build_builtin_registry()
        for recipe_id in registry.ids():
            plan = resolve_project_execution(registry, recipe_id)
            if plan.target is not None:
                self.assertIn(
                    plan.target.launch_path,
                    mounted_paths,
                    f"{recipe_id} advertises unmounted target {plan.target.launch_path}",
                )
            if plan.compatibility is ExecutionCompatibility.AVAILABLE:
                self.assertIsNotNone(
                    plan.target,
                    f"{recipe_id} is AVAILABLE without a current executable base target",
                )


if __name__ == "__main__":
    unittest.main()
