import { useState } from 'react';
import { getMetaPrompt, setMetaPrompt } from '../api/client';
import { FiSave, FiRotateCcw } from 'react-icons/fi';

const DEFAULT_META_PROMPT = 'hyper-realistic semi-professional camera photo taken with natural lighting, product photography style, clean background, high detail';

export const SettingsPage = () => {
  const [metaPrompt, setMetaPromptState] = useState(getMetaPrompt());
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setMetaPrompt(metaPrompt);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleReset = () => {
    const confirmed = confirm('Reset to default meta prompt?');
    if (confirmed) {
      setMetaPromptState(DEFAULT_META_PROMPT);
      setMetaPrompt(DEFAULT_META_PROMPT);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Settings</h1>
        <p className="text-gray-600 mb-8">
          Configure the meta prompt that will be applied to all image generations
        </p>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Meta Prompt Configuration</h2>
            <p className="text-sm text-gray-600 mb-4">
              The meta prompt is automatically prepended to all image generation requests to ensure
              consistent style and quality. This helps maintain a cohesive look across all generated
              images without having to specify these details in every prompt.
            </p>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <p className="text-sm font-semibold text-blue-800 mb-1">Default Meta Prompt:</p>
              <p className="text-sm text-blue-700 font-mono">{DEFAULT_META_PROMPT}</p>
            </div>
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Current Meta Prompt
            </label>
            <textarea
              value={metaPrompt}
              onChange={(e) => setMetaPromptState(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
              rows={6}
              placeholder="Enter your meta prompt here..."
            />
            <p className="text-sm text-gray-500 mt-2">
              This prompt will be prepended to all generation requests. Use it to define the overall
              style, lighting, background, and quality expectations.
            </p>
          </div>

          {saved && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-4">
              Meta prompt saved successfully!
            </div>
          )}

          <div className="flex items-center space-x-4">
            <button
              onClick={handleSave}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition flex items-center space-x-2"
            >
              <FiSave />
              <span>Save Changes</span>
            </button>

            <button
              onClick={handleReset}
              className="bg-gray-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-gray-700 transition flex items-center space-x-2"
            >
              <FiRotateCcw />
              <span>Reset to Default</span>
            </button>
          </div>

          <div className="mt-8 pt-6 border-t border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">Tips for Writing Meta Prompts</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-start">
                <span className="text-blue-600 mr-2">•</span>
                <span>Be specific about photography style and lighting conditions</span>
              </li>
              <li className="flex items-start">
                <span className="text-blue-600 mr-2">•</span>
                <span>Include background preferences (e.g., clean, white, natural)</span>
              </li>
              <li className="flex items-start">
                <span className="text-blue-600 mr-2">•</span>
                <span>Specify quality expectations (e.g., high detail, professional, sharp focus)</span>
              </li>
              <li className="flex items-start">
                <span className="text-blue-600 mr-2">•</span>
                <span>Keep it concise but descriptive - GPT Image works best with clear instructions</span>
              </li>
              <li className="flex items-start">
                <span className="text-blue-600 mr-2">•</span>
                <span>Test your meta prompt with single generations before bulk uploads</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
