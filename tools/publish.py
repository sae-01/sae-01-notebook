"""Publish the public part of my folder to my notebook repo.

    python tools/publish.py stage            # copy, privacy check, tests, show diff
    python tools/publish.py push "message"   # stage again, then commit and push

Only files listed in public/manifest.txt go out. The notebook clone lives
in <my folder>/notebook (gitignored) and is wired so pushes can only use the
sae-01 login. A push needs a clean privacy check and passing tests on the
copy. Log every push in the journal (AGENTS.md exception).
"""
from __future__ import annotations

import argparse
import glob
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import privacy_check  # noqa: E402


def home() -> Path:
    """My main folder (the parent of the shared .git), even from a worktree."""
    out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"],
                         capture_output=True, text=True, encoding="utf-8", check=True)
    common = Path(out.stdout.strip())
    if not common.is_absolute():
        common = ROOT / common
    return common.resolve().parent


def manifest(root: Path) -> list[tuple[Path, str]]:
    """(source file, destination path) pairs from public/manifest.txt."""
    pairs = []
    for line in (root / "public" / "manifest.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        src, _, dest = (p.strip() for p in line.partition("->"))
        matches = sorted(glob.glob(str(root / src)))
        if not matches:
            raise SystemExit(f"manifest: nothing matches {src!r}")
        for m in matches:
            m = Path(m)
            if not dest:
                d = m.relative_to(root).as_posix()
            elif dest.endswith("/"):
                d = dest + m.name
            else:
                d = dest
            pairs.append((m, d))
    return pairs


def stage(nb: Path) -> bool:
    """Mirror the manifest into the clone; return True if checks pass."""
    for item in nb.iterdir():
        if item.name == ".git":
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()
    for src, dest in manifest(ROOT):
        out = nb / dest
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)

    terms_file = home() / "privacy.txt"
    if not terms_file.exists():
        print("STOP: no privacy.txt in my folder; refusing to stage.")
        return False
    terms = privacy_check.load_terms(terms_file)
    findings = privacy_check.scan_paths([nb], nb, terms)
    for rel, line, kind, match in findings:
        print(f"PRIVACY {rel}:{line}: {kind}")  # match not echoed on purpose
    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                           cwd=nb, capture_output=True, text=True, encoding="utf-8")
    last = (tests.stderr.strip().splitlines() or ["?"])[-1]
    print(f"tests: {last}")
    status = subprocess.run(["git", "-C", str(nb), "status", "--short"],
                            capture_output=True, text=True, encoding="utf-8").stdout
    print(status or "(no changes)")
    return not findings and tests.returncode == 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Publish my notebook.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stage")
    push = sub.add_parser("push")
    push.add_argument("message")
    args = p.parse_args(argv)

    nb = home() / "notebook"
    if not (nb / ".git").exists():
        print(f"no clone at {nb.name}/; see memory/notes.md")
        return 1
    ok = stage(nb)
    if not ok:
        print("NOT clean: fix the above before pushing.")
        return 1
    if args.cmd == "stage":
        print("clean: ready to push")
        return 0
    git = ["git", "-C", str(nb)]
    subprocess.run(git + ["add", "-A"], check=True)
    if subprocess.run(git + ["diff", "--cached", "--quiet"]).returncode == 0:
        print("nothing to publish")
        return 0
    subprocess.run(git + ["commit", "-q", "-m", args.message], check=True)
    subprocess.run(git + ["push", "-q", "origin", "HEAD:main"], check=True)
    head = subprocess.run(git + ["log", "--oneline", "-1"], capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()
    print(f"published: {head}")
    print("now log it: python tools/journal.py \"Published ...\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
