import { FileText, CheckCircle, XCircle } from "lucide-react";
import Spinner from "../ui/Spinner";
import clsx from "clsx";

export default function UploadProgress({ file, status, error }) {
  // 3 status: 'uploading' | 'success' | 'error'
  return (
    <div className="mt-4 border border-gray-200 rounded-lg px-4 py-3 bg-white flex items-center gap-3">
      <FileText size={20} className="text-gray-400 shrink-0" />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-700 truncate">{file.name}</p>
        <p className="text-xs text-gray-400">
          {(file.size / 1024 / 1024).toFixed(2)} MB
        </p>
      </div>

      <div className="shrink-0">
        {status === "uploading" && <Spinner size="sm" />}
        {status === "success" && (
          <CheckCircle size={20} className="text-green-500" />
        )}
        {status === "error" && (
          <XCircle size={20} className="text-red-500" />
        )}
      </div>

      {error && (
        <p className="text-xs text-red-600 mt-1 col-span-full">{error}</p>
      )}
    </div>
  );
}