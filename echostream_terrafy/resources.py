"""Terraform resources.""" ""
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
    """Base class for Terraform resources."""

    @property
    def _artifacts_path(self) -> str:
        """Return the path to the resource's artifacts."""
        return f"artifacts/{self._object_type}/{self._local_name}"
    
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
        """The identity of the resource."""
        return self["name"]


class AppResource(Resource):
    """Base class for Terraform app resources."""

    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        APPS[self["name"]] = self


class FunctionResource(Resource):
    """Base class for Terraform function resources."""

    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        FUNCTIONS[self["name"]] = self


class NodeResource(Resource):
    """Base class for Terraform node resources."""

    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        NODES[self["name"]] = self


class ConfigResource(Resource):
    """Base class for Terraform config resources."""

    @property
    def _attributes(self) -> dict:
        attributes = super()._attributes
        if self.get("config"):
            attributes["config"] = f'${{file("${{path.module}}/{self._artifacts_path}/config.json")}}'
        return attributes
    
    def encode(self) -> dict:

        return super().encode()

class ApiAuthenticatorFunction(FunctionResource):
    """Terraform resource for an API authenticator function."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["code", "description", "name"], ["readme", "requirements"]


class ApiUser(Resource):
    """Terraform resource for an API user"""

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
    """Terraform resource for a bitmap router node."""

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
    """Terraform resource for a bitmapper function."""

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
    """Terraform resource for a cross-account app."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["account", "name"], ["config", "description", "tableAccess"]


class CrossTenantReceivingApp(AppResource):
    """Terraform resource for a cross-tenant receiving app."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name", "sendingTenant"], ["description"]


class CrossTenantReceivingNode(NodeResource):
    """Terraform resource for a cross-tenant receiving node."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return list(), list()


class CrossTenantSendingApp(AppResource):
    """Terraform resource for a cross-tenant sending app."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name", "receivingApp", "receivingTenant"], ["description"]


class CrossTenantSendingNode(NodeResource):
    """Terraform resource for a cross-tenant sending node."""

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
        attributes["sequential_processing"] = attributes.get(
            "sequential_processing", False
        )
        return attributes


class Edge(Resource):
    """Terraform resource for an edge."""

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
    """Terraform resource for an external app."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["config", "description", "tableAccess"]


class ExternalNode(NodeResource):
    """Terraform resource for an external node."""

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
    """Terraform resource for a Files.com webhook node."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["description"]


class KmsKey(Resource):
    """Terraform resource for a KMS key."""

    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        KMS_KEYS[self["name"]] = self

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["description"]


class LoadBalancerNode(NodeResource):
    """Terraform resource for a load balancer node."""

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
    """Terraform resource for a managed app."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["config", "description", "tableAccess"]


class ManagedNode(NodeResource):
    """Terraform resource for a managed node."""

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
    """Terraform resource for a managed node type."""

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
    """Terraform resource for a message type."""

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
    """Terraform resource for a processor function."""

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
    """Terraform resource for a processor node."""

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
        attributes["sequential_processing"] = attributes.get(
            "sequential_processing", False
        )
        return attributes


class Tenant(Resource):
    """Terraform resource for a tenant."""

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
    """Terraform resource for a tenant user."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["email", "role"], ["status"]

    @property
    def identity(self) -> str:
        return self["email"]


class TimerNode(NodeResource):
    """Terraform resource for a timer node."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name", "scheduleExpression"], ["description"]


class WebhookNode(NodeResource):
    """Terraform resource for a webhook node."""

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


class WebSubHubNode(NodeResource):
    """Terraform resource for a WebSub hub node."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], [
            "config",
            "defaultLeaseSeconds",
            "deliverRetries",
            "description",
            "inlineApiAuthenticator",
            "maxLeaseSeconds",
            "loggingLevel",
            "requirements",
            "signatureAlgorithm",
            "subscriptionSecurity",
        ]

    @property
    def _attributes(self) -> dict:
        attributes = super()._attributes
        if managed_api_authenticator := self.get("managedApiAuthenticator"):
            attributes["managed_api_authenticator"] = TerraformObjectReference(
                FUNCTIONS[managed_api_authenticator["name"]]
            )
        return attributes


def factory(data: dict) -> Resource:
    """Create a resource from a dictionary."""
    cls = globals().get(data["__typename"])
    return cls(data) if cls else None
