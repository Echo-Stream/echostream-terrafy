from .objects import (
    APPS,
    FUNCTIONS,
    KMS_KEYS,
    MANAGED_NODE_TYPES,
    MESSAGE_TYPES,
    NODES,
    TerraformObject,
    TerraformObjectReference,
)
import simplejson as json


class Resource(TerraformObject):
    @property
    def _local_name(self) -> str:
        return self._convert_to_local_name(self.identity)

    @property
    def _object_class(self) -> str:
        return "resource"

    @property
    def address(self) -> str:
        return f"{self._object_type}.{self._local_name}"

    @property
    def identity(self) -> str:
        return self["name"]


class AppResource(Resource):
    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        APPS[self["name"]] = self


class FunctionResource(Resource):
    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        FUNCTIONS[self["name"]] = self


class NodeResource(Resource):
    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        NODES[self["name"]] = self


class ApiAuthenticatorFunction(FunctionResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["code", "description", "name"], ["readme", "requirements"]


class ApiUser(Resource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["role"], ["description"]

    @property
    def _local_name(self) -> str:
        return f"_{self.identity}_".lower()

    @property
    def identity(self) -> str:
        return self["username"]


class BitmapRouterNode(NodeResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], [
            "config",
            "description",
            "inlineBitmapper",
            "loggingLevel",
            "requirements",
        ]

    @property
    def _attributes(self) -> dict:
        attributes = dict(
            super()._attributes,
            receive_message_type=TerraformObjectReference(
                MESSAGE_TYPES[self["receiveMessageType"]["name"]]
            ),
        )
        if managed_bitmapper := self.get("managedBitmapper"):
            attributes["managed_bitmapper"] = TerraformObjectReference(
                FUNCTIONS[managed_bitmapper["name"]]
            )
        if route_table := json.loads(self.get("routeTable", "{}")):
            attributes["route_table"] = route_table
        return attributes


class BitmapperFunction(FunctionResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["code", "description", "name"], ["readme", "requirements"]

    @property
    def _attributes(self) -> dict:
        return dict(
            super()._attributes,
            argument_message_type=TerraformObjectReference(
                MESSAGE_TYPES[self["argumentMessageType"]["name"]]
            ),
        )


class CrossAccountApp(AppResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["account", "name"], ["config", "description", "tableAccess"]


class CrossTenantReceivingApp(AppResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name", "sendingTenant"], ["description"]


class CrossTenantReceivingNode(NodeResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], []


class CrossTenantSendingApp(AppResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name", "receivingApp", "receivingTenant"], ["description"]


class CrossTenantSendingNode(NodeResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], [
            "config",
            "description",
            "inlineProcessor",
            "loggingLevel",
            "requirements",
            "sequentialProcessing",
        ]

    @property
    def _attributes(self) -> dict:
        attributes = dict(
            super()._attributes,
            app=TerraformObjectReference(APPS[self["app"]["name"]]),
            receive_message_type=TerraformObjectReference(
                MESSAGE_TYPES[self["receiveMessageType"]["name"]]
            ),
        )
        if managed_processor := self.get("managedProcessor"):
            attributes["managed_processor"] = TerraformObjectReference(
                obj=FUNCTIONS[managed_processor["name"]], attr="name"
            )
        if send_message_type := self.get("sendMessageType"):
            attributes["send_message_type"] = TerraformObjectReference(
                obj=MESSAGE_TYPES[send_message_type["name"]], attr="name"
            )
        attributes["sequential_processing"] = attributes.get("sequential_processing", False)
        return attributes


class Edge(Resource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return [], ["description", "maxReceiveCount"]

    @property
    def _attributes(self) -> dict:
        attributes = dict(
            super()._attributes,
            source=TerraformObjectReference(NODES[self["source"]["name"]]),
            target=TerraformObjectReference(NODES[self["target"]["name"]]),
        )
        if kmskey := self.get("kmsKey"):
            attributes["kmskey"] = TerraformObjectReference(
                obj=KMS_KEYS[kmskey["name"]], attr="name"
            )
        return attributes

    @property
    def identity(self) -> str:
        return f'{self["source"]["name"]}|{self["target"]["name"]}'


class ExternalApp(AppResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["config", "description", "tableAccess"]


class ExternalNode(NodeResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["config", "description"]

    @property
    def _attributes(self) -> dict:
        attributes = dict(
            super()._attributes,
            app=TerraformObjectReference(APPS[self["app"]["name"]]),
        )
        if receive_message_type := self.get("receiveMessageType"):
            attributes["receive_message_type"] = TerraformObjectReference(
                MESSAGE_TYPES[receive_message_type["name"]]
            )
        if send_message_type := self.get("sendMessageType"):
            attributes["send_message_type"] = TerraformObjectReference(
                MESSAGE_TYPES[send_message_type["name"]]
            )
        return attributes


class FilesDotComWebhookNode(NodeResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["description"]


class KmsKey(Resource):
    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        KMS_KEYS[self["name"]] = self

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["description"]


class LoadBalancerNode(NodeResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["description"]

    @property
    def _attributes(self) -> dict:
        return dict(
            super()._attributes,
            receive_message_type=TerraformObjectReference(
                MESSAGE_TYPES[self["receiveMessageType"]["name"]]
            ),
        )


class ManagedApp(AppResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["config", "description", "tableAccess"]


class ManagedNode(NodeResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["config", "description", "loggingLevel", "mounts", "ports"]

    @property
    def _attributes(self) -> dict:
        return dict(
            super()._attributes,
            app=TerraformObjectReference(APPS[self["app"]["name"]]),
            managed_node_type=TerraformObjectReference(
                MANAGED_NODE_TYPES[self["managedNodeType"]["name"]]
            ),
        )


class ManagedNodeType(Resource):
    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        MANAGED_NODE_TYPES[self["name"]] = self

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["description", "imageUri", "name"], [
            "configTemplate",
            "mountRequirements",
            "portRequirements",
            "readme",
        ]

    @property
    def _attributes(self) -> dict:
        attributes = (super()._attributes,)
        if receive_message_type := self.get("receiveMessageType"):
            attributes["receive_message_type"] = TerraformObjectReference(
                MESSAGE_TYPES[receive_message_type["name"]]
            )
        if send_message_type := self.get("sendMessageType"):
            attributes["send_message_type"] = TerraformObjectReference(
                MESSAGE_TYPES[send_message_type["name"]]
            )
        return attributes


class MessageType(Resource):
    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        MESSAGE_TYPES[self["name"]] = self

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return [
            "auditor",
            "bitmapperTemplate",
            "description",
            "name",
            "processorTemplate",
            "sampleMessage",
        ], ["readme", "requirements"]


class ProcessorFunction(FunctionResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["code", "description", "name"], ["readme", "requirements"]

    @property
    def _attributes(self) -> dict:
        attributes = dict(
            super()._attributes,
            argument_message_type=TerraformObjectReference(
                MESSAGE_TYPES[self["argumentMessageType"]["name"]]
            ),
        )
        if return_message_type := self.get("returnMessageType"):
            attributes["return_message_type"] = TerraformObjectReference(
                MESSAGE_TYPES[return_message_type["name"]]
            )
        return attributes


class ProcessorNode(NodeResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], [
            "config",
            "description",
            "inlineProcessor",
            "loggingLevel",
            "requirements",
            "sequentialProcessing",
        ]

    @property
    def _attributes(self) -> dict:
        attributes = dict(
            super()._attributes,
            receive_message_type=TerraformObjectReference(
                MESSAGE_TYPES[self["receiveMessageType"]["name"]]
            ),
        )
        if managed_processor := self.get("managedProcessor"):
            attributes["managed_processor"] = TerraformObjectReference(
                FUNCTIONS[managed_processor["name"]]
            )
        if send_message_type := self.get("sendMessageType"):
            attributes["send_message_type"] = TerraformObjectReference(
                MESSAGE_TYPES[send_message_type["name"]]
            )
        attributes["sequential_processing"] = attributes.get("sequential_processing", False)
        return attributes


class Tenant(Resource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return [], ["config", "description"]

    @property
    def _local_name(self) -> str:
        return "current"

    @property
    def identity(self) -> str:
        return ""


class TenantUser(Resource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["email", "role"], ["status"]

    @property
    def identity(self) -> str:
        return self["email"]


class TimerNode(NodeResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name", "scheduleExpression"], ["description"]


class WebhookNode(NodeResource):
    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], [
            "config",
            "description",
            "inlineApiAuthenticator",
            "loggingLevel",
            "requirements",
        ]

    @property
    def _attributes(self) -> dict:
        attributes = dict(
            super()._attributes,
            send_message_type=TerraformObjectReference(
                MESSAGE_TYPES[self["sendMessageType"]["name"]]
            ),
        )
        if managed_api_authenticator := self.get("managedApiAuthenticator"):
            attributes["managed_api_authenticator"] = TerraformObjectReference(
                FUNCTIONS[managed_api_authenticator["name"]]
            )
        return attributes


def factory(data: dict) -> Resource:
    cls = globals().get(data["__typename"])
    return cls(data) if cls else None
