"""
Image Service
=============
Provider-abstracted stock photo engine with multi-credential pools,
health-based routing, 24h TTL caching, and per-provider compliance.

Strictly uses Pexels, Pixabay, Unsplash (+ Wikimedia zero-key fallback).
NO AI image generation.
"""
from .service import ImageService, get_best_image

__all__ = ["ImageService", "get_best_image"]
