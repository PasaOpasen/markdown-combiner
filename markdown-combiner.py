

from typing import Optional, Tuple, List, Union, Literal, Dict, Sequence, Any

import os
import sys
import argparse

from pathlib import Path

import re

from dataclasses import dataclass

from traceback import print_exc

#region CONSTANTS

IS_WINDOWS = sys.platform == 'win32'

HEADING_RE = re.compile(
    r"^#+\s+\d+(\.\d+)*(\s.*)?$",
    re.MULTILINE
)

start_to_type: Dict[str, Literal['put', 'shell']] = {
    '@@': 'shell',
    '@put@': 'put'
}
"""command start to the string type of the command"""


type_to_start = {t: s for s, t in start_to_type.items()}

#endregion


#region UTILS

def read_text(path: Union[str, os.PathLike], encoding: str = 'utf-8'):
    return Path(path).read_text(encoding=encoding, errors='ignore')


def write_text(path: Union[str, os.PathLike], text: str, encoding: str = 'utf-8'):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding=encoding)


def get_cmd_output(command: Union[str, Sequence[Any]], cwd: Optional[str] = None):
    """runs shell command and returns its output"""
    import subprocess

    if isinstance(command, str):
        args = command.split()
    else:
        args = [str(c) for c in command]
    return subprocess.check_output(
        args,
        shell=True,
        cwd=cwd
    ).decode('utf-8', 'replace').strip()


def get_backticks_indexes(text: str):
    """
    Searches and filters indexes of backticks (`)
    Args:
        text:

    Returns:

    """

    res = []
    start = 0
    last_index = len(text) - 1

    while True:
        new_line = text.find('\n', start)
        if new_line < 0:
            new_line = last_index

        # find all backticks in this string
        backticks = [
            s.start() for s in re.finditer('`', text[start:new_line])
        ]

        #
        # keep backticks only if there are 3 in line or even count in line
        #
        if len(backticks) % 2 == 0 or len(backticks) == 3:
            res.extend(
                b + start for b in backticks
            )
        # else:
        #     print(text[start:new_line])

        if new_line == last_index:
            break
        start = new_line + 1


    return backticks

#endregion


#region HEADINGS

