/**
 * Status Chips — native ES module for pet room status chip text.
 *
 * Owns only the Mood/Presence/Energy/Bond chip value text updates.
 * Uses textContent, not HTML insertion.
 *
 * Does NOT call fetch, provider APIs, voice preview,
 * food mutation, relationship memory, identity save, skill
 * execution, or durable runtime tools.
 */

/**
 * Update all four status chip text values.
 * @param {object} state - Pet state (energy, mood, hunger, bond, etc.)
 * @param {object|null} expr - Pre-computed expression from expressionFromState()
 * @param {object|null} pres - Pre-computed presence from presenceFromState()
 */
export function updateStatusChips(state, expr, pres) {
  if (!state) return;

  var chipMood = document.getElementById('chip-mood-value');
  if (chipMood) chipMood.textContent = expr ? expr.label : '—';

  var chipPresence = document.getElementById('chip-presence-value');
  if (chipPresence) chipPresence.textContent = pres ? pres.label : '—';

  var chipEnergy = document.getElementById('chip-energy-value');
  if (chipEnergy) chipEnergy.textContent = state.energy != null ? state.energy : '—';

  var chipBond = document.getElementById('chip-bond-value');
  if (chipBond) chipBond.textContent = state.bond != null ? state.bond : '—';
}
