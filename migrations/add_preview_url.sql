-- Migration: Ajouter colonne preview_url pour aperçus PDF générés côté client
-- Date: 2025-12-07
-- Objectif: Stocker l'URL de l'aperçu pré-généré (première page PDF) pour éviter
--           la génération côté serveur et améliorer les performances

-- Ajouter colonne preview_url
ALTER TABLE products
ADD COLUMN IF NOT EXISTS preview_url TEXT;

-- Créer index pour optimiser les requêtes
CREATE INDEX IF NOT EXISTS idx_products_preview_url
ON products(preview_url)
WHERE preview_url IS NOT NULL;

-- Commentaire pour documentation
COMMENT ON COLUMN products.preview_url IS 'URL B2 de l''aperçu (première page PDF en PNG) généré lors de l''upload via miniapp';
