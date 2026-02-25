import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import CardSelector from "../components/CardSelector";
import { CardOut, createInventoryItem } from "../api";

export default function AddInventory() {
  const qc = useQueryClient();
  const [selectedCard, setSelectedCard] = useState<CardOut | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [ebayPrice, setEbayPrice] = useState("");
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCard) return;
    setStatus("loading");
    try {
      await createInventoryItem({
        card_id: selectedCard.id,
        condition: "NM",
        quantity,
        ebay_price: ebayPrice || null,
        notes: notes || null,
      });
      setStatus("success");
      setMessage(`Added ${selectedCard.name} × ${quantity} to inventory`);
      qc.invalidateQueries({ queryKey: ["inventory"] });
      // Reset form
      setSelectedCard(null);
      setQuantity(1);
      setEbayPrice("");
      setNotes("");
    } catch (e: unknown) {
      setStatus("error");
      setMessage(e instanceof Error ? e.message : "Failed to add card");
    }
  };

  return (
    <div className="max-w-xl space-y-6">
      <h1 className="text-2xl font-bold">Add Cards to Inventory</h1>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
        <CardSelector onCardSelect={(card) => { setSelectedCard(card); setStatus("idle"); }} />

        {selectedCard && (
          <>
            {/* Card preview */}
            <div className="flex items-center gap-3 bg-gray-800 rounded-lg p-3">
              {selectedCard.image_url && (
                <img src={selectedCard.image_url} alt={selectedCard.name} className="h-16 rounded" />
              )}
              <div>
                <p className="font-medium">{selectedCard.name}</p>
                <p className="text-sm text-gray-400">{selectedCard.set_name}</p>
                {selectedCard.card_number && !selectedCard.card_number.startsWith("tcg-") && (
                  <p className="text-xs text-gray-500">#{selectedCard.card_number}</p>
                )}
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Quantity</label>
                <input
                  type="number"
                  min={1}
                  value={quantity}
                  onChange={(e) => setQuantity(Number(e.target.value))}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">eBay Price ($)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="e.g. 5.49"
                  value={ebayPrice}
                  onChange={(e) => setEbayPrice(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Notes (optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Holo, reverse holo…"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <button
                type="submit"
                disabled={status === "loading"}
                className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded px-4 py-2 text-sm font-medium transition-colors"
              >
                {status === "loading" ? "Adding…" : "Add to Inventory"}
              </button>

              {status === "success" && (
                <p className="text-green-400 text-sm">{message}</p>
              )}
              {status === "error" && (
                <p className="text-red-400 text-sm">{message}</p>
              )}
            </form>
          </>
        )}
      </div>
    </div>
  );
}
