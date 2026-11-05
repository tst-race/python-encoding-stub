"""Run separately with the matching Raceboat runtime and its real SWIG bindings."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import commsPluginBindings as bindings

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from PluginPythonStubEncoding import plugin


class RecordingSdk(bindings.IEncodingSdk):
    def __init__(self):
        super().__init__()
        self.events = []

    def updateState(self, state):
        self.events.append(("state", state))
        response = bindings.ChannelResponse()
        response.status = bindings.CM_OK
        return response

    def onBytesEncoded(self, handle, content, status):
        self.events.append(("encoded", handle, bytes(content), status))
        response = bindings.ChannelResponse()
        response.status = bindings.CM_OK
        return response

    def onBytesDecoded(self, handle, content, status):
        self.events.append(("decoded", handle, bytes(content), status))
        response = bindings.ChannelResponse()
        response.status = bindings.CM_OK
        return response


def main():
    sdk = RecordingSdk()
    metadata = '{"mime_type":"application/octet-stream","max_bytes":256,"encoding_time_seconds":0.25}'
    with patch.object(Path, "read_text", return_value=metadata):
        component = plugin.createEncoding("pythonStub", sdk, "", SimpleNamespace(pluginDirectory="/kits/test"))
    params = bindings.EncodingParameters()
    params.json = "{}"
    assert component.getEncodingProperties().type == "application/octet-stream"
    assert component.getEncodingPropertiesForParameters(params).maxBytes == 256
    for payload in (b"", bytes(range(256))):
        vector = bindings.ByteVector(payload)
        assert bytes(vector) == payload
        with patch.object(plugin.codec, "encode", return_value=payload):
            assert component.encodeBytes(7, params, vector) == bindings.COMPONENT_OK
        assert sdk.events[-1] == ("encoded", 7, payload, bindings.ENCODE_OK)
        with patch.object(plugin.codec, "decode", return_value=payload):
            assert component.decodeBytes(8, params, vector) == bindings.COMPONENT_OK
        assert sdk.events[-1] == ("decoded", 8, payload, bindings.ENCODE_OK)
    assert component.encodeBytes(9, params, bindings.ByteVector()) == bindings.COMPONENT_ERROR
    assert sdk.events[-1] == ("encoded", 9, b"", bindings.ENCODE_FAILED)
    print("Real SWIG properties, byte vectors, and Python SDK callbacks passed (test codec hooks).")


if __name__ == "__main__":
    main()