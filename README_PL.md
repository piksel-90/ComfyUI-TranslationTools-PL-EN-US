# ComfyUI PL → en-US → CLIP (offline)

Dodatek tłumaczy prompty z polskiego na angielski do ComfyUI. Całe tłumaczenie wykonuje lokalnie na CPU, bez zewnętrznego API.

## Trzy tryby

1. **Przycisk w natywnym CLIP Text Encode:** wpisz polski prompt w polu `text`, kliknij `Przetłumacz PL → en-US`. Wynik zastąpi tekst w tym samym polu, nadal będzie edytowalny i zapisze się w workflow.
2. **PL → en-US | Offline Translator:** node z wejściem `text_pl` i wyjściem `text_en_us` typu `STRING`. Połącz z wejściem `text` standardowego CLIP Text Encode (zamień widget na wejście).
3. **PL → en-US → CLIP | Offline:** wejścia `clip`, `text_pl`; wyjścia `conditioning` i `text_en_us`. Użyj dla automatycznego tłumaczenia przy kolejce generacji.

## Instalacja bez internetu na komputerze docelowym

1. Umieść folder projektu w `ComfyUI/custom_nodes/ComfyUI-TranslationTools-PL-EN-US/`.
2. Pobierz na innym komputerze model Argos PL → EN w formacie `translate-pl_en-*.argosmodel`. Indeks pakietów: https://github.com/argosopentech/argospm-index/blob/main/index.json . Upewnij się, że pakiet ma `from_code: pl` i `to_code: en`. Skopiuj `.argosmodel` do lokalnego katalogu `models/`. Model nie jest częścią repozytorium.
3. Na komputerze przygotowawczym o kompatybilnym systemie, architekturze i wersji Pythona pobierz zależności:

   ```bash
   python -m pip download --only-binary=:all: -d wheelhouse -r requirements.txt
   ```

4. Przenieś folder `wheelhouse/` na komputer docelowy i zainstaluj w **tym samym środowisku Python, z którego korzysta ComfyUI**:

   ```bash
   python -m pip install --no-index --find-links=wheelhouse -r requirements.txt
   ```

   W wersji Windows Portable użyj `python_embeded\python.exe` i odpowiednich ścieżek. Brak wymaganej paczki wheel dla platformy oznacza konieczność przygotowania jej na komputerze z dostępem do sieci.

5. Zrestartuj ComfyUI i odśwież przeglądarkę (`Ctrl+F5`).

Przy pierwszym tłumaczeniu plik `.argosmodel` zostanie lokalnie rozpakowany do `models/pl_en/`. Nie jest uruchamiane automatyczne pobieranie modelu ani sieciowy sentence splitter. Przycisk w przeglądarce wysyła żądanie tylko do lokalnego serwera ComfyUI.

## Przykładowe workflow

**Ręcznie w CLIP:** `CheckpointLoader.CLIP → CLIPTextEncode.clip`. Wpisz polski tekst w standardowym polu i kliknij przycisk tłumaczenia.

**Zintegrowany node:** `CheckpointLoader.CLIP → PL → en-US → CLIP | Offline.clip`, następnie `conditioning → KSampler.positive`. Podobnie dla promptu negatywnego.

**Przez STRING:** `PL → en-US | Offline Translator.text_en_us → CLIPTextEncode.text` po zmianie widgetu na input.

## Zachowanie składni i ograniczenia

- Zachowywane są typowe elementy składni promptów, m.in. nawiasy, przecinki, wagi w stylu `(tekst:1.2)`, `<lora:...>`, `embedding:...` oraz wildcardy `__nazwa__`. Niestandardowe rozszerzenia mogą wymagać ręcznej kontroli.
- Pakiet Argos tłumaczy na ogólny angielski `en`, po czym kod częściowo normalizuje pisownię do `en-US` (`colour → color`, `centre → center`). Nie jest to pełny model dialektu en-US.
- Silnik pracuje na CPU i nie zużywa VRAM. Limitem wejścia jest 20 000 znaków.
- Nie wkładaj w `models/` plików z nieznanych źródeł. Rozpakowywanie i ładowanie nieznanych modeli jest potencjalnie niebezpieczne.
- Zanim użyjesz produkcyjnie, sprawdź zgodność z własną wersją ComfyUI oraz modelem Argos. Testy bez zależności: `python -m unittest discover -s tests`.

## Diagnostyka

- Brak modelu: skopiuj plik `translate-pl_en-*.argosmodel` do `models/`.
- Błąd bibliotek: instaluj zależności w Pythonie uruchamiającym ComfyUI.
- Brak przycisku: upewnij się, że `web/js/clip_translate.js` jest w folderze dodatku i zrestartuj interfejs.
- Gdy do pola `text` jest podłączony przewód, przycisk nie nadpisze wejścia. Odłącz przewód przed tłumaczeniem w tym samym polu.

## Status

To wstępna implementacja, a nie wydanie przetestowane end-to-end z ComfyUI i rzeczywistym modelem tłumaczenia.
