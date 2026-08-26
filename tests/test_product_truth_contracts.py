from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from uv_studio.product_truth import (
    PRODUCT_TRUTH_DIRECTORY,
    ProductTruthError,
    validate_product_truth_contract,
    validate_product_truth_registry,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / PRODUCT_TRUTH_DIRECTORY / "generate-shot-take.json"


class ProductTruthContractTests(unittest.TestCase):
    def test_ready_named_generation_contract_resolves_real_product_references(self) -> None:
        contracts = validate_product_truth_registry(ROOT)
        self.assertEqual([item["feature_id"] for item in contracts], ["generate-shot-take"])

        contract = contracts[0]
        self.assertTrue(contract["user_visible"])
        self.assertEqual(contract["readiness"], "ready")
        self.assertEqual(
            contract["canonical"]["backend"]["route"],
            "/api/uv/projects/{project_id}/studio/generation/jobs",
        )
        self.assertEqual(
            contract["canonical"]["frontend"]["mount_chain"][0]["path"],
            "frontend/app/projects/[projectId]/studio/page.tsx",
        )
        self.assertEqual(
            contract["evidence"]["browser_e2e"]["test"],
            "test_visible_named_model_generates_take_accepts_to_timeline_and_undo_keeps_job",
        )
        self.assertTrue(contract["availability"]["requires_available_offer"])
        self.assertIn("test-only", contract["availability"]["proof_transport"])

    def test_ready_contract_fails_when_frontend_symbol_no_longer_resolves(self) -> None:
        raw = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        broken = copy.deepcopy(raw)
        broken["canonical"]["frontend"]["symbol"] = "MissingGenerationWorkspacePanel"

        with self.assertRaises(ProductTruthError):
            validate_product_truth_contract(ROOT, broken, location="broken-contract")

    def test_ready_contract_fails_when_declared_frontend_route_does_not_match_next_entry(self) -> None:
        raw = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        broken = copy.deepcopy(raw)
        broken["canonical"]["frontend"]["route"] = "/projects/{project_id}/generation"

        with self.assertRaises(ProductTruthError):
            validate_product_truth_contract(ROOT, broken, location="wrong-route-contract")

    def test_ready_contract_fails_when_frontend_mount_chain_is_broken(self) -> None:
        raw = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        broken = copy.deepcopy(raw)
        broken["canonical"]["frontend"]["mount_chain"][2]["symbol"] = "StudioWorkspace"

        with self.assertRaises(ProductTruthError):
            validate_product_truth_contract(ROOT, broken, location="broken-mount-contract")

    def test_ready_contract_requires_all_visible_job_and_result_states(self) -> None:
        raw = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        broken = copy.deepcopy(raw)
        broken["visible_states"].remove("failed")

        with self.assertRaises(ProductTruthError):
            validate_product_truth_contract(ROOT, broken, location="missing-state-contract")


if __name__ == "__main__":
    unittest.main()
