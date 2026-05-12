import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useJobPoller } from "../../hooks/useJobPoller";
import JobStatusBadge from "./JobStatusBadge";
import Spinner from "../ui/Spinner";
import Alert from "../ui/Alert";
import { Clock, FileText, Hash, Layers } from "lucide-react";
import { formatTimestamp } from "../../utils/formatters";

const TERMINAL_STATUSES = ["COMPLETED", "FAILED", "REVIEW_REQUIRED"];

export default function JobStatusPoller({ jobId }) {
  const { job, isPolling, error } = useJobPoller(jobId);
  const navigate = useNavigate();

  // Auto-navigate to results when processing completes
  useEffect(() => {
    if (!job) return;
    if (
      job.status === "COMPLETED" ||
      job.status === "REVIEW_REQUIRED"
    ) {
      // Small delay so user sees the completed state
      const timer = setTimeout(() => {
        navigate(`/results/${jobId}`);
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [job, jobId, navigate]);

  if (error) {
    return <Alert variant="error" title="Polling error">{error}</Alert>;
  }

  if (!job) {
    return (
      <div className="flex items-center justify-center py-16 gap-3 text-gray-500">
        <Spinner />
        <span>Loading job status…</span>
      </div>
    );
  }

  const isTerminal = TERMINAL_STATUSES.includes(job.status);

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText size={18} className="text-gray-400" />
          <span className="font-medium text-gray-900 truncate max-w-xs">
            {job.filename}
          </span>
        </div>
        <JobStatusBadge status={job.status} />
      </div>

      {/* Details */}
      <div className="px-6 py-5 grid grid-cols-2 gap-4 sm:grid-cols-3">
        <MetaItem icon={Hash} label="Job ID" value={job.job_id.slice(0, 8) + "…"} mono />
        <MetaItem icon={Layers} label="Pages" value={job.page_count ?? "—"} />
        <MetaItem
          icon={Clock}
          label="Started"
          value={formatTimestamp(job.processing_started_at)}
        />
      </div>

      {/* Processing animation */}
      {!isTerminal && (
        <div className="px-6 pb-6">
          <div className="bg-gray-50 rounded-lg p-4 flex items-center gap-3">
            <Spinner size="md" />
            <div>
              <p className="text-sm font-medium text-gray-700">
                Processing your document…
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                This usually takes 30–90 seconds
              </p>
            </div>
          </div>
          <ProcessingSteps currentStatus={job.status} />
        </div>
      )}

      {/* Error state */}
      {job.status === "FAILED" && job.error && (
        <div className="px-6 pb-6">
          <Alert variant="error" title="Processing failed">
            {job.error}
          </Alert>
        </div>
      )}

      {/* Completed — redirecting */}
      {isTerminal && job.status !== "FAILED" && (
        <div className="px-6 pb-5">
          <div className="flex items-center gap-2 text-sm text-green-600 font-medium">
            <Spinner size="sm" />
            Redirecting to results…
          </div>
        </div>
      )}
    </div>
  );
}

function MetaItem({ icon: Icon, label, value, mono }) {
  return (
    <div>
      <div className="flex items-center gap-1 text-xs text-gray-400 mb-1">
        <Icon size={12} />
        {label}
      </div>
      <p className={`text-sm font-medium text-gray-900 ${mono ? "font-mono" : ""}`}>
        {value}
      </p>
    </div>
  );
}

const STEPS = [
  { status: "CLASSIFYING", label: "Classifying pages" },
  { status: "EXTRACTING", label: "Extracting data" },
  { status: "VALIDATING", label: "Validating fields" },
  { status: "MATCHING", label: "Matching documents" },
];

function ProcessingSteps({ currentStatus }) {
  const currentIdx = STEPS.findIndex((s) => s.status === currentStatus);

  return (
    <div className="mt-4 flex items-center gap-0">
      {STEPS.map((step, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;
        return (
          <div key={step.status} className="flex items-center flex-1">
            <div className="flex flex-col items-center">
              <div
                className={`w-3 h-3 rounded-full border-2 transition-colors ${
                  done
                    ? "bg-green-500 border-green-500"
                    : active
                    ? "bg-blue-500 border-blue-500 animate-pulse"
                    : "bg-white border-gray-300"
                }`}
              />
              <span className={`text-xs mt-1 whitespace-nowrap ${
                active ? "text-blue-600 font-medium" :
                done ? "text-green-600" :
                "text-gray-400"
              }`}>
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`flex-1 h-0.5 mx-1 -mt-4 ${done ? "bg-green-400" : "bg-gray-200"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}