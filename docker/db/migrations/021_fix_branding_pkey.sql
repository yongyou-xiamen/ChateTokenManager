-- 021: 修复 branding/ai_policies_settings 主键为自增
-- 问题: id INTEGER PRIMARY KEY DEFAULT 1 导致多租户创建行时主键冲突

-- 1. branding: 改 id 为 SERIAL
ALTER TABLE aihelms.branding ALTER COLUMN id SET DEFAULT nextval('branding_id_seq'::regclass);
CREATE SEQUENCE IF NOT EXISTS aihelms.branding_id_seq OWNED BY aihelms.branding.id;
SELECT setval('aihelms.branding_id_seq', COALESCE((SELECT MAX(id) FROM aihelms.branding), 1));

-- 2. ai_policies_settings: 改 id 为 SERIAL
ALTER TABLE aihelms.ai_policies_settings ALTER COLUMN id SET DEFAULT nextval('ai_policies_settings_id_seq'::regclass);
CREATE SEQUENCE IF NOT EXISTS aihelms.ai_policies_settings_id_seq OWNED BY aihelms.ai_policies_settings.id;
SELECT setval('aihelms.ai_policies_settings_id_seq', COALESCE((SELECT MAX(id) FROM aihelms.ai_policies_settings), 1));
