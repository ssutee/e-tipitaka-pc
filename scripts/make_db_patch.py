#!/usr/bin/env python3
"""Generate a SQL patch between two versions of the same sqlite database.

Usage:
    scripts/make_db_patch.py OLD.sqlite NEW.sqlite [--output-dir DIR]
                             [--old-version N] [--new-version N]
                             [--no-schema] [--no-data] [--no-sqldiff]

Versions are read from `PRAGMA user_version` on each database (override with
`--old-version` / `--new-version`).

Output filename: `<basename>-<old>-<new>.sql`, where `<basename>` is the OLD
file's stem with any trailing `-vN` or `_vN` stripped.

The patch is wrapped in a `BEGIN; ... COMMIT;` block, prefixed with a guard
trigger that aborts the transaction if the target database is at the wrong
version, and ends with `PRAGMA user_version = <new>` so re-applying the same
patch is detected and rejected.

Backend selection:
- Prefers the official `sqldiff` CLI (ships with the sqlite3 source build
  and is in `brew install sqlite`).
- Falls back to a pure-Python diff if `sqldiff` is missing or
  `--no-sqldiff` is passed. The pure-Python path emits:
    * DROP/CREATE for tables, indexes, views, triggers whose `sql` differs
      (no ALTER — relies on the data section to repopulate)
    * Per-table data delta keyed on PRIMARY KEY (`INSERT OR REPLACE` for
      new/changed rows, `DELETE` for removed rows)
    * Full DELETE + INSERT for PK-less tables or tables whose column list
      changed
"""

import argparse
import os
import re
import shutil
import sqlite3
import subprocess
import sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def detect_version(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute('PRAGMA user_version').fetchone()[0]
    finally:
        conn.close()


def strip_version(name):
    """`thaiwn-v8.sqlite` -> `thaiwn`; `thai.sqlite` -> `thai`."""
    stem = os.path.splitext(os.path.basename(name))[0]
    return re.sub(r'[-_]v\d+$', '', stem)


def quote_ident(name):
    return '"%s"' % name.replace('"', '""')


def quote_value(value):
    if value is None:
        return 'NULL'
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, bytes):
        return "X'%s'" % value.hex()
    return "'%s'" % str(value).replace("'", "''")


def list_objects(conn, kind):
    """Return ordered [(name, sql)] for `sqlite_master.type = kind`."""
    rows = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type=? "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name",
        (kind,)
    ).fetchall()
    return [(n, s) for n, s in rows if s is not None]


def table_info(conn, table):
    """Return (cols, pk_cols) for a table. pk_cols ordered by their pk index."""
    rows = conn.execute('PRAGMA table_info(%s)' % quote_ident(table)).fetchall()
    cols = [r[1] for r in rows]
    pk = sorted([(r[5], r[1]) for r in rows if r[5]])
    return cols, [name for _, name in pk]


def fetch_all(conn, table):
    cur = conn.execute('SELECT * FROM %s' % quote_ident(table))
    cols = [d[0] for d in cur.description]
    return cols, cur.fetchall()


def insert_row(table, cols, row):
    return 'INSERT OR REPLACE INTO %s(%s) VALUES (%s);' % (
        quote_ident(table),
        ','.join(quote_ident(c) for c in cols),
        ','.join(quote_value(v) for v in row),
    )


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------

def schema_diff(old_conn, new_conn):
    out = []
    for kind in ('table', 'index', 'view', 'trigger'):
        old = dict(list_objects(old_conn, kind))
        new = dict(list_objects(new_conn, kind))
        for name in sorted(set(old) - set(new)):
            out.append('DROP %s IF EXISTS %s;' % (kind.upper(), quote_ident(name)))
        for name in sorted(new):
            if old.get(name) == new[name]:
                continue
            if name in old:
                out.append('DROP %s IF EXISTS %s;' % (kind.upper(), quote_ident(name)))
            out.append('%s;' % new[name])
    return out


def data_diff(old_conn, new_conn):
    out = []
    old_tables = dict(list_objects(old_conn, 'table'))
    new_tables = dict(list_objects(new_conn, 'table'))
    for table in sorted(new_tables):
        new_cols, new_pk = table_info(new_conn, table)
        if table not in old_tables:
            # Brand-new table — populate everything.
            cols, rows = fetch_all(new_conn, table)
            for row in rows:
                out.append(insert_row(table, cols, row))
            continue
        old_cols, _ = table_info(old_conn, table)

        full_replace = (old_cols != new_cols) or (not new_pk)
        if full_replace:
            cols, rows = fetch_all(new_conn, table)
            out.append('DELETE FROM %s;' % quote_ident(table))
            for row in rows:
                out.append(insert_row(table, cols, row))
            continue

        # PK-based row delta.
        _, old_rows = fetch_all(old_conn, table)
        _, new_rows = fetch_all(new_conn, table)
        pk_idx = [new_cols.index(c) for c in new_pk]
        key = lambda r: tuple(r[i] for i in pk_idx)
        old_map = {key(r): r for r in old_rows}
        new_map = {key(r): r for r in new_rows}

        for k in sorted(set(old_map) - set(new_map)):
            conds = ' AND '.join(
                '%s = %s' % (quote_ident(c), quote_value(v))
                for c, v in zip(new_pk, k)
            )
            out.append('DELETE FROM %s WHERE %s;' % (quote_ident(table), conds))

        for k in sorted(new_map):
            row = new_map[k]
            if old_map.get(k) == row:
                continue
            out.append(insert_row(table, new_cols, row))
    return out


