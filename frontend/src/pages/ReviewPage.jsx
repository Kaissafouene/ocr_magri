import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useJobResults } from "../hooks/useJobResults";
import { submitReview } from "../api/admin";
import PageWrapper from "../components/layout/PageWrapper";
import VerdictBanner from "../components/results/VerdictBanner";
import DocumentSummary from "../components/results/DocumentSummary";
import LineItemTable from "../components/results/LineItemTable";
import Spinner from "../components/ui/Spinner";
import Alert from "../components/ui/Alert";
import { CheckCircle, XCircle, ArrowLeft } from "lucide-react";

export default function ReviewPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const { job, results, loading, error } = useJobResults(jobId);

  const [reviewerId, setReviewerId] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  const status = job?.status ?? results?.status;
  const documents = results?.documents ?? [];
  const matchResult = results?.match_result;
  const failureMessage = job?.error || results?.message;
  const canReview = status === "REVIEW_REQUIRED" && documents.length > 0;

  const handleSubmit = async (approved) => {
    if (!reviewerId.trim()) {
      setSubmitError("Please enter your name or reviewer ID.");
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    try {
      await submitReview(jobId, { reviewerId, approved, notes });
      setSubmitted(true);
      setTimeout(() => navigate(`/results/${jobId}`), 1500);
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <PageWrapper title="Loading...">
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      </PageWrapper>
    );
  }

  if (error) {
    return (
      <PageWrapper title="Error">
        <Alert variant="error">{error}</Alert>
      </PageWrapper>
    );
  }

  if (!results) return null;

  if (submitted) {
    return (
      <PageWrapper title="Review Submitted">
        <Alert variant="success" title="Decision recorded">
          Your review has been saved to the audit log. Redirecting...
        </Alert>
      </PageWrapper>
    );
  }

  if (!canReview) {
    return (
      <PageWrapper
        title="Review Unavailable"
        subtitle="This job does not currently have reviewable extracted documents."
      >
        <div className="space-y-6">
          <button
            onClick={() => navigate(`/results/${jobId}`)}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
          >
            <ArrowLeft size={14} />
            Back to results
          </button>

          <Alert variant="warning" title="Nothing to review">
            {failureMessage ||
              "The pipeline did not produce any extracted documents, so there is nothing to approve or reject yet."}
          </Alert>
        </div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper
      title="Human Review"
      subtitle="Review the extracted data and matching results, then approve or reject."
    >
      <div className="space-y-6">
        <button
          onClick={() => navigate(`/results/${jobId}`)}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft size={14} />
          Back to results
        </button>

        <VerdictBanner
          verdict={job?.verdict ?? results.verdict}
          matchResult={matchResult}
          status={status}
          errorMessage={failureMessage}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents.map((doc, i) => (
            <DocumentSummary key={i} document={doc} />
          ))}
        </div>

        {matchResult?.line_verdicts?.length > 0 && (
          <LineItemTable lineVerdicts={matchResult.line_verdicts} />
        )}

        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h3 className="text-base font-semibold text-gray-900 mb-4">
            Submit Review Decision
          </h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Your name / Reviewer ID *
              </label>
              <input
                type="text"
                value={reviewerId}
                onChange={(e) => setReviewerId(e.target.value)}
                placeholder="e.g. Ahmed Benali"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notes (optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add any comments about this decision..."
                rows={3}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            {submitError && (
              <Alert variant="error">{submitError}</Alert>
            )}

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => handleSubmit(true)}
                disabled={submitting}
                className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white font-semibold py-3 rounded-xl transition-colors"
              >
                {submitting ? <Spinner size="sm" /> : <CheckCircle size={18} />}
                Approve
              </button>

              <button
                onClick={() => handleSubmit(false)}
                disabled={submitting}
                className="flex-1 flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white font-semibold py-3 rounded-xl transition-colors"
              >
                {submitting ? <Spinner size="sm" /> : <XCircle size={18} />}
                Reject
              </button>
            </div>

            <p className="text-xs text-gray-400 text-center">
              This decision is permanent and will be recorded in the immutable audit log.
            </p>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
