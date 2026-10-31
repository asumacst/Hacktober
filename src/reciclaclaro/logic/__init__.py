"""Catalogo y comparacion deterministica, independientes de la IA y de la UI."""

from .catalog import load_centers
from .comparator import compare_item, compare_items

__all__ = ["load_centers", "compare_item", "compare_items"]
