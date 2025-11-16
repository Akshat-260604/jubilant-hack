'use client';

import { useState, useCallback } from 'react';
import { Upload, File, X, CheckCircle, AlertCircle, Cloud, Loader2 } from 'lucide-react';
import api from '@/lib/api';

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

interface DocumentUploadProps {
  userId: string;
}

export default function DocumentUpload({ userId }: DocumentUploadProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [googleDriveConnected, setGoogleDriveConnected] = useState(false);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const uploadAndProcessFile = async (fileMetaId: string, file: File) => {
    // Mark as uploading
    setFiles((prev) =>
      prev.map((f) => (f.id === fileMetaId ? { ...f, status: 'uploading', progress: 10 } : f))
    );

    try {
      // 1) Get presigned upload URL and document UUID from src12
      const { presigned_url, uuid } = await api.getPresignedUploadUrl(userId, file.name);

      // 2) Upload the file to S3 using the presigned URL
      await fetch(presigned_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type || 'application/pdf',
        },
      });

      // 3) Trigger document processing so embeddings are generated
      await api.triggerDocumentProcessing(userId, uuid);

      // Mark as success
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileMetaId ? { ...f, status: 'success', progress: 100 } : f
        )
      );
    } catch (error: any) {
      console.error('Error uploading or processing document:', error);
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileMetaId
            ? {
                ...f,
                status: 'error',
                progress: 0,
                error:
                  error?.response?.data?.detail ||
                  error?.message ||
                  'Failed to upload or process document',
              }
            : f
        )
      );
    }
  };

  const handleFileSelect = useCallback(
    (selectedFiles: FileList | null) => {
      if (!selectedFiles) return;

      const newFiles: UploadedFile[] = Array.from(selectedFiles).map((file) => ({
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        name: file.name,
        size: file.size,
        type: file.type || 'application/octet-stream',
        status: 'pending' as const,
        progress: 0,
      }));

      setFiles((prev) => [...prev, ...newFiles]);

      // For each selected file, call the backend pipeline
      newFiles.forEach((fileMeta, index) => {
        const file = selectedFiles[index];
        if (file) {
          uploadAndProcessFile(fileMeta.id, file);
        }
      });
    },
    [userId]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const removeFile = (fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const getFileIcon = (type: string) => {
    if (type.includes('pdf')) return '📄';
    if (type.includes('word') || type.includes('document')) return '📝';
    if (type.includes('excel') || type.includes('spreadsheet')) return '📊';
    if (type.includes('image')) return '🖼️';
    return '📎';
  };

  const acceptedTypes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'image/png',
    'image/jpeg',
    'image/jpg',
  ];

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Upload Medical Documents</h2>
        <p className="text-sm text-gray-600">
          Upload PDFs, Word documents, Excel files, or images containing medical data
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Google Drive Section */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Cloud className="w-8 h-8 text-blue-600" />
                <div>
                  <h3 className="font-semibold text-gray-900">Google Drive Integration</h3>
                  <p className="text-sm text-gray-600">
                    Access documents from your Google Drive folder
                  </p>
                </div>
              </div>
              <button
                onClick={() => setGoogleDriveConnected(!googleDriveConnected)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  googleDriveConnected
                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {googleDriveConnected ? (
                  <span className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    Connected
                  </span>
                ) : (
                  'Connect Drive'
                )}
              </button>
            </div>
            {googleDriveConnected && (
              <div className="mt-4 p-4 bg-white rounded-lg border border-blue-200">
                <p className="text-sm text-gray-600">
                  Google Drive is connected. Documents from the shared folder will be automatically
                  available for chat and report generation.
                </p>
              </div>
            )}
          </div>

          {/* File Upload Area */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
              isDragging
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
            }`}
          >
            <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Drag and drop files here
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              or click to browse (PDF, Word, Excel, Images)
            </p>
            <input
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
              onChange={(e) => handleFileSelect(e.target.files)}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="inline-block px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 cursor-pointer transition-colors"
            >
              Select Files
            </label>
          </div>

          {/* Uploaded Files List */}
          {files.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-semibold text-gray-900">Uploaded Files</h3>
              <div className="space-y-2">
                {files.map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200"
                  >
                    <div className="text-2xl">{getFileIcon(file.type)}</div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 truncate">{file.name}</p>
                      <p className="text-sm text-gray-500">
                        {formatFileSize(file.size)} • {file.type.split('/')[1]?.toUpperCase() || 'FILE'}
                      </p>
                      {file.status === 'uploading' && (
                        <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${file.progress}%` }}
                          />
                        </div>
                      )}
                      {file.status === 'error' && file.error && (
                        <p className="text-sm text-red-600 mt-1 flex items-center gap-1">
                          <AlertCircle className="w-4 h-4" />
                          {file.error}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {file.status === 'success' && (
                        <CheckCircle className="w-5 h-5 text-green-600" />
                      )}
                      {file.status === 'uploading' && (
                        <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
                      )}
                      {file.status === 'error' && (
                        <AlertCircle className="w-5 h-5 text-red-600" />
                      )}
                      <button
                        onClick={() => removeFile(file.id)}
                        className="p-1 hover:bg-gray-200 rounded transition-colors"
                      >
                        <X className="w-5 h-5 text-gray-500" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {files.length === 0 && !isDragging && (
            <div className="text-center text-gray-500 py-12">
              <File className="w-16 h-16 mx-auto mb-4 text-gray-400" />
              <p>No files uploaded yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

