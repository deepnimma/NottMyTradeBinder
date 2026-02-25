import { useQuery } from "@tanstack/react-query";
import { getSettings, getEbayAuthUrl, getEbayStatus } from "../api";

export default function Settings() {
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: getSettings });
  const { data: ebayStatus } = useQuery({ queryKey: ["ebay-status"], queryFn: getEbayStatus });

  const handleEbayConnect = async () => {
    try {
      const { auth_url } = await getEbayAuthUrl();
      window.location.href = auth_url;
    } catch (e: unknown) {
      alert(`eBay auth error: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  return (
    <div className="max-w-xl space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* TCGPlayer */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
        <h2 className="text-lg font-semibold text-blue-400">TCGPlayer</h2>
        <p className="text-sm text-gray-400">
          Configure TCGPlayer API keys in your <code className="bg-gray-800 px-1 rounded">.env</code> file:
        </p>
        <div className="bg-gray-800 rounded p-3 text-xs font-mono text-gray-300 space-y-1">
          <div>TCGPLAYER_PUBLIC_KEY={String(settings?.tcgplayer_public_key ?? "****")}</div>
          <div>TCGPLAYER_STORE_KEY={String(settings?.tcgplayer_store_key ?? "****")}</div>
        </div>
        <p className="text-xs text-gray-500">
          Apply for API access at{" "}
          <a
            href="https://developer.tcgplayer.com"
            target="_blank"
            rel="noreferrer"
            className="text-blue-400 hover:underline"
          >
            developer.tcgplayer.com
          </a>
        </p>
      </div>

      {/* eBay */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
        <h2 className="text-lg font-semibold text-yellow-400">eBay</h2>
        <div className="flex items-center gap-3">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              ebayStatus?.authenticated ? "bg-green-400" : "bg-red-500"
            }`}
          />
          <span className="text-sm text-gray-300">
            {ebayStatus?.authenticated ? "Connected" : "Not connected"}
          </span>
        </div>
        <button
          onClick={handleEbayConnect}
          className="px-4 py-2 text-sm bg-yellow-700 hover:bg-yellow-600 rounded transition-colors"
        >
          {ebayStatus?.authenticated ? "Re-authorize eBay" : "Connect eBay Account"}
        </button>
        <p className="text-xs text-gray-500">
          Configure eBay credentials in <code className="bg-gray-800 px-1 rounded">.env</code> first.
          Apply at{" "}
          <a
            href="https://developer.ebay.com"
            target="_blank"
            rel="noreferrer"
            className="text-yellow-400 hover:underline"
          >
            developer.ebay.com
          </a>
        </p>
        <div className="bg-gray-800 rounded p-3 text-xs font-mono text-gray-300 space-y-1">
          <div>EBAY_CLIENT_ID={String(settings?.ebay_client_id ?? "****")}</div>
          <div>EBAY_SANDBOX={String(settings?.ebay_sandbox ?? false)}</div>
        </div>
      </div>

      {/* Sync */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-2">
        <h2 className="text-lg font-semibold">Sync Settings</h2>
        <p className="text-sm text-gray-400">
          Sync interval:{" "}
          <span className="text-white font-medium">
            {String(settings?.sync_interval_minutes ?? 5)} minutes
          </span>
        </p>
        <p className="text-xs text-gray-500">
          Change <code className="bg-gray-800 px-1 rounded">SYNC_INTERVAL_MINUTES</code> in .env and restart.
        </p>
        <p className="text-sm text-gray-400 mt-2">
          App base URL:{" "}
          <span className="text-white font-mono text-xs">
            {String(settings?.app_base_url ?? "")}
          </span>
        </p>
        <p className="text-xs text-gray-500">
          Set <code className="bg-gray-800 px-1 rounded">APP_BASE_URL</code> to your server's public URL (used for eBay OAuth callback).
        </p>
      </div>
    </div>
  );
}
