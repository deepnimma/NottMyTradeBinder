import { useQuery } from "@tanstack/react-query";
import { getInventory, getOrders, syncEbayOrders } from "../api";

export default function Dashboard() {
  const inv = useQuery({ queryKey: ["inventory"], queryFn: getInventory });
  const orders = useQuery({ queryKey: ["orders"], queryFn: getOrders });

  const totalCards = inv.data?.reduce((s, i) => s + i.quantity, 0) ?? 0;
  const totalItems = inv.data?.length ?? 0;
  const listedEbay = inv.data?.filter((i) => i.listed_on_ebay).length ?? 0;

  const recentSales = orders.data?.slice(0, 10) ?? [];

  const handleSync = async () => {
    try {
      const result = await syncEbayOrders();
      alert(`Synced ${result.processed} new orders from eBay`);
      orders.refetch();
      inv.refetch();
    } catch (e: unknown) {
      alert(`Sync failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex gap-2">
          <button
            onClick={handleSync}
            className="px-3 py-1.5 text-sm bg-red-700 hover:bg-red-600 rounded transition-colors"
          >
            Sync eBay
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-4">
          <p className="text-xs text-neutral-500 uppercase tracking-wide">Total Cards</p>
          <p className="text-3xl font-bold mt-1 text-red-400">{totalCards}</p>
        </div>
        <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-4">
          <p className="text-xs text-neutral-500 uppercase tracking-wide">Unique Listings</p>
          <p className="text-3xl font-bold mt-1 text-red-400">{totalItems}</p>
        </div>
        <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-4">
          <p className="text-xs text-neutral-500 uppercase tracking-wide">Listed on eBay</p>
          <p className="text-3xl font-bold mt-1 text-yellow-400">{listedEbay}</p>
        </div>
      </div>

      {/* Recent sales */}
      <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-4">
        <h2 className="text-lg font-semibold mb-3">Recent Sales</h2>
        {recentSales.length === 0 ? (
          <p className="text-neutral-500 text-sm">No sales recorded yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-neutral-500 border-b border-[#2a2a2a]">
                <th className="pb-2">Platform</th>
                <th className="pb-2">Order ID</th>
                <th className="pb-2">Qty</th>
                <th className="pb-2">Price</th>
                <th className="pb-2">Date</th>
              </tr>
            </thead>
            <tbody>
              {recentSales.map((o) => (
                <tr key={o.id} className="border-b border-[#2a2a2a]/50">
                  <td className="py-2">
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-yellow-900/60 text-yellow-300">
                      {o.platform}
                    </span>
                  </td>
                  <td className="py-2 text-neutral-400">{o.external_order_id}</td>
                  <td className="py-2">{o.quantity_sold}</td>
                  <td className="py-2">${o.sale_price ?? "—"}</td>
                  <td className="py-2 text-neutral-500">
                    {o.sold_at ? new Date(o.sold_at).toLocaleDateString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
