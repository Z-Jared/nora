/**
 * Memory Diary — native ES module for Pet Room Today diary and relationship memory UI.
 *
 * Owns:
 *   - pet-today-content rendering (Today diary)
 *   - pet-memory-list rendering (relationship memories)
 *   - pet-memory-moment-btn wiring (shared moment)
 *   - pet-loading empty state copy
 *
 * Does NOT call fetch directly. Uses injected api namespace.
 * Does NOT mutate pet state, food, or voice preview.
 */

// ── Helpers ──────────────────────────────────────────

function escapeHtml(s) {
  if (typeof s !== 'string') return '';
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Today diary ─────────────────────────────────────

/**
 * Load and render the Today diary (activity events + recent memories).
 *
 * @param {string} petId
 * @param {object} api - namespace with getPetActivity(petId, limit) and getRelationshipMemory(petId, limit)
 */
export function loadTodayDiary(petId, api) {
  if (!petId || !api) return;

  Promise.all([
    api.getPetActivity(petId, 5).catch(function () { return []; }),
    api.getRelationshipMemory(petId, 3).catch(function () { return []; })
  ]).then(function (results) {
    var events = results[0] || [];
    var memories = results[1] || [];
    var el = document.getElementById('pet-today-content');
    if (!el) return;

    if (!events.length && !memories.length) {
      el.innerHTML = '<div class="pet-loading">Start your first interaction above.</div>';
      return;
    }

    var items = [];
    events.forEach(function (e) {
      var t = e.created_at ? e.created_at.substring(11, 16) : '';
      items.push(
        '<div class="pet-today-item">'
        + '<span class="today-time">' + escapeHtml(t) + '</span>'
        + '<span class="today-text">' + escapeHtml(e.summary) + '</span>'
        + '</div>'
      );
    });
    memories.forEach(function (m) {
      items.push(
        '<div class="pet-today-item">'
        + '<span class="today-time">memory</span>'
        + '<span class="today-text">[' + escapeHtml(m.kind) + '] ' + escapeHtml(m.summary) + '</span>'
        + '</div>'
      );
    });
    el.innerHTML = items.join('');
  });
}

// ── Relationship memory list ────────────────────────

/**
 * Load and render the relationship memory list.
 *
 * @param {string} petId
 * @param {object} api - namespace with getRelationshipMemory(petId) returning Promise
 * @param {function} [onAuthError] - optional (resp) => void, called on 401
 */
export function loadRelationshipMemories(petId, api, onAuthError) {
  if (!petId || !api) return;

  api.getRelationshipMemory(petId).then(function (memories) {
    var list = document.getElementById('pet-memory-list');
    if (!list) return;

    if (!memories.length) {
      list.innerHTML = '<div class="pet-loading">No memories yet.</div>';
      return;
    }

    list.innerHTML = memories.map(function (m) {
      var t = m.created_at ? escapeHtml(m.created_at.substring(11, 16)) : '';
      return '<div class="pet-memory-item">'
        + '<div class="kind">' + escapeHtml(m.kind) + '</div>'
        + '<div class="mem-summary">' + escapeHtml(m.summary) + '</div>'
        + '<div class="mem-meta"><span>importance: ' + m.importance + '</span><span>' + t + '</span></div>'
        + '</div>';
    }).join('');
  }).catch(function (err) {
    if (onAuthError && err && err._authError) { onAuthError({ status: 401 }); }
  });
}

// ── Shared moment wiring ────────────────────────────

/**
 * Wire the pet-memory-moment-btn to prompt for a shared moment and record it.
 *
 * @param {function} getCurrentPet - () => pet object or null
 * @param {object}   api           - namespace with createRelationshipMemory(body) returning Promise
 * @param {object}   callbacks     - { showRoomNotice(msg), applyReaction(key, state, result) }
 */
export function wireMemoryDiary(getCurrentPet, api, callbacks) {
  var btn = document.getElementById('pet-memory-moment-btn');
  if (!btn) return;

  btn.addEventListener('click', function () {
    var pet = getCurrentPet();
    if (!pet) return;

    var summary = prompt('Describe the shared moment:');
    if (!summary || !summary.trim()) return;

    api.createRelationshipMemory({
      pet_id: pet.pet_id,
      kind: 'shared_moment',
      summary: summary.trim(),
      source: 'pet_room_demo'
    }).then(function (result) {
      if (!result.error) {
        loadRelationshipMemories(pet.pet_id, api);
        loadTodayDiary(pet.pet_id, api);
        if (callbacks && callbacks.showRoomNotice) {
          callbacks.showRoomNotice('memory recorded.');
        }
        if (callbacks && callbacks.applyReaction) {
          callbacks.applyReaction('shared_moment', pet.state, result);
        }
      }
    }).catch(function (err) {
      if (err && err._authError) {
        if (callbacks && callbacks.onAuthError) {
          callbacks.onAuthError({ status: 401 });
        }
      }
    });
  });
}
