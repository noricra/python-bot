-- Migration: Add soft delete support to products table
-- Date: 2025-11-10
-- Purpose: Enable soft delete to preserve data for purchased products

-- Add deleted_at column
ALTER TABLE products
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP DEFAULT NULL;

-- Add index for performance (filtering deleted products)
CREATE INDEX IF NOT EXISTS idx_products_deleted_at ON products(deleted_at);

-- Add composite index for common queries (status + deleted_at)
CREATE INDEX IF NOT EXISTS idx_products_status_deleted ON products(status, deleted_at);

-- Add comment for documentation
COMMENT ON COLUMN products.deleted_at IS 'Timestamp when product was soft deleted. NULL = active, NOT NULL = deleted. Preserves data for purchased products.';
