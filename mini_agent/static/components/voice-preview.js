/**
 * Voice Preview — native ES module for Pet Room text-only voice preview UI.
 *
 * Owns:
 *   - speech-bubble-area, voice-consent-panel, voice-consent-checkbox
 *   - speech-bubble, speech-bubble-text, speech-bubble-meta
 *   - speech-preview-input, speech-preview-btn, speech-bubble-error
 *   - consent-before-call validation
 *   - meta tag rendering for cost, audio status, network, recording, food debit, provider
 *
 * Does NOT call fetch directly. Uses injected api.previewVoice.
 * Does NOT mutate pet state, food, activity, or relationship memory.
 */

// ── Helpers ──────────────────────────────────────────

function escapeHtml(s) {
  if (typeof s !== 'string') return '';
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Wiring ───────────────────────────────────────────

/**
 * Wire the speech preview button to call the voice preview API.
 *
 * @param {function} getCurrentPet - () => pet object or null
 * @param {object}   api           - namespace with previewVoice(body) returning Promise
 * @param {function} [onAuthError] - optional (resp) => boolean, called on 401
 */
export function wireVoicePreview(getCurrentPet, api, onAuthError) {
  var btn = document.getElementById('speech-preview-btn');
  if (!btn) return;

  btn.addEventListener('click', function () {
    var pet = getCurrentPet();
    if (!pet) return;

    var consent = document.getElementById('voice-consent-checkbox');
    var errorEl = document.getElementById('speech-bubble-error');
    var bubbleEl = document.getElementById('speech-bubble');
    var textEl = document.getElementById('speech-bubble-text');
    var metaEl = document.getElementById('speech-bubble-meta');

    if (errorEl) errorEl.textContent = '';

    // Consent gate
    if (!consent || !consent.checked) {
      if (errorEl) errorEl.textContent = 'Please confirm the consent boundary first.';
      return;
    }

    var input = document.getElementById('speech-preview-input');
    var text = input ? input.value.trim() : '';

    // Validation
    if (!text) {
      if (errorEl) errorEl.textContent = 'Enter text to preview.';
      return;
    }
    if (text.length > 500) {
      if (errorEl) errorEl.textContent = 'Text too long (max 500).';
      return;
    }

    // Call API
    api.previewVoice({ pet_id: pet.pet_id, text: text })
      .then(function (result) {
        if (result.error) {
          if (errorEl) errorEl.textContent = result.error;
          if (bubbleEl) bubbleEl.classList.remove('visible');
          return;
        }
        // Render text
        if (textEl) textEl.textContent = result.text || '';
        // Render meta tags
        if (metaEl) {
          var tags = [];
          tags.push('cost: ' + (result.cost_tokens || 0) + ' tokens');
          tags.push(result.has_audio ? 'audio: yes' : 'audio: no (text only)');
          if (result.no_network_call) tags.push('no network');
          if (result.no_recording) tags.push('no recording');
          if (result.food_debit === false) tags.push('no food debit');
          if (result.provider_status) tags.push('provider: ' + result.provider_status);
          if (result.audio_requires_confirmation) tags.push('audio requires confirmation');
          metaEl.innerHTML = tags.map(function (t) {
            return '<span class="meta-tag">' + escapeHtml(t) + '</span>';
          }).join('');
        }
        if (bubbleEl) bubbleEl.classList.add('visible');
      })
      .catch(function (err) {
        if (onAuthError && err && err._authError) { onAuthError({ status: 401 }); return; }
        if (errorEl) errorEl.textContent = 'Preview failed.';
        if (bubbleEl) bubbleEl.classList.remove('visible');
      });
  });
}
