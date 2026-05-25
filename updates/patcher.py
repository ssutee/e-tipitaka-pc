#-*- coding:utf-8 -*-

"""Online sqlite-database patcher.

Flow:

    raw_bytes  = downloader(constants.PATCH_INDEX_URL)
    index      = parse_index(raw_bytes)
    local_vers = {db: get_local_version(...) for db in ...}
    pending    = compute_pending(index, local_vers, ignore=(...))

    for p in pending:
        apply_chain(shipped_path, USER_DB_DIR, p.chain, downloader)

Each db patch is `<basename>-<from>-<to>.sql` produced by
`scripts/make_db_patch.py`. The chain is the ordered list of
(from_ver, to_ver, url) tuples that take the local copy up to the
remote target. We always apply to a *copy* under `USER_DB_DIR` so the
shipped bundle is never mutated (read-only on macOS .app, lost on
reinstall on Windows). `constants.resolve_db()` picks the user copy
once it exists.
"""

import os
import shutil
import sqlite3
import sys

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


class PatchError(Exception):
    pass


class PendingPatch(object):
    """One database's upgrade plan: ordered (from, to, url) steps."""

    __slots__ = ('db', 'chain')

    def __init__(self, db, chain):
        self.db = db
        self.chain = chain

    def __repr__(self):
        return 'PendingPatch(%r, %r)' % (self.db, self.chain)


def parse_index(raw_bytes):
    """Parse the remote patches.toml into a normalized dict::

        {
            'thai': {'version': 2, 'from': {1: 'http://.../thai-1-2.sql'}},
            'pali': {'version': 3, 'from': {1: '...', 2: '...'}},
        }
    """
    data = tomllib.loads(raw_bytes.decode('utf-8'))
    out = {}
    for db, entry in data.items():
        if not isinstance(entry, dict):
            continue
        version = entry.get('version')
        if version is None:
            continue
        # `from.N = "url"` in TOML parses as nested table `from: {N: url}`
        # where the key `N` may be a string or int depending on syntax used.
        from_table = entry.get('from', {}) or {}
        froms = {}
        if isinstance(from_table, dict):
            for k, url in from_table.items():
                try:
                    froms[int(k)] = url
                except (TypeError, ValueError):
                    continue
        out[db] = {'version': int(version), 'from': froms}
    return out


def compute_pending(index, local, ignore=()):
    """Return [PendingPatch...] for dbs that need upgrading.

    `local` is a {db_name: current_user_version}. user_version == 0 is
    treated as 1 (matches project default for un-versioned shipped dbs).

    Skipped silently:
      * dbs in `ignore`
      * dbs not in `local` (we don't ship them)
      * local >= remote target (already at or beyond target — no downgrade)
      * remote chain has a gap (no `from.N` entry for some intermediate)
    """
    ignore = set(ignore)
    pending = []
    for db in sorted(index):
        if db in ignore:
            continue
        if db not in local:
            continue
        target = index[db]['version']
        froms = index[db]['from']
        current = local[db] or 1   # treat 0 as 1
        if current >= target:
            continue
        chain = []
        v = current
        ok = True
        while v < target:
            url = froms.get(v)
            if url is None:
                ok = False  # gap in chain
                break
            chain.append((v, v + 1, url))
            v += 1
        if not ok:
            continue
        pending.append(PendingPatch(db, chain))
    return pending


