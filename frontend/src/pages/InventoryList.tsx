import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getInventory,
  deleteInventoryItem,
  listOnTCGPlayer,
  delistFromTCGPlayer,
  listOnEbay,
  delistFromEbay,
  updateInventoryItem,
  InventoryItemOut,
} from "../api";
import SyncStatusBadge from "../components/SyncStatusBadge";

export default function InventoryList() {
  const qc = useQueryClient();
  const { data: items = [], isLoading } = useQuery({
    queryKey: ["inventory"],
    queryFn: getInventory,
  });

  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<number | null>(null);
  const [editValues, setEditValues] = useState<Partial<InventoryItemOut>>({});
  const [busyId, setBusyId] = useState<string | null>(null); // "<itemId>-<action>"

  const filtered = items.filter(
    (i) =>
      i.card.name.toLowerCase().includes(search.toLowerCase()) ||
      i.card.set_name.toLowerCase().includes(search.toLowerCase())
  );

  const act = async (itemId: number, action: string, fn: () => Promise<unknown>) => {
    setBusyId(`${itemId}-${action}`);
    try {
      await fn();
      qc.invalidateQueries({ queryKey: ["inventory"] });
    } catch (e: unknown) {
      alert(`Error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusyId(null);
    }
  };

  const saveEdit = async (item: InventoryItemOut) => {
    await act(item.id, "save", () => updateInventoryItem(item.id, editValues));
    setEditing(null);
  };

  if (isLoading) return <p className="text-gray-500">Loading inventory…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Inventory ({items.length})</h1>
        <input
          type="search"
          placeholder="Search cards…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm w-64 focus:outline-none focus:border-indigo-500"
        />
      </div>

      {filtered.length === 0 && (
        <p className="text-gray-500 text-sm">No cards found. Add some via "Add Cards".</p>
      )}

      <div className="space-y-2">
        {filtered.map((item) => (
          <div
            key={item.id}
            className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-start gap-4"
          >
            {/* Card image */}
            {item.card.image_url && (
              <img
                src={item.card.image_url}
                alt={item.card.name}
                className="h-14 w-10 object-contain rounded flex-shrink-0"
              />
            )}

            {/* Card info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium truncate">{item.card.name}</p>
                  <p className="text-sm text-gray-400">{item.card.set_name}</p>
                </div>
                <SyncStatusBadge
                  listedOnTCG={item.listed_on_tcgplayer}
                  listedOnEbay={item.listed_on_ebay}
                />
              </div>

              {editing === item.id ? (
                /* Edit row */
                <div className="mt-2 flex flex-wrap gap-2 items-center">
                  <label className="text-xs text-gray-500">Qty:</label>
                  <input
                    type="number"
                    min={0}
                    defaultValue={item.quantity}
                    onChange={(e) => setEditValues((v) => ({ ...v, quantity: Number(e.target.value) }))}
                    className="w-16 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs"
                  />
                  <label className="text-xs text-gray-500">TCG $:</label>
                  <input
                    type="number"
                    step="0.01"
                    defaultValue={item.tcgplayer_price ?? ""}
                    onChange={(e) => setEditValues((v) => ({ ...v, tcgplayer_price: e.target.value }))}
                    className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs"
                  />
                  <label className="text-xs text-gray-500">eBay $:</label>
                  <input
                    type="number"
                    step="0.01"
                    defaultValue={item.ebay_price ?? ""}
                    onChange={(e) => setEditValues((v) => ({ ...v, ebay_price: e.target.value }))}
                    className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs"
                  />
                  <button
                    onClick={() => saveEdit(item)}
                    disabled={busyId === `${item.id}-save`}
                    className="px-2 py-1 text-xs bg-green-700 hover:bg-green-600 rounded"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditing(null)}
                    className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                /* Display row */
                <div className="mt-1 flex flex-wrap items-center gap-3 text-sm">
                  <span className="text-gray-400">Qty: <strong className="text-white">{item.quantity}</strong></span>
                  {item.tcgplayer_price && <span className="text-blue-400">TCG: ${item.tcgplayer_price}</span>}
                  {item.ebay_price && <span className="text-yellow-400">eBay: ${item.ebay_price}</span>}
                  {item.notes && <span className="text-gray-500 italic text-xs">{item.notes}</span>}
                </div>
              )}
            </div>

            {/* Actions */}
            {editing !== item.id && (
              <div className="flex flex-col gap-1 flex-shrink-0">
                <button
                  onClick={() => { setEditing(item.id); setEditValues({}); }}
                  className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded"
                >
                  Edit
                </button>
                {item.listed_on_tcgplayer ? (
                  <button
                    onClick={() => act(item.id, "detcg", () => delistFromTCGPlayer(item.id))}
                    disabled={busyId === `${item.id}-detcg`}
                    className="px-2 py-1 text-xs bg-red-900 hover:bg-red-800 rounded text-red-300"
                  >
                    De-TCG
                  </button>
                ) : (
                  <button
                    onClick={() => act(item.id, "tcg", () => listOnTCGPlayer(item.id))}
                    disabled={busyId === `${item.id}-tcg`}
                    className="px-2 py-1 text-xs bg-blue-800 hover:bg-blue-700 rounded"
                  >
                    → TCG
                  </button>
                )}
                {item.listed_on_ebay ? (
                  <button
                    onClick={() => act(item.id, "deebay", () => delistFromEbay(item.id))}
                    disabled={busyId === `${item.id}-deebay`}
                    className="px-2 py-1 text-xs bg-red-900 hover:bg-red-800 rounded text-red-300"
                  >
                    De-eBay
                  </button>
                ) : (
                  <button
                    onClick={() => act(item.id, "ebay", () => listOnEbay(item.id))}
                    disabled={busyId === `${item.id}-ebay`}
                    className="px-2 py-1 text-xs bg-yellow-800 hover:bg-yellow-700 rounded"
                  >
                    → eBay
                  </button>
                )}
                <button
                  onClick={() => {
                    if (confirm(`Delete ${item.card.name}?`)) {
                      act(item.id, "del", () => deleteInventoryItem(item.id));
                    }
                  }}
                  className="px-2 py-1 text-xs bg-gray-800 hover:bg-red-900 rounded text-gray-500 hover:text-red-300"
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
