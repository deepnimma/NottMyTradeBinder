import { useQuery } from "@tanstack/react-query";
import { getInventory, getOrders, syncTCGPlayerOrders, syncEbayOrders } from "../api";

export default function Dashboard() {
  const inv = useQuery({ queryKey: ["inventory"], queryFn: getInventory });
  const orders = useQuery({ queryKey: ["orders"], queryFn: getOrders });

  const totalCards = inv.data?.reduce((s, i) => s + i.quantity, 0) ?? 0;
  const totalItems = inv.data?.length ?? 0;
  const listedTCG = inv.data?.filter((i) => i.listed_on_tcgplayer).length ?? 0;
  const listedEbay = inv.data?.filter((i) => i.listed_on_ebay).length ?? 0;

  const recentSales = orders.data?.slice(0, 10) ?? [];

  const handleSync = async (platform: "tcgplayer" | "ebay") => {
    try {
      const fn = platform === "tcgplayer" ? syncTCGPlayerOrders : syncEbayOrders;
      const result = await fn();
      alert(`Synced ${result.processed} new orders from ${platform}`);
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
            onClick={() => handleSync("tcgplayer")}
            className="px-3 py-1.5 text-sm bg-blue-700 hover:bg-blue-600 rounded"
          >
            Sync TCGPlayer
          </button>
          <button
            onClick={() => handleSync("ebay")}
            className="px-3 py-1.5 text-sm bg-yellow-700 hover:bg-yellow-600 rounded"
          >
            Sync eBay
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Cards", value: totalCards, color: "indigo" },
          { label: "Unique Listings", value: totalItems, color: "purple" },
          { label: "Listed on TCGPlayer", value: listedTCG, color: "blue" },
          { label: "Listed on eBay", value: listedEbay, color: "yellow" },
        ].map(({ label, value, color }) => (
          <div key={label} className={`bg-gray-900 border border-gray-800 rounded-xl p-4`}>
            <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
            <p className={`text-3xl font-bold mt-1 text-${color}-400`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Recent sales */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <h2 className="text-lg font-semibold mb-3">Recent Sales</h2>
        {recentSales.length === 0 ? (
          <p className="text-gray-500 text-sm">No sales recorded yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-800">
                <th className="pb-2">Platform</th>
                <th className="pb-2">Order ID</th>
                <th className="pb-2">Qty</th>
                <th className="pb-2">Price</th>
                <th className="pb-2">Date</th>
              </tr>
            </thead>
            <tbody>
              {recentSales.map((o) => (
                <tr key={o.id} className="border-b border-gray-800/50">
                  <td className="py-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        o.platform === "tcgplayer"
                          ? "bg-blue-900 text-blue-300"
                          : "bg-yellow-900 text-yellow-300"
                      }`}
                    >
                      {o.platform}
                    </span>
                  </td>
                  <td className="py-2 text-gray-400">{o.external_order_id}</td>
                  <td className="py-2">{o.quantity_sold}</td>
                  <td className="py-2">${o.sale_price ?? "—"}</td>
                  <td className="py-2 text-gray-500">
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
