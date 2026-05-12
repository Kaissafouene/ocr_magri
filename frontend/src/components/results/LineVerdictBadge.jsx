import { LINE_VERDICT_STYLES } from "../../utils/verdictColors";
import clsx from "clsx";

export default function LineVerdictBadge({ verdict }) {
  const style = LINE_VERDICT_STYLES[verdict] || LINE_VERDICT_STYLES.PARTIAL_DATA;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold",
        style.badge
      )}
    >
      <span className={clsx("w-1.5 h-1.5 rounded-full", style.dot)} />
      {style.label}
    </span>
  );
}