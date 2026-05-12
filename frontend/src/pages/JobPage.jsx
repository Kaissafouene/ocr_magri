import { useParams } from "react-router-dom";
import PageWrapper from "../components/layout/PageWrapper";
import JobStatusPoller from "../components/job/JobStatusPoller";

export default function JobPage() {
  const { jobId } = useParams();

  return (
    <PageWrapper
      title="Processing"
      subtitle="Your document is being analyzed. You will be redirected automatically when complete."
    >
      <div className="max-w-2xl mx-auto">
        <JobStatusPoller jobId={jobId} />
      </div>
    </PageWrapper>
  );
}