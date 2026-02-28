import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import {
  getInventory,
  deleteInventoryItem,
  deleteSet,
  importTCGPlayerCSV,
  exportTCGPlayerCSV,
  listOnEbay,
  delistFromEbay,
  listSetOnEbay,
  delistSetFromEbay,
  publishSetToEbay,
  updateInventoryItem,
  bulkPriceUpdate,
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

  // Collapse state
  const [collapsedSets, setCollapsedSets] = useState<Set<string>>(new Set());
  const toggleCollapse = (key: string) =>
    setCollapsedSets((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  // Bulk price state: which set is open, mode, and value
  const [bulkPriceSet, setBulkPriceSet] = useState<string | null>(null);
  const [bulkMode, setBulkMode] = useState<"multiply" | "flat">("multiply");
  const [bulkValue, setBulkValue] = useState("1.3");

  const handleImportCSV = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const result = await importTCGPlayerCSV(file);
      alert(
        `Import complete: ${result.created} created, ${result.updated} updated, ${result.skipped} skipped.\n${result.staged} item(s) staged — use "Publish to eBay" per set to push changes.`
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
      let msg = e instanceof Error ? e.message : String(e);
      if (axios.isAxiosError(e) && e.response?.data?.detail) {
        msg = String(e.response.data.detail);
      }
      alert(`Error: ${msg}`);
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

  if (isLoading) return <p className="text-neutral-500">Loading inventory…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">Inventory ({items.length})</h1>
          <button
            onClick={() => setCollapsedSets(new Set(Object.keys(setGroups)))}
            className="px-2 py-1 text-xs bg-[#222] hover:bg-[#2a2a2a] rounded text-neutral-400"
          >
            Collapse All
          </button>
          <button
            onClick={() => setCollapsedSets(new Set())}
            className="px-2 py-1 text-xs bg-[#222] hover:bg-[#2a2a2a] rounded text-neutral-400"
          >
            Expand All
          </button>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="search"
            placeholder="Search cards…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-[#1a1a1a] border border-[#333] rounded px-3 py-1.5 text-sm w-64 focus:outline-none focus:border-red-600"
          />
          <input ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={handleImportCSV} />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="px-3 py-1.5 text-sm bg-red-700 hover:bg-red-600 disabled:opacity-50 rounded whitespace-nowrap"
          >
            {importing ? "Importing…" : "Import TCG CSV"}
          </button>
          <button
            onClick={() => exportTCGPlayerCSV()}
            className="px-3 py-1.5 text-sm bg-[#222] hover:bg-[#2a2a2a] rounded whitespace-nowrap"
          >
            Export TCG CSV
          </button>
        </div>
      </div>

      {filtered.length === 0 && (
        <p className="text-neutral-500 text-sm">No cards found. Add some via "Add Cards".</p>
      )}

      {Object.entries(setGroups).map(([groupKey, group]) => {
        const groupBusyKey = `set-${groupKey}`;
        const allGroupListed = group.items.length > 0 && group.items.every((i) => !!i.ebay_group_key);
        const stagedCount = group.items.filter((i) => i.staged).length;
        const isBulkOpen = bulkPriceSet === groupKey;
        const isCollapsed = collapsedSets.has(groupKey);

        const applyBulkPrice = async () => {
          const val = parseFloat(bulkValue);
          if (isNaN(val) || val <= 0) return;
          const updates = group.items
            .filter((i) => bulkMode === "flat" || (i.tcgplayer_price && parseFloat(i.tcgplayer_price) > 0))
            .map((i) => ({
              id: i.id,
              ebay_price: bulkMode === "flat" ? val : Math.round(parseFloat(i.tcgplayer_price!) * val * 100) / 100,
            }));
          if (updates.length === 0) return;
          await act(`${groupBusyKey}-bulk`, () => bulkPriceUpdate(updates));
          setBulkPriceSet(null);
        };

        return (
          <div key={groupKey} className="space-y-2">
            {/* Set header */}
            <div className="flex items-center justify-between px-1">
              <button
                onClick={() => toggleCollapse(groupKey)}
                className="flex items-center gap-2 text-left hover:text-white transition-colors"
              >
                <span className="text-neutral-600 text-xs">{isCollapsed ? "▶" : "▼"}</span>
                <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide">
                  {group.set_name}
                  <span className="ml-2 text-neutral-600 font-normal normal-case">({group.items.length} cards)</span>
                  {stagedCount > 0 && (
                    <span className="ml-2 text-xs bg-orange-900/60 text-orange-300 rounded px-1.5 py-0.5 normal-case font-normal">
                      {stagedCount} staged
                    </span>
                  )}
                </h2>
              </button>
              <div className="flex items-center gap-1.5">
                {/* Bulk price button */}
                <button
                  onClick={() => { setBulkPriceSet(isBulkOpen ? null : groupKey); setBulkValue("1.3"); setBulkMode("multiply"); }}
                  className={`px-2 py-1 text-xs rounded ${isBulkOpen ? "bg-red-900/60 text-red-300" : "bg-[#222] hover:bg-[#2a2a2a] text-neutral-400"}`}
                >
                  {isBulkOpen ? "Cancel" : "Bulk Price"}
                </button>
                {/* Publish button — visible when there are staged items */}
                {stagedCount > 0 && (
                  <button
                    onClick={() => act(`${groupBusyKey}-publish`, () => publishSetToEbay(group.game, group.set_id))}
                    disabled={busyId === `${groupBusyKey}-publish`}
                    title={allGroupListed ? "Push staged changes to existing eBay listing" : "Create new eBay listing with staged items"}
                    className="px-2 py-1 text-xs bg-green-800 hover:bg-green-700 rounded text-green-200"
                  >
                    {busyId === `${groupBusyKey}-publish` ? "Publishing…" : `Publish to eBay (${stagedCount})`}
                  </button>
                )}
                {/* Delete set */}
                <button
                  onClick={() => {
                    if (confirm(`Delete all ${group.items.length} cards in "${group.set_name}"?`)) {
                      act(`${groupBusyKey}-delete`, () => deleteSet(group.game, group.set_id));
                    }
                  }}
                  disabled={busyId === `${groupBusyKey}-delete`}
                  className="px-2 py-1 text-xs bg-[#1a1a1a] hover:bg-red-950 rounded text-neutral-600 hover:text-red-400"
                >
                  {busyId === `${groupBusyKey}-delete` ? "Deleting…" : "Delete Set"}
                </button>
                {/* Delist / List Set button */}
                {allGroupListed ? (
                  <button
                    onClick={() => act(groupBusyKey, () => delistSetFromEbay(group.game, group.set_id))}
                    disabled={busyId === groupBusyKey}
                    className="px-2 py-1 text-xs bg-red-900 hover:bg-red-800 rounded text-red-300"
                  >
                    {busyId === groupBusyKey ? "Delisting…" : "Delist Set"}
                  </button>
                ) : (
                  <button
                    onClick={() => act(groupBusyKey, () => listSetOnEbay(group.game, group.set_id))}
                    disabled={busyId === groupBusyKey}
                    title="List all priced cards in this set as one eBay multi-variation listing"
                    className="px-2 py-1 text-xs bg-yellow-800 hover:bg-yellow-700 rounded"
                  >
                    {busyId === groupBusyKey ? "Listing…" : "List Set on eBay"}
                  </button>
                )}
              </div>
            </div>

            {/* Bulk price panel */}
            {!isCollapsed && isBulkOpen && (
              <div className="bg-[#111111] border border-[#2a2a2a] rounded-lg px-4 py-3 flex flex-wrap items-center gap-3">
                <span className="text-xs text-neutral-400 font-medium">Set eBay prices for {group.set_name}:</span>
                <div className="flex items-center gap-1 bg-[#1a1a1a] rounded p-0.5">
                  <button
                    onClick={() => setBulkMode("multiply")}
                    className={`px-2 py-1 text-xs rounded transition-colors ${bulkMode === "multiply" ? "bg-red-700 text-white" : "text-neutral-400 hover:text-white"}`}
                  >
                    × TCG price
                  </button>
                  <button
                    onClick={() => setBulkMode("flat")}
                    className={`px-2 py-1 text-xs rounded transition-colors ${bulkMode === "flat" ? "bg-red-700 text-white" : "text-neutral-400 hover:text-white"}`}
                  >
                    Flat $
                  </button>
                </div>
                {bulkMode === "multiply" && (
                  <div className="flex items-center gap-1">
                    {["1.0", "1.1", "1.2", "1.3", "1.5", "2.0"].map((p) => (
                      <button
                        key={p}
                        onClick={() => setBulkValue(p)}
                        className={`px-1.5 py-0.5 text-xs rounded ${bulkValue === p ? "bg-red-700 text-white" : "bg-[#1a1a1a] text-neutral-400 hover:text-white"}`}
                      >
                        {p}×
                      </button>
                    ))}
                  </div>
                )}
                <input
                  type="number"
                  step={bulkMode === "multiply" ? "0.05" : "0.01"}
                  min="0"
                  value={bulkValue}
                  onChange={(e) => setBulkValue(e.target.value)}
                  className="w-20 bg-[#1a1a1a] border border-[#333] rounded px-2 py-1 text-xs focus:outline-none focus:border-red-600"
                  placeholder={bulkMode === "multiply" ? "1.3" : "9.99"}
                />
                <span className="text-xs text-neutral-500">
                  {bulkMode === "multiply"
                    ? `→ e.g. TCG $1.00 = eBay $${(parseFloat(bulkValue) || 0).toFixed(2)}`
                    : `→ all items set to $${(parseFloat(bulkValue) || 0).toFixed(2)}`}
                </span>
                <button
                  onClick={applyBulkPrice}
                  disabled={busyId === `${groupBusyKey}-bulk`}
                  className="px-3 py-1 text-xs bg-red-700 hover:bg-red-600 disabled:opacity-50 rounded ml-auto"
                >
                  {busyId === `${groupBusyKey}-bulk` ? "Applying…" : `Apply to ${group.items.length} cards`}
                </button>
              </div>
            )}

            {/* Cards in this set */}
            {!isCollapsed && group.items.map((item) => (
              <div
                key={item.id}
                className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-4 flex items-start gap-4"
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
                          <span className="text-xs text-neutral-500">#{item.card.card_number}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs bg-[#1e1e1e] text-neutral-300 rounded px-1.5 py-0.5">
                          {item.condition}
                        </span>
                        {item.variant && item.variant !== "Normal" && (
                          <span className="text-xs bg-red-900/40 text-red-300 rounded px-1.5 py-0.5">
                            {item.variant}
                          </span>
                        )}
                        {item.ebay_group_key && (
                          <span className="text-xs bg-yellow-900/40 text-yellow-400 rounded px-1.5 py-0.5">
                            Set listing
                          </span>
                        )}
                        {item.staged && (
                          <span className="text-xs bg-orange-900/50 text-orange-300 rounded px-1.5 py-0.5">
                            staged
                          </span>
                        )}
                      </div>
                    </div>
                    <SyncStatusBadge listedOnEbay={item.listed_on_ebay} />
                  </div>

                  {editing === item.id ? (
                    <div className="mt-2 flex flex-wrap gap-2 items-center">
                      <label className="text-xs text-neutral-500">Qty:</label>
                      <input
                        type="number"
                        min={0}
                        defaultValue={item.quantity}
                        onChange={(e) => setEditValues((v) => ({ ...v, quantity: Number(e.target.value) }))}
                        className="w-16 bg-[#1a1a1a] border border-[#333] rounded px-2 py-1 text-xs focus:outline-none focus:border-red-600"
                      />
                      <label className="text-xs text-neutral-500">TCG $:</label>
                      <input
                        type="number"
                        step="0.01"
                        defaultValue={item.tcgplayer_price ?? ""}
                        onChange={(e) => setEditValues((v) => ({ ...v, tcgplayer_price: e.target.value }))}
                        className="w-20 bg-[#1a1a1a] border border-[#333] rounded px-2 py-1 text-xs focus:outline-none focus:border-red-600"
                      />
                      <label className="text-xs text-neutral-500">eBay $:</label>
                      <input
                        type="number"
                        step="0.01"
                        defaultValue={item.ebay_price ?? ""}
                        onChange={(e) => setEditValues((v) => ({ ...v, ebay_price: e.target.value }))}
                        className="w-20 bg-[#1a1a1a] border border-[#333] rounded px-2 py-1 text-xs focus:outline-none focus:border-red-600"
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
                        className="px-2 py-1 text-xs bg-[#222] hover:bg-[#2a2a2a] rounded"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="mt-1 flex flex-wrap items-center gap-3 text-sm">
                      <span className="text-neutral-400">Qty: <strong className="text-white">{item.quantity}</strong></span>
                      {item.tcgplayer_price && <span className="text-blue-400">TCG: ${item.tcgplayer_price}</span>}
                      {item.ebay_price && <span className="text-yellow-400">eBay: ${item.ebay_price}</span>}
                      {item.notes && <span className="text-neutral-500 italic text-xs">{item.notes}</span>}
                    </div>
                  )}
                </div>

                {/* Per-card actions */}
                {editing !== item.id && (
                  <div className="flex flex-col gap-1 flex-shrink-0">
                    <button
                      onClick={() => { setEditing(item.id); setEditValues({}); }}
                      className="px-2 py-1 text-xs bg-[#222] hover:bg-[#2a2a2a] rounded"
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
                      className="px-2 py-1 text-xs bg-[#1a1a1a] hover:bg-red-900 rounded text-neutral-500 hover:text-red-300"
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
