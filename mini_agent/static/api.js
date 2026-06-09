/**
 * Nora Pet Room API — centralized fetch wrappers.
 *
 * Native ES module. Same-origin only. No external URLs. No build step.
 */

function _getToken() {
  var el = document.getElementById('token');
  return el ? el.value.trim() : '';
}

function _authHeaders() {
  var h = { 'Content-Type': 'application/json' };
  var t = _getToken();
  if (t) h['Authorization'] = 'Bearer ' + t;
  return h;
}

function _checkAuth(r) {
  if (r.status === 401) {
    return Promise.reject({ _authError: true, status: 401 });
  }
  return r;
}

function _json(r) { return r.json(); }

// ── POST helper ───────────────────────────────────────

export function post(path, body) {
  return fetch(path, { method: 'POST', headers: _authHeaders(), body: JSON.stringify(body) })
    .then(_checkAuth).then(_json);
}

// ── GET endpoints ─────────────────────────────────────

export function getPetCurrent() {
  return fetch('/pet/current', { headers: _authHeaders() })
    .then(_checkAuth).then(_json);
}

export function getPetActivity(petId, limit) {
  var url = '/pet/activity?pet_id=' + encodeURIComponent(petId);
  if (limit != null) url += '&limit=' + limit;
  return fetch(url, { headers: _authHeaders() })
    .then(_checkAuth).then(_json);
}

export function getPetFoodStatus(petId, action) {
  var url = '/pet/food-status?pet_id=' + encodeURIComponent(petId)
          + '&action=' + encodeURIComponent(action);
  return fetch(url, { headers: _authHeaders() })
    .then(_checkAuth).then(_json);
}

export function getRelationshipMemory(petId, limit) {
  var url = '/pet/relationship-memory?pet_id=' + encodeURIComponent(petId);
  if (limit != null) url += '&limit=' + limit;
  return fetch(url, { headers: _authHeaders() })
    .then(_checkAuth).then(_json);
}

// ── POST endpoints ────────────────────────────────────

export function createPet(body)              { return post('/pet/create', body); }
export function addPetFood(body)             { return post('/pet/add-food', body); }
export function feedPet(body)                { return post('/pet/feed', body); }
export function carePet(body)                { return post('/pet/care', body); }
export function updatePetIdentity(body)      { return post('/pet/update-identity', body); }
export function previewVoice(body)           { return post('/pet/voice-preview', body); }
export function createRelationshipMemory(body) { return post('/pet/relationship-memory', body); }

// ── Endpoint catalog ──────────────────────────────────

export var PET_ENDPOINTS = [
  '/pet/current', '/pet/activity', '/pet/food-status',
  '/pet/relationship-memory', '/pet/create', '/pet/add-food',
  '/pet/feed', '/pet/care', '/pet/update-identity', '/pet/voice-preview',
];