def get_local_version(db_path):
    """Read PRAGMA user_version from a sqlite file."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute('PRAGMA user_version').fetchone()[0]
    finally:
        conn.close()


def ensure_user_copy(shipped_path, user_dir):
    """Return the per-user copy path of `shipped_path` under `user_dir`,
    copying the shipped file into place on first call. Subsequent calls
    leave the existing user copy alone."""
    os.makedirs(user_dir, exist_ok=True)
    user_path = os.path.join(user_dir, os.path.basename(shipped_path))
    if not os.path.exists(user_path):
        shutil.copy2(shipped_path, user_path)
    return user_path


def apply_chain(shipped_path, user_dir, chain, downloader):
    """Apply `chain` ((from, to, url), ...) to the user copy of
    `shipped_path`. The user copy is created (copied from shipped) on
    demand. On any sqlite error during a step the whole patch step
    rolls back (the guard trigger uses RAISE(ROLLBACK)); a PatchError
    is raised and remaining steps are skipped."""
    user_path = ensure_user_copy(shipped_path, user_dir)
    for from_ver, to_ver, url in chain:
        try:
            sql = downloader(url).decode('utf-8')
        except Exception as e:
            raise PatchError('download failed for %s: %s' % (url, e))
        conn = sqlite3.connect(user_path)
        try:
            conn.executescript(sql)
        except sqlite3.Error as e:
            conn.close()
            raise PatchError(
                'patch %s (v%d->v%d) failed on %s: %s'
                % (url, from_ver, to_ver, os.path.basename(user_path), e)
            )
        finally:
            try:
                conn.close()
            except Exception:
                pass
        # Confirm version actually advanced. If the guard rolled back,
        # the COMMIT never landed and user_version is still at from_ver.
        post = get_local_version(user_path)
        if post != to_ver:
            raise PatchError(
                'patch %s did not advance user_version (still %d, expected %d)'
                % (url, post, to_ver)
            )
    return user_path


# ---------------------------------------------------------------------------
# Default downloader and high-level orchestration
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 30


def http_get(url, timeout=DEFAULT_TIMEOUT):
    """Default downloader using `requests` (already a project dep)."""
    import requests
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


# Keys in patches.toml that we never apply — orphaned or experimental files.
DEFAULT_IGNORE = ('thaimc2',)


# Map TOML key -> shipped constants attribute name. Assume <key>.sqlite under
# RESOURCES_DIR, but the constant name doesn't follow the file name so we
# keep an explicit table. Anything not listed here is silently ignored.
KEY_TO_CONST = {
    'thai':          'THAI_ROYAL_DB',
    'thaibt':        'THAI_FIVE_BOOKS_DB',
    'thaimc':        'THAI_MAHACHULA_DB',
    'thaimm':        'THAI_MAHAMAKUT_DB',
    'thaict':        'THAI_SCRIPT_DB',
    'romanct':       'ROMAN_SCRIPT_DB',
    'thaiwn':        'THAI_WATNA_DB',
    'thaipb':        'THAI_POCKET_BOOK_DB',
    'palimc':        'PALI_MAHACHULA_DB',
    'thaims':        'THAI_SUPREME_DB',
    'thaivn':        'THAI_VINAYA_DB',
    'pali':          'PALI_SIAM_DB',
    'palinew':       'PALI_SIAM_NEW_DB',
    'p2t_dict':      'PALI_DICT_DB',
    'thaidict':      'THAI_DICT_DB',
    'pali-english':  'ENGLISH_DICT_DB',
}


def check_for_updates(index_url, downloader=None):
    """Top-level convenience: fetch the index and return a list of
    (db_key, PendingPatch, shipped_path) for everything pending.

    Returns [] on any network error (silent — Q5). Raises only on
    programming errors (e.g. malformed TOML)."""
    import constants
    downloader = downloader or http_get
    try:
        raw = downloader(index_url)
    except Exception:
        return []
    index = parse_index(raw)
    local = {}
    shipped = {}
    for key, const_name in KEY_TO_CONST.items():
        shipped_path = getattr(constants, const_name, None)
        if shipped_path is None or not os.path.exists(shipped_path):
            continue
        # Use the resolved path (user copy if present) when reading the
        # current version — that's what the app actually opens.
        active_path = constants.resolve_db(shipped_path)
        local[key] = get_local_version(active_path)
        shipped[key] = shipped_path
    pending = compute_pending(index, local, ignore=DEFAULT_IGNORE)
    return [(p.db, p, shipped[p.db]) for p in pending]


def apply_pending(pending, downloader=None):
    """Apply a list of (key, PendingPatch, shipped_path) tuples. Returns
    a {key: 'ok' | error_message} dict. Errors do not abort the loop —
    each db is patched independently."""
    import constants
    downloader = downloader or http_get
    results = {}
    for key, patch, shipped_path in pending:
        try:
            apply_chain(shipped_path, constants.USER_DB_DIR,
                        patch.chain, downloader)
            results[key] = 'ok'
        except PatchError as e:
            results[key] = str(e)
    return results
