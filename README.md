# kdbx-diff

Compare two or three KeePass (KDBX) files and display added, removed, and modified entries.

## Install

```bash
pip install pykeepass
```

## Usage

```
python main.py [options] FILE FILE [FILE]
```

### Options

| Flag | Description |
|------|-------------|
| `--same-password` | All files share the same password - prompt once |
| `--passwords P1 P2 ...` | Supply passwords inline, in order (avoid on shared machines) |
| `--keyfiles K1 K2 ...` | Key files for each database, in order |
| `-m`, `--mask-passwords` | Hide password values in the diff (shown by default) |
| `--no-color` | Disable ANSI colors |

### Examples

```bash
# Two files, prompted for each password
python main.py old.kdbx new.kdbx

# Three files, same password for all (prompted once)
python main.py v1.kdbx v2.kdbx v3.kdbx --same-password

# Mask passwords in output
python main.py a.kdbx b.kdbx -m

# With key files
python main.py a.kdbx b.kdbx --keyfiles a.key b.key
```

## Output

For each pair of files the tool shows:

- `+` **Added** - entries present in the second file but not the first
- `-` **Removed** - entries present in the first file but not the second
- `~` **Modified** - entries present in both with changed fields, shown as a before/after diff per field

Entries are matched by UUID, so a renamed or moved entry appears as a modification rather than a remove + add pair.

Three-file comparisons run all three pairs: A/B, B/C, and A/C.

### Example

```
$ python main.py old.kdbx new.kdbx --same-password
Password (shared):

──────  old.kdbx  vs  new.kdbx  ──────

  + Added in 'new.kdbx'  (1 entry)
    + Work/AWS Console  [3f2a1b8c...]

  - Removed from 'new.kdbx'  (1 entry)
    - Personal/OldBank  [a1c4e6f2...]

  ~ Modified  (2 entries)

    ~ Personal/Gmail  [d0e1f2a3...]
        password  - hunter2
                  + correct-horse-battery-staple

    ~ Work/GitHub  [b5c6d7e8...]
        url       - https://github.com
                  + https://github.com/acme-corp
        username  - john
                  + john.doe

  +1 added  -1 removed  ~2 modified
```
