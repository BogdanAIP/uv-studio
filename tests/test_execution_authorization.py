from __future__ import annotations

import time
import unittest

from uv_studio.capabilities.authorization import (
    ConsentScope,
    CostEstimateState,
    ExecutionAuthorizationInvalid,
    ExecutionConsentRequired,
    OneShotAuthorizationStore,
    cost_estimate_for_offer,
    prepare_execution,
)
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.capabilities.selection import SelectionPolicy


def offer(
    *,
    offer_id: str = "test.offer",
    locality: LocalityClass = LocalityClass.LOCAL,
    cost_class: CostClass = CostClass.FREE,
) -> CapabilityOffer:
    return CapabilityOffer(
        offer_id=offer_id,
        capability_id="video.generate",
        adapter_id="test_adapter",
        title="Test",
        availability=OfferAvailability.AVAILABLE,
        reason="ready",
        locality=locality,
        cost_class=cost_class,
        asynchronous=True,
    )


class ExecutionAuthorizationTests(unittest.TestCase):
    def test_local_free_requires_no_authorization(self) -> None:
        preparation = prepare_execution(
            project_id="prj_test",
            offer=offer(),
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload={"prompt": "hello"},
        )
        self.assertEqual(preparation.consent_required, ())
        self.assertEqual(preparation.cost_estimate.state, CostEstimateState.NOT_APPLICABLE)
        store = OneShotAuthorizationStore()
        self.assertEqual(store.issue(preparation, acknowledgements=set()), (None, None))
        store.consume(None, preparation)

    def test_remote_free_requires_only_remote_execution_ack(self) -> None:
        preparation = prepare_execution(
            project_id="prj_test",
            offer=offer(locality=LocalityClass.REMOTE),
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload={},
        )
        self.assertEqual(preparation.consent_required, (ConsentScope.REMOTE_EXECUTION,))
        self.assertEqual(preparation.cost_estimate.state, CostEstimateState.NOT_APPLICABLE)

    def test_potentially_paid_unknown_cost_requires_explicit_cost_ack(self) -> None:
        selected = offer(
            locality=LocalityClass.REMOTE,
            cost_class=CostClass.POTENTIALLY_PAID,
        )
        preparation = prepare_execution(
            project_id="prj_test",
            offer=selected,
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload={"prompt": "hello"},
        )
        self.assertEqual(cost_estimate_for_offer(selected).state, CostEstimateState.UNKNOWN)
        self.assertEqual(
            preparation.consent_required,
            (
                ConsentScope.REMOTE_EXECUTION,
                ConsentScope.EXTERNAL_COST,
                ConsentScope.UNKNOWN_COST,
            ),
        )

    def test_missing_acknowledgement_cannot_issue_grant(self) -> None:
        preparation = prepare_execution(
            project_id="prj_test",
            offer=offer(cost_class=CostClass.PAID),
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload={},
        )
        store = OneShotAuthorizationStore()
        with self.assertRaises(ExecutionConsentRequired):
            store.issue(preparation, acknowledgements={ConsentScope.EXTERNAL_COST})

    def test_grant_is_one_shot_and_exact_input_bound(self) -> None:
        selected = offer(cost_class=CostClass.PAID)
        original = prepare_execution(
            project_id="prj_test",
            offer=selected,
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload={"prompt": "A", "options": {"x": 1}},
        )
        mutated = prepare_execution(
            project_id="prj_test",
            offer=selected,
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload={"prompt": "B", "options": {"x": 1}},
        )
        store = OneShotAuthorizationStore()
        required = set(original.consent_required)
        token, _ = store.issue(original, acknowledgements=required)
        with self.assertRaises(ExecutionAuthorizationInvalid):
            store.consume(token, mutated)
        with self.assertRaises(ExecutionAuthorizationInvalid):
            store.consume(token, original)

        token, _ = store.issue(original, acknowledgements=required)
        store.consume(token, original)
        with self.assertRaises(ExecutionAuthorizationInvalid):
            store.consume(token, original)

    def test_grant_expires(self) -> None:
        preparation = prepare_execution(
            project_id="prj_test",
            offer=offer(cost_class=CostClass.PAID),
            selection_policy=SelectionPolicy.PINNED_OFFER,
            payload={},
        )
        store = OneShotAuthorizationStore(ttl_seconds=0.01)
        token, _ = store.issue(preparation, acknowledgements=set(preparation.consent_required))
        time.sleep(0.02)
        with self.assertRaises(ExecutionAuthorizationInvalid):
            store.consume(token, preparation)


if __name__ == "__main__":
    unittest.main()
