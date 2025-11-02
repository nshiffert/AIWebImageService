import { useEffect, useState } from 'react';
import { getReviewQueue, approveImage, deleteImage, getImageUrl } from '../api/client';
import type { Image } from '../types';
import { FiCheckCircle, FiXCircle, FiRefreshCw } from 'react-icons/fi';

export const ReviewPage = () => {
  const [images, setImages] = useState<Image[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState<string | null>(null);

  useEffect(() => {
    loadImages();
  }, []);

  const loadImages = async () => {
    setLoading(true);
    try {
      const data = await getReviewQueue(50);
      setImages(data.images);
    } catch (error) {
      console.error('Failed to load review queue:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSelection = (id: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const handleApprove = async (imageId: string) => {
    setProcessing(imageId);
    try {
      await approveImage(imageId);
      setImages(images.filter((img) => img.id !== imageId));
      setSelectedIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(imageId);
        return newSet;
      });
    } catch (error) {
      console.error('Failed to approve image:', error);
      alert('Failed to approve image');
    } finally {
      setProcessing(null);
    }
  };

  const handleBulkApprove = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Approve ${selectedIds.size} images?`)) return;

    setProcessing('bulk');
    const promises = Array.from(selectedIds).map((id) => approveImage(id));

    try {
      await Promise.all(promises);
      setImages(images.filter((img) => !selectedIds.has(img.id)));
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Failed to bulk approve:', error);
      alert('Some images failed to approve');
    } finally {
      setProcessing(null);
      loadImages();
    }
  };

  const handleDelete = async (imageId: string) => {
    if (!confirm('Are you sure you want to delete this image?')) return;

    setProcessing(imageId);
    try {
      await deleteImage(imageId);
      setImages(images.filter((img) => img.id !== imageId));
      setSelectedIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(imageId);
        return newSet;
      });
    } catch (error) {
      console.error('Failed to delete image:', error);
      alert('Failed to delete image');
    } finally {
      setProcessing(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Review Queue</h1>
            <p className="text-gray-600 mt-1">{images.length} images pending review</p>
          </div>

          <div className="flex items-center space-x-4">
            {selectedIds.size > 0 && (
              <button
                onClick={handleBulkApprove}
                disabled={processing === 'bulk'}
                className="bg-green-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-700 transition disabled:opacity-50 flex items-center space-x-2"
              >
                <FiCheckCircle />
                <span>Approve Selected ({selectedIds.size})</span>
              </button>
            )}

            <button
              onClick={loadImages}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition flex items-center space-x-2"
            >
              <FiRefreshCw />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {images.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-gray-600 text-lg">No images pending review</p>
            <p className="text-gray-500 mt-2">All caught up!</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {images.map((image) => (
              <div key={image.id} className="bg-white rounded-lg shadow overflow-hidden">
                <div className="p-4">
                  {/* Selection Checkbox */}
                  <div className="flex items-center justify-between mb-4">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(image.id)}
                        onChange={() => toggleSelection(image.id)}
                        className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="text-sm font-medium text-gray-700">Select for bulk action</span>
                    </label>
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      image.status === 'ready' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {image.status}
                    </span>
                  </div>

                  {/* Image - find product_card variant */}
                  <div className="aspect-[4/3] bg-gray-200 rounded-lg overflow-hidden mb-4">
                    <img
                      src={getImageUrl(`${image.id}/product_card.jpg`)}
                      alt={image.prompt}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        // Fallback to full_res if product_card not found
                        e.currentTarget.src = getImageUrl(`${image.id}/full_res.jpg`);
                      }}
                    />
                  </div>

                  {/* Prompt */}
                  <div className="mb-3">
                    <p className="text-sm font-semibold text-gray-700 mb-1">Prompt:</p>
                    <p className="text-sm text-gray-600">{image.prompt}</p>
                  </div>

                  {/* Description */}
                  {image.description && (
                    <div className="mb-3">
                      <p className="text-sm font-semibold text-gray-700 mb-1">Description:</p>
                      <p className="text-sm text-gray-600">{image.description}</p>
                    </div>
                  )}

                  {/* Tags */}
                  {image.tags.length > 0 && (
                    <div className="mb-4">
                      <p className="text-sm font-semibold text-gray-700 mb-2">Tags:</p>
                      <div className="flex flex-wrap gap-1">
                        {image.tags.map((tag) => (
                          <span
                            key={tag.tag}
                            className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded"
                          >
                            {tag.tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Confidence Score */}
                  {image.tagging_confidence && (
                    <div className="mb-4">
                      <p className="text-sm text-gray-600">
                        Confidence: {Math.round(image.tagging_confidence * 100)}%
                      </p>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => handleApprove(image.id)}
                      disabled={processing === image.id}
                      className="flex-1 bg-green-600 text-white px-4 py-3 rounded-lg font-semibold hover:bg-green-700 transition disabled:opacity-50 flex items-center justify-center space-x-2"
                    >
                      <FiCheckCircle />
                      <span>Approve</span>
                    </button>

                    <button
                      onClick={() => handleDelete(image.id)}
                      disabled={processing === image.id}
                      className="flex-1 bg-red-600 text-white px-4 py-3 rounded-lg font-semibold hover:bg-red-700 transition disabled:opacity-50 flex items-center justify-center space-x-2"
                    >
                      <FiXCircle />
                      <span>Reject</span>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
