from __future__ import annotations

import unittest

from uv_studio.agent.harness import AgentActionCatalog
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry


class AgentCatalogContractTests(unittest.TestCase):
    def test_catalog_exposes_job_and_d017_routing_facts(self) -> None:
        catalog = AgentActionCatalog(ModelRegistry(CapabilityRegistry()))

        generation = catalog.get("generation.submit")
        self.assertTrue(generation.requires_model)
        self.assertTrue(generation.uses_job_manager)
        self.assertTrue(generation.authorization_may_be_required)
        self.assertTrue(generation.to_dict()["uses_job_manager"])
        self.assertTrue(generation.to_dict()["authorization_may_be_required"])

        local_mutation = catalog.get("production.create_shot")
        self.assertFalse(local_mutation.requires_model)
        self.assertFalse(local_mutation.uses_job_manager)
        self.assertFalse(local_mutation.authorization_may_be_required)


if __name__ == "__main__":
    unittest.main()
