/* LabMate API client — thin fetch wrapper with JWT + refresh. */
(function () {
  'use strict';

  // Базовый URL API:
  //  1) явный override через window.PETPRO_API;
  //  2) если фронт открыт со страницы file:// или localhost:5500 (отдельный
  //     статик-сервер) → ходим на бэкенд localhost:8000;
  //  3) иначе (прод: фронт и API на одном origin) → относительный /api.
  function resolveBase() {
    if (window.PETPRO_API) return window.PETPRO_API;
    const { protocol, hostname, port } = window.location;
    const isLocalStatic =
      protocol === 'file:' ||
      ((hostname === 'localhost' || hostname === '127.0.0.1') && port === '5500');
    return isLocalStatic ? 'http://localhost:8000/api' : '/api';
  }

  const BASE = resolveBase();
  const KEY = 'petpro.tokens';

  function getTokens() {
    try {
      return JSON.parse(localStorage.getItem(KEY) || 'null');
    } catch {
      return null;
    }
  }
  function setTokens(t) {
    localStorage.setItem(KEY, JSON.stringify(t));
  }
  function clearTokens() {
    localStorage.removeItem(KEY);
  }
  function isAuthed() {
    return !!(getTokens() && getTokens().access_token);
  }

  async function raw(path, { method = 'GET', body, auth = true } = {}) {
    const headers = { 'Content-Type': 'application/json' };
    const tokens = getTokens();
    if (auth && tokens) headers['Authorization'] = 'Bearer ' + tokens.access_token;
    const res = await fetch(BASE + path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return res;
  }

  async function request(path, opts = {}) {
    let res = await raw(path, opts);

    // Try a one-shot refresh on 401.
    if (res.status === 401 && opts.auth !== false) {
      const tokens = getTokens();
      if (tokens && tokens.refresh_token) {
        const r = await raw('/auth/refresh', {
          method: 'POST',
          auth: false,
          body: { refresh_token: tokens.refresh_token },
        });
        if (r.ok) {
          setTokens(await r.json());
          res = await raw(path, opts);
        } else {
          clearTokens();
        }
      }
    }

    if (res.status === 204) return null;
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) || `HTTP ${res.status}`;
      const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      err.status = res.status;
      // Per-field validation errors from the 422 handler.
      if (data && data.errors) err.fields = data.errors;
      throw err;
    }
    return data;
  }

  window.api = {
    base: BASE,
    getTokens,
    setTokens,
    clearTokens,
    isAuthed,
    get: (p) => request(p),
    post: (p, body) => request(p, { method: 'POST', body }),
    put: (p, body) => request(p, { method: 'PUT', body }),
    patch: (p, body) => request(p, { method: 'PATCH', body }),
    del: (p) => request(p, { method: 'DELETE' }),
    // auth helpers (no token required)
    login: (body) => request('/auth/login', { method: 'POST', body, auth: false }),
    register: (body) => request('/auth/register', { method: 'POST', body, auth: false }),
  };
})();
