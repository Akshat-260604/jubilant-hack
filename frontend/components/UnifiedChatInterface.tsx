'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Loader2, FileText, ExternalLink, AlertCircle, CheckCircle, Upload, File, X, Cloud, Sparkles, RefreshCw, Eye, ArrowLeft } from 'lucide-react';
import { api } from '@/lib/api';

interface Citation {
  document_id: string;
  document_name?: string;
  chunk_text?: string;
  page_number?: number;
  source_type?: 'uploaded' | 'google_drive';
  google_drive_link?: string;
  score?: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  citations?: Citation[];
  noAnswerFound?: boolean;
  msgId?: string;
}

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

interface GoogleDriveDoc {
  id: string;
  name: string;
  link?: string;
  lastModified?: string;
}

interface UnifiedChatInterfaceProps {
  userId: string;
}

export default function UnifiedChatInterface({ userId }: UnifiedChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [contextId, setContextId] = useState<string | undefined>();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [googleDriveDocs, setGoogleDriveDocs] = useState<GoogleDriveDoc[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [googleDriveConnected, setGoogleDriveConnected] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isRewriting, setIsRewriting] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<{ id: string; name: string; type: 'uploaded' | 'google_drive'; link?: string } | null>(null);
  const [previewImages, setPreviewImages] = useState<{ url: string; page_number?: number }[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Safely extract displayable text from potential JSON-encoded chunks
  const getDisplayContent = (raw: string): string => {
    if (!raw) return '';

    const lines = raw.split('\n');
    const collected: string[] = [];

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
        try {
          const data = JSON.parse(trimmed);
          if (typeof data.msg === 'string') {
            collected.push(data.msg);
            continue;
          }
        } catch {
          // fall through and use raw text
        }
      }
      collected.push(trimmed);
    }

    return collected.join(' ');
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load state from localStorage on mount
  useEffect(() => {
    const savedFiles = localStorage.getItem(`files_${userId}`);
    const savedDriveDocs = localStorage.getItem(`driveDocs_${userId}`);
    const savedDriveConnected = localStorage.getItem(`driveConnected_${userId}`);
    const savedSelectedDoc = localStorage.getItem(`selectedDoc_${userId}`);

    if (savedFiles) {
      try {
        setFiles(JSON.parse(savedFiles));
      } catch (e) {
        console.error('Error loading files:', e);
      }
    }
    if (savedDriveDocs) {
      try {
        setGoogleDriveDocs(JSON.parse(savedDriveDocs));
      } catch (e) {
        console.error('Error loading drive docs:', e);
      }
    }
    if (savedDriveConnected === 'true') {
      setGoogleDriveConnected(true);
    }
    if (savedSelectedDoc) {
      try {
        setSelectedDocument(JSON.parse(savedSelectedDoc));
      } catch (e) {
        console.error('Error loading selected doc:', e);
      }
    }
  }, [userId]);

  // Save state to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(`files_${userId}`, JSON.stringify(files));
  }, [files, userId]);

  useEffect(() => {
    localStorage.setItem(`driveDocs_${userId}`, JSON.stringify(googleDriveDocs));
  }, [googleDriveDocs, userId]);

  useEffect(() => {
    localStorage.setItem(`driveConnected_${userId}`, googleDriveConnected.toString());
  }, [googleDriveConnected, userId]);

  useEffect(() => {
    if (selectedDocument) {
      localStorage.setItem(`selectedDoc_${userId}`, JSON.stringify(selectedDocument));
    } else {
      localStorage.removeItem(`selectedDoc_${userId}`);
    }
  }, [selectedDocument, userId]);

  // Load processed documents for this user from backend
  const refreshProcessedDocs = useCallback(async () => {
    try {
      const docs = await api.listMySelfUploadedDocuments(userId);
      const mapped: UploadedFile[] = (docs || []).map((doc: any) => ({
        id: doc.id,
        name: doc.filename,
        size: 0,
        type: 'application/pdf',
        status: doc.status === 'completed' ? 'success' : 'pending',
        progress: doc.status === 'completed' ? 100 : 0,
      }));
      setFiles(mapped);
    } catch (error) {
      console.error('Error loading processed documents:', error);
    }
  }, [userId]);

  useEffect(() => {
    refreshProcessedDocs();
  }, [refreshProcessedDocs]);

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

      // Update UI as success
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileMetaId ? { ...f, status: 'success', progress: 100 } : f
        )
      );

      // 4) Refresh processed docs list so new document shows with backend ID/status
      await refreshProcessedDocs();
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
    [userId, refreshProcessedDocs]
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
    if (selectedDocument?.id === fileId && selectedDocument.type === 'uploaded') {
      setSelectedDocument(null);
    }
  };

  const loadDocumentPreviews = async (documentId: string) => {
    try {
      const result = await api.getDocumentPreviews(documentId, userId);
      setPreviewImages(result || []);
    } catch (error) {
      console.error('Error loading document previews:', error);
      setPreviewImages([]);
    }
  };

  const handleSyncGoogleDrive = async () => {
    if (isSyncing) return;

    setIsSyncing(true);
    try {
      // 1) Optional: verify Google Drive configuration
      const setupResult = await api.googleDriveSetup();
      if (!setupResult?.success) {
        console.error('Google Drive setup failed:', setupResult?.message);
        setIsSyncing(false);
        return;
      }

      // 2) Sync documents for this user
      await api.syncGoogleDriveDocuments(userId);

      // 3) Fetch available Google Drive documents
      const listResult = await api.getGoogleDriveDocuments();
      const docs = (listResult?.documents || []).map((doc: any) => ({
        id: doc.document_id,
        name: doc.name,
        link: doc.web_view_link,
        lastModified: doc.modified_time,
      }));

      setGoogleDriveDocs(docs);
      setGoogleDriveConnected(true);
    } catch (error) {
      console.error('Error syncing Google Drive:', error);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleRefreshGoogleDrive = async () => {
    setIsSyncing(true);
    try {
      const listResult = await api.getGoogleDriveDocuments();
      const docs = (listResult?.documents || []).map((doc: any) => ({
        id: doc.document_id,
        name: doc.name,
        link: doc.web_view_link,
        lastModified: doc.modified_time,
      }));
      setGoogleDriveDocs(docs);
    } catch (error) {
      console.error('Error refreshing Google Drive:', error);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleRewritePrompt = async () => {
    if (!input.trim()) return;

    setIsRewriting(true);
    try {
      const result = await api.rewrite({ user_prompt: input });
      setInput(result.enhanced_prompt);
    } catch (error) {
      console.error('Error rewriting prompt:', error);
    } finally {
      setIsRewriting(false);
    }
  };

  const autoResizeInput = (element: HTMLTextAreaElement | null) => {
    if (!element) return;
    element.style.height = 'auto';
    const maxHeight = 160; // limit how tall the input can grow
    const newHeight = Math.min(element.scrollHeight, maxHeight);
    element.style.height = `${newHeight}px`;
  };

  useEffect(() => {
    autoResizeInput(inputRef.current);
  }, [input]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setIsLoading(true);

    try {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        citations: [],
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // If a specific uploaded document is selected, use the /chat endpoint which returns JSON with sources.
      // Otherwise, fall back to smart chat across all sources.
      if (selectedDocument && selectedDocument.type === 'uploaded') {
        const response = await api.chat({
          prompt: currentInput,
          document_ids: [selectedDocument.id],
          context_id: contextId,
        });

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body from chat endpoint');
        }

        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          buffer += chunk;

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            try {
              const data = JSON.parse(trimmed);
              const msgText = data.msg as string | undefined;
              const newContextId = data.context_id as string | undefined;
              const msgId = data.msg_id as string | undefined;
              const index = (data.index || []) as Array<{
                document_name: string;
                document_id: string;
                page_number?: number;
              }>;

              if (newContextId) {
                setContextId(newContextId);
              }

              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.id === assistantMessage.id) {
                  if (msgText) {
                    last.content += msgText;
                  }
                  if (msgId) {
                    last.msgId = msgId;
                  }
                  if (index && index.length > 0) {
                    last.citations = index.map((item) => ({
                      document_id: item.document_id,
                      document_name: item.document_name,
                      page_number: item.page_number,
                      source_type: 'uploaded',
                    }));
                  }
                }
                return updated;
              });
            } catch {
              // Ignore partial / invalid JSON; next chunks will complete it.
            }
          }
        }
      } else {
        // Smart chat across all available documents (also returns JSON lines from stream_final_answer)
        const response = await api.healthcareChat({
          prompt: currentInput,
          userId,
          context_id: contextId,
        });

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body from smart chat endpoint');
        }

        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          buffer += chunk;

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            try {
              const data = JSON.parse(trimmed);
              const msgText = data.msg as string | undefined;
              const newContextId = data.context_id as string | undefined;
              const msgId = data.msg_id as string | undefined;
              const index = (data.index || []) as Array<{
                document_name: string;
                document_id: string;
                page_number?: number;
              }>;

              if (newContextId) {
                setContextId(newContextId);
              }

              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.id === assistantMessage.id) {
                  if (msgText) {
                    last.content += msgText;
                  }
                  if (msgId) {
                    last.msgId = msgId;
                  }
                  if (index && index.length > 0) {
                    last.citations = index.map((item) => ({
                      document_id: item.document_id,
                      document_name: item.document_name,
                      page_number: item.page_number,
                      // We don't know exact source type here; default to 'uploaded'
                      source_type: 'uploaded',
                    }));
                  }
                }
                return updated;
              });
            } catch {
              // ignore partial / invalid JSON; next chunks will complete it
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content: 'Sorry, an error occurred. Please try again.',
        timestamp: new Date(),
        noAnswerFound: false,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const canProceed = files.length > 0 || googleDriveConnected;
  const totalUploaded = files.length;
  const totalDriveDocs = googleDriveDocs.length;

  return (
    <div className="flex h-full bg-gray-50">
      {/* Left Panel - Documents List OR Document Preview */}
      <div className="flex-1 bg-white border-r border-gray-200 flex flex-col overflow-hidden">
        {selectedDocument ? (
          // Document Preview View
          <>
            <div className="p-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setSelectedDocument(null)}
                  className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ArrowLeft className="w-4 h-4 text-gray-600" />
                </button>
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <Eye className="w-4 h-4 text-primary-600 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 text-sm truncate">{selectedDocument.name}</p>
                    <p className="text-xs text-gray-500">
                      {selectedDocument.type === 'google_drive' ? 'Google Drive' : 'Uploaded'}
                    </p>
                  </div>
                </div>
              </div>
              {selectedDocument.link && (
                <a
                  href={selectedDocument.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ExternalLink className="w-4 h-4 text-gray-600" />
                </a>
              )}
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {/* Document Preview */}
              {selectedDocument.type === 'uploaded' ? (
                <div className="h-full bg-gray-50 rounded-lg border border-gray-200 flex flex-col items-center justify-start p-4">
                  <button
                    onClick={() => loadDocumentPreviews(selectedDocument.id)}
                    className="mb-4 inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium"
                  >
                    <Eye className="w-4 h-4" />
                    Load Preview Pages
                  </button>
                  {previewImages.length > 0 ? (
                    <div className="w-full space-y-4 overflow-y-auto">
                      {previewImages.map((preview, idx) => (
                        <div key={idx} className="bg-white rounded-lg border border-gray-200 p-2">
                          <p className="text-xs text-gray-500 mb-1">
                            Page {preview.page_number ?? idx + 1}
                          </p>
                          <img
                            src={preview.url}
                            alt={`Preview page ${preview.page_number ?? idx + 1}`}
                            className="w-full rounded"
                          />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex-1 flex items-center justify-center flex-col text-center">
                      <FileText className="w-20 h-20 mx-auto mb-4 text-gray-400" />
                      <p className="text-sm font-medium text-gray-700 mb-2">Document Preview</p>
                      <p className="text-xs text-gray-500">
                        Click &quot;Load Preview Pages&quot; to view generated previews
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="h-full bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center">
                  <div className="text-center">
                    <FileText className="w-20 h-20 mx-auto mb-4 text-gray-400" />
                    <p className="text-sm font-medium text-gray-700 mb-2">Document Preview</p>
                    <p className="text-xs text-gray-500 mb-4">
                      Preview of {selectedDocument.name} will be displayed here
                    </p>
                    {selectedDocument.link && (
                      <a
                        href={selectedDocument.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium"
                      >
                        <ExternalLink className="w-4 h-4" />
                        Open in Google Drive
                      </a>
                    )}
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          // Documents List View
          <>
            <div className="p-4 border-b border-gray-200 flex-shrink-0">
              <h3 className="font-semibold text-gray-900 text-sm mb-4">Documents</h3>
              
              {/* Google Drive Section */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Cloud className="w-4 h-4 text-blue-600" />
                    <span className="text-sm font-medium text-gray-700">Google Drive</span>
                    {totalDriveDocs > 0 && (
                      <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                        {totalDriveDocs}
                      </span>
                    )}
                  </div>
                  {googleDriveConnected && (
                    <button
                      onClick={handleRefreshGoogleDrive}
                      disabled={isSyncing}
                      className="p-1 hover:bg-gray-100 rounded transition-colors"
                      title="Refresh Google Drive"
                    >
                      <RefreshCw className={`w-4 h-4 text-gray-600 ${isSyncing ? 'animate-spin' : ''}`} />
                    </button>
                  )}
                </div>
                {!googleDriveConnected ? (
                  <button
                    onClick={handleSyncGoogleDrive}
                    className="w-full px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium transition-colors flex items-center justify-center gap-2"
                  >
                    <Cloud className="w-4 h-4" />
                    Sync Google Drive
                  </button>
                ) : (
                  <div className="text-xs text-gray-500">Connected</div>
                )}
              </div>

              {/* Upload Section */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Uploaded Files</span>
                  {totalUploaded > 0 && (
                    <span className="px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded text-xs font-medium">
                      {totalUploaded}
                    </span>
                  )}
                </div>
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-lg p-4 text-center transition-all cursor-pointer ${
                    isDragging
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-300 bg-gray-50 hover:border-primary-400'
                  }`}
                >
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
                    onChange={(e) => handleFileSelect(e.target.files)}
                    className="hidden"
                    id="file-upload"
                  />
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <Upload className={`w-5 h-5 mx-auto mb-2 ${isDragging ? 'text-primary-600' : 'text-gray-400'}`} />
                    <p className="text-sm text-gray-600">Drop files or click to browse</p>
                    <p className="text-xs text-gray-500 mt-1">PDF, Word, Excel, Images</p>
                  </label>
                </div>
              </div>
            </div>

            {/* Document Lists */}
            <div className="flex-1 overflow-y-auto">
              {/* Google Drive Documents */}
              {googleDriveDocs.length > 0 && (
                <div className="px-4 pb-4 border-b border-gray-200">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2 px-4 pt-4">Google Drive</h4>
                  <div className="space-y-1">
                    {googleDriveDocs.map((doc) => (
                      <button
                        key={doc.id}
                        onClick={() => setSelectedDocument({ id: doc.id, name: doc.name, type: 'google_drive', link: doc.link })}
                        className="w-full text-left p-3 rounded-lg transition-colors flex items-center gap-3 hover:bg-gray-50"
                      >
                        <FileText className="w-5 h-5 text-blue-600 flex-shrink-0" />
                        <span className="text-sm text-gray-900 truncate flex-1">{doc.name}</span>
                        {doc.link && (
                          <a
                            href={doc.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="p-1.5 hover:bg-gray-200 rounded"
                          >
                            <ExternalLink className="w-4 h-4 text-gray-500" />
                          </a>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Uploaded Files */}
              {files.length > 0 && (
                <div className="px-4 py-4">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2 px-4">Uploaded Files</h4>
                  <div className="space-y-1">
                    {files.map((file) => (
                      <div
                        key={file.id}
                        className="p-3 rounded-lg transition-colors hover:bg-gray-50"
                      >
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => setSelectedDocument({ id: file.id, name: file.name, type: 'uploaded' })}
                            className="flex items-center gap-3 flex-1 min-w-0 text-left"
                          >
                            <FileText className="w-5 h-5 text-gray-600 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm text-gray-900 truncate">{file.name}</p>
                              <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                            </div>
                          </button>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            {file.status === 'success' && (
                              <CheckCircle className="w-5 h-5 text-green-600" />
                            )}
                            {file.status === 'uploading' && (
                              <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
                            )}
                            <button
                              onClick={() => removeFile(file.id)}
                              className="p-1.5 hover:bg-gray-200 rounded"
                            >
                              <X className="w-4 h-4 text-gray-400" />
                            </button>
                          </div>
                        </div>
                        {file.status === 'uploading' && (
                          <div className="mt-2 ml-11 w-[calc(100%-2.75rem)] bg-gray-200 rounded-full h-1.5">
                            <div
                              className="bg-primary-600 h-1.5 rounded-full transition-all"
                              style={{ width: `${file.progress}%` }}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {files.length === 0 && googleDriveDocs.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 p-8">
                  <FileText className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                  <p className="text-sm font-medium mb-1">No documents yet</p>
                  <p className="text-xs">Upload files or sync Google Drive to get started</p>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Right Panel - Chat (Fixed Width) */}
      <div className="w-96 bg-white border-l border-gray-200 flex flex-col overflow-hidden flex-shrink-0">
        {/* Chat Header */}
        {selectedDocument && (
          <div className="p-3 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <Eye className="w-4 h-4 text-primary-600 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-900 truncate">{selectedDocument.name}</p>
                <p className="text-xs text-gray-500">
                  {selectedDocument.type === 'google_drive' ? 'Google Drive' : 'Uploaded'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="p-3 bg-primary-50 rounded-xl mb-4">
                <FileText className="w-10 h-10 text-primary-600" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Start a conversation</h2>
              <p className="text-gray-600 mb-6 text-xs">
                {canProceed
                  ? selectedDocument
                    ? `Ask questions about ${selectedDocument.name}`
                    : 'Ask questions about all your medical documents'
                  : 'Upload documents or sync Google Drive to get started'}
              </p>
              {canProceed && (
                <div className="w-full bg-gray-50 rounded-lg p-3 border border-gray-200">
                  <p className="text-xs font-semibold text-gray-700 mb-2">Example questions:</p>
                  <div className="space-y-1.5 text-left">
                    <div className="p-2 bg-white rounded-lg border border-gray-200 hover:border-primary-300 transition-colors cursor-pointer"
                      onClick={() => setInput("What are the key findings in the patient report?")}
                    >
                      <p className="text-xs text-gray-700">"What are the key findings in the patient report?"</p>
                    </div>
                    <div className="p-2 bg-white rounded-lg border border-gray-200 hover:border-primary-300 transition-colors cursor-pointer"
                      onClick={() => setInput("Summarize the clinical data from the documents")}
                    >
                      <p className="text-xs text-gray-700">"Summarize the clinical data from the documents"</p>
                    </div>
                    <div className="p-2 bg-white rounded-lg border border-gray-200 hover:border-primary-300 transition-colors cursor-pointer"
                      onClick={() => setInput("What medications are mentioned in the files?")}
                    >
                      <p className="text-xs text-gray-700">"What medications are mentioned in the files?"</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[85%] ${message.role === 'user' ? 'flex flex-col items-end' : ''}`}>
                <div
                  className={`rounded-lg px-3 py-2 shadow-sm ${
                    message.role === 'user'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed text-xs">
                    {getDisplayContent(message.content)}
                  </p>
                </div>

                {message.citations && message.citations.length > 0 && (
                  <div className="mt-1.5 space-y-1 w-full">
                    <p className="text-xs font-semibold text-gray-600 mb-1">Sources:</p>
                    {message.citations.map((citation, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={async () => {
                          if (!message.msgId || !citation.document_id || !citation.page_number) return;
                          try {
                            const result = await api.getChatHighlights({
                              document_id: citation.document_id,
                              page_number: citation.page_number,
                              msg_id: message.msgId as string,
                            });
                            if (result?.presigned_url) {
                              window.open(result.presigned_url, '_blank', 'noopener,noreferrer');
                            }
                          } catch (err) {
                            console.error('Error fetching chat highlights:', err);
                          }
                        }}
                        className="w-full text-left bg-blue-50 border border-blue-200 rounded-lg p-2 text-xs shadow-sm hover:bg-blue-100 hover:border-blue-300 transition-colors cursor-pointer"
                      >
                        <div className="flex items-start justify-between mb-1">
                          <div className="flex items-center gap-1.5 flex-1 min-w-0">
                            <FileText className="w-3 h-3 text-blue-600 flex-shrink-0" />
                            <span className="font-medium text-gray-900 truncate text-xs">
                              {citation.document_name || citation.document_id}
                            </span>
                            {citation.source_type === 'google_drive' && (
                              <span className="px-1 py-0.5 bg-green-100 text-green-700 rounded text-xs flex-shrink-0">
                                Drive
                              </span>
                            )}
                            {citation.page_number && (
                              <span className="px-1 py-0.5 bg-gray-100 text-gray-700 rounded text-xs flex-shrink-0">
                                Page {citation.page_number}
                              </span>
                            )}
                          </div>
                          {citation.google_drive_link && (
                            <a
                              href={citation.google_drive_link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-blue-600 hover:text-blue-700 ml-1 flex-shrink-0"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                        {citation.chunk_text && (
                          <p className="text-gray-600 text-xs mt-1 italic leading-relaxed">
                            "{citation.chunk_text.substring(0, 100)}..."
                          </p>
                        )}
                      </button>
                    ))}
                  </div>
                )}

                {message.noAnswerFound && (
                  <div className="mt-1.5 bg-yellow-50 border border-yellow-200 rounded-lg p-2 flex items-start gap-2 shadow-sm">
                    <AlertCircle className="w-3.5 h-3.5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-yellow-800">
                        Information Not Available
                      </p>
                      <p className="text-xs text-yellow-700 mt-0.5">
                        The requested information could not be found in the documents.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg px-3 py-2 flex items-center gap-2 shadow-sm">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-gray-600" />
                <span className="text-xs text-gray-600">Thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 bg-white p-3 flex-shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex gap-2 items-end"
          >
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder={
                  canProceed
                    ? selectedDocument
                      ? `Ask about ${selectedDocument.name}...`
                      : 'Ask questions about all your documents...'
                    : 'Upload documents or sync Google Drive first...'
                }
                disabled={isLoading || !canProceed}
                rows={1}
                className="w-full px-3 py-2 pr-20 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-50 disabled:cursor-not-allowed text-gray-900 placeholder-gray-400 text-xs resize-none max-h-40 leading-relaxed"
              />
              <button
                type="button"
                onClick={handleRewritePrompt}
                disabled={isRewriting || !input.trim()}
                className="absolute right-1 top-1/2 -translate-y-1/2 px-2 py-1 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 text-xs text-gray-700 font-medium"
                title="Enhance prompt with AI"
              >
                {isRewriting ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Sparkles className="w-3 h-3" />
                )}
                <span className="hidden sm:inline">Enhance</span>
              </button>
            </div>
            <button
              type="submit"
              disabled={isLoading || !input.trim() || !canProceed}
              className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-1 font-medium shadow-sm hover:shadow transition-all"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
