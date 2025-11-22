-- Migration: Add Telegram file_id columns for image caching
-- Date: 2025-11-22
-- Purpose: Store Telegram file_id to avoid re-uploading images (Railway-proof)

-- Add columns for Telegram file_id (cache instantané, gratuit)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS telegram_thumb_file_id TEXT,
ADD COLUMN IF NOT EXISTS telegram_cover_file_id TEXT;

-- Create indexes for optimization
CREATE INDEX IF NOT EXISTS idx_products_telegram_thumb ON products(telegram_thumb_file_id) WHERE telegram_thumb_file_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_telegram_cover ON products(telegram_cover_file_id) WHERE telegram_cover_file_id IS NOT NULL;

-- Verify columns added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'products'
AND column_name LIKE '%telegram%';
