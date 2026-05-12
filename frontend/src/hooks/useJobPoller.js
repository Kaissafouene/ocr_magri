import { useState, useEffect, useRef, useCallback } from "react";
import { getJobStatus } from "../api/jobs";

const TERMINAL_STATUSES = ["COMPLETED", "FAILED", "REVIEW_REQUIRED"];
const POLL_INTERVAL_MS = 2500;

/**
 * Polls GET /jobs/{jobId} kol 2.5 seconds 7ata tkaml statusw ta5o 3 states (processing, completed, failed)
 * Returns { job, isPolling, error }
 */
export function useJobPoller(jobId) {
  const [job, setJob] = useState(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const poll = useCallback(async () => {
    if (!jobId) return;

    try {
      const data = await getJobStatus(jobId);
      setJob(data);
      setError(null);

      if (TERMINAL_STATUSES.includes(data.status)) {
        stopPolling();
      }
    } catch (err) {
      setError(err.message);
      stopPolling();
    }
  }, [jobId, stopPolling]);

  useEffect(() => {
    if (!jobId) return;

    setIsPolling(true);
    setError(null);
    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => stopPolling();
  }, [jobId, poll, stopPolling]);

  return { job, isPolling, error };
}