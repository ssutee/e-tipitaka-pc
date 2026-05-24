#-*- coding:utf-8 -*-

import json
import os
import sys

import constants


class TokenStore(object):
    """Persist {token, username, last_upload} as JSON at `path`."""

    def __init__(self, path=None):
        self._path = path if path is not None else constants.ACCOUNT_CFG

    def get(self):
        if not os.path.exists(self._path):
            return None
        try:
            with open(self._path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (IOError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def set(self, token, username):
        data = self.get() or {}
        data['token'] = token
        data['username'] = username
        self._write(data)

    def set_last_upload(self, iso_timestamp):
        data = self.get() or {}
        data['last_upload'] = iso_timestamp
        self._write(data)

    def clear(self):
        if os.path.exists(self._path):
            os.remove(self._path)

    def is_logged_in(self):
        data = self.get()
        return bool(data and data.get('token'))

    def _write(self, data):
        parent = os.path.dirname(self._path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        if sys.platform != 'win32':
            os.chmod(self._path, 0o600)
