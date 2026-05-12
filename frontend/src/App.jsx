import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/layout/Navbar";
import UploadPage from "./pages/UploadPage";
import JobPage from "./pages/JobPage";
import ResultsPage from "./pages/ResultsPage";
import ReviewPage from "./pages/ReviewPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Navbar />
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/jobs/:jobId" element={<JobPage />} />
            <Route path="/results/:jobId" element={<ResultsPage />} />
            <Route path="/review/:jobId" element={<ReviewPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}