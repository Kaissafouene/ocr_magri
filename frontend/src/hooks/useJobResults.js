import { useState, useEffect } from "react";
import { getJobResults, getAuditTrail, getJobStatus } from "../api/jobs";

export function useJobResults(jobId) {
  const [results, setResults] = useState(null);
  const [job, setJob] = useState(null);
  const [auditTrail, setAuditTrail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      setError(null);

      try {
        const [jobData, resultsData, auditData] = await Promise.all([
          getJobStatus(jobId),
          getJobResults(jobId),
          getAuditTrail(jobId).catch(() => null), 
        ]);

        if (!cancelled) {
          setJob(jobData);
          setResults(resultsData);
          setAuditTrail(auditData);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();
    return () => { cancelled = true; };
  }, [jobId]);

  return { job, results, auditTrail, loading, error };
}
