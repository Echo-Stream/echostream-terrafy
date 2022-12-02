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
    @property
    def _object_class(self) -> str:
        return "data"

    @property
    def address(self) -> str:
        return f"data.{self._object_type}.{self._local_name}"


class NodeDataSource(DataSource):
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
    pass


class ApiAuthenticatorFunction(FunctionDataSource):
    pass


class AppChangeReceiverNode(NodeDataSource):
    @property
    def _attributes(self) -> dict:
        attributes = super()._attributes
        attributes["app"] = TerraformObjectReference(APPS[self["app"]["name"]])
        return attributes

    @property
    def _local_name(self) -> str:
        return self._convert_to_local_name(self["app"]["name"])


class AppChangeRouterNode(NodeDataSource):
    pass


class AuditEmitterNode(NodeDataSource):
    pass


class BitmapperFunction(FunctionDataSource):
    pass


class ChangeEmitterNode(NodeDataSource):
    pass


class CrossTenantReceivingNode(NodeDataSource):
    pass


class DeadLetterEmitterNode(NodeDataSource):
    pass


class LogEmitterNode(NodeDataSource):
    pass


class ManagedNodeType(DataSource):
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
    pass


def factory(data: dict) -> DataSource:
    cls = globals().get(data["__typename"])
    return cls(data) if cls else None
