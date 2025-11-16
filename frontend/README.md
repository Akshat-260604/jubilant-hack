# Healthcare AI Assistant Frontend

A modern Next.js frontend for the Healthcare AI Assistant that helps healthcare organizations manage and make sense of large collections of medical documents.

## Features

### Part 1 - Q&A / Conversational Interface
- **Chat with Documents**: Ask questions about uploaded documents and Google Drive files
- **Citations & References**: Every answer includes citations showing:
  - Which document(s) were used
  - Which chunks/portions map to those documents
  - Clickable links to Google Drive files
- **Multi-turn Conversations**: Maintains context across conversation turns
- **No Hallucinations**: Explicitly states when information is not available

### Part 2 - Report Generation
- **Structured Medical Reports**: Generate reports with customizable sections:
  - Introduction
  - Clinical Findings
  - Patient Tables
  - Graphs & Charts
  - Summary
- **Exact Data Extraction**: Preserves tables, charts, and figures exactly as they appear
- **PDF Export**: Download generated reports as PDF files

### Part 3 - Document Management
- **Multi-format Upload**: Support for PDFs, Word files, Excel sheets, and images
- **Google Drive Integration**: Connect and access documents from Google Drive
- **Document Management**: View and manage uploaded documents

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running (default: http://localhost:8000)

### Installation

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Create environment file:**
   ```bash
   cp .env.local.example .env.local
   ```

4. **Update `.env.local` with your backend URL:**
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

5. **Start the development server:**
   ```bash
   npm run dev
   ```

6. **Open your browser:**
   Navigate to [http://localhost:3000](http://localhost:3000)

## Project Structure

```
frontend/
├── app/                      # Next.js app directory
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Main page with tab navigation
│   └── globals.css          # Global styles
├── components/              # React components
│   ├── DocumentUpload.tsx   # Document upload interface
│   ├── HealthcareChat.tsx  # Chat interface with citations
│   ├── ReportGenerator.tsx # Report generation interface
│   └── Sidebar.tsx          # Navigation sidebar
├── lib/                     # Utilities
│   ├── api.ts              # API client with all endpoints
│   └── utils.ts            # Helper functions
└── package.json
```

## API Endpoints

### Document Management
- `POST /api/v1/documents/upload` - Upload documents
- `POST /api/v1/google-drive/connect` - Connect Google Drive
- `GET /api/v1/google-drive/documents` - Get Google Drive documents

### Chat & Q&A
- `POST /api/v1/chat/smart` - Smart chat with auto-discovery
- `POST /api/v1/chat` - Chat with specific documents
- `POST /api/v1/chat-highlights` - Get chat highlights

### Report Generation
- `POST /api/v1/reports/generate` - Generate medical report
- `GET /api/v1/reports/{id}/download` - Download report as PDF

### Search
- `POST /api/v1/search/preview` - Preview document search
- `POST /api/v1/search/unified` - Unified search

## Key Features Implementation

### Citations Display
The chat interface displays citations for each answer, showing:
- Document name and ID
- Source type (uploaded or Google Drive)
- Clickable links to Google Drive files
- Relevant chunk text
- Page numbers and relevance scores

### Report Generation
Users can:
- Select which sections to include
- Add custom sections
- Provide specific instructions
- Download generated reports as PDFs

### Document Upload
Supports:
- Drag and drop interface
- Multiple file types (PDF, Word, Excel, Images)
- Upload progress tracking
- Google Drive integration

## Build for Production

```bash
npm run build
npm start
```

## Notes

- The frontend is designed to work with the backend API
- Some features use mock data until backend endpoints are fully implemented
- All API calls are structured to match the expected backend interface
- The UI is fully responsive and healthcare-focused

## Tech Stack

- **Framework**: Next.js 14
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **HTTP Client**: Axios & Fetch API
