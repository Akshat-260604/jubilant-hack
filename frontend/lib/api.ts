import axios from 'axios';

// Base URLs
// By default, both chat and document APIs point to NEXT_PUBLIC_API_URL.
// You can override them separately if chat and document backends run on different hosts/ports.
const DEFAULT_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const CHAT_API_URL = process.env.NEXT_PUBLIC_CHAT_API_URL || DEFAULT_API_URL;
const DOC_API_URL = process.env.NEXT_PUBLIC_DOC_API_URL || DEFAULT_API_URL;

const CHAT_BASE_URL = `${CHAT_API_URL}/api/v1`;
const DOC_BASE_URL = `${DOC_API_URL}/api/v1`;

const chatApiClient = axios.create({
  baseURL: CHAT_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

const docApiClient = axios.create({
  baseURL: DOC_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ChatRequest {
  prompt: string;
  document_ids: string[];
  context_id?: string;
}

export interface SmartChatRequest {
  prompt: string;
  userId: string;
  context_id?: string;
  max_documents?: number;
  relevance_threshold?: number;
}

export interface TranslationRequest {
  text: string;
  target_lang: string;
}

export interface RephraseRequest {
  text: string;
  tone: string;
}

export interface RewriteRequest {
  user_prompt: string;
}

export interface ChatHighlightsRequest {
  document_id: string;
  page_number: number;
  msg_id: string;
}

export interface SearchPreviewRequest {
  query: string;
  userId: string;
  max_results?: number;
  score_threshold?: number;
}

export interface DocumentUploadRequest {
  file: File;
  userId: string;
}

export interface ReportGenerationRequest {
  userId: string;
  sections: string[];
  instructions?: string;
  // Optional: when provided and scope === 'single', backend targets this document
  documentId?: string;
  // 'single' (default) or 'combined'
  scope?: 'single' | 'combined';
}

export interface Citation {
  document_id: string;
  document_name?: string;
  chunk_text?: string;
  page_number?: number;
  source_type?: 'uploaded' | 'google_drive';
  google_drive_link?: string;
  score?: number;
}

export interface ChatResponse {
  content: string;
  citations?: Citation[];
  no_answer_found?: boolean;
  context_id?: string;
}

export const api = {
  // Health check
  healthCheck: async () => {
    const response = await chatApiClient.get('/health_check');
    return response.data;
  },

  // Chat endpoints
  chat: async (request: ChatRequest) => {
    const response = await fetch(`${CHAT_BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return response;
  },

  smartChat: async (request: SmartChatRequest) => {
    const response = await fetch(`${CHAT_BASE_URL}/chat/smart`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return response;
  },

  // Translation
  translate: async (request: TranslationRequest) => {
    const response = await chatApiClient.post('/translate', request);
    return response.data;
  },

  getLanguages: async () => {
    const response = await chatApiClient.get('/list_of_languages');
    return response.data;
  },

  // Rephrase
  rephrase: async (request: RephraseRequest) => {
    const response = await chatApiClient.post('/rephrase', request);
    return response.data;
  },

  // Rewrite
  rewrite: async (request: RewriteRequest) => {
    const response = await chatApiClient.post('/rewrite', request);
    return response.data;
  },

  // Chat highlights
  getChatHighlights: async (request: ChatHighlightsRequest) => {
    const response = await chatApiClient.post('/chat-highlights', request);
    return response.data;
  },

  // Search
  searchPreview: async (request: SearchPreviewRequest) => {
    const response = await chatApiClient.post('/search/preview', request);
    return response.data;
  },

  unifiedSearch: async (request: SearchPreviewRequest) => {
    const response = await chatApiClient.post('/search/unified', request);
    return response.data;
  },

  searchHealth: async () => {
    const response = await chatApiClient.get('/search/health');
    return response.data;
  },

  // Document Upload
  uploadDocument: async (request: DocumentUploadRequest) => {
    const formData = new FormData();
    formData.append('file', request.file);
    formData.append('userId', request.userId);
    
    const response = await docApiClient.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Google Drive
  // Uses src12 Google Drive endpoints
  googleDriveSetup: async () => {
    // Maps to: POST /google-drive/setup
    const response = await docApiClient.post('/google-drive/setup');
    return response.data;
  },

  getGoogleDriveDocuments: async () => {
    // Maps to: GET /google-drive/documents
    const response = await docApiClient.get('/google-drive/documents');
    return response.data;
  },

  syncGoogleDriveDocuments: async (userId: string, force_resync = false) => {
    // Maps to: POST /google-drive/sync
    const response = await docApiClient.post('/google-drive/sync', {
      userId,
      force_resync,
    });
    return response.data;
  },

  getGoogleDriveDocumentContent: async (userId: string, file_id: string) => {
    // Maps to: POST /google-drive/document/content
    const response = await docApiClient.post('/google-drive/document/content', {
      userId,
      file_id,
    });
    return response.data;
  },

  getGoogleDriveDocumentLink: async (file_id: string) => {
    // Maps to: GET /google-drive/document/{file_id}/link
    const response = await docApiClient.get(`/google-drive/document/${file_id}/link`);
    return response.data;
  },

  // Report Generation
  generateReport: async (request: ReportGenerationRequest) => {
    const response = await docApiClient.post('/reports/generate', request);
    return response.data;
  },

  downloadReportPDF: async (reportId: string) => {
    const response = await docApiClient.get(`/reports/${reportId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Healthcare Chat (with citations)
  healthcareChat: async (request: SmartChatRequest) => {
    const response = await fetch(`${CHAT_BASE_URL}/chat/smart`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return response;
  },

  // ---- src12 document & upload utilities ----

  getPresignedUploadUrl: async (userId: string, fileName: string) => {
    // Maps to: POST /get-presigned-upload-url
    const response = await docApiClient.post('/get-presigned-upload-url', {
      userId,
      fileName,
    });
    return response.data;
  },

  triggerDocumentProcessing: async (userId: string, uuid: string) => {
    // Maps to: POST /trigger-document-processing
    const response = await docApiClient.post('/trigger-document-processing', {
      userId,
      uuid,
    });
    return response.data;
  },

  listMySelfUploadedDocuments: async (userId: string) => {
    // Maps to: POST /list-my-self-uploaded-documents
    const response = await docApiClient.post('/list-my-self-uploaded-documents', {
      userId,
    });
    return response.data;
  },

  getDocumentPreviews: async (document_id: string, user_id: string) => {
    // Maps to: POST /get-document-previews
    const response = await docApiClient.post('/get-document-previews', {
      document_id,
      user_id,
    });
    return response.data;
  },
};

export default api;

