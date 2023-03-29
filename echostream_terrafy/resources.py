"""Terraform resources."""
from io import TextIOBase
from os import makedirs, path

import simplejson as json

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


class Resource(TerraformObject):
    """Base class for Terraform resources."""

    @property
    def __artifacts_path(self) -> str:
        """Return the path to the resource's artifacts."""
        return path.join("artifacts", self._object_type, self._local_name)

    def _file(self, file_name: str) -> str:
        """Return a Terraform file reference to an artifact file."""
        return f'${{file("{path.join("${path.module}", self.__artifacts_path, file_name)}")}}'

    @property
    def _local_name(self) -> str:
        return self._convert_to_local_name(self.identity)

    @property
    def _object_class(self) -> str:
        return "resource"

    def _open_artifact(self, file_name: str) -> TextIOBase:
        """Open an artifact file for writing."""
        makedirs(self.__artifacts_path, exist_ok=True)
        return open(path.join(self.__artifacts_path, file_name), "wt")

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

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["description", "name"], ["requirements"]

    @property
    def _attributes(self) -> dict:
        attributes = dict(
            super()._attributes,
            code=self._file("code.py"),
        )
        if self.get("readme"):
            attributes["readme"] = self._file("readme.md")
        return attributes

    def encode(self) -> dict:
        with self._open_artifact("code.py") as f:
            f.write(self["code"])
        if readme := self.get("readme"):
            with self._open_artifact("readme.md") as f:
                f.write(readme)
        return super().encode()


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
            attributes["config"] = self._file("config.json")
        return attributes

    def encode(self) -> dict:
        if config := self.get("config"):
            with self._open_artifact("config.json") as f:
                f.write(config)
        return super().encode()


class ApiAuthenticatorFunction(FunctionResource):
    """Terraform resource for an API authenticator function."""

    pass


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


class BitmapRouterNode(ConfigResource, NodeResource):
    """Terraform resource for a bitmap router node."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], [
            "description",
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
        if self.get("inlineBitmapper"):
            attributes["inline_bitmapper"] = self._file("inline_bitmapper.py")
        if managed_bitmapper := self.get("managedBitmapper"):
            attributes["managed_bitmapper"] = TerraformObjectReference(
                FUNCTIONS[managed_bitmapper["name"]]
            )
        if route_table := json.loads(self.get("routeTable", "{}")):
            attributes["route_table"] = route_table
        return attributes

    def encode(self) -> dict:
        if inline_bitmapper := self.get("inlineBitmapper"):
            with self._open_artifact("inline_bitmapper.py") as f:
                f.write(inline_bitmapper)
        return super().encode()


class BitmapperFunction(FunctionResource):
    """Terraform resource for a bitmapper function."""

    @property
    def _attributes(self) -> dict:
        return dict(
            super()._attributes,
            argument_message_type=TerraformObjectReference(
                MESSAGE_TYPES[self["argumentMessageType"]["name"]]
            ),
        )


class CrossAccountApp(ConfigResource, AppResource):
    """Terraform resource for a cross-account app."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["account", "name"], ["description", "tableAccess"]


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


class CrossTenantSendingNode(ConfigResource, NodeResource):
    """Terraform resource for a cross-tenant sending node."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], [
            "description",
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
        if self.get("inlineProcessor"):
            attributes["inline_processor"] = self._file("inline_processor.py")
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

    def encode(self) -> dict:
        if inline_processor := self.get("inlineProcessor"):
            with self._open_artifact("inline_processor.py") as f:
                f.write(inline_processor)
        return super().encode()


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


class ExternalApp(ConfigResource, AppResource):
    """Terraform resource for an external app."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["description", "tableAccess"]


class ExternalNode(ConfigResource, NodeResource):
    """Terraform resource for an external node."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["description"]

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


class ManagedApp(ConfigResource, AppResource):
    """Terraform resource for a managed app."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["description", "tableAccess"]


