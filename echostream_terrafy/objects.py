"""Base classes for Terraform objects.""" ""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import UserDict
from typing import Any

APPS: dict[str, TerraformObject] = dict()
FUNCTIONS: dict[str, TerraformObject] = dict()
KMS_KEYS: dict[str, TerraformObject] = dict()
MANAGED_NODE_TYPES: dict[str, TerraformObject] = dict()
MESSAGE_TYPES: dict[str, TerraformObject] = dict()
NODES: dict[str, TerraformObject] = dict()


def encode_terraform(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (TerraformObject, TerraformObjectReference)):
        return obj.encode()
    raise TypeError(repr(obj) + " is not JSON serializable")


class TerraformObject(ABC, UserDict):
    """Base class for Terraform objects."""

    __LOCAL_NAME_PATTERN = re.compile(r"[^A-Za-z0-9\_]")
    __CAMEL_CASE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")

    @property
    @abstractmethod
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        """Return a tuple of required and optional attribute keys."""
        return list(), list()

    @property
    def _attributes(self) -> dict:
        """Return a dictionary of attributes in Terraform format."""

        def convert_key(key: str) -> str:
            return self.__CAMEL_CASE_PATTERN.sub("_", key).lower()

        def convert_value(value: Any) -> Any:
            if isinstance(value, list):
                return [convert_value(v) for v in value]
            elif isinstance(value, dict):
                return {convert_key(k): convert_value(v) for k, v in value.items()}
            return value

        attributes = dict()
        required, optional = self._attribute_keys
        for key in required:
            attributes[convert_key(key)] = convert_value(self[key])
        for key in optional:
            if (value := self.get(key)) is not None:
                attributes[convert_key(key)] = convert_value(value)
        return attributes

    @classmethod
    def _convert_to_local_name(cls, value: str) -> str:
        """Convert a string to a Terraform local name."""
        return cls.__LOCAL_NAME_PATTERN.sub("_", value).lower()

    @property
    @abstractmethod
    def _local_name(self) -> str:
        """Return the Terraform local name for the object."""
        pass

    @property
    @abstractmethod
    def _object_class(self) -> str:
        """Return the Terraform object class for the object."""
        pass

    @property
    def _object_type(self) -> str:
        """Return the Terraform object type for the object."""
        return (
            "echostream_"
            + self.__CAMEL_CASE_PATTERN.sub("_", self.__class__.__name__).lower()
        )

    @property
    @abstractmethod
    def address(self) -> str:
        """Return the Terraform address for the object."""
        pass

    def encode(self) -> dict:
        """Return a dictionary of the object in Terraform format."""
        return {
            self._object_class: {
                self._object_type: {self._local_name: self._attributes}
            }
        }


class TerraformObjectReference:
    """Base class for Terraform object references."""

    def __init__(self, obj: TerraformObject):
        """Initialize the object reference."""
        self.obj = obj

    def encode(self) -> str:
        """Return a string of the object reference in Terraform format."""
        return "${" + f"{self.obj.address}.name" + "}"
