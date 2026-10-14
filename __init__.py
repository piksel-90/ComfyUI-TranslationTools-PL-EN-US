"""ComfyUI PL->EN-US Offline: editable CLIP button and workflow nodes."""

import asyncio
import zipfile
from aiohttp import web
from server import PromptServer

from .offline_translate import translate_prompt


class PLToENOffline:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text_pl": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False})}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text_en_us",)
    FUNCTION = "translate"
    CATEGORY = "language/offline"
    DESCRIPTION = "Offline Polish to English (US spelling). Connect STRING to CLIP Text Encode."

    def translate(self, text_pl):
        return (translate_prompt(text_pl),)


class PLToENClipOffline:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "clip": ("CLIP",),
            "text_pl": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False}),
        }}

    RETURN_TYPES = ("CONDITIONING", "STRING")
    RETURN_NAMES = ("conditioning", "text_en_us")
    FUNCTION = "encode"
    CATEGORY = "language/offline"
    DESCRIPTION = "Translate locally from Polish, then encode immediately with supplied CLIP."

    def encode(self, clip, text_pl):
        if clip is None:
            raise RuntimeError("Podłącz wejście CLIP z Checkpoint Loader / Text Encoder")
        english = translate_prompt(text_pl)
        conditioning = clip.encode_from_tokens_scheduled(clip.tokenize(english))
        return (conditioning, english)


NODE_CLASS_MAPPINGS = {
    "PLToENOffline": PLToENOffline,
    "PLToENClipOffline": PLToENClipOffline,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PLToENOffline": "PL → en-US | Offline Translator",
    "PLToENClipOffline": "PL → en-US → CLIP | Offline",
}
WEB_DIRECTORY = "./web"


@PromptServer.instance.routes.post("/pl_en_clip_offline/translate")
async def pl_en_clip_offline_translate(request):
    try:
        payload = await request.json()
        text = payload.get("text") if isinstance(payload, dict) else None
        if not isinstance(text, str):
            return web.json_response({"error": "Wymagany parametr text"}, status=400)
        translated = await asyncio.to_thread(translate_prompt, text)
        return web.json_response({"text": translated})
    except (RuntimeError, ValueError, OSError, zipfile.BadZipFile) as exc:
        return web.json_response({"error": str(exc)}, status=400)
