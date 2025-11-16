# Frontend Setup Guide

## Quick Start

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
   (Change the port if your backend runs on a different port)

5. **Start the development server:**
   ```bash
   npm run dev
   ```

6. **Open your browser:**
   Navigate to [http://localhost:3000](http://localhost:3000)

## Connecting to Backend

Make sure your backend is running and accessible at the URL specified in `NEXT_PUBLIC_API_URL`.

The frontend expects the backend to be running on `http://localhost:8000` by default (as configured in the FastAPI backend).

## Troubleshooting

- **TypeScript errors**: These will resolve after running `npm install`
- **Connection errors**: Verify your backend is running and the URL in `.env.local` is correct
- **CORS errors**: Make sure your backend has CORS configured to allow requests from `http://localhost:3000`

## Features Available

1. **Chat**: Add document IDs and chat with them
2. **Smart Chat**: Ask questions - AI automatically finds relevant documents
3. **Search**: Search across all document sources
4. **Translate**: Translate text to multiple languages
5. **Tools**: Rewrite prompts and rephrase text