class ManagedNode(ConfigResource, NodeResource):
    """Terraform resource for a managed node."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], ["description", "loggingLevel", "mounts", "ports"]

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
            "mountRequirements",
            "portRequirements",
        ]

    @property
    def _attributes(self) -> dict:
        attributes = (super()._attributes,)
        if self.get("configTemplate"):
            attributes["config_template"] = self._file("config_template.json")
        if self.get("readme"):
            attributes["readme"] = self._file("readme.md")
        if receive_message_type := self.get("receiveMessageType"):
            attributes["receive_message_type"] = TerraformObjectReference(
                MESSAGE_TYPES[receive_message_type["name"]]
            )
        if send_message_type := self.get("sendMessageType"):
            attributes["send_message_type"] = TerraformObjectReference(
                MESSAGE_TYPES[send_message_type["name"]]
            )
        return attributes

    def encode(self) -> dict:
        if config_template := self.get("configTemplate"):
            with self._open_artifact("config_template.json", "w") as f:
                f.write(config_template)
        if readme := self.get("readme"):
            with self._open_artifact("readme.md") as f:
                f.write(readme)
        return super().encode()


class MessageType(Resource):
    """Terraform resource for a message type."""

    def __init__(self, dict=None, /, **kwargs):
        super().__init__(dict, **kwargs)
        MESSAGE_TYPES[self["name"]] = self

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return [
            "description",
            "name",
        ], ["requirements"]

    @property
    def _attributes(self) -> dict:
        attributes = dict(
            super()._attributes,
            auditor=self._file("auditor.py"),
            bitmapper_template=self._file("bitmapper_template.py"),
            processor_template=self._file("processor_template.py"),
            sample_message=self._file("sample_message.txt"),
        )
        if self.get("readme"):
            attributes["readme"] = self._file("readme.md")
        return attributes

    def encode(self) -> dict:
        with self._open_artifact("auditor.py") as f:
            f.write(self["auditor"])
        with self._open_artifact("bitmapper_template.py") as f:
            f.write(self["bitmapperTemplate"])
        with self._open_artifact("processor_template.py") as f:
            f.write(self["processorTemplate"])
        with self._open_artifact("sample_message.txt") as f:
            f.write(self["sampleMessage"])
        if readme := self.get("readme"):
            with self._open_artifact("readme.md") as f:
                f.write(readme)
        return super().encode()


class ProcessorFunction(FunctionResource):
    """Terraform resource for a processor function."""

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


class ProcessorNode(ConfigResource, NodeResource):
    """Terraform resource for a processor node."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], [
            "description",
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
        if self.get("inlineProcessor"):
            attributes["inline_processor"] = self._file("inline_processor.py")
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

    def encode(self) -> dict:
        if inline_processor := self.get("inlineProcessor"):
            with self._open_artifact("inline_processor.py") as f:
                f.write(inline_processor)
        return super().encode()


class Tenant(ConfigResource, Resource):
    """Terraform resource for a tenant."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return [], ["description"]

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


class WebhookNode(ConfigResource, NodeResource):
    """Terraform resource for a webhook node."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], [
            "description",
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
        if self.get("inlineApiAuthenticator"):
            attributes["inline_api_authenticator"] = self._file(
                "inline_api_authenticator.py"
            )
        if managed_api_authenticator := self.get("managedApiAuthenticator"):
            attributes["managed_api_authenticator"] = TerraformObjectReference(
                FUNCTIONS[managed_api_authenticator["name"]]
            )
        return attributes

    def encode(self) -> dict:
        if inline_api_authenticator := self.get("inlineApiAuthenticator"):
            with self._open_artifact("inline_api_authenticator.py") as f:
                f.write(inline_api_authenticator)
        return super().encode()


class WebSubHubNode(ConfigResource, NodeResource):
    """Terraform resource for a WebSub hub node."""

    @property
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return ["name"], [
            "defaultLeaseSeconds",
            "deliverRetries",
            "description",
            "maxLeaseSeconds",
            "loggingLevel",
            "requirements",
            "signatureAlgorithm",
            "subscriptionSecurity",
        ]

    @property
    def _attributes(self) -> dict:
        attributes = super()._attributes
        if self.get("inlineApiAuthenticator"):
            attributes["inline_api_authenticator"] = self._file(
                "inline_api_authenticator.py"
            )
        if managed_api_authenticator := self.get("managedApiAuthenticator"):
            attributes["managed_api_authenticator"] = TerraformObjectReference(
                FUNCTIONS[managed_api_authenticator["name"]]
            )
        return attributes

    def encode(self) -> dict:
        if inline_api_authenticator := self.get("inlineApiAuthenticator"):
            with self._open_artifact("inline_api_authenticator.py") as f:
                f.write(inline_api_authenticator)
        return super().encode()


def factory(data: dict) -> Resource:
    """Create a resource from a dictionary."""
    cls = globals().get(data["__typename"])
    return cls(data) if cls else None
