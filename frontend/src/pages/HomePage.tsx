import { useState, useEffect } from 'react';
import { searchImages } from '../api/client';
import { ImageCard } from '../components/ImageCard';
import type { SearchResult } from '../types';
import { FiSearch } from 'react-icons/fi';

export const HomePage = () => {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  // Load recent images on mount
  useEffect(() => {
    handleSearch('cookies'); // Default search to show some images
  }, []);

  const handleSearch = async (searchQuery: string = query) => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setSearched(true);
    try {
      const response = await searchImages({
        query: searchQuery,
        size: 'product_card',
        limit: 20,
        min_score: 0.5,
      });
      setResults(response.results);
    } catch (error) {
      console.error('Search failed:', error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-20">
        <div className="container mx-auto px-4">
          <h1 className="text-5xl font-bold mb-4 text-center">
            AI-Generated Image Library
          </h1>
          <p className="text-xl text-center mb-8 max-w-2xl mx-auto">
            Search through thousands of high-quality, AI-generated images perfect for cottage food businesses
          </p>

          {/* Search Bar */}
          <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <FiSearch className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-500 text-xl" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search for images... (e.g., 'chocolate cookies', 'sourdough bread')"
                  className="w-full pl-12 pr-4 py-4 text-gray-900 placeholder-gray-500 bg-white rounded-lg shadow-md focus:outline-none focus:ring-2 focus:ring-blue-400 focus:shadow-lg"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="bg-white text-blue-600 px-8 py-4 rounded-lg font-semibold shadow-md hover:bg-gray-100 hover:shadow-lg transition disabled:opacity-50"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Results Grid */}
      <div className="container mx-auto px-4 py-12">
        {loading ? (
          <div className="text-center py-20">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Searching images...</p>
          </div>
        ) : results.length > 0 ? (
          <>
            <h2 className="text-2xl font-bold mb-6 text-gray-800">
              {searched ? `Found ${results.length} images` : 'Recently Added Images'}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {results.map((result) => (
                <ImageCard
                  key={result.id}
                  storagePath={result.storage_path}
                  tags={result.tags}
                  description={result.description}
                  score={result.score}
                />
              ))}
            </div>
          </>
        ) : searched ? (
          <div className="text-center py-20">
            <p className="text-gray-600 text-lg">No images found for "{query}"</p>
            <p className="text-gray-500 mt-2">Try a different search term</p>
          </div>
        ) : (
          <div className="text-center py-20">
            <p className="text-gray-600 text-lg">Search for images to get started</p>
          </div>
        )}
      </div>
    </div>
  );
};
