"""
Legal Sources — Fetchers

Modules de téléchargement des données juridiques.
"""

from .base import BaseFetcher, PisteAuthMixin
from .judilibre import JudilibreFetcher
from .legifrance import LegiFranceFetcher

__all__ = [
    "BaseFetcher",
    "PisteAuthMixin",
    "JudilibreFetcher",
    "LegiFranceFetcher",
]