# ---------------------------------------------------------------------------
# Header / footer
# ---------------------------------------------------------------------------

def header(old_ver, new_ver, backend):
    return [
        '-- Patch from user_version %d to %d' % (old_ver, new_ver),
        '-- Generated by scripts/make_db_patch.py (backend=%s)' % backend,
        '',
        'BEGIN;',
        '',
        '-- Guard: abort if the target database is not at version %d' % old_ver,
        'CREATE TEMP TABLE _patch_vchk(x INTEGER);',
        'CREATE TEMP TRIGGER _patch_vchk_t BEFORE INSERT ON _patch_vchk',
        'BEGIN',
        '  SELECT CASE',
        '    WHEN (SELECT user_version FROM pragma_user_version()) != %d' % old_ver,
        "    THEN RAISE(ROLLBACK, 'patch expects user_version=%d')" % old_ver,
        '  END;',
        'END;',
        'INSERT INTO _patch_vchk VALUES (1);',
        'DROP TRIGGER _patch_vchk_t;',
        'DROP TABLE _patch_vchk;',
        '',
    ]


def footer(new_ver):
    return [
        '',
        'PRAGMA user_version = %d;' % new_ver,
        'COMMIT;',
    ]


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

def build_pure(old_path, new_path, old_ver, new_ver, do_schema, do_data):
    old_conn = sqlite3.connect(old_path)
    new_conn = sqlite3.connect(new_path)
    try:
        lines = header(old_ver, new_ver, 'pure-Python')
        if do_schema:
            lines.append('-- Schema')
            lines.extend(schema_diff(old_conn, new_conn))
            lines.append('')
        if do_data:
            lines.append('-- Data')
            lines.extend(data_diff(old_conn, new_conn))
        lines.extend(footer(new_ver))
        return '\n'.join(lines) + '\n'
    finally:
        old_conn.close()
        new_conn.close()


def build_sqldiff(old_path, new_path, old_ver, new_ver):
    diff = subprocess.check_output(['sqldiff', old_path, new_path], text=True)
    return (
        '\n'.join(header(old_ver, new_ver, 'sqldiff'))
        + '\n-- Begin sqldiff output --\n'
        + diff
        + '-- End sqldiff output --\n'
        + '\n'.join(footer(new_ver))
        + '\n'
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('old', help='Path to the older sqlite database')
    p.add_argument('new', help='Path to the newer sqlite database')
    p.add_argument('--output-dir', default='.',
                   help='Where to write the .sql patch (default: cwd)')
    p.add_argument('--old-version', type=int, default=None,
                   help='Override PRAGMA user_version on OLD')
    p.add_argument('--new-version', type=int, default=None,
                   help='Override PRAGMA user_version on NEW')
    p.add_argument('--no-schema', action='store_true',
                   help='Skip the schema section (pure-Python only)')
    p.add_argument('--no-data', action='store_true',
                   help='Skip the data section (pure-Python only)')
    p.add_argument('--no-sqldiff', action='store_true',
                   help='Force pure-Python backend even if sqldiff is available')
    args = p.parse_args(argv)

    for path in (args.old, args.new):
        if not os.path.isfile(path):
            p.error('not a file: %s' % path)

    if args.no_schema and args.no_data:
        p.error('--no-schema and --no-data both set; nothing to emit')

    old_ver = args.old_version if args.old_version is not None else detect_version(args.old)
    new_ver = args.new_version if args.new_version is not None else detect_version(args.new)

    if old_ver == 0 and args.old_version is None:
        print('warning: OLD has user_version=0; pass --old-version to override',
              file=sys.stderr)
    if new_ver == 0 and args.new_version is None:
        print('warning: NEW has user_version=0; pass --new-version to override',
              file=sys.stderr)
    if new_ver == old_ver:
        print('error: old and new versions are identical (%d); nothing to patch' % old_ver,
              file=sys.stderr)
        return 2

    base = strip_version(args.old)
    out_name = '%s-%d-%d.sql' % (base, old_ver, new_ver)
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, out_name)

    has_sqldiff = shutil.which('sqldiff') is not None
    use_sqldiff = has_sqldiff and not args.no_sqldiff \
        and not args.no_schema and not args.no_data

    if use_sqldiff:
        sql = build_sqldiff(args.old, args.new, old_ver, new_ver)
        backend = 'sqldiff'
    else:
        sql = build_pure(args.old, args.new, old_ver, new_ver,
                         do_schema=not args.no_schema,
                         do_data=not args.no_data)
        backend = 'pure-Python'

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(sql)
    size = os.path.getsize(out_path)
    print('wrote %s (%d bytes, backend=%s)' % (out_path, size, backend))
    return 0


if __name__ == '__main__':
    sys.exit(main())
