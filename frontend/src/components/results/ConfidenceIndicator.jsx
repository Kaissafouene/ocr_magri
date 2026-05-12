import { AlertTriangle } from "lucide-react";
import { formatConfidence } from "../../utils/formatters";
import clsx from "clsx";

export default function ConfidenceIndicator({ value, showIcon = true }) {
  if (value === null || value === undefined) return <span className="text-gray-400">—</span>;

  const pct = Math.round(value * 100);
  const isLow = pct < 70;
  const isMedium = pct >= 70 && pct < 85;

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 text-xs font-medium",
        isLow ? "text-red-600" : isMedium ? "text-yellow-600" : "text-green-600"
      )}
    >
      {showIcon && isLow && <AlertTriangle size={12} />}
      {formatConfidence(value)}
    </span>
  );
}