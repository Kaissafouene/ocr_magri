import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useJobResults } from "../hooks/useJobResults";
import PageWrapper from "../components/layout/PageWrapper";
import VerdictBanner from "../components/results/VerdictBanner";
import DocumentSummary from "../components/results/DocumentSummary";
import LineItemTable from "../components/results/LineItemTable";
import AuditTrail from "../components/results/AuditTrail";
import Spinner from "../components/ui/Spinner";
import Alert from "../components/ui/Alert";
import Modal from "../components/ui/Modal";
import { AlertTriangle, ClipboardList, FileText, Upload } from "lucide-react";

export default function ResultsPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const { job, results, auditTrail, loading, error } = useJobResults(jobId);
  const [auditOpen, setAuditOpen] = useState(false);

  if (loading) {
    return (
      <PageWrapper title="Loading Results...">
        <div className="flex justify-center py-20">
          <Spinner size="lg" />
        </div>
      </PageWrapper>
    );
  }

  if (error) {
    return (
      <PageWrapper title="Error">
        <Alert variant="error" title="Failed to load results">
          {error}
        </Alert>
      </PageWrapper>
    );
  }

  if (!results) return null;

  const status = job?.status ?? results.status;
  const verdict = job?.verdict ?? results.verdict;
  const documents = results.documents ?? [];
  const matchResult = results.match_result;
  const failureMessage = job?.error || results.message;
  const needsReview = status === "REVIEW_REQUIRED";
  const isFailed = status === "FAILED";
  const hasExtractedDocuments = documents.length > 0;
  const showReviewAction = needsReview && hasExtractedDocuments;
  const pageTitle = isFailed ? "Verification Failed" : "Verification Results";
  const pageSubtitle = job?.filename
    ? `${job.filename} · Job ${jobId.slice(0, 8)}...`
    : `Job ${jobId.slice(0, 8)}...`;

  return (
    <PageWrapper title={pageTitle} subtitle={pageSubtitle}>
      <div className="space-y-6">
        <VerdictBanner
          verdict={verdict}
          matchResult={matchResult}
          status={status}
          errorMessage={failureMessage}
        />

        {isFailed && (
          <Alert variant="error" title="Processing failed">
            {failureMessage || "The document could not be processed."}
          </Alert>
        )}

        {needsReview && (
          <Alert variant="warning" title="Human Review Required">
            {showReviewAction ? (
              <>
                This document set has been flagged for manual review.{" "}
                <button
                  onClick={() => navigate(`/review/${jobId}`)}
                  className="underline font-semibold"
                >
                  Go to review page →
                </button>
              </>
            ) : (
              "Manual review is not actionable yet because no structured documents were extracted. Check the audit log for page-by-page details."
            )}
          </Alert>
        )}

        <section>
          <h2 className="text-base font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <FileText size={16} />
            Extracted Documents ({documents.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {documents.map((doc, i) => (
              <DocumentSummary key={i} document={doc} />
            ))}
          </div>
          {!hasExtractedDocuments && (
            <div className="mt-4 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-5 text-sm text-gray-600 flex items-start gap-3">
              <AlertTriangle size={18} className="mt-0.5 shrink-0 text-gray-400" />
              <p>
                No extracted documents are available for this job.
                {isFailed
                  ? " The pipeline stopped before producing BC, BL, or Facture data."
                  : " The pipeline could not extract structured data from this PDF."}
              </p>
            </div>
          )}
        </section>

        {matchResult?.line_verdicts?.length > 0 && (
          <section>
            <h2 className="text-base font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <ClipboardList size={16} />
              Line Item Comparison ({matchResult.total_lines} items)
            </h2>
            <LineItemTable lineVerdicts={matchResult.line_verdicts} />
          </section>
        )}

        <div className="flex items-center gap-3 pt-2 border-t border-gray-200">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <Upload size={14} />
            Upload another
          </button>

          <button
            onClick={() => setAuditOpen(true)}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <ClipboardList size={14} />
            View audit log
          </button>

          {showReviewAction && (
            <button
              onClick={() => navigate(`/review/${jobId}`)}
              className="flex items-center gap-2 px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white rounded-lg text-sm font-semibold transition-colors"
            >
              Review & Approve
            </button>
          )}
        </div>
      </div>

      <Modal
        open={auditOpen}
        onClose={() => setAuditOpen(false)}
        title="Audit Trail"
      >
        <AuditTrail auditTrail={auditTrail} />
      </Modal>
    </PageWrapper>
  );
}
