"""inkline — Markdown → Kindle EPUB3（公式精确基线对齐）。"""
from .pipeline import build
from .util import next_version, read_sources

__all__ = ['build', 'next_version', 'read_sources']
__version__ = '0.3.0'
