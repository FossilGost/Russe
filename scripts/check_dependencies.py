"""Fast, offline dependency check before the Windows launcher invokes pip."""
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import re
import sys


def ready(lock, requirements=None):
    for line in Path(lock).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s;]+)', line)
        if not match:
            return False
        try:
            if version(match[1]) != match[2]:
                return False
        except PackageNotFoundError:
            return False
    if requirements is not None:
        for line in Path(requirements).read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.fullmatch(r'([A-Za-z0-9_.-]+)(.*)',line)
            if not match:
                return False
            try:
                installed = version(match[1])
            except PackageNotFoundError:
                return False
            if not re.fullmatch(r'\d+(?:\.\d+)*',installed):
                return False  # Unusual versions/specifications go through pip.
            current = tuple((list(map(int,installed.split('.')))+[0]*8)[:8])
            for spec in filter(None,match[2].split(',')):
                constraint = re.fullmatch(r'(>=|<=|==|!=|<|>)(\d+(?:\.\d+)*)',spec)
                if not constraint:
                    return False
                target = tuple((list(map(int,constraint[2].split('.')))+[0]*8)[:8])
                if not {'>=':current>=target,'<=':current<=target,'==':current==target,
                        '!=':current!=target,'<':current<target,'>':current>target}[constraint[1]]:
                    return False
    return True


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    sys.exit(0 if ready(root/'requirements.lock',root/'requirements.txt') else 1)
