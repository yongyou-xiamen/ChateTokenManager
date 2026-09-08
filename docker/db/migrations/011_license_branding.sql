CREATE TABLE IF NOT EXISTS aihelms.branding (
    id INTEGER PRIMARY KEY DEFAULT 1,
    platform_name TEXT NOT NULL DEFAULT 'AIHelms',
    logo_path TEXT,
    favicon_path TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT branding_singleton CHECK (id = 1)
);

INSERT INTO aihelms.branding (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;
