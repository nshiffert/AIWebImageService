import { useState, useEffect, useRef } from 'react';
import { generateImage, generateBatch, getMetaPrompt, getJobStatus } from '../api/client';
import { FiUpload, FiZap, FiCheckCircle, FiXCircle } from 'react-icons/fi';
import type { JobStatusResponse } from '../types';

export const GeneratePage = () => {
  const [singlePrompt, setSinglePrompt] = useState('');
  const [bulkPrompts, setBulkPrompts] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'single' | 'bulk'>('single');

  // Job tracking state
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const pollingInterval = useRef<NodeJS.Timeout | null>(null);

  const metaPrompt = getMetaPrompt();

  const handleSingleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const fullPrompt = `${metaPrompt}. ${singlePrompt}`;
      const response = await generateImage({
        prompt: fullPrompt,
        style: 'product_photography',
      });
      setResult(response);
      setSinglePrompt('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate image');
    } finally {
      setLoading(false);
    }
  };

  // Poll job status
  useEffect(() => {
    if (currentJobId && loading) {
      const pollStatus = async () => {
        try {
          const status = await getJobStatus(currentJobId);
          setJobStatus(status);

          // Stop polling if job is complete
          if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
            setLoading(false);
            setCurrentJobId(null);
            if (pollingInterval.current) {
              clearInterval(pollingInterval.current);
              pollingInterval.current = null;
            }

            // Set result message
            if (status.status === 'completed') {
              setResult({
                message: `Batch generation complete!`,
                total: status.total_tasks,
                completed: status.completed_tasks,
                failed: status.failed_tasks,
              });
            } else if (status.status === 'failed') {
              setError(`Job failed. Completed: ${status.completed_tasks}, Failed: ${status.failed_tasks}`);
            }
          }
        } catch (err: any) {
          console.error('Error polling job status:', err);
          setError('Failed to check job status');
          setLoading(false);
          if (pollingInterval.current) {
            clearInterval(pollingInterval.current);
            pollingInterval.current = null;
          }
        }
      };

      // Start polling every 2 seconds
      pollingInterval.current = setInterval(pollStatus, 2000);
      pollStatus(); // Call immediately

      // Cleanup on unmount
      return () => {
        if (pollingInterval.current) {
          clearInterval(pollingInterval.current);
        }
      };
    }
  }, [currentJobId, loading]);

  const handleBulkGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    setJobStatus(null);

    try {
      // Parse JSON or newline-separated prompts
      let prompts: string[];
      try {
        prompts = JSON.parse(bulkPrompts);
      } catch {
        prompts = bulkPrompts
          .split('\n')
          .map((p) => p.trim())
          .filter((p) => p.length > 0);
      }

      if (prompts.length === 0) {
        setError('Please provide at least one prompt');
        setLoading(false);
        return;
      }

      // Add meta prompt to each
      const enhancedPrompts = prompts.map((p) => `${metaPrompt}. ${p}`);

      // Submit batch job
      const job = await generateBatch({
        prompts: enhancedPrompts,
        style: 'product_photography',
        count_per_prompt: 1,
      });

      // Start polling for job status
      setCurrentJobId(job.id);
      setJobStatus({
        id: job.id,
        status: job.status,
        total_tasks: job.total_tasks,
        completed_tasks: job.completed_tasks,
        failed_tasks: job.failed_tasks,
        progress_percentage: 0,
        created_at: job.created_at,
        completed_at: null,
      });

      setBulkPrompts('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate images');
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setBulkPrompts(content);
    };
    reader.readAsText(file);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Generate Images</h1>
        <p className="text-gray-600 mb-8">
          Create new images using AI. Meta prompt is automatically applied to all generations.
        </p>

        {/* Tabs */}
        <div className="flex space-x-4 mb-6">
          <button
            onClick={() => setActiveTab('single')}
            className={`px-6 py-3 rounded-lg font-semibold transition ${
              activeTab === 'single'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            Single Image
          </button>
          <button
            onClick={() => setActiveTab('bulk')}
            className={`px-6 py-3 rounded-lg font-semibold transition ${
              activeTab === 'bulk'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            Bulk Generation
          </button>
        </div>

        {/* Meta Prompt Display */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <p className="text-sm font-semibold text-blue-800 mb-1">Active Meta Prompt:</p>
          <p className="text-sm text-blue-700">{metaPrompt}</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {result && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
            <p className="font-semibold text-green-800 mb-2">Success!</p>
            <pre className="text-sm text-green-700 overflow-auto">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}

        {/* Single Generation Form */}
        {activeTab === 'single' && (
          <div className="bg-white rounded-lg shadow p-6">
            <form onSubmit={handleSingleGenerate}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Image Prompt
                </label>
                <textarea
                  value={singlePrompt}
                  onChange={(e) => setSinglePrompt(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={4}
                  placeholder="e.g., chocolate chip cookies on a white plate"
                  required
                />
                <p className="text-sm text-gray-500 mt-1">
                  Describe the image you want to generate. The meta prompt will be applied automatically.
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center space-x-2"
              >
                <FiZap />
                <span>{loading ? 'Generating...' : 'Generate Image'}</span>
              </button>
            </form>
          </div>
        )}

        {/* Bulk Generation Form */}
        {activeTab === 'bulk' && (
          <div className="bg-white rounded-lg shadow p-6">
            <form onSubmit={handleBulkGenerate}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Bulk Prompts
                </label>
                <textarea
                  value={bulkPrompts}
                  onChange={(e) => setBulkPrompts(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                  rows={12}
                  placeholder={`Enter prompts in one of these formats:

JSON array:
["chocolate chip cookies", "sourdough bread", "strawberry jam"]

OR newline-separated:
chocolate chip cookies
sourdough bread
strawberry jam`}
                  required
                />
                <p className="text-sm text-gray-500 mt-1">
                  Provide multiple prompts as JSON array or one per line
                </p>
              </div>

              <div className="flex items-center space-x-4 mb-4">
                <label className="flex items-center space-x-2 cursor-pointer px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 transition">
                  <FiUpload />
                  <span className="text-sm font-medium">Upload JSON File</span>
                  <input
                    type="file"
                    accept=".json,.txt"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center space-x-2"
              >
                <FiZap />
                <span>{loading ? 'Generating...' : 'Generate All Images'}</span>
              </button>
            </form>
          </div>
        )}

        {loading && jobStatus && (
          <div className="mt-6 bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Generation Progress</h3>

            {/* Progress Bar */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-700">
                  {jobStatus.completed_tasks + jobStatus.failed_tasks} / {jobStatus.total_tasks} tasks processed
                </span>
                <span className="text-sm font-bold text-blue-600">
                  {Math.round(jobStatus.progress_percentage)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all duration-300 ease-in-out"
                  style={{ width: `${jobStatus.progress_percentage}%` }}
                ></div>
              </div>
            </div>

            {/* Status Details */}
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="bg-blue-50 rounded p-3">
                <div className="text-2xl font-bold text-blue-600">{jobStatus.completed_tasks}</div>
                <div className="text-xs text-gray-600 flex items-center justify-center gap-1">
                  <FiCheckCircle className="text-green-600" />
                  Completed
                </div>
              </div>
              <div className="bg-red-50 rounded p-3">
                <div className="text-2xl font-bold text-red-600">{jobStatus.failed_tasks}</div>
                <div className="text-xs text-gray-600 flex items-center justify-center gap-1">
                  <FiXCircle className="text-red-600" />
                  Failed
                </div>
              </div>
              <div className="bg-gray-50 rounded p-3">
                <div className="text-2xl font-bold text-gray-600">
                  {jobStatus.total_tasks - jobStatus.completed_tasks - jobStatus.failed_tasks}
                </div>
                <div className="text-xs text-gray-600">Pending</div>
              </div>
            </div>

            {/* Status Text */}
            <div className="mt-4 text-center">
              <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mr-2"></div>
              <span className="text-sm text-gray-600">
                Processing... (30-60 seconds per image, max 5 concurrent)
              </span>
            </div>
          </div>
        )}

        {loading && !jobStatus && (
          <div className="mt-6 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-600">
              Starting batch generation...
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
