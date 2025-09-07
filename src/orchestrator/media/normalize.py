# orchestrator/media/normalize.py
"""
Normalization helpers for media-derived text:
- normalize_text_to_entities(media_text) -> structured_entities
  - Normalize date to YYYY-MM-DD
  - Map place aliases (TPHCM/HCMC/SG → HCM)
  - Validate booking_id/trip_id patterns
"""

from typing import Dict

def normalize_text_to_entities(media_text: str) -> Dict[str, str]:
    """Return structured fields parsed from media text (placeholder)."""
    return {}


