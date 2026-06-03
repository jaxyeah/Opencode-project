"""ZPL macro file manager — discovery, categorization, search."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from zpl_toolkit.types import MacroInfo

logger = logging.getLogger(__name__)

# ── Category detection rules ───────────────────────────────────

_CATEGORY_RULES: list[tuple[list[str], str]] = [
    (["tilt", "倾斜", "image orientation"], "tilt_analysis"),
    (["distortion", "畸变"], "distortion"),
    (["pvb", "楔角", "wedge", "lcb"], "wedge_analysis"),
    (["双目", "binocular", "viewing"], "binocular_viewing"),
    (["stp", ".stp", "cad", "export"], "cad_export"),
    (["hud", "hud"], "hud_analysis"),
    (["ghost", "杂光", "鬼影", "stray", "flare"], "ghost_analysis"),
    (["动态", "dynamic", "state"], "dynamic_analysis"),
    (["眼盒", "eyebox"], "eyebox_analysis"),
    (["mtf", "mtf"], "mtf_analysis"),
    (["focus", "调焦"], "focus_analysis"),
]


def _detect_category(filename_lower: str) -> str:
    """Detect macro category from filename heuristics."""
    for keywords, category in _CATEGORY_RULES:
        if any(kw in filename_lower for kw in keywords):
            return category
    return "general"


class ZPLManager:
    """Manages ZPL macro files — discovery, categorization, and search."""

    def discover(
        self,
        search_dir: str,
        recursive: bool = True,
    ) -> list[MacroInfo]:
        """Find all .ZPL files in a directory.

        Args:
            search_dir: Directory to search.
            recursive: If True, search subdirectories.

        Returns:
            List of MacroInfo for each discovered macro.

        Raises:
            FileNotFoundError: Directory does not exist.
        """
        root = Path(search_dir)
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {search_dir}")

        pattern = "**/*.ZPL" if recursive else "*.ZPL"
        matches = list(root.glob(pattern))

        macros: list[MacroInfo] = []
        for filepath in matches:
            if filepath.is_file():
                info = self.get_macro_info(str(filepath))
                macros.append(info)

        logger.info(
            "Discovered %d macros in %s (recursive=%s)",
            len(macros),
            search_dir,
            recursive,
        )
        return macros

    def get_macro_info(self, path: str) -> MacroInfo:
        """Get detailed info for a single macro file."""
        filepath = Path(path)
        stat = filepath.stat()

        # Count lines
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            lines = content.splitlines()
            line_count = len(lines)

            # Extract header comments (lines starting with ! or #)
            header: list[str] = []
            for line in lines[:30]:
                stripped = line.strip()
                if stripped.startswith(("!", "#")):
                    header.append(stripped)
                elif header and not stripped:
                    continue
                elif header:
                    break
        except Exception:
            line_count = 0
            header = []

        category = _detect_category(filepath.name.lower())

        return MacroInfo(
            path=str(filepath.resolve()),
            name=filepath.name,
            size=stat.st_size,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            category=category,
            line_count=line_count,
            header_comments=header,
        )

    def categorize(
        self, macros: list[MacroInfo]
    ) -> dict[str, list[MacroInfo]]:
        """Group macros by detected category."""
        groups: dict[str, list[MacroInfo]] = {}
        for m in macros:
            groups.setdefault(m.category, []).append(m)
        return dict(sorted(groups.items()))

    def search(
        self,
        search_dir: str,
        query: str,
        recursive: bool = True,
    ) -> list[MacroInfo]:
        """Search macros by filename or header content.

        Args:
            search_dir: Directory to search.
            query: Search term (case-insensitive).
            recursive: If True, search subdirectories.

        Returns:
            Matching MacroInfo objects.
        """
        query_lower = query.lower()
        all_macros = self.discover(search_dir, recursive=recursive)
        results: list[MacroInfo] = []

        for m in all_macros:
            # Match against filename
            if query_lower in m.name.lower():
                results.append(m)
                continue
            # Match against header comments
            for comment in m.header_comments:
                if query_lower in comment.lower():
                    results.append(m)
                    break

        logger.info(
            "Search '%s' → %d results (of %d macros)",
            query,
            len(results),
            len(all_macros),
        )
        return results
