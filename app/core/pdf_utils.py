"""PDF utility functions for preview generation with PyMuPDF"""

import os
import tempfile
from typing import Optional
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

def generate_pdf_preview(pdf_path: str, max_width: int = 800, max_height: int = 600) -> Optional[BytesIO]:
    """
    Generate a preview image from the first page of a PDF

    Args:
        pdf_path: Path to the PDF file
        max_width: Maximum width for the preview image
        max_height: Maximum height for the preview image

    Returns:
        BytesIO object containing PNG image data, or None if failed
    """
    pdf_doc = None
    try:
        import fitz  # PyMuPDF

        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return None

        file_size = os.path.getsize(pdf_path)
        logger.info(f"Processing PDF: {pdf_path} ({file_size} bytes)")

        # Open PDF
        pdf_doc = fitz.open(pdf_path)
        if len(pdf_doc) == 0:
            logger.error("PDF has no pages")
            return None

        logger.info(f"PDF has {len(pdf_doc)} pages")

        # Get first page
        page = pdf_doc[0]
        logger.info(f"First page loaded: {page}")

        # Calculate zoom to fit within max dimensions
        rect = page.rect
        logger.info(f"Page dimensions: {rect.width} x {rect.height}")

        zoom_x = max_width / rect.width if rect.width > 0 else 1.0
        zoom_y = max_height / rect.height if rect.height > 0 else 1.0
        zoom = min(zoom_x, zoom_y, 2.0)  # Max zoom of 2x

        logger.info(f"Calculated zoom: {zoom:.2f}")

        # Create transformation matrix
        mat = fitz.Matrix(zoom, zoom)

        # Render page to pixmap with higher quality
        pix = page.get_pixmap(matrix=mat, alpha=False)
        logger.info(f"Pixmap generated: {pix.width} x {pix.height}")

        # Convert to PNG bytes
        png_data = pix.tobytes("png")
        logger.info(f"PNG data size: {len(png_data)} bytes")

        # Return as BytesIO
        preview_bytes = BytesIO(png_data)
        preview_bytes.seek(0)

        logger.info(f"Successfully generated PDF preview for {pdf_path}")
        return preview_bytes

    except ImportError:
        logger.error("PyMuPDF not installed - cannot generate PDF preview")
        return None
    except Exception as e:
        logger.error(f"Error generating PDF preview for {pdf_path}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None
    finally:
        # Ensure PDF is closed even if error occurs
        if pdf_doc:
            try:
                pdf_doc.close()
            except:
                pass

def get_pdf_info(pdf_path: str) -> dict:
    """
    Extract basic information from PDF

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary with PDF info (pages, title, etc.)
    """
    info = {
        'pages': 0,
        'title': '',
        'author': '',
        'file_size': 0,
        'has_preview': False
    }

    try:
        import fitz  # PyMuPDF

        if not os.path.exists(pdf_path):
            return info

        info['file_size'] = os.path.getsize(pdf_path)

        # Open PDF
        pdf_doc = fitz.open(pdf_path)
        info['pages'] = len(pdf_doc)

        # Get metadata
        metadata = pdf_doc.metadata
        info['title'] = metadata.get('title', '')
        info['author'] = metadata.get('author', '')

        # Check if we can generate preview
        if info['pages'] > 0:
            info['has_preview'] = True

        pdf_doc.close()

    except ImportError:
        logger.warning("PyMuPDF not available for PDF info extraction")
    except Exception as e:
        logger.error(f"Error extracting PDF info: {e}")

    return info

def is_pdf_file(file_path: str) -> bool:
    """Check if file is a PDF based on extension and magic bytes"""
    if not file_path or not os.path.exists(file_path):
        return False

    # Check extension
    if not file_path.lower().endswith('.pdf'):
        return False

    # Check magic bytes
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header.startswith(b'%PDF')
    except Exception:
        return False