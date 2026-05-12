import client from "./client";

/**
 * Upload a PDF file for processing.
 * Returns { job_id, status, filename, page_count }
 */
export async function uploadDocument(file, uploadedBy = "anonymous") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("uploaded_by", uploadedBy);

  const response = await client.post("/jobs/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

/**
 * Get job processing status.
 * Returns { job_id, status, verdict, filename, page_count, ... }
 */
export async function getJobStatus(jobId) {
  const response = await client.get(`/jobs/${jobId}`);
  return response.data;
}

/**
 * Get full matching results for a completed job.
 */
export async function getJobResults(jobId) {
  const response = await client.get(`/jobs/${jobId}/results`);
  return response.data;
}

/**
 * Get audit trail for a job.
 */
export async function getAuditTrail(jobId) {
  const response = await client.get(`/jobs/${jobId}/audit`);
  return response.data;
}