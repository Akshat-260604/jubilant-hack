'use client';

import { useState } from 'react';
import { Search as SearchIcon, Loader2, FileText, Database } from 'lucide-react';
import { api, SearchPreviewRequest } from '@/lib/api';

interface SearchViewProps {
  userId: string;
}

export default function SearchView({ userId }: SearchViewProps) {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [searchType, setSearchType] = useState<'preview' | 'unified'>('preview');
  const [maxResults, setMaxResults] = useState(10);
  const [scoreThreshold, setScoreThreshold] = useState(0.6);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    setResults(null);

    try {
      const request: SearchPreviewRequest = {
        query,
        userId,
        max_results: maxResults,
        score_threshold: scoreThreshold,
      };

      const data = searchType === 'preview'
        ? await api.searchPreview(request)
        : await api.unifiedSearch(request);

      setResults(data);
    } catch (error) {
      console.error('Error:', error);
      setResults({ error: 'Failed to perform search' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="p-6 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2 mb-4">
          <SearchIcon className="w-5 h-5 text-primary-600" />
          <h3 className="font-semibold text-gray-900">Document Search</h3>
        </div>
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Enter search query..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-gray-900"
            />
            <button
              onClick={handleSearch}
              disabled={isLoading || !query.trim()}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <SearchIcon className="w-5 h-5" />
              )}
              Search
            </button>
          </div>
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Search Type
              </label>
              <select
                value={searchType}
                onChange={(e) => setSearchType(e.target.value as 'preview' | 'unified')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900"
              >
                <option value="preview">Preview</option>
                <option value="unified">Unified</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Results
              </label>
              <input
                type="number"
                min="1"
                max="50"
                value={maxResults}
                onChange={(e) => setMaxResults(parseInt(e.target.value) || 10)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Score Threshold
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={scoreThreshold}
                onChange={(e) => setScoreThreshold(parseFloat(e.target.value) || 0.6)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          </div>
        )}

        {!isLoading && results && (
          <div className="space-y-4">
            {results.error ? (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                {results.error}
              </div>
            ) : (
              <>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-900">
                    <strong>Total Results:</strong> {results.total_results || results.total_sources || 0}
                  </p>
                  {results.sources_summary && (
                    <p className="text-sm text-blue-700 mt-1">
                      Uploaded: {results.sources_summary.uploaded} | 
                      Google Drive: {results.sources_summary.google_drive}
                    </p>
                  )}
                </div>

                {results.preview && (
                  <div className="space-y-4">
                    {results.preview.uploaded_documents && (
                      <div>
                        <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                          <FileText className="w-4 h-4" />
                          Uploaded Documents ({results.preview.uploaded_documents.count || 0})
                        </h4>
                        <div className="space-y-2">
                          {results.preview.uploaded_documents.documents?.map((doc: any, idx: number) => (
                            <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4">
                              <p className="font-medium">{doc.document_id || doc.id}</p>
                              <p className="text-sm text-gray-600 mt-1">Score: {doc.score?.toFixed(3)}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {results.preview.google_drive_documents && (
                      <div>
                        <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                          <Database className="w-4 h-4" />
                          Google Drive Documents ({results.preview.google_drive_documents.count || 0})
                        </h4>
                        <div className="space-y-2">
                          {results.preview.google_drive_documents.documents?.map((doc: any, idx: number) => (
                            <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4">
                              <p className="font-medium">{doc.name || doc.document_id}</p>
                              <p className="text-sm text-gray-600 mt-1">Score: {doc.score?.toFixed(3)}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {results.results && (
                  <div className="space-y-2">
                    {results.results.map((result: any, idx: number) => (
                      <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="font-medium text-gray-900">
                              {result.document_id || result.name || `Result ${idx + 1}`}
                            </p>
                            <p className="text-sm text-gray-600 mt-1">
                              Source: {result.source_type || 'Unknown'}
                            </p>
                            {result.score && (
                              <p className="text-sm text-gray-500 mt-1">
                                Score: {result.score.toFixed(3)}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {!isLoading && !results && (
          <div className="text-center text-gray-500 mt-12">
            <SearchIcon className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p>Enter a search query to find documents</p>
          </div>
        )}
      </div>
    </div>
  );
}

