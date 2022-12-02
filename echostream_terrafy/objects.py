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
    if isinstance(obj, (TerraformObject, TerraformObjectReference)):
        return obj.encode()
    raise TypeError(repr(obj) + " is not JSON serializable")


class TerraformObject(ABC, UserDict):

    __LOCAL_NAME_PATTERN = re.compile(r"[^A-Za-z0-9\_]")
    __CAMEL_CASE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")

    @property
    @abstractmethod
    def _attribute_keys(self) -> tuple[list[str], list[str]]:
        return list(), list()

    @property
    def _attributes(self) -> dict:
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
        return cls.__LOCAL_NAME_PATTERN.sub("_", value).lower()

    @property
    @abstractmethod
    def _local_name(self) -> str:
        pass

    @property
    @abstractmethod
    def _object_class(self) -> str:
        pass

    @property
    def _object_type(self) -> str:
        return (
            "echostream_"
            + self.__CAMEL_CASE_PATTERN.sub("_", self.__class__.__name__).lower()
        )

    @property
    @abstractmethod
    def address(self) -> str:
        pass

    def encode(self) -> dict:
        return {
            self._object_class: {
                self._object_type: {self._local_name: self._attributes}
            }
        }


class TerraformObjectReference:
    def __init__(self, obj: TerraformObject):
        self.obj = obj

    def encode(self) -> str:
        return "${" + f"{self.obj.address}.name" + "}"
