from __future__ import annotations

import unittest

from uv_studio.capabilities import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.capabilities.consent import (
    CostEstimateState,
    ExecutionAuthorizationExpired,
    ExecutionAuthorizationRejected,
    ExecutionAuthorizationStore,
    ExecutionAuthorizationUsed,
    ExecutionConsentRequired,
    prepare_external_execution,
)


class ExecutionConsentTests(unittest.TestCase):
    @staticmethod
    def _offer(*, locality: LocalityClass, cost: CostClass) -> CapabilityOffer:
        return CapabilityOffer(
            "mcp.fixture.echo",
            "media.understand",
            "mcp.fixture",
            "Fixture",
            OfferAvailability.AVAILABLE,
            "ready",
            locality,
            cost,
            True,
        )

    def test_free_local_requires_no_authorization(self) -> None:
        prepared = prepare_external_execution(
            project_id="prj_test",
            offer=self._offer(locality=LocalityClass.LOCAL, cost=CostClass.FREE),
            payload={"text": "hello"},
        )
        self.assertFalse(prepared.authorization_required)
        self.assertEqual(prepared.intent.cost_estimate.state, CostEstimateState.NOT_APPLICABLE)

    def test_remote_free_requires_remote_confirmation_only(self) -> None:
        prepared = prepare_external_execution(
            project_id="prj_test",
            offer=self._offer(locality=LocalityClass.REMOTE, cost=CostClass.FREE),
            payload={"text": "hello"},
        )
        self.assertTrue(prepared.authorization_required)
        self.assertTrue(prepared.remote_consent_required)
        self.assertFalse(prepared.cost_consent_required)
        store = ExecutionAuthorizationStore(ttl_seconds=30)
        with self.assertRaises(ExecutionConsentRequired):
            store.authorize(
                prepared,
                confirm_remote=False,
                confirm_cost=False,
                acknowledge_unknown_cost=False,
                now=100,
            )
        grant = store.authorize(
            prepared,
            confirm_remote=True,
            confirm_cost=False,
            acknowledge_unknown_cost=False,
            now=100,
        )
        self.assertTrue(grant.token)

    def test_potentially_paid_unknown_requires_all_confirmations(self) -> None:
        prepared = prepare_external_execution(
            project_id="prj_test",
            offer=self._offer(
                locality=LocalityClass.REMOTE,
                cost=CostClass.POTENTIALLY_PAID,
            ),
            payload={"prompt": "hello"},
        )
        self.assertEqual(prepared.intent.cost_estimate.state, CostEstimateState.UNKNOWN)
        self.assertTrue(prepared.unknown_cost_ack_required)
        store = ExecutionAuthorizationStore(ttl_seconds=30)
        with self.assertRaises(ExecutionConsentRequired):
            store.authorize(
                prepared,
                confirm_remote=True,
                confirm_cost=True,
                acknowledge_unknown_cost=False,
                now=100,
            )
        grant = store.authorize(
            prepared,
            confirm_remote=True,
            confirm_cost=True,
            acknowledge_unknown_cost=True,
            now=100,
        )
        self.assertTrue(grant.token)

    def test_grant_is_bound_to_exact_input_digest(self) -> None:
        offer = self._offer(locality=LocalityClass.REMOTE, cost=CostClass.FREE)
        prepared = prepare_external_execution(
            project_id="prj_test",
            offer=offer,
            payload={"text": "original"},
        )
        changed = prepare_external_execution(
            project_id="prj_test",
            offer=offer,
            payload={"text": "changed"},
        )
        store = ExecutionAuthorizationStore(ttl_seconds=30)
        grant = store.authorize(
            prepared,
            confirm_remote=True,
            confirm_cost=False,
            acknowledge_unknown_cost=False,
            now=100,
        )
        with self.assertRaises(ExecutionAuthorizationRejected):
            store.consume(
                grant.token,
                expected_intent_digest=changed.intent.intent_digest,
                now=101,
            )
        # Mismatch does not consume a legitimate grant, so the exact intent can still use it.
        consumed = store.consume(
            grant.token,
            expected_intent_digest=prepared.intent.intent_digest,
            now=101,
        )
        self.assertEqual(consumed.grant_id, grant.grant_id)

    def test_grant_is_one_shot(self) -> None:
        prepared = prepare_external_execution(
            project_id="prj_test",
            offer=self._offer(locality=LocalityClass.REMOTE, cost=CostClass.FREE),
            payload={"text": "hello"},
        )
        store = ExecutionAuthorizationStore(ttl_seconds=30)
        grant = store.authorize(
            prepared,
            confirm_remote=True,
            confirm_cost=False,
            acknowledge_unknown_cost=False,
            now=100,
        )
        store.consume(
            grant.token,
            expected_intent_digest=prepared.intent.intent_digest,
            now=101,
        )
        with self.assertRaises(ExecutionAuthorizationUsed):
            store.consume(
                grant.token,
                expected_intent_digest=prepared.intent.intent_digest,
                now=102,
            )

    def test_expired_grant_is_rejected_and_cannot_be_revived(self) -> None:
        prepared = prepare_external_execution(
            project_id="prj_test",
            offer=self._offer(locality=LocalityClass.REMOTE, cost=CostClass.FREE),
            payload={"text": "hello"},
        )
        store = ExecutionAuthorizationStore(ttl_seconds=2)
        grant = store.authorize(
            prepared,
            confirm_remote=True,
            confirm_cost=False,
            acknowledge_unknown_cost=False,
            now=100,
        )
        with self.assertRaises(ExecutionAuthorizationExpired):
            store.consume(
                grant.token,
                expected_intent_digest=prepared.intent.intent_digest,
                now=103,
            )
        with self.assertRaises(ExecutionAuthorizationUsed):
            store.consume(
                grant.token,
                expected_intent_digest=prepared.intent.intent_digest,
                now=101,
            )


if __name__ == "__main__":
    unittest.main()
