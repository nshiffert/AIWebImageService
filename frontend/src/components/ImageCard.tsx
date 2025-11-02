import { useState } from 'react';
import { getImageUrl } from '../api/client';
import { FiCopy, FiCheck } from 'react-icons/fi';

interface ImageCardProps {
  storagePath: string;
  tags: string[];
  description?: string | null;
  score?: number;
  onClick?: () => void;
}

const IMAGE_SIZES = [
  { name: 'Thumbnail', key: 'thumbnail', label: '150x150' },
  { name: 'Product Card', key: 'product_card', label: '400x300' },
  { name: 'Full Product', key: 'full_product', label: '800x600' },
  { name: 'Hero Image', key: 'hero_image', label: '1920x600' },
  { name: 'Full Resolution', key: 'full_res', label: '2048x2048' },
];

export const ImageCard = ({ storagePath, tags, description, score, onClick }: ImageCardProps) => {
  const [copiedSize, setCopiedSize] = useState<string | null>(null);
  const [showSizes, setShowSizes] = useState(false);

  // Extract image ID from storage path (e.g., "image-id/product_card.jpg" -> "image-id")
  const imageId = storagePath.split('/')[0];

  const copyToClipboard = async (sizeKey: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    const url = getImageUrl(`${imageId}/${sizeKey}.jpg`);

    try {
      await navigator.clipboard.writeText(url);
      setCopiedSize(sizeKey);
      setTimeout(() => setCopiedSize(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const toggleSizes = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    setShowSizes(!showSizes);
  };

  return (
    <div
      className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="aspect-[4/3] relative">
        <img
          src={getImageUrl(storagePath)}
          alt={description || 'Generated image'}
          className="w-full h-full object-cover"
          loading="lazy"
        />
        {score && (
          <div className="absolute top-2 right-2 bg-black bg-opacity-70 text-white px-2 py-1 rounded text-sm">
            {Math.round(score * 100)}% match
          </div>
        )}

        {/* Copy URLs Button */}
        <button
          onClick={toggleSizes}
          className="absolute bottom-2 right-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1 shadow-lg transition"
        >
          <FiCopy className="text-sm" />
          Copy URLs
        </button>
      </div>

      {/* Expandable Size Options */}
      {showSizes && (
        <div className="bg-gray-50 border-t border-gray-200 p-3" onClick={(e) => e.stopPropagation()}>
          <p className="text-xs font-semibold text-gray-700 mb-2">Copy Image URL:</p>
          <div className="space-y-1">
            {IMAGE_SIZES.map((size) => (
              <button
                key={size.key}
                onClick={(e) => copyToClipboard(size.key, e)}
                className="w-full flex items-center justify-between px-3 py-2 bg-white hover:bg-gray-100 rounded border border-gray-200 transition text-left"
              >
                <div className="flex-1">
                  <span className="text-sm font-medium text-gray-800">{size.name}</span>
                  <span className="text-xs text-gray-500 ml-2">({size.label})</span>
                </div>
                {copiedSize === size.key ? (
                  <FiCheck className="text-green-600 text-sm" />
                ) : (
                  <FiCopy className="text-gray-400 text-sm" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="p-4">
        {description && (
          <p className="text-gray-700 text-sm mb-2 line-clamp-2">{description}</p>
        )}
        <div className="flex flex-wrap gap-1">
          {tags.slice(0, 5).map((tag) => (
            <span
              key={tag}
              className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded"
            >
              {tag}
            </span>
          ))}
          {tags.length > 5 && (
            <span className="text-gray-500 text-xs px-2 py-1">
              +{tags.length - 5} more
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
