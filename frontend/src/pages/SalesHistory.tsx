import { useQuery } from "@tanstack/react-query";
import { getOrders } from "../api";

export default function SalesHistory() {
  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: getOrders,
  });

  const tcgOrders = orders.filter((o) => o.platform === "tcgplayer");
  const ebayOrders = orders.filter((o) => o.platform === "ebay");
  const totalRevenue = orders.reduce((s, o) => s + parseFloat(o.sale_price ?? "0"), 0);

  if (isLoading) return <p className="text-gray-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Sales History</h1>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Sales", value: orders.length, color: "indigo" },
          { label: "TCGPlayer", value: tcgOrders.length, color: "blue" },
          { label: "eBay", value: ebayOrders.length, color: "yellow" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
            <p className={`text-3xl font-bold mt-1 text-${color}-400`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <p className="text-sm text-gray-400 mb-3">
          Total Revenue:{" "}
          <span className="text-green-400 font-semibold">${totalRevenue.toFixed(2)}</span>
        </p>

        {orders.length === 0 ? (
          <p className="text-gray-500 text-sm">No sales yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-800">
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
                <tr key={o.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
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
                  <td className="py-2 text-gray-400 font-mono text-xs">{o.external_order_id}</td>
                  <td className="py-2">{o.quantity_sold}</td>
                  <td className="py-2 text-green-400">${o.sale_price ?? "—"}</td>
                  <td className="py-2 text-gray-500 text-xs">
                    {o.sold_at ? new Date(o.sold_at).toLocaleString() : "—"}
                  </td>
                  <td className="py-2 text-gray-600 text-xs">
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
