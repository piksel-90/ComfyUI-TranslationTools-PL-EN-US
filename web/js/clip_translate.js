import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

app.registerExtension({
  name: "comfy.pl_en_clip_offline",
  nodeCreated(node) {
    // Adds a button to the native CLIP Text Encode node, not a replacement.
    if (node.comfyClass !== "CLIPTextEncode" && node.type !== "CLIPTextEncode") return;
    if (node.widgets?.some((w) => w.name === "pl_en_offline_button")) return;

    let busy = false;
    node.addWidget("button", "pl_en_offline_button", "Przetłumacz PL → en-US", async () => {
      if (busy) return;
      const textWidget = node.widgets?.find((w) => w.name === "text");
      if (!textWidget) {
        alert("Nie znaleziono pola text w tym CLIP. Przycisk działa w standardowym CLIP Text Encode.");
        return;
      }
      // Never silently replace connected inputs. Here the text box must be editable.
      const input = node.inputs?.find((i) => i.name === "text");
      if (input?.link != null) {
        alert("Pole text ma podłączony przewód. Odłącz go, aby tłumaczyć tekst bezpośrednio w oknie CLIP.");
        return;
      }
      const original = String(textWidget.value ?? "");
      if (!original.trim()) return;
      busy = true;
      try {
        const response = await api.fetchApi("/pl_en_clip_offline/translate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: original }),
        });
        const data = await response.json();
        if (!response.ok || typeof data.text !== "string") {
          throw new Error(data.error || `Błąd HTTP ${response.status}`);
        }
        // Avoid overwriting anything typed while the translation was running.
        if (textWidget.value !== original) {
          alert("Prompt został zmieniony w trakcie tłumaczenia. Wynik odrzucono, aby nie nadpisać zmian.");
          return;
        }
        textWidget.value = data.text;
        textWidget.callback?.(data.text);
        app.graph?.setDirtyCanvas(true, true);
      } catch (error) {
        console.error("[PL-EN Offline]", error);
        alert(`Nie udało się przetłumaczyć offline: ${error.message}`);
      } finally {
        busy = false;
      }
    }, { serialize: false });
    const size = node.computeSize?.();
    if (size && node.size) node.setSize?.([Math.max(node.size[0], size[0]), Math.max(node.size[1], size[1])]);
  },
});
