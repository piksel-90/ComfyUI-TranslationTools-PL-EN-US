# ComfyUI TranslationTools PL → EN-US (offline)

Lokalne tłumaczenie polskich promptów do języka angielskiego dla ComfyUI i CLIP Text Encode.

## Funkcje

- Przycisk tłumaczenia bezpośrednio w standardowym `CLIP Text Encode`.
- Osobny node `PL → en-US | Offline Translator` (`STRING`).
- Node `PL → en-US → CLIP | Offline` (`CONDITIONING` i `STRING`).
- Bez wywołań zewnętrznych API i bez pobierania modeli podczas tłumaczenia.

## Instalacja

Zainstaluj zależności z `requirements.txt` w środowisku ComfyUI i umieść pobrany wcześniej pakiet Argos Translate PL→EN (`translate-pl_en-*.argosmodel`) w folderze `models/`. Szczegóły po polsku: [README_PL.md](README_PL.md).

**Status:** wstępna implementacja do przetestowania w rzeczywistym ComfyUI. Model językowy oraz pakiety Python nie są dołączone; przygotuj je wcześniej dla komputera offline. Tłumaczenie jest z ogólnego angielskiego (`en`) z częściową normalizacją amerykańskiej pisowni (`en-US`).
