import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, AlertCircle } from "lucide-react";
import clsx from "clsx";

export default function UploadZone({ onFileSelected, disabled }) {
  const [fileError, setFileError] = useState(null);

  const onDrop = useCallback(
    (acceptedFiles, rejectedFiles) => {
      setFileError(null);

      if (rejectedFiles.length > 0) {
        const reasons = rejectedFiles[0].errors.map((e) => e.message).join(", ");
        setFileError(`File rejected: ${reasons}`);
        return;
      }

      if (acceptedFiles.length > 0) {
        const file = acceptedFiles[0];
        if (file.size > 50 * 1024 * 1024) {
          setFileError("File is too large. Maximum size is 50MB.");
          return;
        }
        onFileSelected(file);
      }
    },
    [onFileSelected]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    disabled,
  });

  return (
    <div>
      <div
        {...getRootProps()}
        className={clsx(
          "border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200",
          isDragActive && !isDragReject && "border-blue-500 bg-blue-50",
          isDragReject && "border-red-400 bg-red-50",
          !isDragActive && !isDragReject && "border-gray-300 hover:border-blue-400 hover:bg-gray-50",
          disabled && "opacity-50 cursor-not-allowed pointer-events-none"
        )}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center gap-3">
          <div
            className={clsx(
              "p-4 rounded-full",
              isDragActive && !isDragReject ? "bg-blue-100" : "bg-gray-100"
            )}
          >
            {isDragReject ? (
              <AlertCircle size={32} className="text-red-500" />
            ) : (
              <Upload
                size={32}
                className={isDragActive ? "text-blue-600" : "text-gray-400"}
              />
            )}
          </div>

          <div>
            {isDragActive && !isDragReject ? (
              <p className="text-blue-600 font-semibold text-lg">
                Drop the PDF here
              </p>
            ) : isDragReject ? (
              <p className="text-red-600 font-semibold text-lg">
                Only PDF files are accepted
              </p>
            ) : (
              <>
                <p className="text-gray-700 font-semibold text-lg">
                  Drag & drop your PDF here
                </p>
                <p className="text-gray-400 text-sm mt-1">
                  or{" "}
                  <span className="text-blue-600 underline">
                    browse to select
                  </span>
                </p>
              </>
            )}
          </div>

          <div className="flex items-center gap-2 text-xs text-gray-400 mt-2">
            <FileText size={14} />
            <span>PDF only · Max 50MB · Up to 50 pages</span>
          </div>
        </div>
      </div>

      {fileError && (
        <p className="mt-2 text-sm text-red-600 flex items-center gap-1">
          <AlertCircle size={14} />
          {fileError}
        </p>
      )}
    </div>
  );
}