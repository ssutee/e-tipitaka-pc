#-*- coding:utf-8 -*-

import json

import requests


class AccountError(Exception):
    def __init__(self, status, message):
        super(AccountError, self).__init__('%d: %s' % (status, message))
        self.status = status
        self.message = message


def _extract_message(resp):
    try:
        body = resp.json()
    except ValueError:
        return resp.text or ''
    if isinstance(body, dict):
        if 'detail' in body:
            return str(body['detail'])
        if 'non_field_errors' in body and body['non_field_errors']:
            return str(body['non_field_errors'][0])
        for v in body.values():
            if isinstance(v, list) and v:
                return str(v[0])
            if isinstance(v, str):
                return v
    return str(body)


class AccountClient(object):

    def __init__(self, base_url, tokenstore, timeout=30):
        self._base = base_url.rstrip('/')
        self._store = tokenstore
        self._timeout = timeout

    def login(self, username, password):
        resp = requests.post(
            self._base + '/rest-auth/login/',
            json={'username': username, 'password': password},
            timeout=self._timeout,
        )
        self._raise_if_error(resp)
        body = resp.json() if resp.content else {}
        token = body.get('key')
        if not token:
            raise AccountError(resp.status_code, 'login response missing token')
        self._store.clear()
        self._store.set(token, username)
        return token

    def register(self, email, username, password):
        resp = requests.post(
            self._base + '/rest-auth/registration/',
            json={'email': email, 'username': username,
                  'password1': password, 'password2': password},
            timeout=self._timeout,
        )
        self._raise_if_error(resp)

    def logout(self):
        if not self._store.is_logged_in():
            return
        try:
            resp = requests.post(
                self._base + '/rest-auth/logout/',
                headers=self._auth_headers(),
                timeout=self._timeout,
            )
            if not resp.ok and resp.status_code != 401:
                self._raise_if_error(resp)
        finally:
            self._store.clear()

    def current_user(self):
        resp = requests.get(
            self._base + '/rest-auth/user/',
            headers=self._auth_headers(),
            timeout=self._timeout,
        )
        self._raise_if_error(resp)
        return resp.json()

    def upload(self, etz_path, title):
        with open(etz_path, 'rb') as f:
            resp = requests.post(
                self._base + '/upload/',
                headers=self._auth_headers(),
                data={'title': title},
                files={'file': (title, f, 'application/octet-stream')},
                timeout=self._timeout,
            )
        self._raise_if_error(resp)
        return resp.json()

    def list_backups(self, platform=None):
        resp = requests.get(
            self._base + '/user_data_list/',
            headers=self._auth_headers(),
            timeout=self._timeout,
        )
        self._raise_if_error(resp)
        raw = resp.json().get('items', '[]')
        items = json.loads(raw) if isinstance(raw, str) else raw
        rows = []
        for it in items:
            fields = it.get('fields', it)
            rows.append({
                'pk': it.get('pk', fields.get('pk')),
                'file': fields.get('file', ''),
                'platform': fields.get('platform', ''),
                'created_at': fields.get('created_at', ''),
            })
        if platform is not None:
            rows = [r for r in rows if r['platform'] == platform]
        return rows

    def download(self, pk):
        resp = requests.get(
            '%s/user_data/%d/' % (self._base, pk),
            headers=self._auth_headers(),
            timeout=self._timeout,
        )
        self._raise_if_error(resp)
        return resp.content

    def delete_backup(self, pk):
        resp = requests.delete(
            '%s/user_data/%d/' % (self._base, pk),
            headers=self._auth_headers(),
            timeout=self._timeout,
        )
        self._raise_if_error(resp)

    def _auth_headers(self):
        data = self._store.get() or {}
        token = data.get('token')
        if not token:
            raise AccountError(401, 'not logged in')
        return {'Authorization': 'Token ' + token}

    def _raise_if_error(self, resp):
        if not resp.ok:
            raise AccountError(resp.status_code, _extract_message(resp))
