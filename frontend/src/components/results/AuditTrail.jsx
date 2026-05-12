import { formatTimestamp } from "../../utils/formatters";
import { Shield } from "lucide-react";

const EVENT_LABELS = {
  PIPELINE_STARTED: "Pipeline started",
  PDF_ANALYZED: "PDF analyzed",
  PAGE_CLASSIFIED: "Page classified",
  PAGES_GROUPED: "Pages grouped into documents",
  LLM_FALLBACK_TRIGGERED: "AI extraction fallback triggered",
  EXTRACTION_FAILED: "Extraction failed",
  DOCUMENT_VALIDATED: "Document validated",
  DATE_ORDER_WARNING: "Date ordering warning",
  MATCHING_COMPLETE: "Matching completed",
  JOB_FAILED: "Job failed",
  HUMAN_REVIEW_COMPLETED: "Human review completed",
  PAGE_REQUIRES_HUMAN_CLASSIFICATION: "Page requires human classification",
};

const EVENT_COLORS = {
  JOB_FAILED: "border-red-400 bg-red-50",
  LLM_FALLBACK_TRIGGERED: "border-yellow-400 bg-yellow-50",
  HUMAN_REVIEW_COMPLETED: "border-blue-400 bg-blue-50",
  MATCHING_COMPLETE: "border-green-400 bg-green-50",
  DEFAULT: "border-gray-200 bg-white",
};

export default function AuditTrail({ auditTrail }) {
  if (!auditTrail?.audit_trail?.length) {
    return (
      <p className="text-sm text-gray-400 text-center py-8">
        No audit logs available
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-4">
        <Shield size={16} className="text-gray-400" />
        <p className="text-xs text-gray-500 font-medium">
          Immutable audit log — all system decisions recorded
        </p>
      </div>

      {auditTrail.audit_trail.map((entry, idx) => {
        const color = EVENT_COLORS[entry.event_type] || EVENT_COLORS.DEFAULT;
        return (
          <div key={idx} className={`border-l-4 rounded-r-lg px-4 py-3 ${color}`}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-800">
                  {EVENT_LABELS[entry.event_type] || entry.event_type}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  Actor: {entry.actor}
                </p>

                {/* Show key fields from event_data */}
                {entry.data && Object.keys(entry.data).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {Object.entries(entry.data)
                      .filter(([, v]) => typeof v !== "object" || v === null)
                      .slice(0, 6)
                      .map(([k, v]) => (
                        <span key={k} className="text-xs bg-white/70 border border-gray-200 rounded px-1.5 py-0.5 font-mono">
                          {k}: <strong>{String(v)}</strong>
                        </span>
                      ))}
                  </div>
                )}
              </div>
              <time className="text-xs text-gray-400 shrink-0">
                {formatTimestamp(entry.timestamp)}
              </time>
            </div>
          </div>
        );
      })}
    </div>
  );
}