@dataclass
class Heading:
    """wrapper on Markdown heading and the text after it"""

    start_index: int
    end_index: int


    level: int = 0
    """the level means the count of # in the heading"""

    tag: str = ''
    """numeric tag like 5.4.2"""

    title: str = ''
    """the text after tag"""

    text: str = ''
    """the text after heading line but before next heading"""

    @staticmethod
    def from_str(text: str, start: int, end: int):
        """

        Args:
            text: the text to construct the heading from
            start: index of first #
            end: index of next heading #

        Returns:

        """

        head, txt = text[start: end].split('\n', 1)
        sharps, other = head.split(' ', 1)
        tag, title = other.split(' ', 1)
        return Heading(
            start_index=start,
            end_index=end,
            level=len(sharps),
            tag=tag,
            title=title,
            text=txt
        )

    def as_string(self, additional_level: str = ''):

        add_levels = len(additional_level.split('.'))
        if additional_level:
            additional_level += '.'

        return (
            f"{'#' * (self.level + add_levels)} {additional_level + self.tag} {self.title}\n{self.text}"
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

        backticks = get_backticks_indexes(text)
        """backticks indexes"""

        if len(backticks) > 1:  # some heading candidates maybe must be removed

            code_intervals = [
                (a, b)
                for a, b in zip(backticks[::2], backticks[1::2])
                if b - a > 1  # filter useless
            ]
            """intervals with code between them, like `this`"""

            to_remove = set()
            for h in heading_candidates:
                if h < backticks[0] or h > backticks[-1]:
                    continue

                if any(
                    a < h < b for a, b in code_intervals
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
                Heading.from_str(text, s, e)
            )

        return init_string, headings

    @staticmethod
    def add_headings(text: str, additional_level: str = ''):
        if not additional_level:
            return text

        init_s, headings = Heading.extract_headings(text)
        return init_s + ''.join(h.as_string(additional_level=additional_level) for h in headings)

    @staticmethod
    def get_sectors_map(text: str) -> Dict[Tuple[int, int], str]:
        """
        returns sectors map of text symbols intervals
        Args:
            text:

        Returns:
            dict like {(0, 10): '', (10, 15): '1', (15, 20): '1.1'}
        """

        init_s, headings = Heading.extract_headings(text)
        result = {
            (h.start_index, h.end_index): h.tag
            for h in headings
        }

        if init_s:
            result[(0, len(init_s))] = ''

        return result

#endregion

#region HPARSER CLI


class kvdictAppendAction(argparse.Action):
    """
    argparse action to split an argument into KEY=VALUE form
    on the first = and append to a dictionary.
    """
    def __call__(self, parser, args, values, option_string=None):
        assert(len(values) == 1)
        try:
            (k, v) = values[0].split("=", 2)
        except ValueError as ex:
            raise argparse.ArgumentError(self, f"could not parse argument \"{values[0]}\" as k=v format")
        d = getattr(args, self.dest) or {}
        d[k] = v
        setattr(args, self.dest, d)


hparser = argparse.ArgumentParser(
    prog='@put@ inner command parser',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)

hparser.add_argument(
    'FILE', action='store', type=str, nargs='+',
    help=(
        'file to put, absolute path or the path relative to file contains current directive; '
        'if u put several files the first existing will be chosen'
    ),
)
hparser.add_argument(
    '--start-after', '-s', action='store', type=str,
    help='use only text after the last line contains this pattern matching',
    dest='start_after'
)

hparser.add_argument(
    '--ends-before', '-e', action='store', type=str,
    help='use only text before the first line contains this pattern matching',
    dest='end_before'
)

hparser.add_argument(
    '--strip', '-t', action='store_true',
    help='strip output text',
    dest='strip'
)

hparser.add_argument(
    "--replace", "-r",
    nargs=1,
    action=kvdictAppendAction,
    metavar="KEY=VALUE",
    default={},
    type=str,
    help="Add replacing in format like OLD=NEW. May appear multiple times",
    dest='replaces'
)

hparser.add_argument(
    '--allow-file-not-found', '-l', action='store_true',
    help='skip commands with unknown file',
    dest='allow_file_not_found'
)

#endregion


class Command:

    RE = re.compile(
        f"({'|'.join(start_to_type.keys())})[^@]+@@"
    )

    __slots__ = ('command', 'type', 'file')

    def __init__(self, text: str, from_file: str):
        """
        Args:
            text: command like @@echo 1@@ or @put@file.md -s ---@@
            from_file: the file the command come from
        """

        for s, t in start_to_type.items():
            if text.startswith(s):
                self.command = text[len(s):].rstrip('@')
                self.type = t
                break
        else:
            raise ValueError(f"unknown command type: {text}")

        assert self.command, 'empty command'

        self.file = from_file

    @property
    def short_string(self):
        return f"{type_to_start[self.type]}{self.command}@@"

    def __str__(self):
        return (
            f"{self.short_string} (in file {self.file})"
        )

    def _select_file(
        self,
        directory: str,
        candidates: Sequence[str],
        allow_file_not_found: bool = False
    ) -> str:
        """from several file candidates selects the first existing file"""

        for i, f in enumerate(candidates):

            if not os.path.exists(f):
                n = os.path.join(directory, f)
                if not os.path.exists(n):
                    message = f"not found file {f} using in command {self}"

                    if i == len(candidates) - 1:  # the last attempt
                        if allow_file_not_found:
                            print(message)
                            return self.short_string

                        raise FileNotFoundError(message)
                    else:
                        message += f"\n\twill try next files: {candidates[i+1:]}"
                        print(message)
                        continue
                f = n

            #
            # file found
            #
            if i != 0:  # not from first attempt
                print(f"\tOK {f} file is chosen")
            return f

    def _exec_shell(self, directory: str, **kwargs) -> str:

        print(f"Executing {self}")

        _f = lambda: get_cmd_output(self.command, cwd=directory)
        f = _f
        if kwargs.get('parsed_namespace').ignore_shell_errors:
            def f():
                try:
                    return _f()
                except Exception:
                    print(
                        f"Some shell error on command {self.short_string} in file {self.file}, ignored"
                    )
                    print_exc()
                    print()
                    return self.short_string

        if IS_WINDOWS:
            try:
                return f()
            except OSError:
                print_exc()
                return self.short_string

        return f()

    def _exec_put(self, directory: str, additional_level: str = '', **kwargs) -> str:
        parsed = hparser.parse_args(self.command.split())

        files_to_try = parsed.FILE
        pattern_start = parsed.start_after
        pattern_end = parsed.end_before

        f = self._select_file(
            directory=directory, candidates=files_to_try,
            allow_file_not_found=parsed.allow_file_not_found
        )
        if f == self.short_string:  # file not found
            return f

        directory = os.path.dirname(f)
        text = read_text(f)

        def get_matches(pattern: str) -> List[re.Match]:
            pattern = pattern.strip("'")
            e = re.compile(pattern, flags=re.MULTILINE)
            _matches = [
                m for m in e.finditer(text)
                if not Command.RE.match(
                    text[
                        text.rfind('\n', 0, m.start()) + 1:text.find('\n', m.end())
                    ]
                )
            ]
            """the matches of the pattern but outside of commands"""
            return _matches

        if pattern_start:
            matches = get_matches(pattern_start)
            if matches:
                end_match = matches[-1].end()
                end_match = text.find('\n', end_match) + 1
                """the index of first text symbol after the line contains the match"""
                text = text[end_match:]

        if pattern_end:
            matches = get_matches(pattern_end)
            if matches:
                start_match = matches[0].start()
                start_match = text.rfind('\n', 0, start_match) + 1
                """the index of last text symbol before the line contains the match"""
                text = text[:start_match]

        text = Command.translate_text(
            text,
            directory=directory,
            file_name=f,

            parsed_namespace=kwargs.get('parsed_namespace')
        )

        if f.endswith('.md'):  # additional markdown process
            text = Heading.add_headings(text, additional_level=additional_level)

        if parsed.strip:
            text = text.strip()

        if parsed.replaces:
            for old, new in parsed.replaces.items():
                text = text.replace(old, new)

        return text


    def exec(self, *args, **kwargs) -> str:
        f = getattr(self, f"_exec_{self.type}", None)
        assert f is not None, f"no exec func for type {self.type}"
        return f(*args, **kwargs)

    @staticmethod
    def translate_text(
        file_text: str,
        directory: str,
        file_name: str,
        parsed_namespace: argparse.Namespace
    ) -> str:

        matches = [(m.start(), m.end()) for m in Command.RE.finditer(file_text)]
        if not matches:
            return file_text

        if file_name.endswith('.md'):  # get sectors for markdown
            sectors = Heading.get_sectors_map(file_text)
        else:
            sectors = {(0, len(file_text)): ''}

        def get_sector(index: int) -> str:
            """returns the sector for current index"""
            for (_s, _e), r in sectors.items():
                if _s <= index < _e:
                    return r
            raise ValueError(f"no sector for index {index}, exist only {sectors}")

        def translate(pos: Tuple[int, int]) -> str:
            """executes the command on this position"""
            _s, _e = pos
            return Command(file_text[_s:_e], from_file=file_name).exec(
                additional_level=get_sector(_s),
                directory=directory,
                parsed_namespace=parsed_namespace
            )

        texts = []
        """collected parts of the file as text"""

        if matches[0][0] > 0:  # file does not start from command
            texts.append(file_text[:matches[0][0]])

        for command, next_command in zip(matches[:-1], matches[1:]):

            texts.append(translate(command))

            #
            # add the text between commands
            #
            s = command[-1]
            e = next_command[0]
            if e != s + 1:
                texts.append(file_text[s:e])

        texts.append(
            translate(matches[-1])
        )
        le = matches[-1][-1]
        if le != len(file_text):
            texts.append(file_text[le:])

        return ''.join(texts)

    @staticmethod
    def translate_file(path: str, parsed_namespace: argparse.Namespace) -> str:
        return Command.translate_text(
            file_text=read_text(path),
            directory=str(Path(path).parent.absolute()),
            file_name=path,
            parsed_namespace=parsed_namespace
        )


#region CLI

mparser = argparse.ArgumentParser(
    prog='markdown-combiner.py',
    description=(
        'Script which combines several files with shell insertions execution and special features for *.md files'
    ),
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)

mparser.add_argument('INPUT_FILE', type=str, help='Text file to process')
mparser.add_argument('OUTPUT_FILE', type=str, help='Path to save the output document')
mparser.add_argument(
    '-e', '--ignore-shell-errors', action='store_true',
    help='whether to ignore errors on shell commands',
    dest='ignore_shell_errors'
)


def main():

    args = sys.argv[1:]

    if os.getenv('PARSER', 'main') != 'main':
        parsed = hparser.parse_args()
        return

    parsed = mparser.parse_args(args)

    write_text(
        parsed.OUTPUT_FILE,
        text=Command.translate_file(
            parsed.INPUT_FILE,
            parsed_namespace=parsed
        ),
    )

    print(f"\n\n{parsed.INPUT_FILE} is successfully translated to {parsed.OUTPUT_FILE}")


#endregion


if __name__ == '__main__':

    # # Heading.extract_headings(read_text('test/README.md'))
    # write_text(
    #     'result.md',
    #     # Command.translate_file('test/README.md'),
    #     # Command.translate_file('test/example2.md'),
    #     Command.translate_file('../docutable/README.md'),
    # )

    main()


