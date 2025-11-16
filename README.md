## Healthcare AI Assistant – Hackathon Workspace

This repository contains a full-stack prototype of a **Healthcare AI Assistant** that lets you:

- **Upload & process medical documents** (PDFs, etc.) and index them into Qdrant + MongoDB  
- **Chat with documents** (including Google Drive content) with sources and page-level highlights  
- **Generate structured medical reports** from one or many documents with sections like *Introduction, Clinical Findings, Patient Tables, Graphs & Charts, Summary*.

The implementation is split into:

- `unified-backend/` – FastAPI backend exposing all endpoints used by the frontend  
- `frontend/` – Next.js 14 + TypeScript UI  
- `src12/` and `chat-fun/` – original microservices the unified backend was derived from (kept for reference)

---

## 1. Prerequisites

- Python **3.9** (for the backend virtualenv)
- Node.js **18+** and **npm**
- Running instances of:
  - **MongoDB** (document + metadata storage)
  - **Qdrant** (vector DB)
- **AWS S3** bucket & credentials (for document storage, previews, tables, highlights)
- **OpenAI API key** (for RAG, smart chat, report summaries, findings, etc.)

---

## 2. Backend – `unified-backend`

The unified backend is a copy of `src12` plus all working chat endpoints and utilities from `chat-fun`.  
It exposes *all* endpoints the frontend calls under `/api/v1` – chat, search, upload, Google Drive, highlights, and report generation.

### 2.1 Environment

From the repo root:

```bash
cd unified-backend

# If you already have a working .env in src12, reuse it:
cp ../src12/.env .env
```

At minimum, `.env` must define:

- `DOCUMENT_DB_CONNECTION_STRING` – MongoDB connection URI  
- `QDRANT_HOST_URL` – Qdrant endpoint  
- `OPENAI_API_KEY` – OpenAI key  
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `BUCKET_NAME` – S3 access (or via `aws_settings` in config)

### 2.2 Install & run

```bash
cd /Users/akshat-bynd/Desktop/hackathon/unified-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the FastAPI app on port 8004
uvicorn main:app --host 0.0.0.0 --port 8004
```

The API will be available at `http://localhost:8004/api/v1`.

Key routes (non‑exhaustive):

- **Health**: `GET /api/v1/health_check`
- **Chat & search**: `/chat`, `/chat/smart`, `/chat-highlights`, `/search/preview`, `/search/unified`
- **Upload & processing**: `/documents/upload`, `/get-presigned-upload-url`, `/trigger-document-processing`, `/list-my-self-uploaded-documents`, `/get-document-previews`
- **Google Drive**: `/google-drive/setup`, `/google-drive/documents`, `/google-drive/sync`, `/google-drive/document/content`, `/google-drive/document/{file_id}/link`
- **Reports**: `POST /reports/generate`, `GET /reports/{id}/download`

---

## 3. Frontend – `frontend`

The frontend is a Next.js 14 app that provides:

- A **Unified Chat** interface (upload + Drive + smart RAG chat with citations & highlights)
- A **Report Generator** that:
  - Lets the user choose sections
  - Can target a **single selected document** or **aggregate all processed documents**
  - Uses exact extracted content for tables/figures/text and only uses the LLM for summaries

### 3.1 Install dependencies

```bash
cd /Users/akshat-bynd/Desktop/hackathon/frontend
npm install
```

### 3.2 Environment

Create `.env.local` (if not already present) and point it to the unified backend:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8004
NEXT_PUBLIC_CHAT_API_URL=http://localhost:8004
NEXT_PUBLIC_DOC_API_URL=http://localhost:8004
```

### 3.3 Run the dev server

```bash
cd /Users/akshat-bynd/Desktop/hackathon/frontend
npm run dev
```

Open `http://localhost:3000` in the browser.

---

## 4. Typical Flow

1. **Start backend** (`unified-backend` on port 8004) and ensure MongoDB, Qdrant, S3, and OpenAI env vars are configured.
2. **Start frontend** (`frontend` on port 3000).
3. In the UI:
   - Upload PDFs in the **Chat / Documents** view, or sync Google Drive.
   - Wait for processing to complete (documents appear as *Completed*).
   - Use **Unified Chat** to ask questions; click citations to open page highlights.
   - Go to **Reports**:
     - Choose **Selected document only** or **All uploaded documents**.
     - Select sections (Introduction, Clinical Findings, Patient Tables, Graphs & Charts, Summary).
     - Optionally add instructions.
     - Generate a structured medical report built from your documents.

---

## 5. Notes

- `src12/` and `chat-fun/` are legacy microservices; all production‑facing endpoints that the frontend uses are now exposed via `unified-backend/`.
- The project assumes you have access to the necessary cloud services (MongoDB, Qdrant, AWS S3, OpenAI). These are not provisioned automatically.
- For any changes to shared models or services, update `unified-backend` first; `src12` / `chat-fun` can be kept as references. 


