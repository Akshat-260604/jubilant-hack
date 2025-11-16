'use client';

import { useState, useEffect } from 'react';
import { FileCheck, Download, Loader2, CheckCircle, Plus, X, FileText, Sparkles } from 'lucide-react';
import { api } from '@/lib/api';

interface ReportSection {
  id: string;
  name: string;
  enabled: boolean;
  content?: string;
}

interface ReportGeneratorProps {
  userId: string;
}

interface ProcessedDoc {
  id: string;
  filename: string;
  status: string;
}

const DEFAULT_SECTIONS: ReportSection[] = [
  { id: 'introduction', name: 'Introduction', enabled: true },
  { id: 'clinical_findings', name: 'Clinical Findings', enabled: true },
  { id: 'patient_tables', name: 'Patient Tables', enabled: false },
  { id: 'graphs', name: 'Graphs & Charts', enabled: false },
  { id: 'summary', name: 'Summary', enabled: true },
];

export default function ReportGenerator({ userId }: ReportGeneratorProps) {
  const [sections, setSections] = useState<ReportSection[]>(DEFAULT_SECTIONS);
  const [reportPrompt, setReportPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedReport, setGeneratedReport] = useState<string | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);
  const [isRewriting, setIsRewriting] = useState(false);
  const [scope, setScope] = useState<'single' | 'combined'>('single');
  const [availableDocs, setAvailableDocs] = useState<ProcessedDoc[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | ''>('');

  useEffect(() => {
    const loadDocs = async () => {
      try {
        const docs = await api.listMySelfUploadedDocuments(userId);
        setAvailableDocs(docs || []);
        if (docs && docs.length > 0) {
          setSelectedDocId(docs[0].id);
        }
      } catch (err) {
        console.error('Error loading processed documents for reports:', err);
      }
    };
    loadDocs();
  }, [userId]);

  const toggleSection = (sectionId: string) => {
    setSections((prev) =>
      prev.map((s) => (s.id === sectionId ? { ...s, enabled: !s.enabled } : s))
    );
  };

  const addCustomSection = () => {
    const newSection: ReportSection = {
      id: `custom_${Date.now()}`,
      name: 'New Section',
      enabled: true,
    };
    setSections((prev) => [...prev, newSection]);
  };

  const removeSection = (sectionId: string) => {
    setSections((prev) => prev.filter((s) => s.id !== sectionId));
  };

  const updateSectionName = (sectionId: string, name: string) => {
    setSections((prev) =>
      prev.map((s) => (s.id === sectionId ? { ...s, name } : s))
    );
  };

  const handleRewriteInstructions = async () => {
    if (!reportPrompt.trim()) return;

    setIsRewriting(true);
    try {
      const result = await api.rewrite({ user_prompt: reportPrompt });
      setReportPrompt(result.enhanced_prompt);
    } catch (error) {
      console.error('Error rewriting instructions:', error);
    } finally {
      setIsRewriting(false);
    }
  };

  const handleGenerateReport = async () => {
    const enabledSections = sections.filter((s) => s.enabled);
    if (enabledSections.length === 0) {
      alert('Please select at least one section');
      return;
    }

    if (scope === 'single' && !selectedDocId) {
      alert('Please select a document for the report.');
      return;
    }

    setIsGenerating(true);
    setGeneratedReport(null);

    try {
      // Call backend to generate a structured medical report
      const payload = {
        userId,
        // Send stable section identifiers so backend can decide behaviour per section
        sections: enabledSections.map((s) => s.id),
        instructions: reportPrompt || undefined,
        scope,
        documentId: scope === 'single' ? selectedDocId : undefined,
      };

      const result = await api.generateReport(payload);
      setGeneratedReport(result.content);
      setReportId(result.report_id);
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Failed to generate report. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownloadPDF = async () => {
    if (!reportId) return;

    try {
      // TODO: Replace with actual API call to download PDF
      alert('PDF download will be implemented when backend is ready');
      // const response = await fetch(`/api/v1/reports/${reportId}/download`);
      // const blob = await response.blob();
      // const url = window.URL.createObjectURL(blob);
      // const a = document.createElement('a');
      // a.href = url;
      // a.download = `medical_report_${reportId}.pdf`;
      // document.body.appendChild(a);
      // a.click();
      // window.URL.revokeObjectURL(url);
      // document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading PDF:', error);
      alert('Failed to download PDF. Please try again.');
    }
  };

  const enabledSectionsCount = sections.filter((s) => s.enabled).length;

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Generate Medical Report</h2>
            <p className="text-sm text-gray-600">
              Create structured reports from your medical documents
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto space-y-6">
          {/* Scope + Report Configuration */}
          <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Report Sections
              </h3>
              <div className="flex items-center gap-4 text-sm text-gray-700">
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    id="scope-single"
                    checked={scope === 'single'}
                    onChange={() => setScope('single')}
                    className="w-4 h-4 text-primary-600"
                  />
                  <label htmlFor="scope-single">Selected document only</label>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    id="scope-combined"
                    checked={scope === 'combined'}
                    onChange={() => setScope('combined')}
                    className="w-4 h-4 text-primary-600"
                  />
                  <label htmlFor="scope-combined">All uploaded documents</label>
                </div>
              </div>
            </div>

            {scope === 'single' && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Select document
                </label>
                <select
                  value={selectedDocId}
                  onChange={(e) => setSelectedDocId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-gray-900"
                >
                  {availableDocs.length === 0 && (
                    <option value="">No processed documents available</option>
                  )}
                  {availableDocs.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.filename} ({doc.status})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="space-y-3 mb-4">
              {sections.map((section) => (
                <div
                  key={section.id}
                  className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200"
                >
                  <input
                    type="checkbox"
                    checked={section.enabled}
                    onChange={() => toggleSection(section.id)}
                    className="w-5 h-5 text-primary-600 rounded focus:ring-primary-500"
                  />
                  <input
                    type="text"
                    value={section.name}
                    onChange={(e) => updateSectionName(section.id, e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-gray-900"
                    disabled={!section.enabled}
                  />
                  {sections.length > 1 && (
                    <button
                      onClick={() => removeSection(section.id)}
                      className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4 text-red-600" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            <button
              onClick={addCustomSection}
              className="flex items-center gap-2 px-4 py-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Custom Section
            </button>
          </div>

          {/* Report Instructions */}
          <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-gray-900">Report Instructions (Optional)</h3>
              <button
                type="button"
                onClick={handleRewriteInstructions}
                disabled={isRewriting || !reportPrompt.trim()}
                className="px-3 py-1.5 bg-white hover:bg-gray-50 border border-gray-300 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 text-sm text-gray-700"
                title="Enhance instructions with AI"
              >
                {isRewriting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                <span>Enhance</span>
              </button>
            </div>
            <textarea
              value={reportPrompt}
              onChange={(e) => setReportPrompt(e.target.value)}
              placeholder="Add any specific instructions for the report generation (e.g., focus on specific findings, include particular data points, etc.)"
              rows={4}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none text-gray-900"
            />
          </div>

          {/* Generate Button */}
          <div className="flex justify-center">
            <button
              onClick={handleGenerateReport}
              disabled={isGenerating || enabledSectionsCount === 0}
              className="px-8 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2 font-medium"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Generating Report...
                </>
              ) : (
                <>
                  <FileCheck className="w-5 h-5" />
                  Generate Report
                </>
              )}
            </button>
          </div>

          {/* Generated Report Preview */}
          {generatedReport && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  Report Generated Successfully
                </h3>
                <button
                  onClick={handleDownloadPDF}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  <Download className="w-4 h-4" />
                  Download PDF
                </button>
              </div>

              <div className="prose max-w-none bg-gray-50 rounded-lg p-6 border border-gray-200">
                <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans">
                  {generatedReport}
                </pre>
              </div>

              <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-sm text-blue-800">
                  <strong>Note:</strong> The report extracts exact data from your documents. Tables,
                  charts, and figures are preserved as they appear in the original documents. Only
                  summary sections are generated by the AI.
                </p>
              </div>
            </div>
          )}

          {/* Info Box */}
          {!generatedReport && (
            <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
              <p className="text-sm text-yellow-800">
                <strong>How it works:</strong> The system will use LLM function calling to extract
                exact data from relevant sections, pull tables/charts from PDFs and Word files, and
                insert them into the selected sections. Content is preserved exactly as it appears
                in the original documents.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

