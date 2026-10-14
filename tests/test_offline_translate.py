"""Dependency-free smoke tests: python -m unittest discover -s tests"""
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "offline_translate.py"
spec = importlib.util.spec_from_file_location("offline_translate", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeEngine:
    dictionary = {"czerwone oczy": "red eyes", "kot": "cat", "piękny krajobraz": "beautiful landscape", "kolor": "colour"}

    def translate(self, text):
        return self.dictionary.get(text, "translated " + text)


class OfflineTranslateTests(unittest.TestCase):
    def test_syntax(self):
        with patch.object(mod, "_get_engine", return_value=FakeEngine()):
            inp = "(czerwone oczy:1.25), <lora:my_style:0.7>; __city__ [kot]\npiekny"
            output = mod.translate_prompt(inp)
            self.assertEqual(output, "(red eyes:1.25), <lora:my_style:0.7>; __city__ [cat]\ntranslated piekny")

    def test_us_spelling(self):
        with patch.object(mod, "_get_engine", return_value=FakeEngine()):
            self.assertEqual(mod.translate_prompt("kolor"), "color")

    def test_blank_no_engine(self):
        self.assertEqual(mod.translate_prompt("   "), "   ")

    def test_length(self):
        with self.assertRaises(ValueError):
            mod.translate_prompt("a" * (mod.MAX_PROMPT_LENGTH + 1))

    def test_model_zip_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            archive = base / "ok.argosmodel"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("metadata.json", json.dumps({"from_code": "pl", "to_code": "en"}))
                z.writestr("model/model.bin", b"fake")
            with patch.object(mod, "MODEL_DIR", base), patch.object(mod, "EXTRACTED", base / "pl_en"):
                self.assertEqual(mod._archive_model(archive), base / "pl_en")
                self.assertTrue((base / "pl_en" / "metadata.json").exists())

    def test_reject_archive_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            archive = base / "bad.argosmodel"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("../evil", "x")
            with patch.object(mod, "MODEL_DIR", base), patch.object(mod, "EXTRACTED", base / "pl_en"):
                with self.assertRaises(RuntimeError):
                    mod._archive_model(archive)
                self.assertFalse((base.parent / "evil").exists())


if __name__ == "__main__":
    unittest.main()
