interface Props {
  listedOnEbay: boolean;
}

export default function SyncStatusBadge({ listedOnEbay }: Props) {
  return (
    <div className="flex gap-1">
      <span
        className={`px-1.5 py-0.5 rounded text-xs font-medium ${
          listedOnEbay ? "bg-yellow-900 text-yellow-300" : "bg-gray-800 text-gray-600"
        }`}
      >
        eBay
      </span>
    </div>
  );
}
