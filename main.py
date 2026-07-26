#!/usr/bin/env python3
"""
kdbx_diff.py - Compare 2 or 3 KDBX files and show differences.

Usage:
    python kdbx_diff.py a.kdbx b.kdbx
    python kdbx_diff.py a.kdbx b.kdbx c.kdbx
    python kdbx_diff.py a.kdbx b.kdbx --show-passwords
    python kdbx_diff.py a.kdbx b.kdbx --passwords pass1 pass2

Requires: pip install pykeepass
"""

import sys
import getpass
import argparse

try:
    from pykeepass import PyKeePass
except ImportError:
    print("Missing dependency: pip install pykeepass", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

USE_COLOR = sys.stdout.isatty()

def _c(*codes):
    return "\033[" + ";".join(str(c) for c in codes) + "m" if USE_COLOR else ""

RED    = _c(31)
GREEN  = _c(32)
YELLOW = _c(33)
CYAN   = _c(36)
BOLD   = _c(1)
DIM    = _c(2)
RESET  = _c(0)

# ---------------------------------------------------------------------------
# KDBX helpers
# ---------------------------------------------------------------------------

TRACKED_FIELDS = ["title", "username", "password", "url", "notes"]

def entry_path(entry):
    parts = []
    g = entry.group
    while g and g.name:
        parts.insert(0, g.name)
        g = g.parentgroup
    parts.append(entry.title or "<no title>")
    return "/".join(parts)

def entry_to_dict(entry):
    d = {f: (getattr(entry, f) or "") for f in TRACKED_FIELDS}
    d["tags"] = ", ".join(sorted(entry.tags)) if entry.tags else ""
    for k, v in (entry.custom_properties or {}).items():
        d[f"custom:{k}"] = v or ""
    return d

def load_db(path, password=None, keyfile=None):
    if password is None:
        password = getpass.getpass(f"Password for {path}: ")
    try:
        return PyKeePass(path, password=password, keyfile=keyfile)
    except Exception as exc:
        print(f"{RED}Cannot open {path}: {exc}{RESET}", file=sys.stderr)
        sys.exit(1)

def entries_by_uuid(db):
    return {str(e.uuid): e for e in db.entries}

# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare(db_a, db_b):
    """Return (added, removed, modified) between db_a and db_b."""
    ea = entries_by_uuid(db_a)
    eb = entries_by_uuid(db_b)
    sa, sb = set(ea), set(eb)

    added   = [(uid, eb[uid]) for uid in sorted(sb - sa)]
    removed = [(uid, ea[uid]) for uid in sorted(sa - sb)]

    modified = []
    for uid in sorted(sa & sb):
        da = entry_to_dict(ea[uid])
        db_ = entry_to_dict(eb[uid])
        all_keys = sorted(set(da) | set(db_))
        diffs = {k: (da.get(k, ""), db_.get(k, "")) for k in all_keys if da.get(k, "") != db_.get(k, "")}
        if diffs:
            modified.append((uid, ea[uid], eb[uid], diffs))

    return added, removed, modified

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def _short_uuid(uid):
    return uid[:8] + "..."

def _display_value(value, field, show_passwords):
    if field == "password" and not show_passwords:
        return "***" if value else "(empty)"
    return repr(value) if not value else value

def print_comparison(added, removed, modified, label_a, label_b, show_passwords):
    header = f"{BOLD}{CYAN}{'─'*6}  {label_a}  vs  {label_b}  {'─'*6}{RESET}"
    print(f"\n{header}")

    if not added and not removed and not modified:
        print(f"  {GREEN}{BOLD}Identical{RESET} - no differences found.\n")
        return

    # --- Added ---
    if added:
        print(f"\n  {GREEN}{BOLD}+ Added in '{label_b}'{RESET}  ({len(added)} entr{'y' if len(added)==1 else 'ies'})")
        for uid, entry in sorted(added, key=lambda x: entry_path(x[1]).lower()):
            print(f"    {GREEN}+{RESET} {BOLD}{entry_path(entry)}{RESET}  {DIM}[{_short_uuid(uid)}]{RESET}")

    # --- Removed ---
    if removed:
        print(f"\n  {RED}{BOLD}- Removed from '{label_b}'{RESET}  ({len(removed)} entr{'y' if len(removed)==1 else 'ies'})")
        for uid, entry in sorted(removed, key=lambda x: entry_path(x[1]).lower()):
            print(f"    {RED}-{RESET} {BOLD}{entry_path(entry)}{RESET}  {DIM}[{_short_uuid(uid)}]{RESET}")

    # --- Modified ---
    if modified:
        print(f"\n  {YELLOW}{BOLD}~ Modified{RESET}  ({len(modified)} entr{'y' if len(modified)==1 else 'ies'})")
        for uid, entry_a, _entry_b, diffs in sorted(modified, key=lambda x: entry_path(x[1]).lower()):
            print(f"\n    {YELLOW}~{RESET} {BOLD}{entry_path(entry_a)}{RESET}  {DIM}[{_short_uuid(uid)}]{RESET}")
            # column-align field names
            max_w = max(len(f) for f in diffs)
            for field, (old_val, new_val) in sorted(diffs.items()):
                pad = " " * (max_w - len(field))
                old_d = _display_value(old_val, field, show_passwords)
                new_d = _display_value(new_val, field, show_passwords)
                print(f"        {DIM}{field}{pad}{RESET}  {RED}- {old_d}{RESET}")
                print(f"        {' '*max_w}  {GREEN}+ {new_d}{RESET}")

    # --- Summary line ---
    parts = []
    if added:
        parts.append(f"{GREEN}+{len(added)} added{RESET}")
    if removed:
        parts.append(f"{RED}-{len(removed)} removed{RESET}")
    if modified:
        parts.append(f"{YELLOW}~{len(modified)} modified{RESET}")
    print(f"\n  {DIM}{'  '.join(parts)}{RESET}\n")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def basename(path):
    return path.rsplit("/", 1)[-1]

def main():
    parser = argparse.ArgumentParser(
        description="Compare 2 or 3 KDBX (KeePass) files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("files", nargs="+", metavar="FILE",
                        help="KDBX files to compare (2 or 3)")
    parser.add_argument("--passwords", nargs="*", metavar="PASS",
                        help="Passwords in order (insecure on shared machines)")
    parser.add_argument("--same-password", action="store_true",
                        help="All files share the same password (prompt once)")
    parser.add_argument("--keyfiles", nargs="*", metavar="KEY",
                        help="Key files in order (optional)")
    parser.add_argument("-m", "--mask-passwords", action="store_true",
                        help="Mask password values in diff (shown by default)")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors")
    args = parser.parse_args()

    if len(args.files) not in (2, 3):
        parser.error("Provide exactly 2 or 3 KDBX files.")

    if args.no_color:
        global RED, GREEN, YELLOW, CYAN, BOLD, DIM, RESET
        RED = GREEN = YELLOW = CYAN = BOLD = DIM = RESET = ""

    keyfiles = args.keyfiles or []

    if args.same_password:
        shared_pw = getpass.getpass("Password (shared): ")
        passwords = [shared_pw] * len(args.files)
    else:
        passwords = args.passwords or []

    dbs    = []
    labels = []
    for i, path in enumerate(args.files):
        pw  = passwords[i] if i < len(passwords) else None
        kf  = keyfiles[i]  if i < len(keyfiles)  else None
        dbs.append(load_db(path, pw, kf))
        labels.append(basename(path))

    n = len(dbs)
    pairs = [(0, 1)] if n == 2 else [(0, 1), (1, 2), (0, 2)]

    for i, j in pairs:
        added, removed, modified = compare(dbs[i], dbs[j])
        print_comparison(added, removed, modified, labels[i], labels[j], not args.mask_passwords)

if __name__ == "__main__":
    main()
