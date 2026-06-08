"""Deck ingestion: PDF/PPTX upload -> draft scene matrix (human confirms)."""

from .extractor import DeckExtractor, extract_deck

__all__ = ["DeckExtractor", "extract_deck"]
