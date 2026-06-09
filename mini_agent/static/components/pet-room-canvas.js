/**
 * Pet Room Canvas — native ES module for visual canvas boundary.
 *
 * Owns only the first-screen visual room rendering:
 * - wall/floor canvas markers
 * - Nora-01 hero image reference
 * - ground shadow / visual shell markers
 * - pet name and role text
 *
 * Delegates chip text updates to status-chips.js.
 *
 * Does NOT call fetch, provider APIs, voice preview,
 * food mutation, relationship memory, identity save, skill
 * execution, or durable runtime tools.
 */

import { updateStatusChips } from '/static/components/status-chips.js';

/**
 * Update the visual canvas with pet identity and state.
 * @param {object} identity - Pet identity (name, relationship_role, etc.)
 * @param {object} state - Pet state (energy, mood, hunger, bond, etc.)
 * @param {object|null} expr - Pre-computed expression from expressionFromState()
 * @param {object|null} pres - Pre-computed presence from presenceFromState()
 */
export function updateCanvas(identity, state, expr, pres) {
  if (!identity || !state) return;

  // Room name
  var roomNameEl = document.getElementById('pet-room-name');
  if (roomNameEl) roomNameEl.textContent = identity.name || 'Nora-01';

  // Room role
  var roomRoleEl = document.getElementById('pet-room-role');
  if (roomRoleEl) roomRoleEl.textContent = identity.relationship_role || 'ceramic desktop pet agent';

  // Delegate chip updates to status-chips module
  updateStatusChips(state, expr, pres);
}

/**
 * Update only the chip values (lighter call for state-only refresh).
 * Delegates to status-chips module.
 * @param {object} state - Pet state
 * @param {object|null} expr - Pre-computed expression
 * @param {object|null} pres - Pre-computed presence
 */
export function updateChips(state, expr, pres) {
  updateStatusChips(state, expr, pres);
}
