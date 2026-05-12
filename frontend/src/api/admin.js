import client from "./client";

/**
 * Submit a human review decision.
 * approved: true = mark VALIDATED, false = mark REJECTED
 */
export async function submitReview(jobId, { reviewerId, approved, notes }) {
  const response = await client.patch(`/jobs/${jobId}/review`, {
    reviewer_id: reviewerId,
    approved,
    notes,
  });
  return response.data;
}