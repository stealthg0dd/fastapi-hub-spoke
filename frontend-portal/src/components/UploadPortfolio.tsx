import { useCallback, useState } from "react";
import { Upload } from "lucide-react";
import { toast } from "sonner";
import apiClient from "../api/apiClient";
import type { UploadSummary } from "../api/types";
import { useVenture } from "../context/venturecontext";

export function UploadPortfolio() {
  const { userId } = useVenture();
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const handleFiles = useCallback(
    async (file: File | null) => {
      if (!file) return;
      if (!userId) {
        setStatus("Please sign in so we can attribute this upload to your user account.");
        return;
      }

      setIsUploading(true);
      setStatus(null);

      const formData = new FormData();
      formData.append("user_id", userId);
      formData.append("file", file);

      try {
        const { data } = await apiClient.post<UploadSummary>(
          "/api/v1/neufin/portfolio/upload",
          formData,
          {
            headers: { "Content-Type": "multipart/form-data" },
          },
        );

        const message =
          `Imported ${data.imported} rows, Skipped ${data.skipped} rows` +
          (data.errors.length ? ` (${data.errors.length} errors)` : "");

        setStatus(message);
        toast.success(message);
      } catch {
        const message = "Upload failed. Please check your CSV and try again.";
        setStatus(message);
        toast.error(message);
      } finally {
        setIsUploading(false);
      }
    },
    [userId],
  );

  const onDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);

    const file = event.dataTransfer.files?.[0] ?? null;
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setStatus("Please upload a .csv file.");
      return;
    }
    void handleFiles(file);
  };

  const onDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(true);
  };

  const onDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
  };

  const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setStatus("Please upload a .csv file.");
      return;
    }
    void handleFiles(file);
    // reset so the same file can be chosen again
    event.target.value = "";
  };

  return (
    <div className="space-y-3">
      <div
        className={`flex flex-col items-center justify-center rounded-xl border border-dashed px-6 py-8 text-center transition-colors ${
          isDragging
            ? "border-[#00C087] bg-[#00C087]/5"
            : "border-[#1A1D23] bg-[#0D1117]"
        } ${isUploading ? "opacity-70" : ""}`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
      >
        <Upload className="mb-3 h-6 w-6 text-gray-400" />
        <p className="text-sm font-mono text-white">
          Drag and drop your <span className="text-[#00C087]">.csv</span> file here
        </p>
        <p className="mt-1 text-[11px] font-mono text-gray-500">
          Columns: Ticker, Quantity, Average Price
        </p>
        <label className="mt-4 inline-flex cursor-pointer items-center justify-center rounded-lg border border-white/10 px-3 py-1.5 text-[11px] font-mono text-white hover:bg-white/5">
          <span>{isUploading ? "Uploading…" : "Browse files"}</span>
          <input
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={onFileChange}
            disabled={isUploading}
          />
        </label>
        {!userId && (
          <p className="mt-3 text-[11px] font-mono text-yellow-400">
            Uploads are disabled until we know which user you are.
          </p>
        )}
      </div>

      {status && (
        <div className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-xs font-mono text-gray-200">
          {status}
        </div>
      )}
    </div>
  );
}

