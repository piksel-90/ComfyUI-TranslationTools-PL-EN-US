"""Local PL->EN translation for ComfyUI, without any network operations.

Uses an existing .argosmodel from ./models, its bundled tokenizer and
CTranslate2 inference directly (not Argos' downloadable sentence splitter).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import tempfile
import threading
import zipfile
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent / "models"
EXTRACTED = MODEL_DIR / "pl_en"
_LOAD_LOCK = threading.RLock()
_ENGINE = None
MAX_PROMPT_LENGTH = 20_000

# Keep common CLIP/ComfyUI metasyntax byte-for-byte. Delimiters are not passed
# through the translator. Weighted text is translated but its number isn't.
SPLIT = re.compile(
    r"(<[^>\n]+>|__[-\w./\\]+__|\b(?:embedding|lora):[^,;\s()\[\]]+|\b(?:BREAK|AND)\b|[()\[\],;\n])"
)
WEIGHT = re.compile(r"^(.*?)(\s*:\s*[+-]?\d+(?:\.\d+)?)$", re.DOTALL)
PROTECTED = re.compile(
    r"^(?:<[^>\n]+>|__[-\w./\\]+__|(?:embedding|lora):[^,;\s()\[\]]+|BREAK|AND|[()\[\],;\n])$"
)
US_SPELLINGS = {
    "colour": "color", "colours": "colors", "favourite": "favorite",
    "favourites": "favorites", "centre": "center", "centres": "centers",
    "grey": "gray", "armour": "armor", "theatre": "theater",
    "travelling": "traveling", "traveller": "traveler", "modelling": "modeling",
    "organise": "organize", "organised": "organized", "realise": "realize",
    "realised": "realized", "analyse": "analyze", "analysed": "analyzed",
}
US_PATTERN = re.compile(r"\b(" + "|".join(map(re.escape, US_SPELLINGS)) + r")\b", re.I)


def _americanize(text: str) -> str:
    """Light spelling normalization; not a full en-US dialect model."""
    def replace(match):
        original = match.group(0)
        replacement = US_SPELLINGS[original.lower()]
        if original.isupper():
            return replacement.upper()
        if original[0].isupper():
            return replacement.capitalize()
        return replacement
    return US_PATTERN.sub(replace, text)


def _archive_model(archive: Path) -> Path:
    """Extract to an extension-local directory. Reject unsafe zip entries."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix="._pl_en_", dir=MODEL_DIR))
    payload = temp / "payload"
    payload.mkdir()
    try:
        with zipfile.ZipFile(archive) as zf:
            entries = zf.infolist()
            if len(entries) > 500 or sum(e.file_size for e in entries) > 3_000_000_000:
                raise RuntimeError("Nieprawidłowy lub zbyt duży plik .argosmodel")
            for entry in entries:
                name = entry.filename.replace("\\", "/")
                parts = Path(name).parts
                if not name or name.startswith("/") or ".." in parts or ":" in parts[0]:
                    raise RuntimeError("Niebezpieczna ścieżka w pliku .argosmodel")
                if stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFLNK:
                    raise RuntimeError("Niedozwolone dowiązanie w pliku .argosmodel")
                destination = (payload / name).resolve()
                if not destination.is_relative_to(payload.resolve()):
                    raise RuntimeError("Niedozwolona ścieżka w pliku .argosmodel")
                if entry.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(entry, "r") as source, destination.open("wb") as target:
                        shutil.copyfileobj(source, target)
        found = [p.parent for p in payload.rglob("metadata.json")]
        candidates = []
        for directory in found:
            metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
            if metadata.get("from_code") == "pl" and metadata.get("to_code") == "en":
                candidates.append(directory)
        if len(candidates) != 1 or not (candidates[0] / "model").is_dir():
            raise RuntimeError("Plik nie zawiera poprawnego modelu Argos PL → EN")
        if EXTRACTED.exists():
            return EXTRACTED
        os.replace(str(candidates[0]), str(EXTRACTED))
        return EXTRACTED
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _model_path() -> Path:
    if (EXTRACTED / "metadata.json").is_file():
        metadata = json.loads((EXTRACTED / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("from_code") != "pl" or metadata.get("to_code") != "en":
            raise RuntimeError("Katalog models/pl_en zawiera model innego języka")
        return EXTRACTED
    archives = sorted(MODEL_DIR.glob("*.argosmodel"))
    if not archives:
        raise RuntimeError(
            "Nie znaleziono lokalnego modelu PL → EN. "
            "Skopiuj plik translate-pl_en-*.argosmodel do katalogu models/ dodatku, "
            "a potem ponów tłumaczenie."
        )
    return _archive_model(archives[0])


class _Engine:
    def __init__(self, package_dir: Path):
        try:
            import argostranslate.package
            import ctranslate2
        except ImportError as exc:
            raise RuntimeError(
                "Brakuje bibliotek offline: argostranslate / ctranslate2. "
                "Zainstaluj requirements.txt w środowisku Python ComfyUI."
            ) from exc
        self.pkg = argostranslate.package.Package(package_dir)
        self.translator = ctranslate2.Translator(
            str(package_dir / "model"), device="cpu", inter_threads=1
        )
        self.infer_lock = threading.Lock()

    def translate(self, phrase: str) -> str:
        source_tokens = self.pkg.tokenizer.encode(phrase)
        if not source_tokens:
            return phrase
        prefix = getattr(self.pkg, "target_prefix", "") or ""
        kwargs = {
            "beam_size": 4,
            "num_hypotheses": 1,
            "replace_unknowns": True,
        }
        if prefix:
            kwargs["target_prefix"] = [[prefix]]
        with self.infer_lock:
            result = self.translator.translate_batch([source_tokens], **kwargs)[0]
        translated = self.pkg.tokenizer.decode(result.hypotheses[0]).strip()
        if prefix and translated.startswith(prefix):
            translated = translated[len(prefix):].lstrip()
        return translated


def _get_engine():
    global _ENGINE
    with _LOAD_LOCK:
        if _ENGINE is None:
            _ENGINE = _Engine(_model_path())
        return _ENGINE


def translate_prompt(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("Prompt musi być tekstem")
    if len(text) > MAX_PROMPT_LENGTH:
        raise ValueError(f"Prompt jest za długi (limit {MAX_PROMPT_LENGTH} znaków)")
    if not text.strip():
        return text
    engine = _get_engine()
    result = []
    for part in SPLIT.split(text):
        if not part or PROTECTED.fullmatch(part):
            result.append(part)
            continue
        leading = part[:len(part) - len(part.lstrip())]
        trailing = part[len(part.rstrip()):]
        value = part.strip()
        if not value:
            result.append(part)
            continue
        weight_match = WEIGHT.match(value)
        suffix = ""
        if weight_match and weight_match.group(1).strip():
            value = weight_match.group(1).strip()
            suffix = weight_match.group(2)
        # Clip prompt fragments sometimes contain pure numbers or punctuation.
        if not re.search(r"[^\W\d_]", value, re.UNICODE):
            translated = value
        else:
            translated = engine.translate(value) or value
        result.append(leading + _americanize(translated) + suffix + trailing)
    return "".join(result)
