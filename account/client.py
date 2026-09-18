#-*- coding:utf-8 -*-

import json

import requests


class AccountError(Exception):
    def __init__(self, status, message):
        super(AccountError, self).__init__('%d: %s' % (status, message))
        self.status = status
        self.message = message


class RateLimited(AccountError):
    """A 429. `retry_after` is the server's Retry-After header in seconds, or
    None if it sent none that is a whole, non-negative number.

    Both of the server's rate limiters send that header, with different
    bodies: nginx's edge limit returns {"error", "retry_after", "detail"},
    while DRF's own throttle returns only {"detail"}. The header is the one
    thing they agree on, so it is what this reads.
    """

    def __init__(self, status, message, retry_after=None):
        super(RateLimited, self).__init__(status, message)
        self.retry_after = retry_after


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


def _retry_after(resp):
    try:
        seconds = int(resp.headers.get('Retry-After'))
    except (TypeError, ValueError):
        return None
    # A negative delay is nonsense; report "unknown" rather than pass it on.
    # (An HTTP-date or a fraction already landed in ValueError above.)
    return seconds if seconds >= 0 else None


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

    def desktop_begin(self):
        """Start a desktop passkey pairing (see account/pairing.py).

        Returns the server's dict: device_code (the app's secret -- never
        shown), user_code (shown to the user), verification_url (opened in
        the browser), interval and expires_in (seconds).
        """
        resp = requests.post(
            self._base + '/api/passkeys/desktop/begin/',
            json={},
            timeout=self._timeout,
        )
        self._raise_if_error(resp)
        body = resp.json() if resp.content else {}
        for key in ('device_code', 'user_code', 'verification_url'):
            if not body.get(key):
                raise AccountError(resp.status_code,
                                   'pairing response missing %s' % key)
        return body

    def desktop_poll(self, device_code):
        """Poll a pairing once. Returns the server's dict:
        {'status': 'pending'}, {'status': 'denied'}, or
        {'status': 'approved', 'key': ..., 'username': ...}.

        Raises AccountError(400) once the pairing is unknown, expired or
        already used -- the server deliberately does not say which -- and
        RateLimited on a 429. Stores nothing: PairingSession decides whether
        a token is kept.
        """
        resp = requests.post(
            self._base + '/api/passkeys/desktop/poll/',
            json={'device_code': device_code},
            timeout=self._timeout,
        )
        self._raise_if_error(resp)
        return resp.json()

    def _auth_headers(self):
        data = self._store.get() or {}
        token = data.get('token')
        if not token:
            raise AccountError(401, 'not logged in')
        return {'Authorization': 'Token ' + token}

    def _raise_if_error(self, resp):
        if resp.status_code == 429:
            raise RateLimited(429, _extract_message(resp), _retry_after(resp))
        if not resp.ok:
            raise AccountError(resp.status_code, _extract_message(resp))
