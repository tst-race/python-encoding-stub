"""Raceboat API adapter; format-specific work belongs in codec.py."""

import json
import math
from pathlib import Path
import uuid

import commsPluginBindings as bindings

from . import codec


class PluginPythonStubEncoding(bindings.IEncodingComponent):
    def __init__(self, sdk, role_name, plugin_config):
        if sdk is None:
            raise ValueError("An encoding SDK is required")
        metadata = json.loads(Path(__file__).with_name("metadata.json").read_text())
        if not isinstance(metadata["mime_type"], str) or not metadata["mime_type"]:
            raise ValueError("Set the designed MIME type using new_encoding.py")
        capacity = metadata["max_bytes"]
        if type(capacity) is not int or not 0 < capacity <= 2**31 - 1:
            raise ValueError("Set a verified positive int32 max_bytes")
        seconds = metadata["encoding_time_seconds"]
        if (type(seconds) not in (int, float)
                or not math.isfinite(seconds) or seconds <= 0):
            raise ValueError("Set a measured positive encoding_time_seconds")
        super().__init__()
        self.sdk = sdk
        self.role_name = role_name
        self.plugin_directory = plugin_config.pluginDirectory
        self.logging_directory = plugin_config.loggingDirectory
        self.metadata = metadata
        self.save_encoded_output_handle = None
        self.save_encoded_outputs = False
        response = self.sdk.requestPluginUserInput(
            "save-encoded-output",
            "Write encoded outputs to the logging directory for offline analysis? (true/false; default false)",
            False,
        )
        if response.status == bindings.CM_OK:
            self.save_encoded_output_handle = response.handle
        self.sdk.updateState(bindings.COMPONENT_STATE_STARTED)

    def onUserInputReceived(self, handle, answered, response):
        if handle != self.save_encoded_output_handle or self.save_encoded_output_handle is None:
            return bindings.COMPONENT_ERROR
        self.save_encoded_output_handle = None
        if not answered:
            self.save_encoded_outputs = False
            return bindings.COMPONENT_OK
        normalized_response = response.strip().lower()
        if normalized_response in ("true", "1"):
            self.save_encoded_outputs = True
            return bindings.COMPONENT_OK
        if normalized_response in ("false", "0"):
            self.save_encoded_outputs = False
            return bindings.COMPONENT_OK
        self.save_encoded_outputs = False
        return bindings.COMPONENT_ERROR

    def _persist_encoded_output(self, handle, encoded):
        if not self.save_encoded_outputs:
            return
        if not self.logging_directory:
            raise OSError("Logging directory is unavailable")
        output_directory = Path(self.logging_directory) / "encoding-outputs"
        output_directory.mkdir(parents=True, exist_ok=True)
        output_path = output_directory / "encoded-output-{}-{}.bin".format(
            handle, uuid.uuid4().hex
        )
        output_path.write_bytes(encoded)

    def getEncodingProperties(self):
        properties = bindings.EncodingProperties()
        properties.type = self.metadata["mime_type"]
        properties.encodingTime = self.metadata["encoding_time_seconds"]
        return properties

    def getEncodingPropertiesForParameters(self, params):
        properties = bindings.SpecificEncodingProperties()
        properties.maxBytes = self.metadata["max_bytes"]
        return properties

    def encodeBytes(self, handle, params, content):
        try:
            payload = bytes(content)
            if len(payload) > self.metadata["max_bytes"]:
                raise ValueError("Payload exceeds maxBytes")
            encoded = codec.encode(payload, params.json)
            if not isinstance(encoded, bytes):
                raise TypeError("codec.encode must return bytes")
            self._persist_encoded_output(handle, encoded)
            output = bindings.ByteVector(encoded)
        except Exception:
            self.sdk.onBytesEncoded(handle, bindings.ByteVector(), bindings.ENCODE_FAILED)
            return bindings.COMPONENT_ERROR
        self.sdk.onBytesEncoded(handle, output, bindings.ENCODE_OK)
        return bindings.COMPONENT_OK

    def decodeBytes(self, handle, params, content):
        try:
            decoded = codec.decode(bytes(content), params.json)
            if not isinstance(decoded, bytes):
                raise TypeError("codec.decode must return bytes")
            if len(decoded) > self.metadata["max_bytes"]:
                raise ValueError("Decoded payload exceeds maxBytes")
            output = bindings.ByteVector(decoded)
        except Exception:
            self.sdk.onBytesDecoded(handle, bindings.ByteVector(), bindings.ENCODE_FAILED)
            return bindings.COMPONENT_ERROR
        self.sdk.onBytesDecoded(handle, output, bindings.ENCODE_OK)
        return bindings.COMPONENT_OK


def createEncoding(name, sdk, roleName, pluginConfig):
    if name != "pythonStub" or sdk is None:
        return None
    return PluginPythonStubEncoding(sdk, roleName, pluginConfig)