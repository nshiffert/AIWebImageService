-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Core image table
CREATE TABLE IF NOT EXISTS images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt TEXT NOT NULL,
    style VARCHAR(50) DEFAULT 'product_photography',
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'tagging', 'ready', 'approved', 'rejected')),
    auto_tagged BOOLEAN DEFAULT FALSE,
    tagging_confidence FLOAT,
    generation_cost DECIMAL(10,4),
    tagging_cost DECIMAL(10,4),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Image size variants
CREATE TABLE IF NOT EXISTS image_variants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    size_preset VARCHAR(20) NOT NULL CHECK (size_preset IN ('thumbnail', 'product_card', 'full_product', 'hero_image', 'full_res')),
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    file_size_bytes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(image_id, size_preset)
);

-- Tags with source tracking
CREATE TABLE IF NOT EXISTS image_tags (
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    tag VARCHAR(50) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source VARCHAR(20) DEFAULT 'auto' CHECK (source IN ('auto', 'manual', 'template')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY(image_id, tag)
);

-- AI-generated descriptions
CREATE TABLE IF NOT EXISTS image_descriptions (
    image_id UUID PRIMARY KEY REFERENCES images(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    vision_analysis JSONB,
    model_version VARCHAR(50),
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Color analysis
CREATE TABLE IF NOT EXISTS image_colors (
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    color_hex CHAR(7) NOT NULL,
    percentage FLOAT NOT NULL CHECK (percentage >= 0 AND percentage <= 100),
    is_dominant BOOLEAN DEFAULT FALSE,
    PRIMARY KEY(image_id, color_hex)
);

-- Vector embeddings for search (1536 dimensions for OpenAI text-embedding-ada-002)
CREATE TABLE IF NOT EXISTS image_embeddings (
    image_id UUID PRIMARY KEY REFERENCES images(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,
    embedding_source TEXT,
    model_version VARCHAR(50) DEFAULT 'text-embedding-ada-002',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Batch image generation jobs
CREATE TABLE IF NOT EXISTS generation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status VARCHAR(20) DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    total_tasks INTEGER DEFAULT 0 NOT NULL,
    completed_tasks INTEGER DEFAULT 0 NOT NULL,
    failed_tasks INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Individual image generation tasks within jobs
CREATE TABLE IF NOT EXISTS generation_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES generation_jobs(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    style VARCHAR(50) DEFAULT 'product_photography',
    status VARCHAR(20) DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    image_id UUID REFERENCES images(id) ON DELETE SET NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- API keys for search endpoint
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100),
    key_hash TEXT UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit INTEGER DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE
);

-- Search cache table
CREATE TABLE IF NOT EXISTS search_cache (
    cache_key VARCHAR(32) PRIMARY KEY,
    query TEXT NOT NULL,
    size VARCHAR(20),
    results JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_images_status ON images(status);
CREATE INDEX IF NOT EXISTS idx_images_created ON images(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_images_approved ON images(approved_at DESC) WHERE status = 'approved';
CREATE INDEX IF NOT EXISTS idx_tags_tag ON image_tags(tag);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON search_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_status ON generation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_created ON generation_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_job_id ON generation_tasks(job_id);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_status ON generation_tasks(status);

-- Vector index for similarity search (using HNSW for better performance)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON image_embeddings
USING hnsw (embedding vector_cosine_ops);

-- Function for vector similarity search
CREATE OR REPLACE FUNCTION search_similar_images(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10,
    size_preset text DEFAULT 'product_card'
)
RETURNS TABLE (
    id uuid,
    storage_path text,
    score float,
    tags text[],
    description text,
    dominant_color text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.id,
        iv.storage_path,
        1 - (ie.embedding <=> query_embedding) as score,
        COALESCE(array_agg(DISTINCT it.tag) FILTER (WHERE it.tag IS NOT NULL), ARRAY[]::text[]) as tags,
        id.description,
        (SELECT ic.color_hex FROM image_colors ic
         WHERE ic.image_id = i.id AND ic.is_dominant = true
         LIMIT 1) as dominant_color
    FROM images i
    JOIN image_embeddings ie ON i.id = ie.image_id
    JOIN image_variants iv ON i.id = iv.image_id AND iv.size_preset = size_preset
    LEFT JOIN image_tags it ON i.id = it.image_id
    LEFT JOIN image_descriptions id ON i.id = id.image_id
    WHERE
        i.status = 'approved'
        AND 1 - (ie.embedding <=> query_embedding) > match_threshold
    GROUP BY i.id, iv.storage_path, id.description, ie.embedding
    ORDER BY score DESC
    LIMIT match_count;
END;
$$;

-- Create a default API key for local testing (hash of 'test-key-local-dev-only')
INSERT INTO api_keys (name, key_hash, is_active, rate_limit)
VALUES (
    'Local Development Key',
    'c24a374c15e7ef8ec61f9a8a80a8c3d0f0c1e5e3f3e5c7f8a9b0c1d2e3f4g5h6',
    true,
    1000
)
ON CONFLICT (key_hash) DO NOTHING;

-- Grant necessary permissions (for local development)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
