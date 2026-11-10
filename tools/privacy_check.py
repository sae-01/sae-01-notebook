"""Privacy checker: flag private info before files are published.

Usage: python tools/privacy_check.py [paths...]
Default: whole repo root. Exit 1 if anything is found, else print "clean".

Patterns: built-in generic ones below, plus literal terms from the local,
never-published `privacy.txt` at the repo root (see privacy.example.txt).
A line containing the marker "privacy:ok" is skipped.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = "privacy:ok"
TERMS_FILE = "privacy.txt"
EXTS = {".md", ".py", ".txt", ".json", ".toml", ".yml", ".yaml", ".cfg"}

PATTERNS = [  # (kind, regex)
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")),  # privacy:ok
    ("winpath", re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s\"'`<>|*?)\]]*")),  # privacy:ok
    ("homepath", re.compile(r"/(?:Users|home)/[^\s/\\\"'`<>]+")),  # privacy:ok
    ("ip", re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?!\d)(?!\.\d)")),  # privacy:ok
    ("secret", re.compile(r"sk-\w{20,}")),  # privacy:ok
    ("secret", re.compile(r"gh[po]_\w{16,}")),  # privacy:ok
    ("secret", re.compile(r"github_pat_\w{16,}")),  # privacy:ok
    ("secret", re.compile(r"AKIA[A-Z0-9]{16}")),  # privacy:ok
    ("secret", re.compile(r"(?i)\b(?:password|api_key|token)\b\s*[=:]\s*\S+")),  # privacy:ok
]


def load_terms(path):
    """Read one term per line; '#' comments and blank lines ignored."""
    p = Path(path)
    if not p.is_file():
        return []
    terms = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return terms


def _term_regex(term):
    pre = r"(?<!\w)" if term[0].isalnum() or term[0] == "_" else ""
    post = r"(?!\w)" if term[-1].isalnum() or term[-1] == "_" else ""
    return re.compile(pre + re.escape(term) + post, re.IGNORECASE)


def scan_text(text, terms):
    """Return [(line_no, kind, match)] for one text blob."""
    term_res = [_term_regex(t) for t in terms if t]
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        if MARKER in line:
            continue
        for kind, rx in PATTERNS:
            for m in rx.finditer(line):
                found.append((n, kind, m.group(0)))
        for rx in term_res:
            for m in rx.finditer(line):
                found.append((n, "term", m.group(0)))
    return found


def _iter_files(path):
    if path.is_file():
        yield path
        return
    for p in sorted(path.rglob("*")):
        if ".git" in p.parts or not p.is_file() or p.suffix.lower() not in EXTS:
            continue
        yield p


def _rel(p, root):
    try:
        return p.resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(p)


def scan_paths(paths, root, terms):
    """Return [(relpath, line, kind, match)] across files/dirs."""
    out = []
    for raw in paths:
        for f in _iter_files(Path(raw)):
            if f.name == TERMS_FILE or ".git" in f.parts:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            rel = _rel(f, root)
            for n, kind, match in scan_text(text, terms):
                out.append((rel, n, kind, match))
    return out


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    terms_path = ROOT / TERMS_FILE
    if not terms_path.is_file():
        print("no privacy.txt: only generic patterns checked", file=sys.stderr)
    terms = load_terms(terms_path)
    findings = scan_paths(argv or [ROOT], ROOT, terms)
    for rel, n, kind, match in findings:
        shown = match[:4] + "…" if kind == "secret" else match
        print(f"{rel}:{n}: {kind}: {shown}")
    if findings:
        print(f"{len(findings)} finding(s)")
        return 1
    print("clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
