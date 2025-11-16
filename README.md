# Healthcare AI Assistant – Comprehensive Documentation

A full-stack **Healthcare AI Assistant** prototype that enables intelligent document processing, semantic search, and AI-powered medical report generation. This system allows healthcare professionals to upload medical documents, sync with Google Drive, chat with documents using RAG (Retrieval Augmented Generation), and generate structured medical reports.

> **Note**: Screenshots and images are referenced in this README. To view them, ensure the image files are present in the `docs/images/` directory. See the [Images Setup](#images-setup) section below.

---

## 📋 Table of Contents

1. [Features](#features)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Installation & Setup](#installation--setup)
5. [Images Setup](#images-setup)
6. [How It Works](#how-it-works)
7. [API Endpoints](#api-endpoints)
8. [Usage Guide](#usage-guide)
9. [Disclaimer](#disclaimer)

---

## ✨ Features

### Core Capabilities

- **📄 Document Upload & Processing**: Upload PDF medical documents that are automatically processed, chunked, and indexed
- **🔍 Semantic Search**: Vector-based semantic search across all documents using embeddings
- **💬 Intelligent Chat**: Chat with specific documents or across all documents with automatic source discovery
- **☁️ Google Drive Integration**: Sync and chat with documents directly from Google Drive
- **📊 Report Generation**: Generate structured medical reports with customizable sections
- **🎯 Source Highlighting**: View exact page-level citations and highlights from source documents
- **🌐 Multi-language Support**: Translation and language processing capabilities
- **📝 Document Previews**: View processed documents with extracted tables, images, and outlines

### Application Interface

![Main Interface](docs/images/Screenshot%202025-11-16%20at%201.19.14%20PM.png)

*Main application interface showing document management, Google Drive integration, and chat functionality*

---

## 🏗️ Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 14)                    │
│  - Unified Chat Interface                                  │
│  - Document Upload & Management                            │
│  - Report Generator                                        │
│  - Google Drive Integration UI                             │
└──────────────────────┬────────────────────────────────────┘
                       │ HTTP/REST API
┌──────────────────────▼────────────────────────────────────┐
│              Backend (FastAPI)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Chat & RAG   │  │ Document     │  │ Google Drive │   │
│  │ Services     │  │ Processing   │  │ Service      │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└──────┬──────────┬──────────┬──────────┬──────────┬──────┘
       │          │          │          │          │
┌──────▼──┐ ┌─────▼──┐ ┌─────▼──┐ ┌─────▼──┐ ┌─────▼──┐
│ MongoDB │ │ Qdrant │ │ AWS S3 │ │ OpenAI │ │ Ollama │
│ (Metadata│ │(Vectors)│ │(Storage)│ │ (LLM)  │ │(Embed) │
└─────────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

### Component Breakdown

#### **Frontend (`frontend/`)**
- **Framework**: Next.js 14 with TypeScript
- **UI Components**: 
  - `UnifiedChatInterface.tsx` - Main chat interface with document selection
  - `DocumentUpload.tsx` - File upload and management
  - `ReportGenerator.tsx` - Medical report generation UI
  - `SearchView.tsx` - Document search interface
- **State Management**: React hooks and context
- **API Client**: Centralized API client in `lib/api.ts`

#### **Backend (`unified-backend/`)**
- **Framework**: FastAPI (Python 3.9)
- **Key Services**:
  - `document_encoder.py` - Document processing and chunking
  - `qdrant_host.py` - Vector database operations
  - `ollama_host.py` - Embedding generation (using Ollama)
  - `s3host.py` - AWS S3 document storage
  - `google_drive_service.py` - Google Drive integration
  - `unified_search.py` - Cross-source semantic search
- **Processing Pipeline**:
  - Text extraction from PDFs
  - Chunking and embedding generation
  - Vector storage in Qdrant
  - Metadata storage in MongoDB
  - Preview image generation
  - Table and image extraction

### Data Flow

#### Document Processing Flow
```
PDF Upload → S3 Storage → Text Extraction → Chunking → Embedding Generation 
→ Qdrant (Vector Store) → MongoDB (Metadata) → Processing Complete
```

#### Chat Flow
```
User Query → Query Embedding → Vector Search (Qdrant) → Context Retrieval 
→ LLM (OpenAI) → Streamed Response → Frontend Display
```

#### Embedding Generation
- **Model**: Uses Ollama for generating embeddings (768-dimensional vectors)
- **Chunking Strategy**: Documents are split into optimized chunks with overlap for context preservation
- **Storage**: Embeddings stored in Qdrant with cosine similarity for retrieval
- **Metadata**: Each embedding chunk includes:
  - Original text
  - Document ID
  - Chunk index
  - Source information

---

## 📦 Prerequisites

### Required Software

- **Python 3.9+** (for backend)
- **Node.js 18+** and **npm** (for frontend)
- **Git** (for cloning the repository)

### Required Services

You need running instances of:

1. **MongoDB** - Document metadata and conversation storage
   - Local installation or MongoDB Atlas account
   - Connection string required

2. **Qdrant** - Vector database for embeddings
   - Local installation or Qdrant Cloud account
   - Host URL required

3. **AWS S3** - Document storage
   - AWS account with S3 bucket
   - Access key ID and secret access key required
   - Bucket name required

4. **OpenAI API** - For LLM responses and advanced processing
   - OpenAI API key with sufficient credits
   - Used for: RAG responses, report generation, summaries

5. **Ollama** (Optional but Recommended) - For local embeddings
   - Local Ollama installation
   - Used for generating document embeddings

6. **Google Cloud** (For Google Drive Integration)
   - Google Cloud project with Drive API enabled
   - Service account credentials JSON file
   - Place in `unified-backend/credentials/service_account.json`

---

## 🚀 Installation & Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/Akshat-260604/jubilant-hack.git
cd jubilant-hack
```

### Step 2: Backend Setup

#### 2.1 Navigate to Backend Directory

```bash
cd unified-backend
```

#### 2.2 Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 2.3 Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2.4 Configure Environment Variables

Create a `.env` file in the `unified-backend/` directory:

```bash
# MongoDB Configuration
DOCUMENT_DB_CONNECTION_STRING=mongodb://localhost:27017/healthcare_ai
# Or for MongoDB Atlas, use your connection string from MongoDB Atlas dashboard

# Qdrant Configuration
QDRANT_HOST_URL=http://localhost:6333
# Or for Qdrant Cloud:
# QDRANT_HOST_URL=https://your-cluster.qdrant.io

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
BUCKET_NAME=your-bucket-name
AWS_REGION=us-east-1

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key

# Ollama Configuration (for embeddings)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text  # or your preferred embedding model

# Application Configuration
API_V1_STR=/api/v1
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

#### 2.5 Google Drive Setup (Optional)

1. Create a Google Cloud Project
2. Enable Google Drive API
3. Create a Service Account
4. Download the service account JSON key
5. Place it at: `unified-backend/credentials/service_account.json`

#### 2.6 Start the Backend Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8004 --reload
```

The API will be available at `http://localhost:8004`

API Documentation: `http://localhost:8004/api/v1/vectoriser/openapi.json`

### Step 3: Frontend Setup

#### 3.1 Navigate to Frontend Directory

```bash
cd ../frontend
```

#### 3.2 Install Dependencies

```bash
npm install
```

#### 3.3 Configure Environment Variables

Create a `.env.local` file in the `frontend/` directory:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8004
NEXT_PUBLIC_CHAT_API_URL=http://localhost:8004
NEXT_PUBLIC_DOC_API_URL=http://localhost:8004
```

#### 3.4 Start the Development Server

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Step 4: Images Setup (Optional)

To view screenshots in this README, add the following image files to the `docs/images/` directory:

- `main-interface.png` - Main application interface
- `document-preview.png` - Document preview interface
- `chat-interface.png` - Chat interface with document preview
- `source-highlighting.png` - Source highlighting example
- `report-generator.png` - Report generation interface
- `document-management.png` - Document management interface

You can add these images by:
1. Taking screenshots of your application
2. Saving them with the exact filenames listed above
3. Placing them in the `docs/images/` directory
4. Committing and pushing them to the repository

```bash
# Add images to the repository
git add docs/images/*.png
git commit -m "Add application screenshots"
git push
```

### Step 5: Verify Installation

1. **Backend Health Check**: Visit `http://localhost:8004/api/v1/health_check`
   - Should return: `{"statusCode": 200, "message": "Server is running successfully"}`

2. **Frontend**: Open `http://localhost:3000` in your browser
   - Should load without errors

---

## 🔧 How It Works

### Document Processing & Embedding Generation

#### 1. Document Upload
When a PDF is uploaded:
- File is stored in AWS S3
- Document metadata is saved to MongoDB
- Processing status is set to "processing"

#### 2. Text Extraction
- PDF content is extracted using `pdfplumber` and `PyMuPDF`
- Text is cleaned and structured
- Document structure (headings, paragraphs) is preserved

#### 3. Chunking Strategy
Documents are split into optimized chunks:
- **Chunk Size**: Configurable (typically 500-1000 tokens)
- **Overlap**: Chunks overlap by ~20% to preserve context
- **Marking**: Each chunk is marked with metadata (page number, section, etc.)

#### 4. Embedding Generation
- Each chunk is converted to a 768-dimensional vector using Ollama's embedding model
- Embeddings capture semantic meaning of the text
- Process is parallelized for efficiency

#### 5. Vector Storage
- Embeddings are stored in Qdrant vector database
- Each vector point includes:
  - **Vector**: 768-dimensional embedding
  - **Payload**: 
    - Original text chunk
    - Document ID
    - Chunk index
    - Page number (if available)
- Collection name: `creator`

#### 6. Additional Processing
In parallel, the system also:
- Generates preview images for each page
- Extracts tables and images
- Creates document outline/summary
- Stores all metadata in MongoDB

![Document Preview](docs/images/Screenshot%202025-11-16%20at%201.27.52%20PM.png)

*Document preview interface showing uploaded documents with page navigation*

### Chat with Documents

#### Single Document Chat
When you select a specific document and chat:

1. **Query Processing**: Your question is converted to an embedding
2. **Vector Search**: System searches Qdrant for similar chunks from the selected document
3. **Context Retrieval**: Top-k most relevant chunks are retrieved (typically 5-10)
4. **Context Assembly**: Retrieved chunks are assembled with metadata
5. **LLM Processing**: OpenAI GPT model processes the query with context
6. **Response Streaming**: Response is streamed back with citations
7. **Source Highlighting**: Citations include page numbers and exact locations

![Chat Interface](docs/images/Screenshot%202025-11-16%20at%201.28.40%20PM.png)

*Split-screen interface showing document preview on the left and AI chat conversation on the right with source citations*

![Source Highlighting](docs/images/Screenshot%202025-11-16%20at%201.29.37%20PM.png)

*Document page with highlighted sections showing exact source locations for chat responses*

**Endpoint**: `POST /api/v1/chat`
```json
{
  "prompt": "What are the key findings?",
  "document_ids": ["doc_id_1"],
  "userId": "user123",
  "context_id": "optional_conversation_id"
}
```

#### Smart Chat (Auto-Discovery)
When you chat without selecting a document:

1. **Query Embedding**: Your question is embedded
2. **Cross-Source Search**: System searches both:
   - Uploaded documents (from S3)
   - Google Drive documents
3. **Relevance Scoring**: Documents are ranked by relevance
4. **Top-K Selection**: Most relevant documents are selected (default: 5)
5. **Mixed Context**: Context is retrieved from multiple sources
6. **Unified Response**: LLM generates response citing multiple sources

**Endpoint**: `POST /api/v1/chat/smart`
```json
{
  "prompt": "What medications are mentioned?",
  "userId": "user123",
  "max_documents": 5,
  "relevance_threshold": 0.6
}
```

### Google Drive Integration

#### Setup Process
1. **Authentication**: User authenticates with Google Drive via OAuth
2. **Document Discovery**: System scans Google Drive for supported files (PDFs)
3. **Sync**: Documents are synced and processed similar to uploaded files
4. **Indexing**: Synced documents are embedded and indexed in Qdrant

#### How It Works
- Google Drive documents are accessed via Google Drive API
- Documents are downloaded and processed like uploaded files
- Metadata includes Google Drive file ID for future sync
- Documents can be queried alongside uploaded documents

**Endpoints**:
- `POST /api/v1/google-drive/setup` - Initialize Google Drive connection
- `GET /api/v1/google-drive/documents` - List available documents
- `POST /api/v1/google-drive/sync` - Sync documents from Drive
- `GET /api/v1/google-drive/document/{file_id}/content` - Get document content

### Report Generation

The system can generate structured medical reports from one or multiple documents:

#### Report Sections
- **Introduction**: Overview of the report
- **Clinical Findings**: Key clinical observations
- **Patient Tables**: Extracted patient data tables
- **Graphs & Charts**: Visual data representations
- **Summary**: Executive summary

#### Generation Process
1. **Document Selection**: User selects single document or "all documents"
2. **Section Selection**: User chooses which sections to include
3. **Content Extraction**: System extracts relevant content from documents
4. **LLM Processing**: OpenAI generates structured content for each section
5. **Report Assembly**: Sections are combined into a formatted report
6. **Download**: Report is available for download as PDF/DOCX

![Report Generator](docs/images/Screenshot%202025-11-16%20at%201.29.45%20PM.png)

*Report generation interface allowing users to select documents, choose report sections, and customize report content*

**Endpoint**: `POST /api/v1/reports/generate`
```json
{
  "userId": "user123",
  "document_ids": ["doc1", "doc2"],  // or null for all documents
  "sections": ["introduction", "clinical_findings", "summary"],
  "instructions": "Focus on cardiovascular findings"
}
```

---

## 📡 API Endpoints

### Health & Status

- `GET /api/v1/health_check` - Server health status

### Document Management

- `POST /api/v1/documents/upload` - Upload a document
- `GET /api/v1/get-presigned-upload-url` - Get S3 presigned URL for upload
- `POST /api/v1/trigger-document-processing` - Trigger document processing
- `GET /api/v1/list-my-self-uploaded-documents` - List user's documents
- `GET /api/v1/get-document-previews` - Get document previews
- `GET /api/v1/get-preview/{document_id}` - Get specific document preview

### Chat & Search

- `POST /api/v1/chat` - Chat with specific document(s)
- `POST /api/v1/chat/smart` - Smart chat with auto-document discovery
- `POST /api/v1/chat-highlights` - Get chat response with source highlights
- `GET /api/v1/search/preview` - Preview search results
- `POST /api/v1/search/unified` - Unified search across all sources

### Google Drive

- `POST /api/v1/google-drive/setup` - Setup Google Drive integration
- `GET /api/v1/google-drive/documents` - List Google Drive documents
- `POST /api/v1/google-drive/sync` - Sync documents from Google Drive
- `GET /api/v1/google-drive/document/{file_id}/content` - Get Drive document content
- `GET /api/v1/google-drive/document/{file_id}/link` - Get Drive document link

### Reports

- `POST /api/v1/reports/generate` - Generate a medical report
- `GET /api/v1/reports/{report_id}/download` - Download generated report

### Additional Features

- `POST /api/v1/translation` - Translate text
- `POST /api/v1/rephraser` - Rephrase text
- `POST /api/v1/ai-rewrite` - AI-powered text rewriting
- `GET /api/v1/get-summary/{document_id}` - Get document summary
- `GET /api/v1/get-tables/{document_id}` - Get extracted tables
- `GET /api/v1/get-images/{document_id}` - Get extracted images
- `GET /api/v1/get-prompt-library` - Get available prompt templates
- `POST /api/v1/content-findings` - Extract content findings

---

## 📖 Usage Guide

### Basic Workflow

1. **Start Services**
   ```bash
   # Terminal 1: Start Backend
   cd unified-backend
   source venv/bin/activate
   uvicorn main:app --host 0.0.0.0 --port 8004 --reload
   
   # Terminal 2: Start Frontend
   cd frontend
   npm run dev
   ```

2. **Upload Documents**
   - Navigate to `http://localhost:3000`
   - Go to "Documents" or "Upload" section
   - Upload PDF medical documents
   - Wait for processing to complete (status will show "Completed")

   ![Document Management](docs/images/Screenshot%202025-11-16%20at%201.29.56%20PM.png)

   *Document management interface showing uploaded files and Google Drive integration*

3. **Chat with Documents**
   - **Single Document**: Select a document from the list, then type your question
   - **All Documents**: Don't select any document, just type your question (smart chat)
   - View citations by clicking on highlighted text in responses

4. **Google Drive Sync**
   - Click "Google Drive" in the sidebar
   - Authenticate with Google
   - Click "Sync" to import documents
   - Synced documents appear in your document list

5. **Generate Reports**
   - Navigate to "Reports" section
   - Select document(s) or choose "All Documents"
   - Select report sections
   - Add optional instructions
   - Click "Generate Report"
   - Download when ready

### Advanced Usage

#### Custom Embedding Models
Edit `unified-backend/services/ollama_host.py` to change the embedding model:
```python
EMBEDDING_MODEL = "nomic-embed-text"  # Change to your preferred model
```

#### Adjusting Chunk Size
Edit `unified-backend/utils/document_handling/chunker.py` to modify chunking parameters:
```python
CHUNK_SIZE = 1000  # Adjust chunk size
CHUNK_OVERLAP = 200  # Adjust overlap
```

#### Customizing RAG Parameters
In chat endpoints, adjust:
- `max_documents`: Number of documents to retrieve
- `relevance_threshold`: Minimum similarity score (0.0-1.0)
- `max_chunks`: Maximum context chunks to use

---

## ⚠️ Disclaimer

### Current Status

This is a **hackathon prototype** with the following status:

#### ✅ **Fully Implemented & Working**
- Document upload and processing pipeline
- Embedding generation and vector storage
- Single document chat functionality
- Google Drive integration and sync
- Report generation endpoints
- All API endpoints are implemented and functional
- Frontend UI components for all major features
- Source highlighting and citation system

#### ⚠️ **Partially Implemented / Needs Testing**
- Some edge cases in document processing may need refinement
- Error handling in some scenarios could be more robust
- Google Drive OAuth flow may need additional testing
- Report generation UI integration may need polish

#### 🚧 **Known Limitations**
- **Time Constraints**: Due to hackathon time limitations, some features were prioritized over others
- **Error Handling**: Some error scenarios may not have comprehensive handling
- **UI Polish**: Some UI components may need additional styling and user experience improvements
- **Testing**: Comprehensive testing was not completed due to time constraints
- **Documentation**: Some internal documentation may be incomplete

### What Works

All the **core endpoints are implemented and functional**. The system architecture is complete, and the following will work:

1. **Document Processing**: Upload, chunk, embed, and index documents ✅
2. **Vector Search**: Semantic search across documents ✅
3. **Chat with Documents**: Both single-doc and smart chat ✅
4. **Google Drive Sync**: Integration endpoints are ready ✅
5. **Report Generation**: Backend endpoints are complete ✅
6. **Embedding Pipeline**: Full embedding generation and storage ✅

### What May Need Work

- **Frontend Integration**: Some frontend components may need additional integration work
- **Error Messages**: User-facing error messages may need refinement
- **Performance**: Large document processing may need optimization
- **Authentication**: User authentication system may need implementation
- **Deployment**: Production deployment configuration may need setup

### Development Notes

- All backend endpoints follow RESTful conventions
- Code is modular and well-structured for easy extension
- Database schemas are defined in `models/` directory
- Service layer abstracts external dependencies
- The codebase is ready for further development and refinement

### Contributing

If you'd like to contribute or continue development:
1. All endpoints are documented in the code
2. Service layer is abstracted for easy modification
3. Database models are clearly defined
4. Frontend components are modular and reusable

---

## 📝 Notes

- The project uses **Ollama** for embeddings (can be replaced with OpenAI embeddings)
- **Qdrant** is used for vector storage (can be replaced with other vector DBs)
- **MongoDB** stores metadata and conversation history
- **AWS S3** stores original documents and generated assets
- **OpenAI** powers the LLM responses and report generation

---

## 🔗 Links

- **Repository**: https://github.com/Akshat-260604/jubilant-hack
- **API Docs**: `http://localhost:8004/api/v1/vectoriser/openapi.json` (when server is running)

---

## 📄 License

This project was developed for a hackathon. Please refer to the repository for license information.

---

**Built with ❤️ for Healthcare AI Innovation**
