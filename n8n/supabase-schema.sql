-- Supabase Schema for YouTube Automation
-- Run this in Supabase SQL Editor (supabase.jclee.me)

-- Videos table
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('horror', 'facts', 'finance')),
    title VARCHAR(100) NOT NULL,
    topic TEXT NOT NULL,
    description TEXT,
    tags TEXT[],
    youtube_id VARCHAR(20),
    youtube_url TEXT GENERATED ALWAYS AS ('https://youtube.com/watch?v=' || youtube_id) STORED,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'processing', 'published', 'failed')),
    word_count INTEGER,
    scene_count INTEGER,
    duration_seconds INTEGER,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    revenue DECIMAL(10, 2) DEFAULT 0,
    script_json JSONB,
    audio_url TEXT,
    thumbnail_url TEXT,
    video_url TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for common queries
CREATE INDEX idx_videos_channel ON videos(channel);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_created_at ON videos(created_at DESC);
CREATE INDEX idx_videos_channel_created ON videos(channel, created_at DESC);

-- Topics history (to avoid duplicates)
CREATE TABLE IF NOT EXISTS topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel VARCHAR(20) NOT NULL,
    topic TEXT NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    video_id UUID REFERENCES videos(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_topics_channel_used ON topics(channel, used);

-- Analytics snapshots
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES videos(id),
    views INTEGER,
    likes INTEGER,
    comments INTEGER,
    watch_time_hours DECIMAL(10, 2),
    ctr DECIMAL(5, 2),
    avg_view_duration_seconds INTEGER,
    revenue DECIMAL(10, 2),
    snapshot_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analytics_video_date ON analytics_snapshots(video_id, snapshot_date DESC);

-- Scheduled jobs
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel VARCHAR(20) NOT NULL,
    scheduled_for TIMESTAMPTZ NOT NULL,
    n8n_execution_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    video_id UUID REFERENCES videos(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Function to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER videos_updated_at
    BEFORE UPDATE ON videos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- View: Recent videos by channel
CREATE OR REPLACE VIEW recent_videos AS
SELECT 
    channel,
    title,
    youtube_url,
    status,
    views,
    revenue,
    created_at,
    published_at
FROM videos
ORDER BY created_at DESC
LIMIT 50;

-- View: Channel stats
CREATE OR REPLACE VIEW channel_stats AS
SELECT 
    channel,
    COUNT(*) as total_videos,
    COUNT(*) FILTER (WHERE status = 'published') as published_videos,
    SUM(views) as total_views,
    SUM(revenue) as total_revenue,
    AVG(views) FILTER (WHERE status = 'published') as avg_views,
    MAX(created_at) as last_video_at
FROM videos
GROUP BY channel;

-- RLS Policies (if needed)
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_snapshots ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role full access" ON videos
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON topics
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON analytics_snapshots
    FOR ALL USING (auth.role() = 'service_role');
