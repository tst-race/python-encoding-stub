import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GeneratorTests(unittest.TestCase):
    def command(self, output):
        return [sys.executable, str(ROOT / "new_encoding.py"), "--name", "Example",
                "--mime-type", "image/png", "--max-bytes", "256",
                "--encoding-time-seconds", "0.5", "--out", str(output)]

    def test_generate_test_and_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "example-encoding"
            subprocess.run(self.command(output), check=True, capture_output=True, text=True)
            package = "PluginExampleEncoding"
            metadata = json.loads((output / "source" / package / "metadata.json").read_text())
            self.assertEqual(metadata, {"encoding_id": "example", "mime_type": "image/png",
                                        "max_bytes": 256, "encoding_time_seconds": 0.5})
            self.assertFalse((output / "new_encoding.py").exists())
            subprocess.run(["bash", str(output / "run_unit_tests.sh"), "-v"],
                           check=True, capture_output=True, text=True)
            subprocess.run([sys.executable, str(output / "build_artifacts.py"), "--arch", "x86_64"],
                           check=True, capture_output=True, text=True)
            for role in ("client", "server"):
                staged = output / "kit" / "artifacts" / ("linux-x86_64-" + role) / package
                manifest = json.loads((staged / "manifest.json").read_text())["plugins"][0]
                self.assertEqual(manifest["python_module"], package + ".plugin")
                self.assertEqual(manifest["python_class"], package)
                self.assertEqual(manifest["encodings"], ["example"])
                self.assertTrue((staged / "codec.py").is_file())
                self.assertTrue((staged / "requirements.txt").is_file())
                self.assertFalse(list(staged.rglob("__pycache__")))
                subprocess.run([sys.executable, "-c",
                                "import importlib.util; assert importlib.util.find_spec('" + package + ".codec')"],
                               cwd=staged.parent, check=True, capture_output=True, text=True)
            rejected = subprocess.run(self.command(output), capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)

    def test_invalid_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            for flag, value in (("--name", "../Bad"), ("--mime-type", "*/*"),
                                ("--max-bytes", "0"), ("--max-bytes", "2147483648"),
                                ("--encoding-time-seconds", "nan"),
                                ("--encoding-time-seconds", "0")):
                with self.subTest(flag=flag, value=value):
                    output = Path(temporary) / "invalid"
                    command = self.command(output)
                    command[command.index(flag) + 1] = value
                    self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
                    self.assertFalse(output.exists())

    def test_template_cannot_be_packaged(self):
        result = subprocess.run([sys.executable, str(ROOT / "build_artifacts.py")], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"template metadata is unset", result.stderr)


if __name__ == "__main__":
    unittest.main()