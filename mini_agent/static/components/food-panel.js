/**
 * Food Panel — native ES module for Pet Room food/cost UI.
 *
 * Owns only:
 *   - stat-food, bar-food, pet-food-balance DOM updates
 *   - pet-cost-table cost estimate rendering
 *   - pet-add-food-btn / pet-feed-btn wiring
 *
 * All API calls go through the shared API wrapper imported by index.html.
 * Does NOT call fetch directly.
 */

// ── Helpers ──────────────────────────────────────────

function escapeHtml(s) {
  if (typeof s !== 'string') return '';
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Food stat / balance ─────────────────────────────

/**
 * Update food stat bar, numeric value, and balance text from pet state.
 * @param {object} state - pet state with compute_food_balance
 */
export function updateFoodPanel(state) {
  if (!state) return;

  var bal = state.compute_food_balance != null ? state.compute_food_balance : 0;

  // bar fill (scaled 0-100)
  var bar = document.getElementById('bar-food');
  if (bar) bar.style.width = Math.max(0, Math.min(100, bal / 10)) + '%';

  // numeric value
  var valEl = document.getElementById('stat-food');
  if (valEl) valEl.textContent = bal;

  // human-readable balance
  var balEl = document.getElementById('pet-food-balance');
  if (balEl) balEl.textContent = 'Balance: ' + bal + ' tokens';
}

// ── Cost estimates ───────────────────────────────────

/**
 * Fetch cost estimates for feed/chat/voice/work and render the
 * pet-cost-table grid.
 *
 * @param {string} petId
 * @param {object} api - the API namespace from api.js
 */
export function loadCostEstimates(petId, api) {
  if (!petId || !api) return;

  var actions = ['feed', 'chat', 'voice', 'work'];
  Promise.all(actions.map(function (action) {
    return api.getPetFoodStatus(petId, action).catch(function () { return null; });
  })).then(function (results) {
    var table = document.getElementById('pet-cost-table');
    if (!table) return;
    table.innerHTML = results.map(function (r) {
      if (!r) return '';
      var statusCls = r.can_run ? 'ok' : 'no';
      var statusText = r.can_run ? 'ok' : 'need ' + r.shortfall;
      return '<div class="pet-cost-item">'
        + '<div class="action-name">' + escapeHtml(r.action) + '</div>'
        + '<div class="cost-value">' + r.cost + '</div>'
        + '<div class="cost-status ' + statusCls + '">' + statusText + '</div>'
        + '</div>';
    }).join('');
  });
}

// ── Button wiring ────────────────────────────────────

/**
 * Wire pet-feed-btn and pet-add-food-btn click handlers.
 *
 * @param {function} getCurrentPet - () => pet object or null
 * @param {function} petActionFn   - (endpoint, body, btn) => void  (index.html helper)
 */
export function wireFoodButtons(getCurrentPet, petActionFn) {
  var feedBtn = document.getElementById('pet-feed-btn');
  if (feedBtn) {
    feedBtn.addEventListener('click', function () {
      var pet = getCurrentPet();
      if (!pet) return;
      petActionFn('/pet/feed', { pet_id: pet.pet_id, amount: 100 }, feedBtn);
    });
  }

  var addBtn = document.getElementById('pet-add-food-btn');
  if (addBtn) {
    addBtn.addEventListener('click', function () {
      var pet = getCurrentPet();
      if (!pet) return;
      var amt = parseInt(document.getElementById('pet-food-amount').value) || 500;
      petActionFn('/pet/add-food', { pet_id: pet.pet_id, amount: amt, reason: 'local demo' }, addBtn);
    });
  }
}
