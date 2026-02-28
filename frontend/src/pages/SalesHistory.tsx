import { useQuery } from "@tanstack/react-query";
import { getOrders } from "../api";

export default function SalesHistory() {
  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: getOrders,
  });

  const ebayOrders = orders.filter((o) => o.platform === "ebay");
  const totalRevenue = orders.reduce((s, o) => s + parseFloat(o.sale_price ?? "0"), 0);

  if (isLoading) return <p className="text-neutral-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Sales History</h1>

      {/* Summary */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-4">
          <p className="text-xs text-neutral-500 uppercase tracking-wide">Total Sales</p>
          <p className="text-3xl font-bold mt-1 text-red-400">{orders.length}</p>
        </div>
        <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-4">
          <p className="text-xs text-neutral-500 uppercase tracking-wide">eBay</p>
          <p className="text-3xl font-bold mt-1 text-yellow-400">{ebayOrders.length}</p>
        </div>
      </div>

      <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-4">
        <p className="text-sm text-neutral-400 mb-3">
          Total Revenue:{" "}
          <span className="text-green-400 font-semibold">${totalRevenue.toFixed(2)}</span>
        </p>

        {orders.length === 0 ? (
          <p className="text-neutral-500 text-sm">No sales yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-neutral-500 border-b border-[#2a2a2a]">
                <th className="pb-2">Platform</th>
                <th className="pb-2">Order ID</th>
                <th className="pb-2">Qty</th>
                <th className="pb-2">Price</th>
                <th className="pb-2">Sold At</th>
                <th className="pb-2">Synced At</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id} className="border-b border-[#2a2a2a]/50 hover:bg-white/[0.02]">
                  <td className="py-2">
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-yellow-900/60 text-yellow-300">
                      {o.platform}
                    </span>
                  </td>
                  <td className="py-2 text-neutral-400 font-mono text-xs">{o.external_order_id}</td>
                  <td className="py-2">{o.quantity_sold}</td>
                  <td className="py-2 text-green-400">${o.sale_price ?? "—"}</td>
                  <td className="py-2 text-neutral-500 text-xs">
                    {o.sold_at ? new Date(o.sold_at).toLocaleString() : "—"}
                  </td>
                  <td className="py-2 text-neutral-600 text-xs">
                    {new Date(o.synced_at).toLocaleString()}
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
