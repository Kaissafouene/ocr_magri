import { JOB_STATUS_STYLES } from "../../utils/verdictColors";
import Spinner from "../ui/Spinner";
import clsx from "clsx";

const PROCESSING_STATUSES = [
  "PROCESSING",
  "CLASSIFYING",
  "EXTRACTING",
  "VALIDATING",
  "MATCHING",
];

export default function JobStatusBadge({ status }) {
  const style = JOB_STATUS_STYLES[status] || JOB_STATUS_STYLES.PENDING;
  const isProcessing = PROCESSING_STATUSES.includes(status);

  return (
    <span className={clsx("inline-flex items-center gap-1.5 text-sm font-medium", style.color)}>
      {isProcessing && <Spinner size="sm" />}
      {style.label}
    </span>
  );
}