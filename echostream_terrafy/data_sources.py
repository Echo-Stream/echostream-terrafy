"""Data sources for Terraform objects."""
from __future__ import annotations

from .objects import (
    APPS,
    FUNCTIONS,
    MANAGED_NODE_TYPES,
    MESSAGE_TYPES,
    NODES,
    TerraformObject,
    TerraformObjectReference,
)


class DataSource(TerraformObject):
    """Base class for Terraform data sources."""

    @property
    def _object_class(self) -> str:
        return "data"

    @property
    def address(self) -> str:
        return f"data.{self._object_type}.{self._local_name}"


class NodeDataSource(DataSource):
    """Base class for Terraform node data sources."""

    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        NODES[self["name"]] = self

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return list(), list()

    @property
    def _local_name(self) -> str:
        return "current"


class FunctionDataSource(DataSource):
    """Base class for Terraform function data sources."""

    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        FUNCTIONS[self["name"]] = self

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], list()

    @property
    def _local_name(self) -> str:
        return self._convert_to_local_name(self["name"])


class AlertEmitterNode(NodeDataSource):
    """Terraform data source for an alert emitter node."""

    pass


class ApiAuthenticatorFunction(FunctionDataSource):
    """Terraform data source for an API authenticator function."""

    pass


class AppChangeReceiverNode(NodeDataSource):
    """Terraform data source for an app change receiver node."""

    @property
    def _attributes(self) -> dict:
        attributes = super()._attributes
        attributes["app"] = TerraformObjectReference(APPS[self["app"]["name"]])
        return attributes

    @property
    def _local_name(self) -> str:
        return self._convert_to_local_name(self["app"]["name"])


class AppChangeRouterNode(NodeDataSource):
    """Terraform data source for an app change router node."""

    pass


class AuditEmitterNode(NodeDataSource):
    """Terraform data source for an audit emitter node."""

    pass


class BitmapperFunction(FunctionDataSource):
    """Terraform data source for a bitmapper function."""

    pass


class ChangeEmitterNode(NodeDataSource):
    """Terraform data source for a change emitter node."""

    pass


class CrossTenantReceivingNode(NodeDataSource):
    """Terraform data source for a cross-tenant receiving node."""

    pass


class DeadLetterEmitterNode(NodeDataSource):
    """Terraform data source for a dead letter emitter node."""

    pass


class LogEmitterNode(NodeDataSource):
    """Terraform data source for a log emitter node."""

    pass


class ManagedNodeType(DataSource):
    """Terraform data source for a managed node type."""

    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        MANAGED_NODE_TYPES[self["name"]] = self

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], list()

    @property
    def _local_name(self) -> str:
        return self._convert_to_local_name(self["name"])


class MessageType(DataSource):
    """Terraform data source for a message type."""

    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        MESSAGE_TYPES[self["name"]] = self

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], list()

    @property
    def _local_name(self) -> str:
        return self._convert_to_local_name(self["name"])


class ProcessorFunction(FunctionDataSource):
    """Terraform data source for a processor function."""

    pass


def factory(data: dict) -> DataSource:
    """Factory function for data sources."""
    cls = globals().get(data["__typename"])
    return cls(data) if cls else None
