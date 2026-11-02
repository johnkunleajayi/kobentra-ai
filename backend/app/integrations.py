from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class IntegrationScope:
    organization_id: str
    user_id: str
    # Must be constructed after trusted identity and membership authorization.


class SalesforceAdapter(Protocol):
    def sync_authorized_opportunities(self, scope: IntegrationScope) -> None: ...


class EventDiscoveryAdapter(Protocol):
    # Kobentra-owned contract, NOT an asserted EventSpark API.
    def discover_authorized_events(self, scope: IntegrationScope) -> list[dict]: ...


class DisconnectedSalesforce:
    status = "not_connected"

    def sync_authorized_opportunities(self, scope: IntegrationScope) -> None:
        raise RuntimeError("Salesforce is not connected")


class PlannedEventSpark:
    status = "planned"

    def discover_authorized_events(self, scope: IntegrationScope) -> list[dict]:
        raise RuntimeError("EventSpark capabilities and sandbox access are unverified")
