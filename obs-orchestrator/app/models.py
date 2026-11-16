"""Request bodies of the API.

Only the fields the backend actually reads are declared (missing or mistyped ones are a 422
instead of a KeyError/500). Extra fields are kept: user and simulation payloads are stored as
sent by the console, so dropping unknown keys would silently lose data.
"""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator  # type: ignore


class Payload(BaseModel):
    model_config = ConfigDict(extra="allow")

    def to_dict(self) -> Dict[str, Any]:
        """The payload as the backends expect it: declared and extra fields, as sent."""
        return self.model_dump(exclude_unset=True)


class UserCreate(Payload):
    username: str
    monitoringType: Optional[str] = None


class SimulationUser(Payload):
    monitoringType: str


class SimulationCreate(Payload):
    agents: List[Dict[str, Any]]
    user: SimulationUser


class AgentKick(Payload):
    dns: str
    count: int


class AgentMetric(Payload):
    """`dns` is read by the OpenShift agent manager, `ip` by the mock one."""
    id: str
    metric: Dict[str, Any]


class AlertCreate(Payload):
    scope: Literal["metricAgent", "custom"]
    severity: str
    observabilityStack: str
    definition: Dict[str, Any]
    name: Optional[str] = None

    @model_validator(mode="after")
    def check_definition(self):
        if self.scope == "metricAgent":
            required = ("agent", "metric", "expression", "value")
        else:
            required = ("expression", "summary")
            if not self.name:
                raise ValueError("custom alerts need a name")
        missing = [key for key in required if key not in self.definition]
        if missing:
            raise ValueError(f"{self.scope} alert definition is missing: {', '.join(missing)}")
        return self
