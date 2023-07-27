
from typing import Optional, Tuple, List

import os
import argparse

from pathlib import Path

import re

from dataclasses import dataclass


HEADING_RE = re.compile(
    r"^#+\s+\d+(\.\d+)*(\s.*)?$",
    re.MULTILINE
)


@dataclass
class Heading:

    level: int = 0
    """the level means the count of # in the heading"""

    tag: str = ''
    """numeric tag like 5.4.2"""

    title: str = ''
    """the text after tag"""

    text: str = ''
    """the text after heading line but before next heading"""

    @staticmethod
    def from_str(text: str):
        """

        Args:
            text: the text between first # and next heading #

        Returns:

        """

        head, txt = text.split('\n', 1)
        sharps, other = head.split(' ', 1)
        tag, title = other.split(' ', 1)
        return Heading(
            level=len(sharps),
            tag=tag,
            title=title,
            text=txt
        )

    @staticmethod
    def extract_headings(text: str) -> Tuple[str, List['Heading']]:

        headings: List[Heading] = []

        heading_candidates: List[int] = [
            s.start() for s in HEADING_RE.finditer(text)
        ]
        """starts of candidates to be headings"""

        if not heading_candidates:
            return text, headings

        backticks = [
            s.start() for s in re.finditer('`', text)
        ]
        """backticks indexes"""

        if len(backticks) > 1:  # some heading candidates maybe must be removed

            odds = backticks[::2]
            evens = backticks[1::2]

            to_remove = set()
            for h in heading_candidates:
                if h < backticks[0] or h > backticks[-1]:
                    continue

                if any(
                    a < h < b for a, b in zip(odds, evens)
                ):  # remove headings between odd and even ticks
                    to_remove.add(h)

            if to_remove:
                heading_candidates = sorted(set(heading_candidates) - to_remove)

            if not heading_candidates:
                return text, headings

        init_string = text[:heading_candidates[0]]
        """string content before first heading"""

        heading_candidates.append(len(text))
        for s, e in zip(heading_candidates[:-1], heading_candidates[1:]):
            headings.append(
                Heading.from_str(text[s:e])
            )

        return init_string, headings

    def as_string(self, additional_level: str = ''):

        add_levels = len(additional_level.split('.'))
        if additional_level:
            additional_level += '.'

        return (
            f"{'#' * (self.level + add_levels)} {additional_level + self.tag} {self.title}\n{self.text}"
        )



if __name__ == '__main__':

    Heading.extract_headings(Path('test/README.md').read_text(encoding='utf-8'))
