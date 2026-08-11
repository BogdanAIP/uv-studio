"""Deterministic semantic capability and adapter-offer registry."""

from __future__ import annotations

from collections.abc import Iterable

from .models import (
    AdapterDefinition,
    CapabilityDefinition,
    CapabilityOffer,
    CapabilityValidationError,
    CostClass,
    LocalityClass,
    OfferAvailability,
    validate_capability_id,
)


class CapabilityRegistryError(RuntimeError):
    pass


class DuplicateCapability(CapabilityRegistryError):
    pass


class DuplicateAdapter(CapabilityRegistryError):
    pass


class DuplicateOffer(CapabilityRegistryError):
    pass


class UnknownCapability(CapabilityRegistryError):
    pass


class UnknownAdapter(CapabilityRegistryError):
    pass


class CapabilityRegistry:
    def __init__(
        self,
        capabilities: Iterable[CapabilityDefinition] = (),
        adapters: Iterable[AdapterDefinition] = (),
        offers: Iterable[CapabilityOffer] = (),
    ) -> None:
        self._capabilities: dict[str, CapabilityDefinition] = {}
        self._adapters: dict[str, AdapterDefinition] = {}
        self._offers: dict[str, CapabilityOffer] = {}
        self._offers_by_capability: dict[str, list[str]] = {}
        for capability in capabilities:
            self.register_capability(capability)
        for adapter in adapters:
            self.register_adapter(adapter)
        for offer in offers:
            self.register_offer(offer)

    def register_capability(self, capability: CapabilityDefinition) -> CapabilityDefinition:
        if not isinstance(capability, CapabilityDefinition):
            raise CapabilityValidationError("registry accepts only CapabilityDefinition values")
        if capability.capability_id in self._capabilities:
            raise DuplicateCapability(capability.capability_id)
        self._capabilities[capability.capability_id] = capability
        self._offers_by_capability.setdefault(capability.capability_id, [])
        return capability

    def register_adapter(self, adapter: AdapterDefinition) -> AdapterDefinition:
        if not isinstance(adapter, AdapterDefinition):
            raise CapabilityValidationError("registry accepts only AdapterDefinition values")
        if adapter.adapter_id in self._adapters:
            raise DuplicateAdapter(adapter.adapter_id)
        self._adapters[adapter.adapter_id] = adapter
        return adapter

    def register_offer(self, offer: CapabilityOffer) -> CapabilityOffer:
        if not isinstance(offer, CapabilityOffer):
            raise CapabilityValidationError("registry accepts only CapabilityOffer values")
        if offer.offer_id in self._offers:
            raise DuplicateOffer(offer.offer_id)
        if offer.capability_id not in self._capabilities:
            raise UnknownCapability(offer.capability_id)
        if offer.adapter_id not in self._adapters:
            raise UnknownAdapter(offer.adapter_id)
        self._offers[offer.offer_id] = offer
        self._offers_by_capability[offer.capability_id].append(offer.offer_id)
        return offer

    def get_capability(self, capability_id: str) -> CapabilityDefinition:
        try:
            normalized = validate_capability_id(capability_id, field_name="capability_id")
        except CapabilityValidationError as exc:
            raise UnknownCapability(capability_id) from exc
        try:
            return self._capabilities[normalized]
        except KeyError as exc:
            raise UnknownCapability(normalized) from exc

    def get_adapter(self, adapter_id: str) -> AdapterDefinition:
        try:
            normalized = validate_capability_id(adapter_id, field_name="adapter_id")
        except CapabilityValidationError as exc:
            raise UnknownAdapter(adapter_id) from exc
        try:
            return self._adapters[normalized]
        except KeyError as exc:
            raise UnknownAdapter(normalized) from exc

    def list_capabilities(self) -> tuple[CapabilityDefinition, ...]:
        return tuple(self._capabilities.values())

    def list_adapters(self) -> tuple[AdapterDefinition, ...]:
        return tuple(self._adapters.values())

    def offers_for(
        self,
        capability_id: str,
        *,
        include_unavailable: bool = True,
    ) -> tuple[CapabilityOffer, ...]:
        capability = self.get_capability(capability_id)
        offers = [self._offers[offer_id] for offer_id in self._offers_by_capability[capability.capability_id]]
        if not include_unavailable:
            offers = [offer for offer in offers if offer.availability is OfferAvailability.AVAILABLE]
        return tuple(sorted(offers, key=self._offer_preference_key))

    def offer_summary(self, capability_id: str) -> dict[str, int]:
        offers = self.offers_for(capability_id)
        return {
            "total": len(offers),
            "available": sum(offer.availability is OfferAvailability.AVAILABLE for offer in offers),
            "configuration_required": sum(
                offer.availability is OfferAvailability.CONFIGURATION_REQUIRED for offer in offers
            ),
            "unavailable": sum(offer.availability is OfferAvailability.UNAVAILABLE for offer in offers),
        }

    @staticmethod
    def _offer_preference_key(offer: CapabilityOffer) -> tuple[int, int, int, str]:
        availability_rank = {
            OfferAvailability.AVAILABLE: 0,
            OfferAvailability.CONFIGURATION_REQUIRED: 1,
            OfferAvailability.UNAVAILABLE: 2,
        }[offer.availability]
        cost_rank = {
            CostClass.FREE: 0,
            CostClass.POTENTIALLY_PAID: 1,
            CostClass.PAID: 2,
        }[offer.cost_class]
        locality_rank = {
            LocalityClass.LOCAL: 0,
            LocalityClass.HYBRID: 1,
            LocalityClass.REMOTE: 2,
        }[offer.locality]
        return availability_rank, cost_rank, locality_rank, offer.offer_id
