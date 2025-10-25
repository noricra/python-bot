"""
Image Utilities - Thumbnail generation, compression, and placeholder creation
"""
import os
import logging
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import hashlib

logger = logging.getLogger(__name__)


class ImageUtils:
    """Utilities for image processing and thumbnail generation"""

    # Category color mapping for placeholders
    CATEGORY_COLORS = {
        'Finance & Crypto': '#10B981',      # Green
        'Marketing Digital': '#3B82F6',    # Blue
        'Développement': '#8B5CF6',        # Purple
        'Design & Créatif': '#EC4899',     # Pink
        'Business': '#F59E0B',             # Orange
        'Formation Pro': '#06B6D4',        # Cyan
        'Outils & Tech': '#6366F1',        # Indigo
        'default': '#5EEAD4'               # Teal (fallback)
    }

    @staticmethod
    def generate_thumbnail(image_path: str, output_path: str, size: tuple = (1280, 1280)):
        """
        Generate HIGH QUALITY thumbnail from image with CENTER CROP

        QUALITY OPTIMIZATIONS:
        - Large size (1280x1280) for maximum detail and sharpness
        - BICUBIC resampling for sharper edges (no blur)
        - Quality 98 for maximum clarity
        - NO blur on borders

        Args:
            image_path: Path to source image
            output_path: Path to save thumbnail
            size: Thumbnail size (default 1280x1280 for high quality)

        Returns:
            bool: Success status
        """
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed (handles RGBA, P, etc.)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Calculate resize to fill target size (crop instead of padding)
                img_ratio = img.width / img.height
                target_ratio = size[0] / size[1]

                if img_ratio > target_ratio:
                    # Image is wider - resize based on height, then crop width
                    new_height = size[1]
                    new_width = int(new_height * img_ratio)
                else:
                    # Image is taller - resize based on width, then crop height
                    new_width = size[0]
                    new_height = int(new_width / img_ratio)

                # Resize with BICUBIC for SHARP edges (no blur like LANCZOS)
                img = img.resize((new_width, new_height), Image.Resampling.BICUBIC)

                # Calculate crop box (center crop)
                left = (new_width - size[0]) // 2
                top = (new_height - size[1]) // 2
                right = left + size[0]
                bottom = top + size[1]

                # Crop to exact size
                img = img.crop((left, top, right, bottom))

                # Save with MAXIMUM quality (98 - near lossless)
                img.save(output_path, 'JPEG', quality=98, optimize=True)

            logger.info(f"✅ High-quality thumbnail created: {output_path} ({size[0]}x{size[1]}px, Q98)")
            return True

        except Exception as e:
            logger.error(f"❌ Error generating thumbnail: {e}")
            return False

    @staticmethod
    def compress_for_telegram(image_path: str, max_size_kb: int = 3000) -> str:
        """
        Compress image for Telegram with HIGH QUALITY preservation

        Args:
            image_path: Path to image to compress
            max_size_kb: Maximum size in KB (default 3MB for better quality)

        Returns:
            str: Path to compressed image (or original if already small enough)
        """
        try:
            file_size_kb = os.path.getsize(image_path) / 1024

            # Already small enough
            if file_size_kb <= max_size_kb:
                logger.info(f"✅ Image already optimal: {file_size_kb:.1f}KB")
                return image_path

            output_path = image_path.replace('.jpg', '_compressed.jpg').replace('.jpeg', '_compressed.jpg')

            with Image.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Resize ONLY if extremely large (max 2048px width for HD quality)
                if img.width > 2048:
                    ratio = 2048 / img.width
                    new_size = (2048, int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    logger.info(f"📐 Resized to {new_size[0]}x{new_size[1]}px")

                # Binary search for optimal quality (start at 95, min 75)
                quality = 95
                while quality >= 75:
                    buffer = BytesIO()
                    img.save(buffer, 'JPEG', quality=quality, optimize=True)
                    size_kb = len(buffer.getvalue()) / 1024

                    if size_kb <= max_size_kb:
                        # Save to file
                        with open(output_path, 'wb') as f:
                            f.write(buffer.getvalue())
                        logger.info(f"✅ Image compressed: {size_kb:.1f}KB (quality={quality})")
                        return output_path

                    quality -= 3

                # Fallback: save at quality 75 (still good quality)
                img.save(output_path, 'JPEG', quality=75, optimize=True)
                final_size = os.path.getsize(output_path) / 1024
                logger.info(f"✅ Image compressed at min quality: {final_size:.1f}KB (quality=75)")
                return output_path

        except Exception as e:
            logger.error(f"❌ Error compressing image: {e}")
            return image_path  # Return original on error

    @staticmethod
    def generate_placeholder(
        product_title: str,
        category: str,
        output_path: str,
        size: tuple = (1280, 1280)
    ) -> bool:
        """
        Generate HIGH QUALITY gradient placeholder image with product initial

        Args:
            product_title: Product title (first letter used)
            category: Product category (determines color)
            output_path: Where to save placeholder
            size: Image size (default 1280x1280 for high quality)

        Returns:
            bool: Success status
        """
        try:
            # Get category color
            color = ImageUtils.CATEGORY_COLORS.get(category, ImageUtils.CATEGORY_COLORS['default'])

            # Create gradient background in HIGH resolution
            img = Image.new('RGB', size, color)
            draw = ImageDraw.Draw(img)

            # Darken gradient from top to bottom
            for y in range(size[1]):
                darkness = int(y / size[1] * 40)  # Max 40 darker
                current_color = ImageUtils._hex_to_rgb(color)
                darker_color = tuple(max(0, c - darkness) for c in current_color)
                draw.rectangle([(0, y), (size[0], y + 1)], fill=darker_color)

            # Add product initial in center
            initial = product_title[0].upper() if product_title else '?'

            # Try to use a nice font, fallback to default
            try:
                font_size = int(size[0] * 0.5)
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except:
                # Fallback to default font
                font = ImageFont.load_default()

            # Get text bounding box
            bbox = draw.textbbox((0, 0), initial, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Center text
            position = (
                (size[0] - text_width) // 2,
                (size[1] - text_height) // 2 - text_height // 4  # Adjust for font baseline
            )

            # Draw white text with shadow for depth
            shadow_offset = 4
            draw.text((position[0] + shadow_offset, position[1] + shadow_offset),
                     initial, fill=(0, 0, 0, 120), font=font)
            draw.text(position, initial, fill=(255, 255, 255), font=font)

            # Save with HIGH quality (98)
            img.save(output_path, 'JPEG', quality=98, optimize=True)
            logger.info(f"✅ High-quality placeholder generated: {output_path} ({size[0]}x{size[1]}px)")
            return True

        except Exception as e:
            logger.error(f"❌ Error generating placeholder: {e}")
            return False

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color (#RRGGBB) to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def get_image_hash(image_path: str) -> str:
        """Generate MD5 hash of image for caching/deduplication"""
        try:
            with open(image_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"❌ Error hashing image: {e}")
            return None

    @staticmethod
    def ensure_product_image_dir(seller_id: int, product_id: str) -> str:
        """
        Create product image directory structure

        Returns:
            str: ABSOLUTE path to product image directory
        """
        from app.core.settings import get_absolute_path

        # Build relative path
        base_dir_rel = os.path.join('data', 'product_images', str(seller_id), product_id)

        # Convert to absolute path
        base_dir = get_absolute_path(base_dir_rel)
        os.makedirs(base_dir, exist_ok=True)

        logger.info(f"📁 Product image directory: {base_dir}")
        return base_dir

    @staticmethod
    def save_telegram_photo(file_path: str, seller_id: int, product_id: str) -> tuple:
        """
        Save Telegram photo SANS ALTÉRER L'ORIGINAL

        Stratégie:
        1. TOUJOURS garder l'original (cover_original.jpg)
        2. Créer version optimisée Telegram si besoin (cover.jpg)
        3. Générer thumbnail depuis l'original haute qualité

        Args:
            file_path: Path to downloaded Telegram photo
            seller_id: Seller user ID
            product_id: Product ID

        Returns:
            tuple: (cover_path, thumbnail_path) or (None, None) on error
        """
        try:
            # Create directory
            product_dir = ImageUtils.ensure_product_image_dir(seller_id, product_id)

            # Define paths
            original_path = os.path.join(product_dir, 'cover_original.jpg')
            cover_path = os.path.join(product_dir, 'cover.jpg')
            thumbnail_path = os.path.join(product_dir, 'thumb.jpg')

            # 1. TOUJOURS sauver l'original intact (JAMAIS altéré)
            with open(file_path, 'rb') as src:
                with open(original_path, 'wb') as dst:
                    dst.write(src.read())
            logger.info(f"✅ Original saved (untouched): {original_path}")

            # 2. Vérifier si compression nécessaire
            file_size_kb = os.path.getsize(original_path) / 1024

            if file_size_kb <= 5000:  # 5MB = limite Telegram, pas besoin compresser
                # Original déjà bon pour Telegram, créer symlink ou copie
                import shutil
                shutil.copy2(original_path, cover_path)
                logger.info(f"✅ Original quality preserved: {file_size_kb:.1f}KB")
            else:
                # Créer version optimisée Telegram (sans toucher original)
                compressed = ImageUtils.compress_for_telegram(original_path, max_size_kb=5000)
                if compressed != original_path:
                    import shutil
                    shutil.copy2(compressed, cover_path)
                    os.remove(compressed)  # Cleanup temp file
                    logger.info(f"✅ Telegram-optimized version created")
                else:
                    shutil.copy2(original_path, cover_path)

            # 3. Générer thumbnail DEPUIS L'ORIGINAL (meilleure qualité)
            success = ImageUtils.generate_thumbnail(original_path, thumbnail_path)

            if not success:
                logger.error("Failed to generate thumbnail")
                return None, None

            logger.info(f"✅ Product images saved: original + cover + thumb")
            return cover_path, thumbnail_path

        except Exception as e:
            logger.error(f"❌ Error saving product photo: {e}")
            return None, None

    @staticmethod
    def create_or_get_placeholder(product_title: str, category: str, product_id: str) -> str:
        """
        Get existing placeholder or create new one

        Returns:
            str: ABSOLUTE path to placeholder image
        """
        from app.core.settings import get_absolute_path

        # Placeholder directory (relative)
        placeholder_dir_rel = os.path.join('data', 'product_images', 'placeholders')

        # Convert to absolute path
        placeholder_dir = get_absolute_path(placeholder_dir_rel)
        os.makedirs(placeholder_dir, exist_ok=True)

        # Use hash of category for filename to cache
        category_hash = hashlib.md5(category.encode()).hexdigest()[:8]
        placeholder_path = os.path.join(placeholder_dir, f'{category_hash}_{product_id}.jpg')

        # Check if already exists
        if os.path.exists(placeholder_path):
            logger.info(f"✅ Using cached placeholder: {placeholder_path}")
            return placeholder_path

        # Generate new placeholder
        success = ImageUtils.generate_placeholder(
            product_title=product_title,
            category=category,
            output_path=placeholder_path
        )

        return placeholder_path if success else None
