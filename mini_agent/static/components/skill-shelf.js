/**
 * Skill Shelf — native ES module for Pet Room deterministic skill ability shelf.
 *
 * Owns only:
 *   - skillCardsFromIdentity: derive skill cards from pet identity
 *   - renderSkillShelf: render skill cards into the pet room DOM
 *
 * Uses DOM text APIs / escaped HTML for dynamic content.
 * Does NOT call fetch, PetAPI, petAction, or any tool/plugin execution.
 */

// ── Constants ────────────────────────────────────────

var SKILL_ICONS = {
  'memory': '🧠', 'patrol': '🛡️', 'chat': '💬', 'code': '💻',
  'research': '🔍', 'browse': '🌐', 'plan': '📋', 'write': '✏️',
  'read': '📖', 'watch': '👁️', 'build': '🔧', 'test': '🧪',
  'deploy': '🚀', 'monitor': '📊', 'analyze': '📈', 'summarize': '📝',
  'translate': '🌍', 'draw': '🎨', 'play': '🎮', 'sing': '🎵',
  'cook': '🍳', 'garden': '🌱', 'exercise': '💪', 'meditate': '🧘',
};

var SECRET_PATTERNS = [/sk[-_]/i, /bearer/i, /api[_-]?key/i, /token/i, /secret/i, /password/i, /passwd/i, /credential/i, /private[_-]?key/i, /auth/i];

// ── Helpers ──────────────────────────────────────────

function escapeHtml(s) {
  if (typeof s !== 'string') return '';
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function isSecretLike(text) {
  if (!text) return false;
  var lower = text.toLowerCase();
  for (var i = 0; i < SECRET_PATTERNS.length; i++) {
    if (SECRET_PATTERNS[i].test(lower)) return true;
  }
  return false;
}

// ── Skill card derivation ────────────────────────────

/**
 * Derive skill cards from pet identity and state.
 * Filters out non-string, empty, overlong, special-character, and secret-like labels.
 * @param {object} identity - pet identity with skills array
 * @param {object} state - pet state (unused currently, reserved for future)
 * @returns {Array<{name: string, icon: string}>}
 */
export function skillCardsFromIdentity(identity, state) {
  var skills = identity && identity.skills;
  if (!skills || !Array.isArray(skills) || skills.length === 0) return [];
  var result = [];
  for (var i = 0; i < skills.length; i++) {
    var raw = skills[i];
    if (typeof raw !== 'string') continue;
    var name = raw.trim();
    if (!name || name.length > 50) continue;
    // Sanitize: only allow alphanumeric, dash, underscore, space
    if (!/^[a-zA-Z0-9_\- ]+$/.test(name)) continue;
    // Reject secret-like skill labels
    if (isSecretLike(name)) continue;
    var icon = SKILL_ICONS[name.toLowerCase()] || '⚡';
    result.push({ name: name, icon: icon });
  }
  return result;
}

// ── DOM rendering ────────────────────────────────────

/**
 * Render the skill shelf into the pet room DOM.
 * @param {object} identity - pet identity
 * @param {object} state - pet state
 */
export function renderSkillShelf(identity, state) {
  var shelf = document.getElementById('pet-skill-shelf');
  var listEl = document.getElementById('pet-skill-list');
  var emptyEl = document.getElementById('pet-skill-empty');
  if (!shelf || !listEl) return;
  var cards = skillCardsFromIdentity(identity, state);
  shelf.setAttribute('data-skill-count', String(cards.length));
  if (cards.length === 0) {
    listEl.innerHTML = '';
    if (emptyEl) emptyEl.style.display = '';
    return;
  }
  if (emptyEl) emptyEl.style.display = 'none';
  // Build card elements
  var html = '';
  for (var i = 0; i < cards.length; i++) {
    var c = cards[i];
    html += '<div class="pet-skill-card"><span class="skill-icon">' + escapeHtml(c.icon) + '</span><span class="skill-name">' + escapeHtml(c.name) + '</span></div>';
  }
  listEl.innerHTML = html;
}
