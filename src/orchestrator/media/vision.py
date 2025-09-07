# orchestrator/media/vision.py
"""
Skeleton for image understanding using GPT-4o Vision.
Provide functions to:
- extract_text_from_images(attachments)
- extract_structured_fields(text)

Implementation details (to be filled by dev team):
- Accept URLs or base64 images
- Call GPT-4o with multi-part content (image + instruction)
- Return plain text plus structured entities (booking_id, date, route_from, route_to, trip_id)
"""

from typing import List, Dict, Tuple

def extract_text_from_images(attachments: List[str]) -> str:
    """Return concatenated textual summary extracted from images (placeholder)."""
    return ""

def extract_structured_fields(text: str) -> Dict[str, str]:
    """Parse important fields from extracted text (placeholder)."""
    return {}


