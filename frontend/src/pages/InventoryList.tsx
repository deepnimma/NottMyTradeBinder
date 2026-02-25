import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getInventory,
  deleteInventoryItem,
  importTCGPlayerCSV,
  exportTCGPlayerCSV,
  listOnEbay,
  delistFromEbay,
  listSetOnEbay,
  delistSetFromEbay,
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
  const [busyId, setBusyId] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImportCSV = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const result = await importTCGPlayerCSV(file);
      alert(
        `Import complete: ${result.created} created, ${result.updated} updated, ${result.skipped} skipped, ${result.ebay_updated} eBay updated.`
      );
      qc.invalidateQueries({ queryKey: ["inventory"] });
    } catch (err: unknown) {
      alert(`Import failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const filtered = items.filter(
    (i) =>
      i.card.name.toLowerCase().includes(search.toLowerCase()) ||
      i.card.set_name.toLowerCase().includes(search.toLowerCase())
  );

  const act = async (key: string, fn: () => Promise<unknown>) => {
    setBusyId(key);
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
    await act(`${item.id}-save`, () => updateInventoryItem(item.id, editValues));
    setEditing(null);
  };

  // Group filtered items by set
  const setGroups = filtered.reduce<Record<string, { game: string; set_id: string; set_name: string; items: InventoryItemOut[] }>>(
    (acc, item) => {
      const key = `${item.card.game}::${item.card.set_id}`;
      if (!acc[key]) {
        acc[key] = { game: item.card.game, set_id: item.card.set_id, set_name: item.card.set_name, items: [] };
      }
      acc[key].items.push(item);
      return acc;
    },
    {}
  );

  if (isLoading) return <p className="text-gray-500">Loading inventory…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Inventory ({items.length})</h1>
        <div className="flex items-center gap-2">
          <input
            type="search"
            placeholder="Search cards…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm w-64 focus:outline-none focus:border-indigo-500"
          />
          <input ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={handleImportCSV} />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="px-3 py-1.5 text-sm bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 rounded whitespace-nowrap"
          >
            {importing ? "Importing…" : "Import TCG CSV"}
          </button>
          <button
            onClick={() => exportTCGPlayerCSV()}
            className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded whitespace-nowrap"
          >
            Export TCG CSV
          </button>
        </div>
      </div>

      {filtered.length === 0 && (
        <p className="text-gray-500 text-sm">No cards found. Add some via "Add Cards".</p>
      )}

      {Object.entries(setGroups).map(([groupKey, group]) => {
        const groupBusyKey = `set-${groupKey}`;
        // Check if any item in this set is listed as a group
        const groupListedItem = group.items.find((i) => !!i.ebay_group_key);
        const allGroupListed = group.items.length > 0 && group.items.every((i) => !!i.ebay_group_key);

        return (
          <div key={groupKey} className="space-y-2">
            {/* Set header */}
            <div className="flex items-center justify-between px-1">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
                {group.set_name}
                <span className="ml-2 text-gray-600 font-normal normal-case">({group.items.length} cards)</span>
              </h2>
              {allGroupListed ? (
                <button
                  onClick={() => act(groupBusyKey, () => delistSetFromEbay(group.game, group.set_id))}
                  disabled={busyId === groupBusyKey}
                  className="px-2 py-1 text-xs bg-red-900 hover:bg-red-800 rounded text-red-300"
                >
                  {busyId === groupBusyKey ? "Delisting…" : "Delist Set from eBay"}
                </button>
              ) : (
                <button
                  onClick={() => act(groupBusyKey, () => listSetOnEbay(group.game, group.set_id))}
                  disabled={busyId === groupBusyKey}
                  title="List all cards in this set as one eBay multi-variation listing"
                  className="px-2 py-1 text-xs bg-yellow-800 hover:bg-yellow-700 rounded"
                >
                  {busyId === groupBusyKey ? "Listing…" : "List Set on eBay"}
                </button>
              )}
            </div>

            {/* Cards in this set */}
            {group.items.map((item) => (
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
                      <div className="flex items-center gap-2">
                        <p className="font-medium truncate">{item.card.name}</p>
                        {item.card.card_number && !item.card.card_number.startsWith("tcg-") && (
                          <span className="text-xs text-gray-500">#{item.card.card_number}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs bg-gray-800 text-gray-300 rounded px-1.5 py-0.5">
                          {item.condition}
                        </span>
                        {item.variant && item.variant !== "Normal" && (
                          <span className="text-xs bg-indigo-900/60 text-indigo-300 rounded px-1.5 py-0.5">
                            {item.variant}
                          </span>
                        )}
                        {item.ebay_group_key && (
                          <span className="text-xs bg-yellow-900/40 text-yellow-400 rounded px-1.5 py-0.5">
                            Set listing
                          </span>
                        )}
                      </div>
                    </div>
                    <SyncStatusBadge listedOnEbay={item.listed_on_ebay} />
                  </div>

                  {editing === item.id ? (
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
                    <div className="mt-1 flex flex-wrap items-center gap-3 text-sm">
                      <span className="text-gray-400">Qty: <strong className="text-white">{item.quantity}</strong></span>
                      {item.tcgplayer_price && <span className="text-blue-400">TCG: ${item.tcgplayer_price}</span>}
                      {item.ebay_price && <span className="text-yellow-400">eBay: ${item.ebay_price}</span>}
                      {item.notes && <span className="text-gray-500 italic text-xs">{item.notes}</span>}
                    </div>
                  )}
                </div>

                {/* Per-card actions */}
                {editing !== item.id && (
                  <div className="flex flex-col gap-1 flex-shrink-0">
                    <button
                      onClick={() => { setEditing(item.id); setEditValues({}); }}
                      className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded"
                    >
                      Edit
                    </button>
                    {/* Only show individual eBay buttons if not part of a group listing */}
                    {!item.ebay_group_key && (
                      item.listed_on_ebay ? (
                        <button
                          onClick={() => act(`${item.id}-deebay`, () => delistFromEbay(item.id))}
                          disabled={busyId === `${item.id}-deebay`}
                          className="px-2 py-1 text-xs bg-red-900 hover:bg-red-800 rounded text-red-300"
                        >
                          De-eBay
                        </button>
                      ) : (
                        <button
                          onClick={() => act(`${item.id}-ebay`, () => listOnEbay(item.id))}
                          disabled={busyId === `${item.id}-ebay`}
                          className="px-2 py-1 text-xs bg-yellow-800 hover:bg-yellow-700 rounded"
                        >
                          → eBay
                        </button>
                      )
                    )}
                    <button
                      onClick={() => {
                        if (confirm(`Delete ${item.card.name}?`)) {
                          act(`${item.id}-del`, () => deleteInventoryItem(item.id));
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
        );
      })}
    </div>
  );
}
