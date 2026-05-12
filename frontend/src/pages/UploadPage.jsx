import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadDocument } from "../api/jobs";
import UploadZone from "../components/upload/UploadZone";
import UploadProgress from "../components/upload/UploadProgress";
import PageWrapper from "../components/layout/PageWrapper";
import Alert from "../components/ui/Alert";
import { ArrowRight, Info } from "lucide-react";

export default function UploadPage() {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null); // null | 'uploading' | 'success' | 'error'
  const [uploadError, setUploadError] = useState(null);

  const handleFileSelected = (file) => {
    setSelectedFile(file);
    setUploadStatus(null);
    setUploadError(null);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploadStatus("uploading");
    setUploadError(null);

    try {
      const result = await uploadDocument(selectedFile);
      setUploadStatus("success");
      setTimeout(() => navigate(`/jobs/${result.job_id}`), 500);
    } catch (err) {
      setUploadStatus("error");
      setUploadError(err.message);
    }
  };

  return (
    <PageWrapper
      title="Upload Document"
      subtitle="Upload a PDF containing your Bon de Commande, Bon de Livraison, and/or Facture"
    >
      <div className="max-w-2xl mx-auto">
        {/* Info banner */}
        <Alert variant="info" className="mb-6">
          <div className="flex items-start gap-2">
            <Info size={14} className="shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Accepted document formats</p>
              <p className="mt-1">
                Upload a single PDF containing one or more of: Bon de Commande (BC),
                Bon de Livraison (BL), or Facture. The system will automatically detect
                and classify each page.
              </p>
            </div>
          </div>
        </Alert>

        {/* Drop zone */}
        <UploadZone
          onFileSelected={handleFileSelected}
          disabled={uploadStatus === "uploading" || uploadStatus === "success"}
        />

        {/* File selected indicator */}
        {selectedFile && (
          <UploadProgress
            file={selectedFile}
            status={uploadStatus}
            error={uploadError}
          />
        )}

        {/* Upload button */}
        {selectedFile && uploadStatus !== "success" && (
          <button
            onClick={handleUpload}
            disabled={uploadStatus === "uploading"}
            className="mt-4 w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold py-3 px-6 rounded-xl transition-colors"
          >
            {uploadStatus === "uploading" ? (
              "Uploading…"
            ) : (
              <>
                Process Document
                <ArrowRight size={18} />
              </>
            )}
          </button>
        )}

        {uploadError && (
          <Alert variant="error" className="mt-4">
            {uploadError}
          </Alert>
        )}
      </div>
    </PageWrapper>
  );
}