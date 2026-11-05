"""Adapter contract tests with an explicit, test-only bindings double."""

import importlib
import tempfile
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / "source"
sys.path.insert(0, str(SOURCE))
fake_bindings = types.ModuleType("commsPluginBindings")
fake_bindings.IEncodingComponent = type("IEncodingComponent", (), {})
fake_bindings.EncodingProperties = type("EncodingProperties", (), {})
fake_bindings.SpecificEncodingProperties = type("SpecificEncodingProperties", (), {})
fake_bindings.ByteVector = list
fake_bindings.CM_OK = "CM_OK"
for constant in ("COMPONENT_OK", "COMPONENT_ERROR", "ENCODE_OK", "ENCODE_FAILED",
                 "COMPONENT_STATE_STARTED"):
    setattr(fake_bindings, constant, constant)
with patch.dict(sys.modules, {"commsPluginBindings": fake_bindings}):
    plugin = importlib.import_module("PluginPythonStubEncoding.plugin")

METADATA = '{"mime_type":"text/plain","max_bytes":256,"encoding_time_seconds":0.25}'


class ComponentTests(unittest.TestCase):
    def setUp(self):
        self.sdk = Mock()
        self.sdk.requestPluginUserInput.return_value = types.SimpleNamespace(
            status="CM_OK", handle=43
        )
        self.params = types.SimpleNamespace(json='{"format":"test"}')
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = types.SimpleNamespace(
            pluginDirectory="/kits/example", loggingDirectory=self.temp_dir.name
        )
        with patch.object(Path, "read_text", return_value=METADATA):
            self.component = plugin.createEncoding("pythonStub", self.sdk, "role", self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_factory_and_properties(self):
        self.assertIsNone(plugin.createEncoding("other", self.sdk, "", self.config))
        self.assertIsNone(plugin.createEncoding("pythonStub", None, "", self.config))
        self.sdk.updateState.assert_called_once_with("COMPONENT_STATE_STARTED")
        self.sdk.requestPluginUserInput.assert_called_once_with(
            "save-encoded-output",
            "Write encoded outputs to the logging directory for offline analysis? (true/false; default false)",
            False,
        )
        self.assertEqual(self.component.plugin_directory, "/kits/example")
        self.assertFalse(self.component.save_encoded_outputs)
        properties = self.component.getEncodingProperties()
        self.assertEqual((properties.type, properties.encodingTime), ("text/plain", 0.25))
        self.assertEqual(self.component.getEncodingPropertiesForParameters(self.params).maxBytes, 256)
        self.assertEqual(self.component.onUserInputReceived(43, False, ""), "COMPONENT_OK")

    def test_unconfigured_template_rejects_creation(self):
        with patch.object(Path, "read_text", return_value='{"mime_type":null}'):
            with self.assertRaises(ValueError):
                plugin.createEncoding("pythonStub", self.sdk, "", self.config)

    def test_hooks_are_unimplemented(self):
        for hook in (plugin.codec.encode, plugin.codec.decode):
            with self.assertRaises(NotImplementedError):
                hook(b"", "{}")

    def test_all_bytes_and_empty_callbacks(self):
        for payload in (b"", bytes(range(256))):
            with self.subTest(size=len(payload)):
                for operation in ("encode", "decode"):
                    self.sdk.reset_mock()
                    with patch.object(plugin.codec, operation, return_value=payload) as hook:
                        method = getattr(self.component, operation + "Bytes")
                        self.assertEqual(method(42, self.params, list(payload)), "COMPONENT_OK")
                        hook.assert_called_once_with(payload, self.params.json)
                    callback = self.sdk.onBytesEncoded if operation == "encode" else self.sdk.onBytesDecoded
                    callback.assert_called_once_with(42, list(payload), "ENCODE_OK")
        self.assertFalse((Path(self.temp_dir.name) / "encoding-outputs").exists())

    def test_persists_encoded_output_only_when_opted_in(self):
        self.assertEqual(self.component.onUserInputReceived(43, True, "true"),
                         "COMPONENT_OK")
        encoded = b"valid encoded content"
        with patch.object(plugin.codec, "encode", return_value=encoded):
            self.assertEqual(self.component.encodeBytes(44, self.params, b"input"),
                             "COMPONENT_OK")
        output_directory = Path(self.temp_dir.name) / "encoding-outputs"
        outputs = list(output_directory.glob("encoded-output-44-*.bin"))
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0].read_bytes(), encoded)

    def test_unanswered_or_invalid_flag_keeps_persistence_disabled(self):
        self.assertEqual(self.component.onUserInputReceived(43, False, ""),
                         "COMPONENT_OK")
        self.assertFalse(self.component.save_encoded_outputs)
        self.assertEqual(self.component.onUserInputReceived(43, True, "yes"),
                         "COMPONENT_ERROR")
        self.assertFalse(self.component.save_encoded_outputs)

    def test_failures_have_one_completion(self):
        for operation in ("encode", "decode"):
            for result in (ValueError("malformed"), NotImplementedError(), "not bytes", b"x" * 257):
                with self.subTest(operation=operation, result=type(result).__name__):
                    self.sdk.reset_mock()
                    kwargs = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
                    with patch.object(plugin.codec, operation, **kwargs):
                        content = b"x" * 257 if operation == "encode" and isinstance(result, bytes) else b"x"
                        status = getattr(self.component, operation + "Bytes")(9, self.params, content)
                    self.assertEqual(status, "COMPONENT_ERROR")
                    callback = self.sdk.onBytesEncoded if operation == "encode" else self.sdk.onBytesDecoded
                    callback.assert_called_once_with(9, [], "ENCODE_FAILED")

    def test_callback_exception_is_not_reported_twice(self):
        self.sdk.onBytesEncoded.side_effect = RuntimeError("SDK failed")
        with patch.object(plugin.codec, "encode", return_value=b"ok"):
            with self.assertRaises(RuntimeError):
                self.component.encodeBytes(1, self.params, b"input")
        self.sdk.onBytesEncoded.assert_called_once()


if __name__ == "__main__":
    unittest.main()