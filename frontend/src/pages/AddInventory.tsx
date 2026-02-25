import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getSets, getCardsBySet, bulkCreateInventoryItems, SetOut, CardOut } from "../api";

const CONDITIONS = ["NM", "LP", "MP", "HP", "D"];
const VARIANTS = ["Normal", "Reverse Holo", "Holo", "First Edition", "Promo"];

interface CardRow {
  card: CardOut;
  selected: boolean;
  variant: string;
  condition: string;
  quantity: number;
  ebayPrice: string;
}

export default function AddInventory() {
  const qc = useQueryClient();
  const [game, setGame] = useState("");
  const [setId, setSetId] = useState("");
  const [rows, setRows] = useState<CardRow[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const setsQuery = useQuery<SetOut[]>({
    queryKey: ["sets", game],
    queryFn: () => getSets(game),
    enabled: !!game,
  });

  const cardsQuery = useQuery<CardOut[]>({
    queryKey: ["cards", game, setId],
    queryFn: () => getCardsBySet(game, setId),
    enabled: !!game && !!setId,
  });

  // When cards load, initialize rows
  const cards = cardsQuery.data ?? [];
  if (cardsQuery.isSuccess && rows.length !== cards.length) {
    setRows(
      cards.map((card) => ({
        card,
        selected: false,
        variant: "Normal",
        condition: "NM",
        quantity: 1,
        ebayPrice: "",
      }))
    );
  }

  const updateRow = (idx: number, patch: Partial<CardRow>) => {
    setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  };

  const toggleAll = (checked: boolean) => {
    setRows((prev) => prev.map((r) => ({ ...r, selected: checked })));
  };

  const selectedRows = rows.filter((r) => r.selected);

  const handleSubmit = async () => {
    if (selectedRows.length === 0) return;
    setStatus("loading");
    setMessage("");
    try {
      const payload = selectedRows.map((r) => ({
        card_id: r.card.id,
        condition: r.condition,
        variant: r.variant,
        quantity: r.quantity,
        ebay_price: r.ebayPrice || null,
        notes: null,
      }));
      await bulkCreateInventoryItems(payload);
      qc.invalidateQueries({ queryKey: ["inventory"] });
      setStatus("success");
      setMessage(`Added ${selectedRows.length} card${selectedRows.length > 1 ? "s" : ""} to inventory`);
      // Deselect all after add
      setRows((prev) => prev.map((r) => ({ ...r, selected: false })));
    } catch (e: unknown) {
      setStatus("error");
      setMessage(e instanceof Error ? e.message : "Failed to add cards");
    }
  };

  const sets: SetOut[] = setsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Add Cards to Inventory</h1>

      {/* Game + Set selectors */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-wrap gap-4">
        <div className="min-w-48">
          <label className="block text-sm text-gray-400 mb-1">Game</label>
          <select
            value={game}
            onChange={(e) => {
              setGame(e.target.value);
              setSetId("");
              setRows([]);
            }}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
          >
            <option value="">— Select game —</option>
            <option value="pokemon">Pokémon</option>
            <option value="weiss_schwarz">Weiss Schwarz</option>
          </select>
        </div>

        {game && (
          <div className="min-w-64">
            <label className="block text-sm text-gray-400 mb-1">
              Set {setsQuery.isLoading && <span className="text-gray-600">(loading…)</span>}
            </label>
            <select
              value={setId}
              onChange={(e) => {
                setSetId(e.target.value);
                setRows([]);
                setStatus("idle");
              }}
              disabled={setsQuery.isLoading}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
            >
              <option value="">— Select set —</option>
              {sets.map((s) => (
                <option key={s.set_id} value={s.set_id}>
                  {s.set_name} ({s.card_count} cards)
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Cards grid */}
      {setId && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          {cardsQuery.isLoading ? (
            <p className="p-5 text-gray-500 text-sm">Fetching cards from API…</p>
          ) : rows.length === 0 ? (
            <p className="p-5 text-gray-500 text-sm">No cards found in this set.</p>
          ) : (
            <>
              {/* Table header */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-400 text-left">
                      <th className="px-4 py-3 w-8">
                        <input
                          type="checkbox"
                          onChange={(e) => toggleAll(e.target.checked)}
                          checked={rows.length > 0 && rows.every((r) => r.selected)}
                          className="accent-indigo-500"
                        />
                      </th>
                      <th className="px-2 py-3 w-10">#</th>
                      <th className="px-2 py-3">Card</th>
                      <th className="px-2 py-3 w-36">Variant</th>
                      <th className="px-2 py-3 w-24">Condition</th>
                      <th className="px-2 py-3 w-16">Qty</th>
                      <th className="px-2 py-3 w-24">eBay Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, idx) => (
                      <tr
                        key={row.card.id}
                        className={`border-b border-gray-800 last:border-0 transition-colors ${
                          row.selected ? "bg-indigo-900/20" : "hover:bg-gray-800/40"
                        }`}
                      >
                        {/* Checkbox */}
                        <td className="px-4 py-2">
                          <input
                            type="checkbox"
                            checked={row.selected}
                            onChange={(e) => updateRow(idx, { selected: e.target.checked })}
                            className="accent-indigo-500"
                          />
                        </td>

                        {/* Card number */}
                        <td className="px-2 py-2 text-gray-500 text-xs whitespace-nowrap">
                          {row.card.card_number && !row.card.card_number.startsWith("tcg-")
                            ? `#${row.card.card_number}`
                            : "—"}
                        </td>

                        {/* Card name + image */}
                        <td className="px-2 py-2">
                          <div className="flex items-center gap-2">
                            {row.card.image_url && (
                              <img
                                src={row.card.image_url}
                                alt={row.card.name}
                                className="h-10 rounded shadow"
                              />
                            )}
                            <span className="font-medium text-sm">{row.card.name}</span>
                          </div>
                        </td>

                        {/* Variant */}
                        <td className="px-2 py-2">
                          <select
                            value={row.variant}
                            onChange={(e) => updateRow(idx, { variant: e.target.value })}
                            disabled={!row.selected}
                            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs focus:outline-none focus:border-indigo-500 disabled:opacity-40"
                          >
                            {VARIANTS.map((v) => (
                              <option key={v} value={v}>{v}</option>
                            ))}
                          </select>
                        </td>

                        {/* Condition */}
                        <td className="px-2 py-2">
                          <select
                            value={row.condition}
                            onChange={(e) => updateRow(idx, { condition: e.target.value })}
                            disabled={!row.selected}
                            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs focus:outline-none focus:border-indigo-500 disabled:opacity-40"
                          >
                            {CONDITIONS.map((c) => (
                              <option key={c} value={c}>{c}</option>
                            ))}
                          </select>
                        </td>

                        {/* Qty */}
                        <td className="px-2 py-2">
                          <input
                            type="number"
                            min={1}
                            value={row.quantity}
                            onChange={(e) => updateRow(idx, { quantity: Number(e.target.value) })}
                            disabled={!row.selected}
                            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs focus:outline-none focus:border-indigo-500 disabled:opacity-40"
                          />
                        </td>

                        {/* eBay Price */}
                        <td className="px-2 py-2">
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            placeholder="0.00"
                            value={row.ebayPrice}
                            onChange={(e) => updateRow(idx, { ebayPrice: e.target.value })}
                            disabled={!row.selected}
                            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs focus:outline-none focus:border-indigo-500 disabled:opacity-40"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Footer actions */}
              <div className="px-4 py-3 border-t border-gray-800 flex items-center justify-between gap-4">
                <span className="text-sm text-gray-400">
                  {selectedRows.length} of {rows.length} cards selected
                </span>
                <div className="flex items-center gap-3">
                  {status === "success" && (
                    <span className="text-green-400 text-sm">{message}</span>
                  )}
                  {status === "error" && (
                    <span className="text-red-400 text-sm">{message}</span>
                  )}
                  <button
                    onClick={handleSubmit}
                    disabled={selectedRows.length === 0 || status === "loading"}
                    className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 rounded px-4 py-2 text-sm font-medium transition-colors"
                  >
                    {status === "loading"
                      ? "Adding…"
                      : `Add ${selectedRows.length > 0 ? selectedRows.length : ""} Selected Card${selectedRows.length !== 1 ? "s" : ""}`}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
