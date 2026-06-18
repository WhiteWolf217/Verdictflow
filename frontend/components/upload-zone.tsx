/**
 * VerdictFlow — Upload Zone (v2)
 * Minimal drag-and-drop upload with clean aesthetics.
 */

"use client";

import { useCallback, useState, useRef } from "react";

interface UploadZoneProps {
  onUpload: (file: File) => void;
  isUploading?: boolean;
}

export default function UploadZone({ onUpload, isUploading }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragging(true);
    } else if (e.type === "dragleave") {
      setIsDragging(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      const files = e.dataTransfer.files;
      if (files.length > 0 && isValidFile(files[0])) {
        onUpload(files[0]);
      }
    },
    [onUpload]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0 && isValidFile(files[0])) {
        onUpload(files[0]);
      }
    },
    [onUpload]
  );

  const isValidFile = (file: File): boolean => {
    return /\.(pdf|docx|doc|txt)$/i.test(file.name);
  };

  return (
    <div
      id="upload-zone"
      className={`upload-zone ${isDragging ? "upload-zone-active" : ""} ${isUploading ? "opacity-50 pointer-events-none" : ""}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.doc,.txt"
        onChange={handleFileSelect}
        className="hidden"
        id="file-input"
      />

      {isUploading ? (
        <div className="flex flex-col items-center gap-3">
          <svg className="w-6 h-6 text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-[13px] text-zinc-400">Processing contract...</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <svg className="w-8 h-8 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.338-2.32 3.75 3.75 0 013.57 5.346A4.5 4.5 0 0118 19.5H6.75z" />
          </svg>
          <div>
            <p className="text-[14px] text-zinc-300">
              Drop contract here or{" "}
              <span className="text-blue-400 font-medium">browse</span>
            </p>
            <p className="text-[12px] text-zinc-600 mt-1">
              PDF, DOCX, or TXT up to 10MB
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
