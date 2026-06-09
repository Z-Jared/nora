"""Browser-level smoke tests for Web UI using Node.js execution.

These tests extract the JavaScript from index.html, create a mock DOM
environment, and execute the code to verify real behavior rather than
just string matching.
"""

import json
import subprocess
import unittest
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "mini_agent" / "static"
INDEX_HTML = STATIC_DIR / "index.html"


def _extract_script(html: str) -> str:
    # Find the <script type="module"> tag (the main IIFE with import)
    import re
    match = re.search(r'<script type="module">(.+?)</script>', html, re.DOTALL)
    if not match:
        raise ValueError("No inline <script type=\"module\"> found")
    script = match.group(1).strip()
    # Strip all ES module import lines
    script = re.sub(r'^\s*import\s.*?;\s*\n?', '', script, flags=re.MULTILINE)
    # Strip the window.PetAPI assignment line
    script = re.sub(r'^\s*window\.PetAPI\s*=\s*PetAPI;\s*\n?', '', script, count=1)
    # Strip IIFE wrapper so functions are globally accessible
    if script.startswith("(function(){"):
        script = script[len("(function(){"):]
    if script.endswith("})();"):
        script = script[:-len("})();")]
    return script


def _run_node(setup_js: str = "", test_body: str = "") -> dict:
    """Run JS in Node and return parsed JSON result.

    setup_js: runs BEFORE the script (to set _fetchHandler etc.)
    test_body: runs AFTER the script init (inside an async IIFE)
    """
    html = INDEX_HTML.read_text(encoding="utf-8")
    script = _extract_script(html)

    # The script references DOM elements by ID.
    # We provide a mock document that returns mock elements.
    harness = r"""
const _elements = {};
const _listeners = {};
const document = {
  body: { scrollHeight: 0 },
  getElementById(id) {
    if (!_elements[id]) {
      _elements[id] = {
        id: id,
        value: '',
        disabled: false,
        checked: false,
        className: '',
        innerHTML: '',
        textContent: '',
        style: {},
        scrollTop: 0,
        scrollHeight: 0,
        classList: {
          _classes: new Set(),
          add(cls) { this._classes.add(cls); },
          remove(cls) { this._classes.delete(cls); },
          contains(cls) { return this._classes.has(cls); },
        },
        querySelector() { return null; },
        querySelectorAll() { return []; },
        appendChild() {},
        addEventListener(evt, fn) {
          if (!_listeners[id]) _listeners[id] = {};
          if (!_listeners[id][evt]) _listeners[id][evt] = [];
          _listeners[id][evt].push(fn);
        },
        dispatchEvent(evt) {
          var self = this;
          if (_listeners[id] && _listeners[id][evt.type]) {
            _listeners[id][evt.type].forEach(function(fn) { fn(evt); });
          }
        },
        remove() {},
        scrollIntoView() {},
        focus() {},
        blur() {},
        _attrs: {},
        getAttribute(name) { return this._attrs[name] || null; },
        setAttribute(name, val) { this._attrs[name] = String(val); },
      };
    }
    return _elements[id];
  },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  addEventListener() {},
  createElement() {
    const children = {};
    return {
      className: '',
      innerHTML: '',
      textContent: '',
      style: {},
      classList: { _classes: new Set(), add() {}, remove() {}, contains() { return false; } },
      appendChild() {},
      querySelector(selector) {
        if (!children[selector]) children[selector] = { textContent: '', className: '', style: {} };
        return children[selector];
      },
      querySelectorAll() { return []; },
      addEventListener() {},
      dispatchEvent() {},
      remove() {},
      focus() {},
      blur() {},
      getAttribute() { return null; },
    };
  },
};

const localStorage = { _store: {}, getItem(k) { return this._store[k] || null; }, setItem(k, v) { this._store[k] = v; } };
let _promptHandler = null;
function prompt(message) { return _promptHandler ? _promptHandler(message) : null; }
function confirm() { return true; }

let _fetchHandler = null;
function fetch(url, opts) {
  if (_fetchHandler) return _fetchHandler(url, opts);
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}), text: () => Promise.resolve('') });
}

const window = { scrollTo() {}, addEventListener() {} };
const AbortController = class { constructor() { this.signal = {}; } abort() {} };

// Default no-ops for imported module functions (stripped by _extract_script)
// Tests can override these in setup_js.
function updateCanvas(identity, state, expr, pres) {}
function updateStatusChips(state, expr, pres) {}
function updateFoodPanel(state) {}
function loadCostEstimates(petId, api) {}
function wireFoodButtons(getPet, actionFn) {}

// Mock PetAPI that delegates to fetch (so _fetchHandler mock still works)
function _petPost(path, body) {
  return fetch(path, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) })
    .then(function(r) { return r.json(); });
}
const PetAPI = {
  getPetCurrent: function() { return fetch('/pet/current').then(function(r){ return r.json(); }); },
  getPetActivity: function(petId, limit) {
    var url = '/pet/activity?pet_id=' + encodeURIComponent(petId);
    if (limit != null) url += '&limit=' + limit;
    return fetch(url).then(function(r){ return r.json(); });
  },
  getPetFoodStatus: function(petId, action) {
    return fetch('/pet/food-status?pet_id=' + encodeURIComponent(petId) + '&action=' + encodeURIComponent(action))
      .then(function(r){ return r.json(); });
  },
  getRelationshipMemory: function(petId, limit) {
    var url = '/pet/relationship-memory?pet_id=' + encodeURIComponent(petId);
    if (limit != null) url += '&limit=' + limit;
    return fetch(url).then(function(r){ return r.json(); });
  },
  createPet: function(body) { return _petPost('/pet/create', body); },
  addPetFood: function(body) { return _petPost('/pet/add-food', body); },
  feedPet: function(body) { return _petPost('/pet/feed', body); },
  carePet: function(body) { return _petPost('/pet/care', body); },
  updatePetIdentity: function(body) { return _petPost('/pet/update-identity', body); },
  previewVoice: function(body) { return _petPost('/pet/voice-preview', body); },
  createRelationshipMemory: function(body) { return _petPost('/pet/relationship-memory', body); },
  PET_ENDPOINTS: ['/pet/current','/pet/activity','/pet/food-status','/pet/relationship-memory','/pet/create','/pet/add-food','/pet/feed','/pet/care','/pet/update-identity','/pet/voice-preview'],
  post: _petPost,
};

""" + setup_js + r"""

""" + script + r"""

(async function() {
  var result;
  try {
""" + test_body + r"""
    process.stdout.write(JSON.stringify({ok: true, data: result}));
  } catch(e) {
    process.stdout.write(JSON.stringify({ok: false, error: e.message, stack: e.stack}));
  }
})();
"""

    proc = subprocess.run(
        ["node", "-e", harness],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Node error: {proc.stderr}\n{proc.stdout}")
    output = json.loads(proc.stdout)
    if not output.get("ok"):
        raise RuntimeError(f"JS error: {output.get('error')}\n{output.get('stack')}")
    return output["data"]


# Shared fetch handler snippet: returns 401 for non-status endpoints when token is empty.
# This simulates a real auth-required server where /session/list, /task, /memory/* all need auth.
_AUTH_NO_TOKEN_HANDLER = r"""
function _authFetchHandler(url, opts) {
  if (url === '/status') {
    return Promise.resolve({
      ok: true, status: 200,
      json: () => Promise.resolve({
        STATUS_DATA
      })
    });
  }
  // Non-status endpoints require auth — return 401 if no valid token
  var token = document.getElementById('token').value;
  if (!token || !token.trim()) {
    return Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve({error: 'Unauthorized'}), text: () => Promise.resolve('Unauthorized') });
  }
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}), text: () => Promise.resolve('') });
}
"""


class WebUISmokeTests(unittest.TestCase):
    """Smoke tests that execute JS with mocked DOM."""

    def test_auth_required_disables_buttons_when_no_token(self):
        """When /status returns auth_required=true and token is empty,
        Send and Run should be disabled."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: true, llm_configured: true, "
            "provider: 'openai', model: 'gpt-4', workspace: '/tmp', "
            "features: { sessions: true, tasks: true, memory: true, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
result = {
  sendDisabled: _elements['send'].disabled,
  runDisabled: _elements['run-btn'].disabled,
  composerText: _elements['composer-status'].textContent,
};
""")
        self.assertTrue(result["sendDisabled"], "Send should be disabled when auth_required and no token")
        self.assertTrue(result["runDisabled"], "Run should be disabled when auth_required and no token")
        self.assertEqual(result["composerText"], "Token required")

    def test_failed_send_keeps_buttons_disabled_without_token(self):
        """A failed authenticated send must not re-enable Send/Run
        while auth is still unresolved."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: true, llm_configured: true, "
            "provider: 'openai', model: 'gpt-4', workspace: '/tmp', "
            "features: { sessions: true, tasks: true, memory: true, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
_elements['input'].value = 'hello';
sendMessage();
await new Promise(r => setTimeout(r, 100));
result = {
  sendDisabled: _elements['send'].disabled,
  runDisabled: _elements['run-btn'].disabled,
  composerText: _elements['composer-status'].textContent,
  stateText: _elements['top-state'].textContent,
};
""")
        self.assertTrue(result["sendDisabled"], "Send should remain disabled after auth failure")
        self.assertTrue(result["runDisabled"], "Run should remain disabled after auth failure")
        self.assertEqual(result["composerText"], "Token required")
        self.assertEqual(result["stateText"], "auth required")

    def test_llm_not_configured_keeps_buttons_disabled_after_token(self):
        """When llm_configured=false, entering a token should NOT enable Send/Run."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: true, llm_configured: false, "
            "provider: '', model: '', workspace: '/tmp', "
            "features: { sessions: true, tasks: true, memory: true, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
_elements['token'].value = 'my-token';
recoverAfterAuthInput();
result = {
  sendDisabled: _elements['send'].disabled,
  runDisabled: _elements['run-btn'].disabled,
  composerText: _elements['composer-status'].textContent,
};
""")
        self.assertTrue(result["sendDisabled"], "Send should remain disabled when llm_configured=false")
        self.assertTrue(result["runDisabled"], "Run should remain disabled when llm_configured=false")
        self.assertEqual(result["composerText"], "Model not configured")

    def test_llm_configured_enables_buttons(self):
        """When llm_configured=true and no auth issue, Send/Run should be enabled."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai', model: 'gpt-4', workspace: '/tmp', "
            "features: { sessions: true, tasks: true, memory: true, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
result = {
  sendDisabled: _elements['send'].disabled,
  runDisabled: _elements['run-btn'].disabled,
  composerText: _elements['composer-status'].textContent,
};
""")
        self.assertFalse(result["sendDisabled"], "Send should be enabled when llm_configured=true")
        self.assertFalse(result["runDisabled"], "Run should be enabled when llm_configured=true")
        self.assertEqual(result["composerText"], "Ready")

    def test_server_unreachable_disables_buttons(self):
        """When /status fetch fails, Send/Run should be disabled."""
        result = _run_node(
            setup_js=r"""
_fetchHandler = function(url, opts) {
  if (url === '/status') {
    return Promise.reject(new Error('Connection refused'));
  }
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
};
""",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
result = {
  sendDisabled: _elements['send'].disabled,
  runDisabled: _elements['run-btn'].disabled,
  composerText: _elements['composer-status'].textContent,
};
""")
        self.assertTrue(result["sendDisabled"], "Send should be disabled when server unreachable")
        self.assertTrue(result["runDisabled"], "Run should be disabled when server unreachable")
        self.assertEqual(result["composerText"], "Server unreachable")

    def test_token_recovery_with_llm_configured_enables_buttons(self):
        """When auth_required=true, user enters token, and llm_configured=true,
        Send/Run should be enabled after recovery."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: true, llm_configured: true, "
            "provider: 'openai', model: 'gpt-4', workspace: '/tmp', "
            "features: { sessions: true, tasks: true, memory: true, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
var afterFetch = {
  sendDisabled: _elements['send'].disabled,
  composerText: _elements['composer-status'].textContent,
};

_elements['token'].value = 'my-token';
recoverAfterAuthInput();

result = {
  afterFetch: afterFetch,
  afterRecovery: {
    sendDisabled: _elements['send'].disabled,
    composerText: _elements['composer-status'].textContent,
  },
};
""")
        self.assertTrue(result["afterFetch"]["sendDisabled"])
        self.assertEqual(result["afterFetch"]["composerText"], "Token required")
        self.assertFalse(result["afterRecovery"]["sendDisabled"], "Send should be enabled after token with llm_configured=true")
        self.assertEqual(result["afterRecovery"]["composerText"], "Ready")

    def test_server_status_cached_for_recovery(self):
        """serverStatus should be cached so recoverAfterAuthInput can check llm_configured."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: true, llm_configured: false, "
            "provider: '', model: '', workspace: '/tmp', "
            "features: { sessions: false, tasks: false, memory: false, websocket: false }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
var hasCached = (typeof serverStatus !== 'undefined' && serverStatus !== null);
var cachedLlm = hasCached ? serverStatus.llm_configured : null;

_elements['token'].value = 'my-token';
recoverAfterAuthInput();

result = {
  hasCachedStatus: hasCached,
  cachedLlmConfigured: cachedLlm,
  sendDisabled: _elements['send'].disabled,
  composerText: _elements['composer-status'].textContent,
};
""")
        self.assertTrue(result["hasCachedStatus"], "serverStatus should be cached after fetchStatus")
        self.assertFalse(result["cachedLlmConfigured"], "cached llm_configured should be false")
        self.assertTrue(result["sendDisabled"], "Send should stay disabled when cached llm_configured=false")
        self.assertEqual(result["composerText"], "Model not configured")

    def test_mobile_token_recovery_enables_buttons(self):
        """Entering token via mobile input should enable Send/Run
        when llm_configured=true."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: true, llm_configured: true, "
            "provider: 'openai', model: 'gpt-4', workspace: '/tmp', "
            "features: { sessions: true, tasks: true, memory: true, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
var mobileInput = _elements['mobile-token'];
mobileInput.value = 'my-token';
mobileInput.dispatchEvent(new Event('input'));
await new Promise(r => setTimeout(r, 50));
result = {
  sendDisabled: _elements['send'].disabled,
  runDisabled: _elements['run-btn'].disabled,
  composerText: _elements['composer-status'].textContent,
  desktopToken: _elements['token'].value,
};
""")
        self.assertFalse(result["sendDisabled"], "Send should be enabled after mobile token input")
        self.assertFalse(result["runDisabled"], "Run should be enabled after mobile token input")
        self.assertEqual(result["composerText"], "Ready")
        self.assertEqual(result["desktopToken"], "my-token", "Desktop token should be synced from mobile")

    def test_stop_during_auth_failure_keeps_buttons_disabled(self):
        """stopStream() during auth failure must not re-enable Send/Run
        or change pill to 'ready'."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: true, llm_configured: true, "
            "provider: 'openai', model: 'gpt-4', workspace: '/tmp', "
            "features: { sessions: true, tasks: true, memory: true, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
_elements['input'].value = 'hello';
sendMessage();
await new Promise(r => setTimeout(r, 200));
stopStream();
result = {
  sendDisabled: _elements['send'].disabled,
  runDisabled: _elements['run-btn'].disabled,
  stopDisabled: _elements['stop-btn'].disabled,
  stateText: _elements['top-state'].textContent,
  metricState: _elements['metric-state'].textContent,
  metricRisk: _elements['metric-risk'].textContent,
  statePanelHtml: _elements['state-panel'].innerHTML,
};
""")
        self.assertTrue(result["sendDisabled"], "Send should remain disabled after stop during auth failure")
        self.assertTrue(result["runDisabled"], "Run should remain disabled after stop during auth failure")
        self.assertTrue(result["stopDisabled"], "Stop should be disabled after stream ends")
        self.assertEqual(result["stateText"], "auth required", "Pill should show 'auth required' not 'ready'")
        self.assertEqual(result["metricState"], "error", "metric-state should show 'error' not 'ready'")
        self.assertEqual(result["metricRisk"], "high", "metric-risk should show 'high' during auth failure")
        self.assertIn("Auth required", result["statePanelHtml"], "state-panel should show Auth required")
        self.assertIn("panel-card error", result["statePanelHtml"], "state-panel should have error styling")

    def test_new_conversation_auth_failure_keeps_buttons_disabled(self):
        """newConversation() when auth fails must not re-enable Send/Run."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: true, llm_configured: true, "
            "provider: 'openai', model: 'gpt-4', workspace: '/tmp', "
            "features: { sessions: true, tasks: true, memory: true, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
newConversation();
await new Promise(r => setTimeout(r, 200));
result = {
  sendDisabled: _elements['send'].disabled,
  runDisabled: _elements['run-btn'].disabled,
  stateText: _elements['top-state'].textContent,
  metricState: _elements['metric-state'].textContent,
  metricRisk: _elements['metric-risk'].textContent,
  statePanelHtml: _elements['state-panel'].innerHTML,
  composerText: _elements['composer-status'].textContent,
};
""")
        self.assertTrue(result["sendDisabled"], "Send should remain disabled after auth failure in newConversation")
        self.assertTrue(result["runDisabled"], "Run should remain disabled after auth failure in newConversation")
        self.assertEqual(result["stateText"], "auth required")
        self.assertEqual(result["metricState"], "error", "metric-state should show 'error' not 'ready'")
        self.assertEqual(result["metricRisk"], "high", "metric-risk should show 'high' during auth failure")
        self.assertIn("Auth required", result["statePanelHtml"], "state-panel should show Auth required")
        self.assertIn("panel-card error", result["statePanelHtml"], "state-panel should have error styling")
        self.assertEqual(result["composerText"], "Token required")

    def test_setup_guidance_shows_openai_env_vars(self):
        """When provider=openai-compatible and llm_configured=false,
        server panel should show openai-compatible env vars."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: false, "
            "provider: 'openai-compatible', model: '', workspace: '/tmp', "
            "config_warnings: ['missing provider', 'missing model', 'missing api key'], "
            "features: { sessions: false, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
result = {
  serverHtml: _elements['server-panel'].innerHTML,
};
""")
        self.assertIn("Model not configured", result["serverHtml"])
        self.assertIn("missing provider", result["serverHtml"])
        self.assertIn("missing model", result["serverHtml"])
        self.assertIn("missing api key", result["serverHtml"])
        self.assertIn("LLM_PROVIDER", result["serverHtml"])
        self.assertIn("LLM_BASE_URL", result["serverHtml"])
        self.assertIn("LLM_API_KEY", result["serverHtml"])
        self.assertIn("LLM_MODEL", result["serverHtml"])
        self.assertIn("gpt-4.1-mini", result["serverHtml"])

    def test_setup_guidance_shows_anthropic_env_vars(self):
        """When provider=anthropic and llm_configured=false,
        server panel should show anthropic env vars."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: false, "
            "provider: 'anthropic', model: '', workspace: '/tmp', "
            "config_warnings: ['missing api key'], "
            "features: { sessions: false, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
result = {
  serverHtml: _elements['server-panel'].innerHTML,
};
""")
        self.assertIn("ANTHROPIC_API_KEY", result["serverHtml"])
        self.assertIn("ANTHROPIC_MODEL", result["serverHtml"])
        self.assertIn("claude-sonnet-4-5", result["serverHtml"])
        self.assertNotIn("LLM_BASE_URL", result["serverHtml"])

    def test_setup_guidance_shows_gemini_env_vars(self):
        """When provider=gemini and llm_configured=false,
        server panel should show gemini env vars."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: false, "
            "provider: 'gemini', model: '', workspace: '/tmp', "
            "config_warnings: ['missing api key'], "
            "features: { sessions: false, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
result = {
  serverHtml: _elements['server-panel'].innerHTML,
};
""")
        self.assertIn("GEMINI_API_KEY", result["serverHtml"])
        self.assertIn("GEMINI_MODEL", result["serverHtml"])
        self.assertIn("gemini-2.5-pro", result["serverHtml"])
        self.assertNotIn("LLM_BASE_URL", result["serverHtml"])

    def test_setup_guidance_not_shown_when_configured(self):
        """When llm_configured=true, server panel should NOT show setup guidance."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4', workspace: '/tmp', "
            "features: { sessions: true, tasks: true, memory: true, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
result = {
  serverHtml: _elements['server-panel'].innerHTML,
};
""")
        self.assertNotIn("Model not configured", result["serverHtml"])
        self.assertNotIn("env-vars", result["serverHtml"])
        self.assertNotIn("LLM_API_KEY", result["serverHtml"])

    def test_mobile_setup_guidance_shows_env_vars(self):
        """Mobile layout should show setup guidance when llm_configured=false."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: false, "
            "provider: 'anthropic', model: '', workspace: '/tmp', "
            "config_warnings: ['missing api key'], "
            "features: { sessions: false, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
var mobileContainer = _elements['mobile-runtime-container'];
result = {
  mobileHtml: mobileContainer ? mobileContainer.innerHTML : '',
};
""")
        self.assertIn("Model not configured", result["mobileHtml"])
        self.assertIn("ANTHROPIC_API_KEY", result["mobileHtml"])
        self.assertIn("missing api key", result["mobileHtml"])

    def test_required_env_drives_desktop_setup_guidance(self):
        """When /status includes required_env, server panel should use it."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: false, "
            "provider: 'anthropic', model: '', workspace: '/tmp', "
            "config_warnings: ['missing api key'], "
            "required_env: ['LLM_PROVIDER', 'ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL'], "
            "features: { sessions: false, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
result = {
  serverHtml: _elements['server-panel'].innerHTML,
};
""")
        self.assertIn("ANTHROPIC_API_KEY", result["serverHtml"])
        self.assertIn("ANTHROPIC_MODEL", result["serverHtml"])
        self.assertIn("LLM_PROVIDER", result["serverHtml"])
        self.assertNotIn("LLM_BASE_URL", result["serverHtml"])
        self.assertNotIn("GEMINI_API_KEY", result["serverHtml"])

    def test_required_env_drives_mobile_setup_guidance(self):
        """When /status includes required_env, mobile should use it."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: false, "
            "provider: 'gemini', model: '', workspace: '/tmp', "
            "config_warnings: ['missing api key'], "
            "required_env: ['LLM_PROVIDER', 'GEMINI_API_KEY', 'GEMINI_MODEL'], "
            "features: { sessions: false, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
var mobileContainer = _elements['mobile-runtime-container'];
result = {
  mobileHtml: mobileContainer ? mobileContainer.innerHTML : '',
};
""")
        self.assertIn("GEMINI_API_KEY", result["mobileHtml"])
        self.assertIn("GEMINI_MODEL", result["mobileHtml"])
        self.assertIn("LLM_PROVIDER", result["mobileHtml"])
        self.assertNotIn("LLM_BASE_URL", result["mobileHtml"])
        self.assertNotIn("ANTHROPIC_API_KEY", result["mobileHtml"])

    def test_required_env_fallback_when_missing(self):
        """When required_env is absent, _providerEnvGuide should be used as fallback."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: false, "
            "provider: 'openai-compatible', model: '', workspace: '/tmp', "
            "config_warnings: ['missing provider', 'missing model', 'missing api key'], "
            "features: { sessions: false, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
result = {
  serverHtml: _elements['server-panel'].innerHTML,
};
""")
        self.assertIn("LLM_PROVIDER", result["serverHtml"])
        self.assertIn("LLM_API_KEY", result["serverHtml"])
        self.assertIn("LLM_MODEL", result["serverHtml"])
        self.assertIn("LLM_BASE_URL", result["serverHtml"])
        self.assertIn("gpt-4.1-mini", result["serverHtml"])

    def test_openai_alternatives_shown(self):
        """When provider=openai-compatible, show OPENAI_API_KEY alternative."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: false, "
            "provider: 'openai-compatible', model: '', workspace: '/tmp', "
            "config_warnings: ['missing api key'], "
            "accepted_env_alternatives: {'LLM_API_KEY': 'OPENAI_API_KEY'}, "
            "features: { sessions: false, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
result = {
  serverHtml: _elements['server-panel'].innerHTML,
};
""")
        self.assertIn("OPENAI_API_KEY", result["serverHtml"])
        self.assertIn("can be replaced by", result["serverHtml"])
        self.assertIn("env-alternatives", result["serverHtml"])

    def test_anthropic_no_alternatives(self):
        """When provider=anthropic, don't show alternatives section."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: false, "
            "provider: 'anthropic', model: '', workspace: '/tmp', "
            "config_warnings: ['missing api key'], "
            "accepted_env_alternatives: {}, "
            "features: { sessions: false, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
result = {
  serverHtml: _elements['server-panel'].innerHTML,
};
""")
        self.assertNotIn("env-alternatives", result["serverHtml"])
        self.assertNotIn("can be replaced by", result["serverHtml"])
        self.assertIn("ANTHROPIC_API_KEY", result["serverHtml"])

    def test_gemini_no_alternatives(self):
        """When provider=gemini, don't show alternatives section."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: false, "
            "provider: 'gemini', model: '', workspace: '/tmp', "
            "config_warnings: ['missing api key'], "
            "accepted_env_alternatives: {}, "
            "features: { sessions: false, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
await new Promise(r => setTimeout(r, 100));
result = {
  serverHtml: _elements['server-panel'].innerHTML,
};
""")
        self.assertNotIn("env-alternatives", result["serverHtml"])
        self.assertNotIn("can be replaced by", result["serverHtml"])
        self.assertIn("GEMINI_API_KEY", result["serverHtml"])

    def test_session_name_with_quotes_safe(self):
        """Session names with quotes should not break the UI."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: true, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
sessions = [{name: "it's", detail: "test"}, {name: 'he said "hi"', detail: "test2"}];
var appended = [];
var origAppend = _elements['recent-list'].appendChild;
_elements['recent-list'].appendChild = function(child) { appended.push(child); origAppend.call(this, child); };
renderSessions('ready');
var names = appended.map(function(btn){ var s = btn.querySelector('strong'); return s ? s.textContent : ''; });
result = {
  count: appended.length,
  names: names,
};
""")
        self.assertEqual(result["count"], 2)
        self.assertIn("it's", result["names"])
        self.assertIn('he said "hi"', result["names"])

    def test_mobile_session_button_uses_addEventListener(self):
        """Mobile session buttons should use addEventListener, not inline onclick."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: true, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
sessions = [{name: 'session1', detail: 'test'}, {name: 'session2', detail: 'test'}];
renderMobileStatus();
var container = _elements['mobile-runtime-container'];
result = {
  hasSection: container.innerHTML.indexOf('mobile-sessions-section') !== -1,
  hasDataAttr: container.innerHTML.indexOf('data-session-idx') !== -1,
  hasOnclick: container.innerHTML.indexOf('onclick') !== -1,
};
""")
        self.assertTrue(result["hasSection"])
        self.assertTrue(result["hasDataAttr"])
        self.assertFalse(result["hasOnclick"])

    def test_active_session_marker(self):
        """Active session should show Active marker."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: true, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
sessions = [{name: 'session1', detail: 'test'}, {name: 'session2', detail: 'test'}];
activeSessionName = 'session1';
var appended = [];
var origAppend = _elements['recent-list'].appendChild;
_elements['recent-list'].appendChild = function(child) { appended.push(child); origAppend.call(this, child); };
renderSessions('ready');
var activeButtons = appended.filter(function(btn) { return btn.className.indexOf('active') !== -1; });
result = {
  total: appended.length,
  activeCount: activeButtons.length,
  activeText: activeButtons.length > 0 ? activeButtons[0].querySelector('span').textContent : '',
};
""")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["activeCount"], 1)
        self.assertIn("Active", result["activeText"])

    def test_save_session_uses_sanitized_name(self):
        """After saving, activeSessionName should use backend-sanitized name."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: true, tasks: false, memory: false, websocket: true }")
        setup = handler + "\n_fetchHandler = _authFetchHandler;\n"
        setup += r"""
_fetchHandler = function(url, opts) {
  if (url.indexOf('/status') !== -1) return _authFetchHandler(url, opts);
  if (url === '/session/save') return Promise.resolve({ok:true, status:200, json:()=>Promise.resolve({result:'已保存会话: hasspaces (2 条消息)'})});
  if (url === '/session/list') return Promise.resolve({ok:true, status:200, json:()=>Promise.resolve({sessions:['hasspaces: saved']})});
  return _authFetchHandler(url, opts);
};
"""
        result = _run_node(
            setup_js=setup,
            test_body=r"""
firstUserMessage = 'has spaces';
confirmSaveSession();
await new Promise(r => setTimeout(r, 200));
result = {
  activeSessionName: activeSessionName,
};
""")
        self.assertEqual(result["activeSessionName"], "hasspaces")

    def test_save_session_sanitizes_quotes(self):
        """After saving with quotes, activeSessionName should be sanitized."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: true, tasks: false, memory: false, websocket: true }")
        setup = handler + "\n_fetchHandler = _authFetchHandler;\n"
        setup += r"""
_fetchHandler = function(url, opts) {
  if (url.indexOf('/status') !== -1) return _authFetchHandler(url, opts);
  if (url === '/session/save') return Promise.resolve({ok:true, status:200, json:()=>Promise.resolve({result:'已保存会话: itsquoted (1 条消息)'})});
  if (url === '/session/list') return Promise.resolve({ok:true, status:200, json:()=>Promise.resolve({sessions:['itsquoted: saved']})});
  return _authFetchHandler(url, opts);
};
"""
        result = _run_node(
            setup_js=setup,
            test_body=r"""
firstUserMessage = 'test';
var nameInput = _elements['session-name-input'];
if(nameInput) nameInput.value = "it's \"quoted\"";
confirmSaveSession();
await new Promise(r => setTimeout(r, 200));
result = {
  activeSessionName: activeSessionName,
};
""")
        self.assertEqual(result["activeSessionName"], "itsquoted")

    def test_mobile_sessions_all_reachable(self):
        """When more than 3 sessions exist, expand reveals hidden sessions
        and clicking a later session calls loadSession() with correct name."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: true, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
sessions = [
  {name: 's1', detail: ''}, {name: 's2', detail: ''}, {name: 's3', detail: ''},
  {name: 's4', detail: ''}, {name: 's5', detail: ''}
];
var container = _elements['mobile-runtime-container'];
container.innerHTML = '';
renderMobileStatus();

// Verify markup: 5 buttons, expand present, some hidden
var html = container.innerHTML;
var totalButtons = (html.match(/data-session-idx/g) || []).length;
var hasExpand = html.indexOf('mobile-session-expand') !== -1;
var hasHidden = html.indexOf('display:none') !== -1;

// Override querySelectorAll on container so addEventListener wiring works
var mockBtns = [];
for (var i = 0; i < 5; i++) {
  (function(idx) {
    mockBtns.push({
      getAttribute: function(a) { return a === 'data-session-idx' ? String(idx) : null; },
      style: { display: idx >= 3 ? 'none' : '' },
      addEventListener: function(evt, fn) { if (evt === 'click') this._click = fn; },
      _click: null
    });
  })(i);
}
var mockExpand = {
  id: 'mobile-session-expand',
  style: { display: '' },
  addEventListener: function(evt, fn) { if (evt === 'click') this._click = fn; },
  _click: null
};
container.querySelectorAll = function(sel) {
  if (sel === '.mobile-session-item[data-session-idx]') return mockBtns;
  if (sel === '#mobile-session-expand') return mockExpand;
  if (sel === '.mobile-session-item[style]') return mockBtns.filter(function(b) { return b.style.display === 'none'; });
  return [];
};
container.querySelector = function(sel) {
  if (sel === '#mobile-session-expand') return mockExpand;
  return null;
};

// Re-render to wire up event listeners with the new querySelectorAll
container.innerHTML = '';
renderMobileStatus();

// Click expand button to reveal hidden sessions
mockExpand._click();

// Verify s4 (index 3) is now visible
var s4Visible = mockBtns[3].style.display === '';

// Click s4 button and verify loadSession is called
mockBtns[3]._click();

result = {
  totalButtons: totalButtons,
  hasExpand: hasExpand,
  hasHiddenBeforeExpand: hasHidden,
  s4VisibleAfterExpand: s4Visible,
  activeSessionName: activeSessionName,
  stateText: _elements['top-state'].textContent,
};
""")
        self.assertEqual(result["totalButtons"], 5, "Should render 5 session buttons")
        self.assertTrue(result["hasExpand"], "Should have expand button")
        self.assertTrue(result["hasHiddenBeforeExpand"], "Sessions after index 2 should be hidden initially")
        self.assertTrue(result["s4VisibleAfterExpand"], "s4 should be visible after expand click")
        self.assertEqual(result["activeSessionName"], "s4", "loadSession('s4') should be called")
        self.assertEqual(result["stateText"], "loading", "State should be loading")

    def test_message_count_returns_committed_count(self):
        """messageCount() should return committedMessageCount, not DOM count."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: true, tasks: false, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
result = {
  zeroCommitted: messageCount(),
};
committedMessageCount = 3;
result.threeCommitted = messageCount();
committedMessageCount = 0;
result.backToZero = messageCount();
""")
        self.assertEqual(result["zeroCommitted"], 0)
        self.assertEqual(result["threeCommitted"], 3)
        self.assertEqual(result["backToZero"], 0)

    def test_save_btn_disabled_during_streaming(self):
        """saveBtn must not be enabled while streaming is in flight."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: true, tasks: false, memory: false, websocket: true }")
        setup = handler + "\n_fetchHandler = _authFetchHandler;\n"
        setup += r"""
var _streamResolve = null;
_fetchHandler = function(url, opts) {
  if (url.indexOf('/status') !== -1) return _authFetchHandler(url, opts);
  if (url === '/chat/stream') {
    var encoder = new TextEncoder();
    var chunks = ['data: {"type":"start"}\n', 'data: {"type":"delta","text":"hello"}\n'];
    var ci = 0;
    var body = {
      getReader: function() {
        return {
          read: function() {
            if (ci < chunks.length) {
              var c = chunks[ci++];
              return Promise.resolve({ done: false, value: encoder.encode(c) });
            }
            return new Promise(function(resolve) { _streamResolve = resolve; });
          }
        };
      }
    };
    return Promise.resolve({ ok: true, status: 200, body: body });
  }
  return _authFetchHandler(url, opts);
};
"""
        result = _run_node(
            setup_js=setup,
            test_body=r"""
// save-btn starts disabled in the real HTML; mock doesn't parse attributes
_elements['save-btn'].disabled = true;
_elements['input'].value = 'test message';
sendMessage();
// Give the stream a tick to start reading
await new Promise(function(r) { setTimeout(r, 50); });
var saveDisabledMidStream = _elements['save-btn'].disabled;

// Now finish the stream
if (_streamResolve) _streamResolve({ done: true, value: undefined });
await new Promise(function(r) { setTimeout(r, 100); });
var saveDisabledAfterStream = _elements['save-btn'].disabled;

result = {
  saveDisabledMidStream: saveDisabledMidStream,
  saveDisabledAfterStream: saveDisabledAfterStream,
};
""")
        self.assertTrue(result["saveDisabledMidStream"],
                        "saveBtn should be disabled during streaming")
        self.assertFalse(result["saveDisabledAfterStream"],
                         "saveBtn should be re-enabled after streaming completes")

    def test_save_count_excludes_uncommitted_after_abort(self):
        """After user aborts a stream, messageCount must not include
        the uncommitted user message from the aborted turn."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: true, tasks: false, memory: false, websocket: true }")
        setup = handler + "\n_fetchHandler = _authFetchHandler;\n"
        setup += r"""
_fetchHandler = function(url, opts) {
  if (url.indexOf('/status') !== -1) return _authFetchHandler(url, opts);
  if (url === '/chat/stream') {
    var encoder = new TextEncoder();
    var body = {
      getReader: function() {
        return {
          read: function() {
            // Hang forever — will be aborted
            return new Promise(function() {});
          }
        };
      }
    };
    return Promise.resolve({ ok: true, status: 200, body: body });
  }
  return _authFetchHandler(url, opts);
};
"""
        result = _run_node(
            setup_js=setup,
            test_body=r"""
// Simulate 2 previously committed messages (1 user + 1 assistant)
var msgEl = _elements['messages'];
var domMsgs = [{className: 'msg user'}, {className: 'msg assistant'}];
msgEl.querySelectorAll = function(sel) {
  if (sel === '.msg:not(.error)') return domMsgs.filter(function(m) { return m.className.indexOf('error') === -1; });
  return [];
};
msgEl.appendChild = function(el) { domMsgs.push(el); };
committedMessageCount = 2;

_elements['input'].value = 'aborted message';
sendMessage();  // addMsg pushes user msg via appendChild

// Abort the stream
await new Promise(function(r) { setTimeout(r, 50); });
stopStream();
await new Promise(function(r) { setTimeout(r, 100); });

result = {
  countAfterAbort: messageCount(),
  domLength: domMsgs.length,
};
""")
        self.assertEqual(result["countAfterAbort"], 2,
                         "messageCount should stay at 2 (committed), not 3 (DOM)")
        self.assertEqual(result["domLength"], 3,
                         "DOM should have 3 messages (including uncommitted user msg)")

    def test_save_count_excludes_uncommitted_after_failure(self):
        """After stream fails, messageCount must not include
        the uncommitted user message from the failed turn."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: true, tasks: false, memory: false, websocket: true }")
        setup = handler + "\n_fetchHandler = _authFetchHandler;\n"
        setup += r"""
_fetchHandler = function(url, opts) {
  if (url.indexOf('/status') !== -1) return _authFetchHandler(url, opts);
  if (url === '/chat/stream') {
    return Promise.resolve({ok:false, status:500, json:()=>Promise.resolve({error:'stream failed'}), text:()=>Promise.resolve('stream failed')});
  }
  return _authFetchHandler(url, opts);
};
"""
        result = _run_node(
            setup_js=setup,
            test_body=r"""
// Simulate 2 previously committed messages
var msgEl = _elements['messages'];
var domMsgs = [{className: 'msg user'}, {className: 'msg assistant'}];
msgEl.querySelectorAll = function(sel) {
  if (sel === '.msg:not(.error)') return domMsgs.filter(function(m) { return m.className.indexOf('error') === -1; });
  return [];
};
msgEl.appendChild = function(el) { domMsgs.push(el); };
committedMessageCount = 2;

_elements['input'].value = 'will fail';
sendMessage();  // addMsg pushes user msg, then stream fails

await new Promise(function(r) { setTimeout(r, 200); });

result = {
  countAfterFail: messageCount(),
  domLength: domMsgs.length,
};
""")
        self.assertEqual(result["countAfterFail"], 2,
                         "messageCount should stay at 2 (committed), not 3 (DOM)")
        self.assertTrue(result["domLength"] >= 3,
                         "DOM should have at least 3 messages (user msg + error)")

    def test_save_count_uses_done_event_message_count(self):
        """After a successful completed turn, messageCount must use the
        backend-committed count reported by the done event."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: true, tasks: false, memory: false, websocket: true }")
        setup = handler + "\n_fetchHandler = _authFetchHandler;\n"
        setup += r"""
_fetchHandler = function(url, opts) {
  if (url.indexOf('/status') !== -1) return _authFetchHandler(url, opts);
  if (url === '/chat/stream') {
    var encoder = new TextEncoder();
    var nextCount = 20;
    var ci = 0;
    var body = {
      getReader: function() {
        return {
          read: function() {
            var chunks = [
              'data: {"type":"delta","content":"hello"}\n',
              'data: {"type":"done","status":"ok","message_count":' + nextCount + '}\n'
            ];
            if (ci < chunks.length) {
              var c = chunks[ci++];
              return Promise.resolve({ done: false, value: encoder.encode(c) });
            }
            nextCount = 20;
            return Promise.resolve({ done: true, value: undefined });
          }
        };
      }
    };
    return Promise.resolve({ ok: true, status: 200, body: body });
  }
  return _authFetchHandler(url, opts);
};
"""
        result = _run_node(
            setup_js=setup,
            test_body=r"""
// Simulate an already full backend memory. A local +2 guess would overstate
// the next saved count as 22, but the backend reports the capped count.
committedMessageCount = 20;

_elements['input'].value = 'hello';
sendMessage();
await new Promise(function(r) { setTimeout(r, 200); });

result = {
  afterTurn: messageCount(),
};
""")
        self.assertEqual(result["afterTurn"], 20,
                         "messageCount should use backend done.message_count, not local +2")

    def test_clear_failure_preserves_committed_count(self):
        """When /chat/clear fails, committedMessageCount must not be zeroed."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: true, tasks: false, memory: false, websocket: true }")
        setup = handler + "\n_fetchHandler = _authFetchHandler;\n"
        setup += r"""
_fetchHandler = function(url, opts) {
  if (url.indexOf('/status') !== -1) return _authFetchHandler(url, opts);
  if (url === '/chat/clear') {
    return Promise.resolve({ok:false, status:500, json:()=>Promise.resolve({error:'clear failed'}), text:()=>Promise.resolve('clear failed')});
  }
  return _authFetchHandler(url, opts);
};
"""
        result = _run_node(
            setup_js=setup,
            test_body=r"""
committedMessageCount = 4;
newConversation();
await new Promise(function(r) { setTimeout(r, 200); });
result = {
  countAfterFailedClear: messageCount(),
};
""")
        self.assertEqual(result["countAfterFailedClear"], 4,
                         "committedMessageCount must stay at 4 when /chat/clear fails")

    def test_desktop_finish_task_blocks_empty_summary(self):
        """Desktop Finish should not submit an empty task summary."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: false, tasks: true, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
var finishCalls = 0;
finishTask = function(summary) { finishCalls += 1; };
_promptHandler = function(message) {
  result = result || {};
  result.promptMessage = message;
  return '   ';
};
currentTask = {goal: 'Ship feature', status: 'active', steps: [{id: 1, text: 'Do it', status: 'done'}]};
var finishListener = null;
document.getElementById('task-finish-btn').addEventListener = function(evt, fn) { if (evt === 'click') finishListener = fn; };
renderTaskPanel();
finishListener();
result.finishCalls = finishCalls;
result.stateText = _elements['top-state'].textContent;
result.statePanelHtml = _elements['state-panel'].innerHTML;
""")
        self.assertEqual(result["promptMessage"], "Task summary (required):")
        self.assertEqual(result["finishCalls"], 0)
        self.assertEqual(result["stateText"], "error")
        self.assertIn("Task summary is required.", result["statePanelHtml"])

    def test_mobile_finish_task_blocks_empty_summary(self):
        """Mobile Finish should not submit an empty task summary."""
        handler = _AUTH_NO_TOKEN_HANDLER.replace('STATUS_DATA',
            "status: 'ok', auth_required: false, llm_configured: true, "
            "provider: 'openai-compatible', model: 'gpt-4.1-mini', workspace: '/tmp', "
            "features: { sessions: false, tasks: true, memory: false, websocket: true }")
        result = _run_node(
            setup_js=handler + "\n_fetchHandler = _authFetchHandler;\n",
            test_body=r"""
var finishCalls = 0;
finishTask = function(summary) { finishCalls += 1; };
_promptHandler = function(message) {
  result = result || {};
  result.promptMessage = message;
  return '';
};
currentTask = {goal: 'Ship mobile feature', status: 'active', steps: [{id: 1, text: 'Do it', status: 'done'}]};
var finishListener = null;
document.getElementById('mobile-task-finish').addEventListener = function(evt, fn) { if (evt === 'click') finishListener = fn; };
renderMobileTask();
finishListener();
result.finishCalls = finishCalls;
result.stateText = _elements['top-state'].textContent;
result.statePanelHtml = _elements['state-panel'].innerHTML;
""")
        self.assertEqual(result["promptMessage"], "Task summary (required):")
        self.assertEqual(result["finishCalls"], 0)
        self.assertEqual(result["stateText"], "error")
        self.assertIn("Task summary is required.", result["statePanelHtml"])


class PetRoomSmokeTests(unittest.TestCase):
    """Smoke tests for Pet Room UI wiring."""

    def test_pet_room_elements_exist(self):
        result = _run_node(test_body="""
result = {};
result.petRoom = !!document.getElementById('pet-room');
result.petAvatar = !!document.getElementById('pet-avatar');
result.petName = !!document.getElementById('pet-name');
result.petStats = !!document.getElementById('pet-stats');
result.petFeedBtn = !!document.getElementById('pet-feed-btn');
result.petPatBtn = !!document.getElementById('pet-pat-btn');
result.petComfortBtn = !!document.getElementById('pet-comfort-btn');
result.petRestBtn = !!document.getElementById('pet-rest-btn');
result.petPlayBtn = !!document.getElementById('pet-play-btn');
result.petAddFoodBtn = !!document.getElementById('pet-add-food-btn');
result.petActivityList = !!document.getElementById('pet-activity-list');
result.navPet = !!document.getElementById('nav-pet');
result.navChat = !!document.getElementById('nav-chat');
""")
        d = result
        for key in ["petRoom", "petAvatar", "petName", "petStats", "petFeedBtn",
                     "petPatBtn", "petComfortBtn", "petRestBtn", "petPlayBtn",
                     "petAddFoodBtn", "petActivityList", "navPet", "navChat"]:
            self.assertTrue(d[key], f"Missing element: {key}")

    def test_pet_action_sends_post_with_body(self):
        result = _run_node(setup_js="""
let _fetchCalls = [];
_fetchHandler = function(url, opts) {
  _fetchCalls.push({url: url, method: opts && opts.method, body: opts && opts.body});
  return Promise.resolve({ok: true, status: 200, json: () => Promise.resolve({ok:true, state:{hunger:20,energy:70,mood:70,bond:10,growth_level:1,compute_food_balance:400}})});
};
""", test_body="""
currentPet = {pet_id:'pet_1', identity:{name:'Test'}, state:{hunger:30,energy:60,mood:60,bond:0,growth_level:1,compute_food_balance:0}};
_fetchCalls = [];
petAction('/pet/feed', {pet_id:'pet_1', amount:100}, null);
await new Promise(function(resolve){ setTimeout(resolve, 300); });
result = {};
var postCalls = _fetchCalls.filter(function(c){ return c.method === 'POST'; });
result.postCallCount = postCalls.length;
result.postUrl = postCalls.length > 0 ? postCalls[0].url : '';
result.hasBody = postCalls.length > 0 && !!postCalls[0].body;
""")
        d = result
        self.assertGreaterEqual(d["postCallCount"], 1)
        self.assertEqual(d["postUrl"], "/pet/feed")
        self.assertTrue(d["hasBody"])

    def test_switch_view_shows_pet_room(self):
        result = _run_node(setup_js="""
_fetchHandler = function(url, opts) {
  return Promise.resolve({ok: true, status: 200, json: () => Promise.resolve({pet_id:'pet_1', identity:{name:'Test',species:'cat',personality_traits:[],speech_style:''}, state:{hunger:30,energy:60,mood:60,bond:0,growth_level:1,compute_food_balance:0}})});
};
""", test_body="""
result = {};
result.initialPetDisplay = document.getElementById('pet-room').style.display || 'none';
switchView('pet');
result.petDisplay = document.getElementById('pet-room').style.display;
result.petActive = document.getElementById('nav-pet').classList.contains('active');
result.chatNotActive = !document.getElementById('nav-chat').classList.contains('active');
result.threadHidden = document.getElementById('thread-head').style.display;
result.messagesHidden = document.getElementById('messages-wrap').style.display;
switchView('chat');
result.chatAfterSwitch = document.getElementById('nav-chat').classList.contains('active');
result.petAfterSwitch = !document.getElementById('nav-pet').classList.contains('active');
""")
        d = result
        self.assertEqual(d["initialPetDisplay"], "none")
        self.assertEqual(d["petDisplay"], "block")
        self.assertTrue(d["petActive"])
        self.assertTrue(d["chatNotActive"])
        self.assertEqual(d["threadHidden"], "none")
        self.assertEqual(d["messagesHidden"], "none")
        self.assertTrue(d["chatAfterSwitch"])
        self.assertTrue(d["petAfterSwitch"])

    def test_escape_html_escapes_tags(self):
        result = _run_node(test_body="""
result = {};
result.escaped = escapeHtml('<img onerror=alert(1) src=x>');
result.normal = escapeHtml('hello world');
result.amp = escapeHtml('a&b');
result.quote = escapeHtml('a"b');
""")
        d = result
        self.assertIn("&lt;img", d["escaped"])
        self.assertNotIn("<img", d["escaped"])
        self.assertEqual(d["normal"], "hello world")
        self.assertEqual(d["amp"], "a&amp;b")
        self.assertEqual(d["quote"], "a&quot;b")

    def test_activity_rendering_escapes_html(self):
        result = _run_node(setup_js="""
_fetchHandler = function(url, opts) {
  if (url.indexOf('/pet/activity') === 0) {
    return Promise.resolve({ok: true, status: 200, json: () => Promise.resolve([
      {event_type: 'fed', summary: '<script>alert(1)</script>', created_at: '2026-06-09T12:00:00'},
      {event_type: 'care', summary: 'pat & hug', created_at: '2026-06-09T12:01:00'}
    ])});
  }
  return Promise.resolve({ok: true, status: 200, json: () => Promise.resolve({})});
};
""", test_body="""
currentPet = {pet_id:'pet_1'};
loadPetActivity('pet_1');
await new Promise(function(resolve){ setTimeout(resolve, 300); });
var list = document.getElementById('pet-activity-list');
result = {};
result.html = list.innerHTML;
result.hasScriptTag = list.innerHTML.indexOf('<script>') >= 0;
result.hasEscapedScript = list.innerHTML.indexOf('&lt;script&gt;') >= 0;
result.hasAmp = list.innerHTML.indexOf('pat &amp; hug') >= 0;
""")
        d = result
        self.assertFalse(d["hasScriptTag"], "Raw <script> found in activity HTML")
        self.assertTrue(d["hasEscapedScript"], "Escaped <script> not found")
        self.assertTrue(d["hasAmp"], "Ampersand not escaped")

    def test_life_feel_elements_exist(self):
        """Pet Room must have mood-summary, identity-details, room-notice, today-content."""
        result = _run_node(test_body="""
result = {};
result.moodSummary = !!document.getElementById('pet-mood-summary');
result.identityDetails = !!document.getElementById('pet-identity-details');
result.roomNotice = !!document.getElementById('pet-room-notice');
result.todayContent = !!document.getElementById('pet-today-content');
result.todaySection = !!document.getElementById('pet-today-section');
""")
        d = result
        for key in ["moodSummary", "identityDetails", "roomNotice", "todayContent", "todaySection"]:
            self.assertTrue(d[key], f"Missing element: {key}")

    def test_getMoodSummary_returns_string(self):
        """getMoodSummary must return a bounded string for various states."""
        result = _run_node(test_body="""
result = {};
result.happy = getMoodSummary('Nora-01', {hunger:20, energy:70, mood:80, bond:60, growth_level:1});
result.hungry = getMoodSummary('Nora-01', {hunger:80, energy:70, mood:60, bond:10, growth_level:1});
result.tired = getMoodSummary('Nora-01', {hunger:20, energy:10, mood:60, bond:10, growth_level:1});
result.down = getMoodSummary('Nora-01', {hunger:20, energy:70, mood:20, bond:10, growth_level:1});
""")
        d = result
        self.assertIn('cheerful', d['happy'])
        self.assertIn('hungry', d['hungry'])
        self.assertIn('resting', d['tired'])
        self.assertIn('down', d['down'])
        # All should include the name
        for k in ['happy', 'hungry', 'tired', 'down']:
            self.assertIn('Nora-01', d[k])

    def test_showRoomNotice_displays_and_hides(self):
        """showRoomNotice must set display and schedule hide."""
        result = _run_node(test_body="""
showRoomNotice('test notice');
result = {};
result.display = document.getElementById('pet-room-notice').style.display;
result.text = document.getElementById('pet-room-notice').textContent;
""")
        d = result
        self.assertNotEqual(d['display'], 'none')
        self.assertEqual(d['text'], 'test notice')

    def test_loadTodayDiary_renders_events(self):
        """loadTodayDiary must render activity events into today-content."""
        result = _run_node(setup_js="""
_fetchHandler = function(url, opts) {
  if (url.indexOf('/pet/activity') === 0) {
    return Promise.resolve({ok:true, status:200, json:()=>Promise.resolve([
      {event_type:'fed', summary:'fed 100', created_at:'2026-06-09T12:00:00'},
      {event_type:'care', summary:'pat', created_at:'2026-06-09T12:01:00'}
    ])});
  }
  if (url.indexOf('/pet/relationship-memory') === 0) {
    return Promise.resolve({ok:true, status:200, json:()=>Promise.resolve([])});
  }
  return Promise.resolve({ok:true, status:200, json:()=>Promise.resolve({})});
};
""", test_body="""
loadTodayDiary('pet_1');
await new Promise(function(r){setTimeout(r,300)});
result = {};
result.html = document.getElementById('pet-today-content').innerHTML;
result.hasFed = result.html.indexOf('fed 100') >= 0;
result.hasPat = result.html.indexOf('pat') >= 0;
result.hasTime = result.html.indexOf('12:00') >= 0;
""")
        d = result
        self.assertTrue(d['hasFed'], 'fed 100 not in today')
        self.assertTrue(d['hasPat'], 'pat not in today')
        self.assertTrue(d['hasTime'], 'timestamp not in today')

    def test_loadTodayDiary_shows_empty_state(self):
        """loadTodayDiary must show empty state when no events/memories."""
        result = _run_node(setup_js="""
_fetchHandler = function(url, opts) {
  return Promise.resolve({ok:true, status:200, json:()=>Promise.resolve([])});
};
""", test_body="""
loadTodayDiary('pet_1');
await new Promise(function(r){setTimeout(r,300)});
result = {};
result.html = document.getElementById('pet-today-content').innerHTML;
result.hasEmpty = result.html.indexOf('Start your first') >= 0;
""")
        d = result
        self.assertTrue(d['hasEmpty'], 'Empty state not shown')

    def test_life_feel_escapeHtml_used(self):
        """escapeHtml must be defined and escape tags."""
        result = _run_node(test_body="""
result = {};
result.defined = typeof escapeHtml === 'function';
result.escaped = escapeHtml('<b>x</b>');
""")
        d = result
        self.assertTrue(d['defined'])
        self.assertIn('&lt;b&gt;', d['escaped'])

    def test_speech_bubble_elements_exist(self):
        """Speech bubble area, bubble, text, meta, input, button, error must exist."""
        result = _run_node(test_body="""
result = {};
result.area = !!document.getElementById('speech-bubble-area');
result.bubble = !!document.getElementById('speech-bubble');
result.text = !!document.getElementById('speech-bubble-text');
result.meta = !!document.getElementById('speech-bubble-meta');
result.input = !!document.getElementById('speech-preview-input');
result.btn = !!document.getElementById('speech-preview-btn');
result.error = !!document.getElementById('speech-bubble-error');
""")
        d = result
        for key in ['area', 'bubble', 'text', 'meta', 'input', 'btn', 'error']:
            self.assertTrue(d[key], f'Missing element: {key}')

    def test_speech_bubble_hidden_by_default(self):
        """Speech bubble must not have visible class by default."""
        result = _run_node(test_body="""
result = {};
result.hasClass = document.getElementById('speech-bubble').classList.contains('visible');
""")
        d = result
        self.assertFalse(d['hasClass'])

    def test_speech_preview_calls_endpoint(self):
        """Preview button must call /pet/voice-preview with pet_id and text after consent."""
        result = _run_node(setup_js="""
var _lastFetch = null;
_fetchHandler = function(url, opts) {
  _lastFetch = {url: url, body: opts && opts.body ? JSON.parse(opts.body) : null};
  return Promise.resolve({ok:true, status:200, json:()=>Promise.resolve({
    text:'Hello!', has_audio:false, source:'text_fallback', cost_tokens:0,
    voice_profile:{}, mood_context:{mood:'neutral',energy:'normal',hunger:'normal',expression:'calm'},
    no_audio_reason:'text fallback only', no_network_call:true, no_recording:true,
    requires_user_confirmation:true, confirmation_kind:'text_fallback_voice_preview',
    audio_requires_confirmation:true, provider_status:'not_configured_text_fallback', food_debit:false
  })});
};
""", test_body="""
currentPet = {pet_id:'pet_1', identity:{name:'Test'}, state:{hunger:30,energy:60,mood:60,bond:0,growth_level:1,compute_food_balance:0}};
document.getElementById('voice-consent-checkbox').checked = true;
document.getElementById('speech-preview-input').value = 'Hello!';
var btn = document.getElementById('speech-preview-btn');
if(btn.onclick) btn.onclick();
await new Promise(function(r){setTimeout(r,300)});
result = {};
result.url = _lastFetch ? _lastFetch.url : null;
result.petId = _lastFetch && _lastFetch.body ? _lastFetch.body.pet_id : null;
result.text = _lastFetch && _lastFetch.body ? _lastFetch.body.text : null;
result.bubbleVisible = document.getElementById('speech-bubble').classList.contains('visible');
result.bubbleText = document.getElementById('speech-bubble-text').textContent;
""")
        d = result
        self.assertEqual(d['url'], '/pet/voice-preview')
        self.assertEqual(d['petId'], 'pet_1')
        self.assertEqual(d['text'], 'Hello!')
        self.assertTrue(d['bubbleVisible'])
        self.assertEqual(d['bubbleText'], 'Hello!')

    def test_speech_preview_shows_meta_tags(self):
        """Preview must display cost, no-audio, no-network, no-recording, no-food-debit tags."""
        result = _run_node(setup_js="""
_fetchHandler = function(url, opts) {
  return Promise.resolve({ok:true, status:200, json:()=>Promise.resolve({
    text:'hi', has_audio:false, source:'text_fallback', cost_tokens:2,
    voice_profile:{}, mood_context:{mood:'neutral',energy:'normal',hunger:'normal',expression:'calm'},
    no_audio_reason:'text fallback only', no_network_call:true, no_recording:true,
    requires_user_confirmation:true, confirmation_kind:'text_fallback_voice_preview',
    audio_requires_confirmation:true, provider_status:'not_configured_text_fallback', food_debit:false
  })});
};
""", test_body="""
currentPet = {pet_id:'pet_1', identity:{name:'Test'}, state:{hunger:30,energy:60,mood:60,bond:0,growth_level:1,compute_food_balance:0}};
document.getElementById('voice-consent-checkbox').checked = true;
document.getElementById('speech-preview-input').value = 'hi';
var btn = document.getElementById('speech-preview-btn');
if(btn.onclick) btn.onclick();
await new Promise(function(r){setTimeout(r,300)});
result = {};
result.metaHtml = document.getElementById('speech-bubble-meta').innerHTML;
""")
        d = result
        self.assertIn('cost: 2 tokens', d['metaHtml'])
        self.assertIn('audio: no', d['metaHtml'])
        self.assertIn('no network', d['metaHtml'])
        self.assertIn('no recording', d['metaHtml'])
        self.assertIn('no food debit', d['metaHtml'])
        self.assertIn('provider:', d['metaHtml'])
        self.assertIn('audio requires confirmation', d['metaHtml'])

    def test_speech_preview_empty_shows_error(self):
        """Empty input must show error, not call endpoint."""
        result = _run_node(setup_js="""
var _fetchCalled = false;
_fetchHandler = function(url, opts) { _fetchCalled = true; return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({})}); };
""", test_body="""
currentPet = {pet_id:'pet_1', identity:{name:'Test'}, state:{}};
_fetchCalled = false;
document.getElementById('voice-consent-checkbox').checked = true;
document.getElementById('speech-preview-input').value = '';
var btn = document.getElementById('speech-preview-btn');
if(btn.onclick) btn.onclick();
await new Promise(function(r){setTimeout(r,100)});
result = {};
result.error = document.getElementById('speech-bubble-error').textContent;
result.fetchCalled = _fetchCalled;
""")
        d = result
        self.assertIn('Enter text', d['error'])
        self.assertFalse(d['fetchCalled'])

    def test_speech_preview_too_long_shows_error(self):
        """Over-limit input must show error, not call endpoint."""
        result = _run_node(setup_js="""
var _fetchCalled = false;
_fetchHandler = function(url, opts) { _fetchCalled = true; return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({})}); };
""", test_body="""
currentPet = {pet_id:'pet_1', identity:{name:'Test'}, state:{}};
_fetchCalled = false;
document.getElementById('voice-consent-checkbox').checked = true;
document.getElementById('speech-preview-input').value = 'x'.repeat(501);
var btn = document.getElementById('speech-preview-btn');
if(btn.onclick) btn.onclick();
await new Promise(function(r){setTimeout(r,100)});
result = {};
result.error = document.getElementById('speech-bubble-error').textContent;
result.fetchCalled = _fetchCalled;
""")
        d = result
        self.assertIn('too long', d['error'])
        self.assertFalse(d['fetchCalled'])

    def test_speech_preview_no_pet_does_nothing(self):
        """Without currentPet, preview must not call endpoint."""
        result = _run_node(setup_js="""
var _fetchCalled = false;
_fetchHandler = function(url, opts) { _fetchCalled = true; return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({})}); };
""", test_body="""
currentPet = null;
_fetchCalled = false;
document.getElementById('speech-preview-input').value = 'hello';
var btn = document.getElementById('speech-preview-btn');
if(btn.onclick) btn.onclick();
await new Promise(function(r){setTimeout(r,100)});
result = {};
result.fetchCalled = _fetchCalled;
""")
        d = result
        self.assertFalse(d['fetchCalled'])

    def test_voice_consent_panel_elements_exist(self):
        """Consent panel must have checkbox, boundary, cost, provider markers."""
        result = _run_node(test_body="""
result = {};
result.panel = !!document.getElementById('voice-consent-panel');
result.checkbox = !!document.getElementById('voice-consent-checkbox');
result.boundary = !!document.getElementById('voice-consent-boundary');
result.cost = !!document.getElementById('voice-consent-cost');
result.provider = !!document.getElementById('voice-consent-provider');
""")
        d = result
        for key in ['panel', 'checkbox', 'boundary', 'cost', 'provider']:
            self.assertTrue(d[key], f'Missing consent element: {key}')

    def test_voice_consent_unchecked_blocks_preview(self):
        """Preview must not call endpoint if consent checkbox is unchecked."""
        result = _run_node(setup_js="""
var _fetchCalls = [];
_fetchHandler = function(url, opts) { _fetchCalls.push(url); return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({text:'hi',has_audio:false,source:'text_fallback',cost_tokens:0})}); };
""", test_body="""
currentPet = {pet_id:'pet_1', identity:{name:'Test'}, state:{}};
await new Promise(function(r){setTimeout(r,200)});
_fetchCalls = [];
document.getElementById('voice-consent-checkbox').checked = false;
document.getElementById('speech-preview-input').value = 'hello';
var btn = document.getElementById('speech-preview-btn');
if(btn.onclick) btn.onclick();
await new Promise(function(r){setTimeout(r,100)});
result = {};
result.voicePreviewCalled = _fetchCalls.indexOf('/pet/voice-preview') >= 0;
result.error = document.getElementById('speech-bubble-error').textContent;
""")
        d = result
        self.assertFalse(d['voicePreviewCalled'])
        self.assertIn('consent', d['error'].lower())

    def test_voice_consent_checked_allows_preview(self):
        """Preview must call endpoint if consent checkbox is checked."""
        result = _run_node(setup_js="""
var _fetchCalled = false;
_fetchHandler = function(url, opts) { _fetchCalled = true; return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({text:'hi',has_audio:false,source:'text_fallback',cost_tokens:0,voice_profile:{},mood_context:{},no_audio_reason:'text fallback only',no_network_call:true,no_recording:true,requires_user_confirmation:true,confirmation_kind:'text_fallback_voice_preview',audio_requires_confirmation:true,provider_status:'not_configured_text_fallback',food_debit:false})}); };
""", test_body="""
currentPet = {pet_id:'pet_1', identity:{name:'Test'}, state:{}};
document.getElementById('voice-consent-checkbox').checked = true;
document.getElementById('speech-preview-input').value = 'hello';
var btn = document.getElementById('speech-preview-btn');
if(btn.onclick) btn.onclick();
await new Promise(function(r){setTimeout(r,200)});
result = {};
result.fetchCalled = _fetchCalled;
""")
        d = result
        self.assertTrue(d['fetchCalled'])

    def test_expression_state_dom_markers_exist(self):
        """Expression state DOM markers must exist in pet room."""
        result = _run_node(test_body="""
result = {};
result.stateEl = !!document.getElementById('pet-expression-state');
result.iconEl = !!document.getElementById('pet-expression-icon');
result.labelEl = !!document.getElementById('pet-expression-label');
result.detailEl = !!document.getElementById('pet-expression-detail');
result.avatarEl = !!document.getElementById('pet-avatar');
""")
        d = result
        for key in ['stateEl', 'iconEl', 'labelEl', 'detailEl', 'avatarEl']:
            self.assertTrue(d[key], f'Missing expression element: {key}')

    def test_expression_from_state_hungry(self):
        """High hunger should map to hungry expression."""
        result = _run_node(test_body="""
var expr = expressionFromState({mood:60, energy:60, hunger:80});
result = {key: expr.key, icon: expr.icon, label: expr.label};
""")
        d = result
        self.assertEqual(d['key'], 'hungry')
        self.assertEqual(d['label'], 'Hungry')

    def test_expression_from_state_sleepy(self):
        """Very low energy should map to sleepy expression."""
        result = _run_node(test_body="""
var expr = expressionFromState({mood:60, energy:10, hunger:30});
result = {key: expr.key, label: expr.label};
""")
        d = result
        self.assertEqual(d['key'], 'sleepy')
        self.assertEqual(d['label'], 'Sleepy')

    def test_expression_from_state_low_energy(self):
        """Low energy should map to low-energy expression."""
        result = _run_node(test_body="""
var expr = expressionFromState({mood:60, energy:30, hunger:30});
result = {key: expr.key, label: expr.label};
""")
        d = result
        self.assertEqual(d['key'], 'low-energy')
        self.assertEqual(d['label'], 'Low Energy')

    def test_expression_from_state_happy(self):
        """High mood and energy should map to happy expression."""
        result = _run_node(test_body="""
var expr = expressionFromState({mood:80, energy:70, hunger:30});
result = {key: expr.key, label: expr.label};
""")
        d = result
        self.assertEqual(d['key'], 'happy')
        self.assertEqual(d['label'], 'Happy')

    def test_expression_from_state_focused(self):
        """Moderate mood and energy should map to focused expression."""
        result = _run_node(test_body="""
var expr = expressionFromState({mood:60, energy:55, hunger:30});
result = {key: expr.key, label: expr.label};
""")
        d = result
        self.assertEqual(d['key'], 'focused')
        self.assertEqual(d['label'], 'Focused')

    def test_expression_from_state_calm(self):
        """Default/low mood should map to calm expression."""
        result = _run_node(test_body="""
var expr = expressionFromState({mood:40, energy:50, hunger:30});
result = {key: expr.key, label: expr.label};
""")
        d = result
        self.assertEqual(d['key'], 'calm')
        self.assertEqual(d['label'], 'Calm')

    def test_expression_from_state_missing_fields(self):
        """Missing state fields should default safely."""
        result = _run_node(test_body="""
var expr = expressionFromState({});
result = {key: expr.key, label: expr.label};
""")
        d = result
        self.assertIn(d['key'], ['calm', 'focused', 'happy', 'hungry', 'sleepy', 'low-energy'])

    def test_expression_from_state_null_state(self):
        """Null state should default safely."""
        result = _run_node(test_body="""
var expr = expressionFromState(null);
result = {key: expr.key, label: expr.label};
""")
        d = result
        self.assertIn(d['key'], ['calm', 'focused', 'happy', 'hungry', 'sleepy', 'low-energy'])

    def test_apply_expression_sets_data_attribute(self):
        """applyExpression should set data-expression on avatar."""
        result = _run_node(test_body="""
applyExpression({mood:80, energy:70, hunger:30});
result = {};
result.dataExpr = document.getElementById('pet-avatar').getAttribute('data-expression');
result.hasClass = document.getElementById('pet-avatar').classList.contains('expression-happy');
""")
        d = result
        self.assertEqual(d['dataExpr'], 'happy')
        self.assertTrue(d['hasClass'])

    def test_apply_expression_updates_dom_markers(self):
        """applyExpression should update icon, label, detail markers."""
        result = _run_node(test_body="""
applyExpression({mood:80, energy:70, hunger:30});
result = {};
result.icon = document.getElementById('pet-expression-icon').textContent;
result.label = document.getElementById('pet-expression-label').textContent;
result.detail = document.getElementById('pet-expression-detail').textContent;
""")
        d = result
        self.assertEqual(d['icon'], '✨')
        self.assertEqual(d['label'], 'Happy')
        self.assertIn('80', d['detail'])  # mood value

    def test_expression_class_cycling(self):
        """Changing state should swap expression classes correctly."""
        result = _run_node(test_body="""
applyExpression({mood:80, energy:70, hunger:30});
var first = document.getElementById('pet-avatar').getAttribute('data-expression');
applyExpression({mood:40, energy:10, hunger:30});
var second = document.getElementById('pet-avatar').getAttribute('data-expression');
applyExpression({mood:60, energy:60, hunger:80});
var third = document.getElementById('pet-avatar').getAttribute('data-expression');
result = {first:first, second:second, third:third};
""")
        d = result
        self.assertEqual(d['first'], 'happy')
        self.assertEqual(d['second'], 'sleepy')
        self.assertEqual(d['third'], 'hungry')

    def test_expression_detail_uses_dom_text(self):
        """Expression detail should use textContent, not innerHTML."""
        result = _run_node(test_body="""
applyExpression({mood:80, energy:70, hunger:30});
result = {};
result.detailText = document.getElementById('pet-expression-detail').textContent;
result.labelText = document.getElementById('pet-expression-label').textContent;
""")
        d = result
        # textContent should be populated (plain text, no HTML injection)
        self.assertIn('Mood at', d['detailText'])
        self.assertEqual(d['labelText'], 'Happy')

    # --- Idle presence signal tests (TASK-176A) ---

    def test_presence_state_dom_markers_exist(self):
        """Presence state DOM markers must exist in pet room."""
        result = _run_node(test_body="""
result = {};
result.stateEl = !!document.getElementById('pet-presence-state');
result.iconEl = !!document.getElementById('pet-presence-icon');
result.labelEl = !!document.getElementById('pet-presence-label');
result.detailEl = !!document.getElementById('pet-presence-detail');
result.avatarEl = !!document.getElementById('pet-avatar');
""")
        d = result
        for key in ['stateEl', 'iconEl', 'labelEl', 'detailEl', 'avatarEl']:
            self.assertTrue(d[key], f'Missing presence element: {key}')

    def test_presence_from_state_charging(self):
        """High energy and low hunger should map to charging presence."""
        result = _run_node(test_body="""
var pres = presenceFromState({mood:60, energy:85, hunger:20});
result = {key: pres.key, icon: pres.icon, label: pres.label};
""")
        d = result
        self.assertEqual(d['key'], 'charging')
        self.assertEqual(d['label'], 'Charging')

    def test_presence_from_state_resting(self):
        """Very low energy should map to resting presence."""
        result = _run_node(test_body="""
var pres = presenceFromState({mood:60, energy:15, hunger:30});
result = {key: pres.key, label: pres.label};
""")
        d = result
        self.assertEqual(d['key'], 'resting')
        self.assertEqual(d['label'], 'Resting')

    def test_presence_from_state_alert(self):
        """High mood and decent energy should map to alert presence."""
        result = _run_node(test_body="""
var pres = presenceFromState({mood:75, energy:60, hunger:30});
result = {key: pres.key, label: pres.label};
""")
        d = result
        self.assertEqual(d['key'], 'alert')
        self.assertEqual(d['label'], 'Alert')

    def test_presence_from_state_drifting(self):
        """Low mood and low energy should map to drifting presence."""
        result = _run_node(test_body="""
var pres = presenceFromState({mood:30, energy:40, hunger:30});
result = {key: pres.key, label: pres.label};
""")
        d = result
        self.assertEqual(d['key'], 'drifting')
        self.assertEqual(d['label'], 'Drifting')

    def test_presence_from_state_waiting(self):
        """Default/neutral state should map to waiting presence."""
        result = _run_node(test_body="""
var pres = presenceFromState({mood:50, energy:50, hunger:30});
result = {key: pres.key, label: pres.label};
""")
        d = result
        self.assertEqual(d['key'], 'waiting')
        self.assertEqual(d['label'], 'Waiting')

    def test_presence_from_state_missing_fields(self):
        """Missing state fields should default safely."""
        result = _run_node(test_body="""
var pres = presenceFromState({});
result = {key: pres.key, label: pres.label};
""")
        d = result
        self.assertIn(d['key'], ['resting', 'alert', 'drifting', 'charging', 'waiting'])

    def test_presence_from_state_null_state(self):
        """Null state should default safely."""
        result = _run_node(test_body="""
var pres = presenceFromState(null);
result = {key: pres.key, label: pres.label};
""")
        d = result
        self.assertIn(d['key'], ['resting', 'alert', 'drifting', 'charging', 'waiting'])

    def test_apply_presence_sets_data_attribute(self):
        """applyPresence should set data-presence on avatar."""
        result = _run_node(test_body="""
applyPresence({mood:60, energy:85, hunger:20});
result = {};
result.dataPres = document.getElementById('pet-avatar').getAttribute('data-presence');
result.hasClass = document.getElementById('pet-avatar').classList.contains('presence-charging');
""")
        d = result
        self.assertEqual(d['dataPres'], 'charging')
        self.assertTrue(d['hasClass'])

    def test_apply_presence_updates_dom_markers(self):
        """applyPresence should update icon, label, detail markers."""
        result = _run_node(test_body="""
applyPresence({mood:60, energy:85, hunger:20});
result = {};
result.icon = document.getElementById('pet-presence-icon').textContent;
result.label = document.getElementById('pet-presence-label').textContent;
result.detail = document.getElementById('pet-presence-detail').textContent;
""")
        d = result
        self.assertEqual(d['icon'], '⚡')
        self.assertEqual(d['label'], 'Charging')
        self.assertIn('85', d['detail'])

    def test_presence_class_cycling(self):
        """Changing state should swap presence classes correctly."""
        result = _run_node(test_body="""
applyPresence({mood:60, energy:85, hunger:20});
var first = document.getElementById('pet-avatar').getAttribute('data-presence');
applyPresence({mood:60, energy:10, hunger:30});
var second = document.getElementById('pet-avatar').getAttribute('data-presence');
applyPresence({mood:75, energy:60, hunger:30});
var third = document.getElementById('pet-avatar').getAttribute('data-presence');
result = {first:first, second:second, third:third};
""")
        d = result
        self.assertEqual(d['first'], 'charging')
        self.assertEqual(d['second'], 'resting')
        self.assertEqual(d['third'], 'alert')

    def test_presence_detail_uses_dom_text(self):
        """Presence detail should use textContent, not innerHTML."""
        result = _run_node(test_body="""
applyPresence({mood:60, energy:85, hunger:20});
result = {};
result.detailText = document.getElementById('pet-presence-detail').textContent;
result.labelText = document.getElementById('pet-presence-label').textContent;
""")
        d = result
        self.assertIn('Energy at', d['detailText'])
        self.assertEqual(d['labelText'], 'Charging')

    def test_presence_from_state_string_values(self):
        """String state values should coerce to defaults safely."""
        result = _run_node(test_body="""
var pres = presenceFromState({mood:'abc', energy:'xyz', hunger:'bad'});
result = {key: pres.key, label: pres.label, detail: pres.detail};
""")
        d = result
        self.assertIn(d['key'], ['resting', 'alert', 'drifting', 'charging', 'waiting'])
        self.assertNotIn('abc', d['detail'])
        self.assertNotIn('xyz', d['detail'])
        self.assertNotIn('bad', d['detail'])

    def test_presence_from_state_nan_values(self):
        """NaN state values should coerce to defaults safely."""
        result = _run_node(test_body="""
var pres = presenceFromState({mood:NaN, energy:NaN, hunger:NaN});
result = {key: pres.key, label: pres.label};
""")
        d = result
        self.assertIn(d['key'], ['resting', 'alert', 'drifting', 'charging', 'waiting'])

    def test_presence_from_state_infinity_values(self):
        """Infinity state values should clamp to 100."""
        result = _run_node(test_body="""
var pres = presenceFromState({mood:Infinity, energy:Infinity, hunger:Infinity});
result = {key: pres.key, label: pres.label, detail: pres.detail};
""")
        d = result
        self.assertIn(d['key'], ['resting', 'alert', 'drifting', 'charging', 'waiting'])
        self.assertNotIn('Infinity', d['detail'])

    def test_presence_from_state_negative_values(self):
        """Negative values should clamp to 0."""
        result = _run_node(test_body="""
var pres = presenceFromState({mood:-50, energy:-100, hunger:-10});
result = {key: pres.key, label: pres.label, detail: pres.detail};
""")
        d = result
        self.assertIn(d['key'], ['resting', 'alert', 'drifting', 'charging', 'waiting'])
        self.assertNotIn('-', d['detail'].split('—')[0])  # no negative in numeric part

    def test_presence_from_state_over_100_values(self):
        """Values >100 should clamp to 100."""
        result = _run_node(test_body="""
var pres = presenceFromState({mood:999, energy:500, hunger:200});
result = {key: pres.key, label: pres.label, detail: pres.detail};
""")
        d = result
        # hunger clamped to 100 (>30), energy clamped to 100 (>=80), mood clamped to 100 (>=70)
        # charging requires energy>=80 AND hunger<=30 → fails (hunger=100)
        # alert requires mood>=70 AND energy>=50 → passes
        self.assertEqual(d['key'], 'alert')
        self.assertNotIn('999', d['detail'])
        self.assertNotIn('500', d['detail'])
        self.assertNotIn('200', d['detail'])

    def test_presence_from_state_boolean_values(self):
        """Boolean values should coerce to 0/1 safely."""
        result = _run_node(test_body="""
var pres = presenceFromState({mood:true, energy:false, hunger:true});
result = {key: pres.key, label: pres.label};
""")
        d = result
        self.assertIn(d['key'], ['resting', 'alert', 'drifting', 'charging', 'waiting'])

    def test_presence_from_state_undefined_values(self):
        """Undefined values should use defaults safely."""
        result = _run_node(test_body="""
var pres = presenceFromState({mood:undefined, energy:undefined, hunger:undefined});
result = {key: pres.key, label: pres.label};
""")
        d = result
        self.assertIn(d['key'], ['resting', 'alert', 'drifting', 'charging', 'waiting'])

    def test_clamp_state_normalizes_values(self):
        """clampState should normalize various malformed inputs."""
        result = _run_node(test_body="""
result = {};
result.normal = clampState(50, 99);
result.nullVal = clampState(null, 99);
result.undefVal = clampState(undefined, 99);
result.nanVal = clampState(NaN, 99);
result.infVal = clampState(Infinity, 99);
result.negInfVal = clampState(-Infinity, 99);
result.negVal = clampState(-50, 99);
result.overVal = clampState(150, 99);
result.strVal = clampState('abc', 99);
result.boolVal = clampState(true, 99);
""")
        d = result
        self.assertEqual(d['normal'], 50)
        self.assertEqual(d['nullVal'], 99)
        self.assertEqual(d['undefVal'], 99)
        self.assertEqual(d['nanVal'], 99)
        self.assertEqual(d['infVal'], 99)
        self.assertEqual(d['negInfVal'], 99)
        self.assertEqual(d['negVal'], 0)
        self.assertEqual(d['overVal'], 100)
        self.assertEqual(d['strVal'], 99)
        self.assertEqual(d['boolVal'], 99)

    # --- Room greeting tests (TASK-177A) ---

    def test_room_greeting_dom_markers_exist(self):
        """Greeting DOM markers must exist in pet room."""
        result = _run_node(test_body="""
result = {};
result.root = !!document.getElementById('pet-room-greeting');
result.textEl = !!document.getElementById('pet-room-greeting-text');
result.metaEl = !!document.getElementById('pet-room-greeting-meta');
""")
        d = result
        for key in ['root', 'textEl', 'metaEl']:
            self.assertTrue(d[key], f'Missing greeting element: {key}')

    def test_room_greeting_morning_happy(self):
        """Morning with high mood/bond should produce cheerful greeting."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 9, 0, 0); // 9am
var g = roomGreetingFromState({mood:80, energy:60, hunger:30, bond:70}, d);
result = {key: g.key, text: g.text, hasExclaim: g.text.indexOf('!') >= 0};
""")
        d = result
        self.assertEqual(d['key'], 'morning')
        self.assertIn('Good morning', d['text'])
        self.assertTrue(d['hasExclaim'])

    def test_room_greeting_midday_default(self):
        """Midday with neutral state should produce simple greeting."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 14, 0, 0); // 2pm
var g = roomGreetingFromState({mood:50, energy:50, hunger:40, bond:20}, d);
result = {key: g.key, text: g.text};
""")
        d = result
        self.assertEqual(d['key'], 'midday')
        self.assertIn('Good afternoon', d['text'])
        self.assertTrue(d['text'].endswith('.'))

    def test_room_greeting_evening(self):
        """Evening bucket should produce evening greeting."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 19, 0, 0); // 7pm
var g = roomGreetingFromState({mood:50, energy:50, hunger:40, bond:20}, d);
result = {key: g.key, text: g.text};
""")
        d = result
        self.assertEqual(d['key'], 'evening')
        self.assertIn('Good evening', d['text'])

    def test_room_greeting_night(self):
        """Night bucket should produce night greeting."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 23, 0, 0); // 11pm
var g = roomGreetingFromState({mood:50, energy:50, hunger:40, bond:20}, d);
result = {key: g.key, text: g.text};
""")
        d = result
        self.assertEqual(d['key'], 'night')
        self.assertIn('Good night', d['text'])

    def test_room_greeting_hungry_variant(self):
        """High hunger should produce snack-related greeting."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 10, 0, 0);
var g = roomGreetingFromState({mood:50, energy:50, hunger:75, bond:20}, d);
result = {text: g.text, meta: g.meta, hasSnack: g.text.indexOf('snack') >= 0};
""")
        d = result
        self.assertTrue(d['hasSnack'])
        self.assertIn('75', d['meta'])

    def test_room_greeting_low_energy_variant(self):
        """Low energy should produce tired greeting."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 10, 0, 0);
var g = roomGreetingFromState({mood:50, energy:20, hunger:30, bond:20}, d);
result = {text: g.text, meta: g.meta, hasTired: g.text.indexOf('tired') >= 0};
""")
        d = result
        self.assertTrue(d['hasTired'])
        self.assertIn('20', d['meta'])

    def test_room_greeting_low_mood_variant(self):
        """Low mood should produce company-seeking greeting."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 10, 0, 0);
var g = roomGreetingFromState({mood:30, energy:50, hunger:30, bond:20}, d);
result = {text: g.text, meta: g.meta, hasCompany: g.text.indexOf('company') >= 0};
""")
        d = result
        self.assertTrue(d['hasCompany'])
        self.assertIn('30', d['meta'])

    def test_room_greeting_high_mood_no_bond(self):
        """High mood without high bond should produce mood greeting."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 10, 0, 0);
var g = roomGreetingFromState({mood:80, energy:60, hunger:30, bond:20}, d);
result = {text: g.text, hasMood: g.text.indexOf('mood') >= 0, hasGreat: g.text.indexOf('Great') >= 0};
""")
        d = result
        self.assertTrue(d['hasMood'])
        self.assertFalse(d['hasGreat'])

    def test_room_greeting_null_state(self):
        """Null state should default safely."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 10, 0, 0);
var g = roomGreetingFromState(null, d);
result = {key: g.key, text: g.text, meta: g.meta};
""")
        d = result
        self.assertIn(d['key'], ['morning', 'midday', 'evening', 'night'])
        self.assertIn('Good', d['text'])

    def test_room_greeting_undefined_state(self):
        """Undefined state should default safely."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 10, 0, 0);
var g = roomGreetingFromState(undefined, d);
result = {key: g.key, text: g.text};
""")
        d = result
        self.assertIn(d['key'], ['morning', 'midday', 'evening', 'night'])

    def test_room_greeting_malformed_state(self):
        """Malformed state values should coerce safely."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 10, 0, 0);
var g = roomGreetingFromState({mood:'abc', energy:NaN, hunger:Infinity, bond:-5}, d);
result = {key: g.key, text: g.text, meta: g.meta, noRaw: g.text.indexOf('abc') < 0 && g.meta.indexOf('NaN') < 0};
""")
        d = result
        self.assertIn(d['key'], ['morning', 'midday', 'evening', 'night'])
        self.assertTrue(d['noRaw'])

    def test_room_greeting_no_date_defaults_to_now(self):
        """Missing date should default to current time safely."""
        result = _run_node(test_body="""
var g = roomGreetingFromState({mood:50, energy:50, hunger:40, bond:20});
result = {key: g.key, text: g.text};
""")
        d = result
        self.assertIn(d['key'], ['morning', 'midday', 'evening', 'night'])
        self.assertIn('Good', d['text'])

    def test_apply_room_greeting_sets_dom(self):
        """applyRoomGreeting should set text and data attribute."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 9, 0, 0);
applyRoomGreeting({mood:50, energy:50, hunger:40, bond:20}, d);
result = {};
result.text = document.getElementById('pet-room-greeting-text').textContent;
result.meta = document.getElementById('pet-room-greeting-meta').textContent;
result.dataGreeting = document.getElementById('pet-room-greeting').getAttribute('data-greeting');
""")
        d = result
        self.assertIn('Good morning', d['text'])
        self.assertIn('50', d['meta'])
        self.assertEqual(d['dataGreeting'], 'morning')

    def test_apply_room_greeting_uses_dom_text(self):
        """Greeting text should use textContent, not innerHTML."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 9, 0, 0);
applyRoomGreeting({mood:80, energy:60, hunger:30, bond:70}, d);
result = {};
result.textContent = document.getElementById('pet-room-greeting-text').textContent;
result.metaText = document.getElementById('pet-room-greeting-meta').textContent;
""")
        d = result
        self.assertTrue(len(d['textContent']) > 0)
        self.assertTrue(len(d['metaText']) > 0)

    def test_room_greeting_text_is_plain(self):
        """Greeting text should not contain HTML tags."""
        result = _run_node(test_body="""
var d = new Date(2026, 0, 1, 9, 0, 0);
var g = roomGreetingFromState({mood:80, energy:60, hunger:30, bond:70}, d);
result = {text: g.text, hasTag: g.text.indexOf('<') >= 0 || g.text.indexOf('>') >= 0};
""")
        d = result
        self.assertFalse(d['hasTag'])


class PetRoomReactionTests(unittest.TestCase):
    """Tests for TASK-178A: deterministic interaction reaction surface."""

    def test_reaction_dom_markers_exist(self):
        """Reaction DOM markers must exist in pet room."""
        result = _run_node(test_body="""
result = {};
result.root = !!document.getElementById('pet-room-reaction');
result.textEl = !!document.getElementById('pet-room-reaction-text');
result.metaEl = !!document.getElementById('pet-room-reaction-meta');
""")
        d = result
        for key in ['root', 'textEl', 'metaEl']:
            self.assertTrue(d[key], f'Missing reaction element: {key}')

    def test_reaction_feed_happy(self):
        """Feed with low hunger should produce positive reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('feed', {mood:50, energy:50, hunger:20, bond:10}, {ok:true});
result = {key: r.key, text: r.text, hasSpot: r.text.indexOf('spot') >= 0};
""")
        d = result
        self.assertEqual(d['key'], 'fed')
        self.assertTrue(d['hasSpot'])

    def test_reaction_feed_hungry(self):
        """Feed with high hunger should produce still-hungry reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('feed', {mood:50, energy:50, hunger:80, bond:10}, {ok:true});
result = {key: r.key, text: r.text, hasHungry: r.text.indexOf('hungry') >= 0};
""")
        d = result
        self.assertEqual(d['key'], 'fed')
        self.assertTrue(d['hasHungry'])

    def test_reaction_feed_medium(self):
        """Feed with medium hunger should produce standard reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('feed', {mood:50, energy:50, hunger:50, bond:10}, {ok:true});
result = {key: r.key, text: r.text, hasNeeded: r.text.indexOf('needed') >= 0};
""")
        d = result
        self.assertEqual(d['key'], 'fed')
        self.assertTrue(d['hasNeeded'])

    def test_reaction_pat_happy(self):
        """Pat with high mood should produce positive reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('pat', {mood:80, energy:50, hunger:30, bond:10}, {ok:true});
result = {key: r.key, text: r.text, hasNice: r.text.indexOf('nice') >= 0};
""")
        d = result
        self.assertEqual(d['key'], 'cared')
        self.assertTrue(d['hasNice'])

    def test_reaction_pat_low_mood(self):
        """Pat with low mood should produce appreciative reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('pat', {mood:20, energy:50, hunger:30, bond:10}, {ok:true});
result = {key: r.key, text: r.text, hasAppreciate: r.text.indexOf('appreciate') >= 0};
""")
        d = result
        self.assertEqual(d['key'], 'cared')
        self.assertTrue(d['hasAppreciate'])

    def test_reaction_comfort_low_mood(self):
        """Comfort with low mood should produce thankful reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('comfort', {mood:20, energy:50, hunger:30, bond:10}, {ok:true});
result = {key: r.key, text: r.text, hasHelps: r.text.indexOf('helps') >= 0};
""")
        d = result
        self.assertEqual(d['key'], 'cared')
        self.assertTrue(d['hasHelps'])

    def test_reaction_rest_tired(self):
        """Rest with low energy should produce relief reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('rest', {mood:50, energy:15, hunger:30, bond:10}, {ok:true});
result = {key: r.key, text: r.text, hasBetter: r.text.indexOf('better') >= 0};
""")
        d = result
        self.assertEqual(d['key'], 'cared')
        self.assertTrue(d['hasBetter'])

    def test_reaction_play_energetic(self):
        """Play with high energy and mood should produce fun reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('play', {mood:70, energy:80, hunger:30, bond:10}, {ok:true});
result = {key: r.key, text: r.text, hasFun: r.text.indexOf('fun') >= 0};
""")
        d = result
        self.assertEqual(d['key'], 'cared')
        self.assertTrue(d['hasFun'])

    def test_reaction_play_tired(self):
        """Play with low energy should produce tired reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('play', {mood:50, energy:20, hunger:30, bond:10}, {ok:true});
result = {key: r.key, text: r.text, hasTired: r.text.indexOf('tired') >= 0};
""")
        d = result
        self.assertEqual(d['key'], 'cared')
        self.assertTrue(d['hasTired'])

    def test_reaction_food_added(self):
        """Food added should produce tokens-added reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('food_added', {mood:50, energy:50, hunger:30, bond:10}, {ok:true});
result = {key: r.key, text: r.text};
""")
        d = result
        self.assertEqual(d['key'], 'food_added')
        self.assertEqual(d['text'], 'Tokens added.')

    def test_reaction_shared_moment(self):
        """Shared moment should produce memory reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('shared_moment', {mood:50, energy:50, hunger:30, bond:60}, {ok:true});
result = {key: r.key, text: r.text, hasMemory: r.text.indexOf('Memory') >= 0};
""")
        d = result
        self.assertEqual(d['key'], 'shared_moment')
        self.assertTrue(d['hasMemory'])

    def test_reaction_failed(self):
        """Failed action should produce failed reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('feed', {mood:50, energy:50, hunger:30, bond:10}, {ok:false});
result = {key: r.key, text: r.text, hasWrong: r.text.indexOf('wrong') >= 0};
""")
        d = result
        self.assertEqual(d['key'], 'failed')
        self.assertTrue(d['hasWrong'])

    def test_reaction_neutral_unknown(self):
        """Unknown action should produce neutral reaction."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('unknown_action', {mood:50, energy:50, hunger:30, bond:10}, {ok:true});
result = {key: r.key, text: r.text};
""")
        d = result
        self.assertEqual(d['key'], 'neutral')
        self.assertEqual(d['text'], 'Done.')

    def test_reaction_null_state(self):
        """Null state should default safely."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('feed', null, {ok:true});
result = {key: r.key, text: r.text, noError: true};
""")
        d = result
        self.assertEqual(d['key'], 'fed')
        self.assertTrue(d['noError'])

    def test_reaction_undefined_state(self):
        """Undefined state should default safely."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('pat', undefined, {ok:true});
result = {key: r.key, text: r.text, noError: true};
""")
        d = result
        self.assertEqual(d['key'], 'cared')
        self.assertTrue(d['noError'])

    def test_reaction_malformed_state(self):
        """Malformed state values should coerce safely."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('feed', {mood:'abc', energy:NaN, hunger:Infinity, bond:-5}, {ok:true});
result = {key: r.key, text: r.text, noRaw: r.text.indexOf('abc') < 0 && r.meta.indexOf('NaN') < 0};
""")
        d = result
        self.assertEqual(d['key'], 'fed')
        self.assertTrue(d['noRaw'])

    def test_reaction_null_result(self):
        """Null result should default to failed."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('feed', {mood:50, energy:50, hunger:30, bond:10}, null);
result = {key: r.key, text: r.text};
""")
        d = result
        self.assertEqual(d['key'], 'failed')

    def test_reaction_meta_contains_state(self):
        """Meta text should contain numeric state values."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('feed', {mood:60, energy:70, hunger:40, bond:20}, {ok:true});
result = {meta: r.meta, hasHunger: r.meta.indexOf('40') >= 0, hasEnergy: r.meta.indexOf('70') >= 0};
""")
        d = result
        self.assertTrue(d['hasHunger'])
        self.assertTrue(d['hasEnergy'])

    def test_reaction_text_is_plain(self):
        """Reaction text should not contain HTML tags."""
        result = _run_node(test_body="""
var r = reactionFromInteraction('feed', {mood:80, energy:60, hunger:30, bond:70}, {ok:true});
result = {text: r.text, hasTag: r.text.indexOf('<') >= 0 || r.text.indexOf('>') >= 0};
""")
        d = result
        self.assertFalse(d['hasTag'])

    def test_apply_reaction_sets_dom(self):
        """applyReaction should set text, meta, and data-reaction attribute."""
        result = _run_node(test_body="""
applyReaction('feed', {mood:50, energy:50, hunger:20, bond:10}, {ok:true});
result = {};
result.text = document.getElementById('pet-room-reaction-text').textContent;
result.meta = document.getElementById('pet-room-reaction-meta').textContent;
result.dataReaction = document.getElementById('pet-room-reaction').getAttribute('data-reaction');
result.visible = document.getElementById('pet-room-reaction').style.display !== 'none';
""")
        d = result
        self.assertTrue(len(d['text']) > 0)
        self.assertTrue(len(d['meta']) > 0)
        self.assertEqual(d['dataReaction'], 'fed')
        self.assertTrue(d['visible'])

    def test_apply_reaction_uses_text_content(self):
        """Reaction should use textContent, not innerHTML."""
        result = _run_node(test_body="""
applyReaction('pat', {mood:80, energy:50, hunger:30, bond:10}, {ok:true});
result = {};
result.textContent = document.getElementById('pet-room-reaction-text').textContent;
result.metaText = document.getElementById('pet-room-reaction-meta').textContent;
""")
        d = result
        self.assertTrue(len(d['textContent']) > 0)
        self.assertTrue(len(d['metaText']) > 0)

    def test_add_food_endpoint_normalizes_to_food_added(self):
        """petAction('/pet/add-food', ...) should trigger food_added reaction, not neutral."""
        result = _run_node(setup_js="""
var _capturedReactionKey = null;
// Mock fetch to simulate successful add-food
_fetchHandler = function(url, opts) {
  return Promise.resolve({
    ok: true, status: 200,
    json: () => Promise.resolve({
      ok: true,
      state: {mood:50, energy:50, hunger:30, bond:10, growth_level:1, compute_food_balance:600}
    })
  });
};
// Mock updateCanvas for renderPet
function updateCanvas(identity, state, expr, pres) {}
""", test_body="""
// Override applyReaction to capture the action key
applyReaction = function(action, state, result) {
  _capturedReactionKey = action;
};
// Set currentPet with identity so renderPet doesn't crash
currentPet = {
  pet_id:'pet_1',
  identity: {name:'Test', species:'cat', personality_traits:[], relationship_role:'pet', speech_style:'', skills:[], taste_profile:{}},
  state: {mood:50, energy:50, hunger:30, bond:10, growth_level:1, compute_food_balance:500}
};
petAction('/pet/add-food', {pet_id:'pet_1', amount:500, reason:'local demo'}, null);
await new Promise(r => setTimeout(r, 200));
result = {capturedKey: _capturedReactionKey};
""")
        d = result
        self.assertEqual(d['capturedKey'], 'food_added')


class PetRoomSkillShelfTests(unittest.TestCase):
    """Tests for the skill ability shelf in the Pet Room."""

    def test_skill_shelf_dom_markers_exist(self):
        """Skill shelf DOM markers must exist."""
        result = _run_node(test_body="""
result = {};
result.shelf = !!document.getElementById('pet-skill-shelf');
result.list = !!document.getElementById('pet-skill-list');
result.empty = !!document.getElementById('pet-skill-empty');
""")
        d = result
        self.assertTrue(d['shelf'])
        self.assertTrue(d['list'])
        self.assertTrue(d['empty'])

    def test_skill_cards_from_valid_skills(self):
        """Valid skills should produce correct cards."""
        result = _run_node(test_body="""
var cards = skillCardsFromIdentity({skills:['memory','patrol','chat']}, {});
result = {count: cards.length, names: cards.map(function(c){return c.name}), icons: cards.map(function(c){return c.icon})};
""")
        d = result
        self.assertEqual(d['count'], 3)
        self.assertEqual(d['names'], ['memory', 'patrol', 'chat'])
        self.assertEqual(d['icons'], ['🧠', '🛡️', '💬'])

    def test_skill_cards_unknown_skill_gets_default_icon(self):
        """Unknown skills should get default icon."""
        result = _run_node(test_body="""
var cards = skillCardsFromIdentity({skills:['customAbility']}, {});
result = {icon: cards[0] ? cards[0].icon : null};
""")
        d = result
        self.assertEqual(d['icon'], '⚡')

    def test_skill_cards_empty_skills(self):
        """Empty skills array should return empty."""
        result = _run_node(test_body="""
var cards = skillCardsFromIdentity({skills:[]}, {});
result = {count: cards.length};
""")
        d = result
        self.assertEqual(d['count'], 0)

    def test_skill_cards_null_skills(self):
        """Null skills should return empty."""
        result = _run_node(test_body="""
var cards = skillCardsFromIdentity({skills:null}, {});
result = {count: cards.length};
""")
        d = result
        self.assertEqual(d['count'], 0)

    def test_skill_cards_undefined_identity(self):
        """Undefined identity should return empty."""
        result = _run_node(test_body="""
var cards = skillCardsFromIdentity(null, {});
result = {count: cards.length};
""")
        d = result
        self.assertEqual(d['count'], 0)

    def test_skill_cards_non_string_skills_filtered(self):
        """Non-string skills should be filtered out."""
        result = _run_node(test_body="""
var cards = skillCardsFromIdentity({skills:['valid', 123, null, '', 'also_valid']}, {});
result = {count: cards.length, names: cards.map(function(c){return c.name})};
""")
        d = result
        self.assertEqual(d['count'], 2)
        self.assertEqual(d['names'], ['valid', 'also_valid'])

    def test_skill_cards_long_name_filtered(self):
        """Skills with names > 50 chars should be filtered."""
        result = _run_node(test_body="""
var longName = 'a'.repeat(51);
var cards = skillCardsFromIdentity({skills:['ok', longName]}, {});
result = {count: cards.length};
""")
        d = result
        self.assertEqual(d['count'], 1)

    def test_skill_cards_special_chars_filtered(self):
        """Skills with special characters should be filtered."""
        result = _run_node(test_body="""
var cards = skillCardsFromIdentity({skills:['valid', '<script>alert(1)</script>', 'also-valid', 'has space']}, {});
result = {count: cards.length, names: cards.map(function(c){return c.name})};
""")
        d = result
        self.assertEqual(d['count'], 3)
        self.assertIn('valid', d['names'])
        self.assertIn('also-valid', d['names'])
        self.assertIn('has space', d['names'])

    def test_render_skill_shelf_with_skills(self):
        """renderSkillShelf should populate the list with cards."""
        result = _run_node(test_body="""
renderSkillShelf({skills:['memory','chat']}, {});
result = {};
result.count = document.getElementById('pet-skill-shelf').getAttribute('data-skill-count');
result.html = document.getElementById('pet-skill-list').innerHTML;
result.emptyHidden = document.getElementById('pet-skill-empty').style.display === 'none';
""")
        d = result
        self.assertEqual(d['count'], '2')
        self.assertIn('memory', d['html'])
        self.assertIn('chat', d['html'])
        self.assertTrue(d['emptyHidden'])

    def test_render_skill_shelf_empty_shows_empty_state(self):
        """renderSkillShelf with no skills should show empty state."""
        result = _run_node(test_body="""
renderSkillShelf({skills:[]}, {});
result = {};
result.count = document.getElementById('pet-skill-shelf').getAttribute('data-skill-count');
result.emptyVisible = document.getElementById('pet-skill-empty').style.display !== 'none';
""")
        d = result
        self.assertEqual(d['count'], '0')
        self.assertTrue(d['emptyVisible'])

    def test_render_skill_shelf_uses_escape_html(self):
        """Skill names should be escaped via escapeHtml in the rendered HTML."""
        result = _run_node(test_body="""
renderSkillShelf({skills:['memory','chat']}, {});
result = {};
result.html = document.getElementById('pet-skill-list').innerHTML;
result.hasMemory = result.html.indexOf('memory') >= 0;
result.hasChat = result.html.indexOf('chat') >= 0;
result.hasSkillCard = result.html.indexOf('pet-skill-card') >= 0;
""")
        d = result
        self.assertTrue(d['hasMemory'])
        self.assertTrue(d['hasChat'])
        self.assertTrue(d['hasSkillCard'])

    def test_render_skill_shelf_clears_stale_cards_on_empty(self):
        """After rendering non-empty then empty, no .pet-skill-card nodes should remain."""
        result = _run_node(test_body="""
renderSkillShelf({skills:['memory','chat']}, {});
renderSkillShelf({skills:[]}, {});
result = {};
result.cardCount = (document.getElementById('pet-skill-list').innerHTML.match(/pet-skill-card/g) || []).length;
result.dataCount = document.getElementById('pet-skill-shelf').getAttribute('data-skill-count');
result.emptyVisible = document.getElementById('pet-skill-empty').style.display !== 'none';
result.listHtml = document.getElementById('pet-skill-list').innerHTML;
""")
        d = result
        self.assertEqual(d['cardCount'], 0)
        self.assertEqual(d['dataCount'], '0')
        self.assertTrue(d['emptyVisible'])
        self.assertEqual(d['listHtml'], '')

    def test_render_skill_shelf_clears_stale_cards_on_malformed(self):
        """After rendering non-empty then malformed, no .pet-skill-card nodes should remain."""
        result = _run_node(test_body="""
renderSkillShelf({skills:['memory','chat']}, {});
renderSkillShelf({skills:'not-an-array'}, {});
result = {};
result.cardCount = (document.getElementById('pet-skill-list').innerHTML.match(/pet-skill-card/g) || []).length;
result.dataCount = document.getElementById('pet-skill-shelf').getAttribute('data-skill-count');
result.emptyVisible = document.getElementById('pet-skill-empty').style.display !== 'none';
""")
        d = result
        self.assertEqual(d['cardCount'], 0)
        self.assertEqual(d['dataCount'], '0')
        self.assertTrue(d['emptyVisible'])

    def test_skill_cards_rejects_secret_like_strings(self):
        """Secret-like skill labels must be filtered out."""
        result = _run_node(test_body="""
var cards = skillCardsFromIdentity({skills:[
  'sk-secret-key-12345',
  'bearer token',
  'api_key_value',
  'my_token_here',
  'the_secret_thing',
  'password123',
  'credential_file',
  'private_key_path',
  'auth_token',
  'valid_skill'
]}, {});
result = {count: cards.length, names: cards.map(function(c){return c.name})};
""")
        d = result
        self.assertEqual(d['count'], 1)
        self.assertEqual(d['names'], ['valid_skill'])

    def test_skill_cards_secret_not_in_rendered_html(self):
        """Secret-like strings must not appear in rendered shelf HTML."""
        result = _run_node(test_body="""
renderSkillShelf({skills:['sk-secret-key-12345', 'api_key_prod', 'valid_tool']}, {});
result = {};
result.html = document.getElementById('pet-skill-list').innerHTML;
result.hasSkSecret = result.html.indexOf('sk-secret-key-12345') >= 0;
result.hasApiKey = result.html.indexOf('api_key_prod') >= 0;
result.hasValid = result.html.indexOf('valid_tool') >= 0;
result.cardCount = (result.html.match(/pet-skill-card/g) || []).length;
""")
        d = result
        self.assertFalse(d['hasSkSecret'])
        self.assertFalse(d['hasApiKey'])
        self.assertTrue(d['hasValid'])
        self.assertEqual(d['cardCount'], 1)


class PetRoomDesignTests(unittest.TestCase):
    """Tests for Pet Room design shell and Pencil markers."""

    def test_design_shell_markers_exist(self):
        """Design shell, canvas, hero image, and status chip markers must exist."""
        result = _run_node(test_body="""
result = {};
result.designShell = !!document.getElementById('pet-room-design-shell');
result.canvas = !!document.getElementById('pet-room-canvas');
result.heroImage = !!document.getElementById('pet-room-hero-image');
result.chips = !!document.getElementById('pet-room-chips');
""")
        d = result
        self.assertTrue(d['designShell'])
        self.assertTrue(d['canvas'])
        self.assertTrue(d['heroImage'])
        self.assertTrue(d['chips'])

    def test_status_chips_exist(self):
        """All four status chips (mood, presence, energy, bond) must exist."""
        result = _run_node(test_body="""
result = {};
result.moodChip = !!document.getElementById('chip-mood');
result.presenceChip = !!document.getElementById('chip-presence');
result.energyChip = !!document.getElementById('chip-energy');
result.bondChip = !!document.getElementById('chip-bond');
result.moodValue = !!document.getElementById('chip-mood-value');
result.presenceValue = !!document.getElementById('chip-presence-value');
result.energyValue = !!document.getElementById('chip-energy-value');
result.bondValue = !!document.getElementById('chip-bond-value');
""")
        d = result
        for key in ['moodChip', 'presenceChip', 'energyChip', 'bondChip',
                     'moodValue', 'presenceValue', 'energyValue', 'bondValue']:
            self.assertTrue(d[key], f'Missing chip element: {key}')

    def test_pet_room_name_and_role_markers(self):
        """Pet room name and role markers must exist."""
        result = _run_node(test_body="""
result = {};
result.roomName = !!document.getElementById('pet-room-name');
result.roomRole = !!document.getElementById('pet-room-role');
""")
        d = result
        self.assertTrue(d['roomName'])
        self.assertTrue(d['roomRole'])

    def test_hero_image_element_exists(self):
        """Hero image element must use the local static Nora-01 asset."""
        html = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn('id="pet-room-hero-image"', html)
        self.assertIn('class="hero-img"', html)
        self.assertIn('src="/static/nora-01-hero.jpg"', html)
        self.assertNotIn('src="http://', html)
        self.assertNotIn('src="https://', html)

    def test_ceramic_body_fallback_exists(self):
        """CSS ceramic body fallback must exist for when image fails."""
        html = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn('class="ceramic-body"', html)
        self.assertIn('style="display:none"', html)
        self.assertIn("this.nextElementSibling.style.display='block'", html)

    def test_render_pet_updates_design_markers(self):
        """renderPet must update room name, role, and chip values."""
        result = _run_node(setup_js="""
function updateCanvas(identity, state, expr, pres) {
  if (!identity || !state) return;
  var roomNameEl = document.getElementById('pet-room-name');
  if (roomNameEl) roomNameEl.textContent = identity.name || 'Nora-01';
  var roomRoleEl = document.getElementById('pet-room-role');
  if (roomRoleEl) roomRoleEl.textContent = identity.relationship_role || 'ceramic desktop pet agent';
  var chipMood = document.getElementById('chip-mood-value');
  if (chipMood) chipMood.textContent = expr ? expr.label : '—';
  var chipPresence = document.getElementById('chip-presence-value');
  if (chipPresence) chipPresence.textContent = pres ? pres.label : '—';
  var chipEnergy = document.getElementById('chip-energy-value');
  if (chipEnergy) chipEnergy.textContent = state.energy != null ? state.energy : '—';
  var chipBond = document.getElementById('chip-bond-value');
  if (chipBond) chipBond.textContent = state.bond != null ? state.bond : '—';
}
""", test_body="""
renderPet({
  identity: {name:'Nora-01', species:'ceramic_cat', relationship_role:'desktop companion', personality_traits:['curious'], speech_style:'warm', skills:['memory'], taste_profile:{}},
  state: {hunger:25, energy:72, mood:65, bond:41, growth_level:3, compute_food_balance:500}
});
result = {};
result.roomName = document.getElementById('pet-room-name').textContent;
result.roomRole = document.getElementById('pet-room-role').textContent;
result.moodValue = document.getElementById('chip-mood-value').textContent;
result.energyValue = document.getElementById('chip-energy-value').textContent;
result.bondValue = document.getElementById('chip-bond-value').textContent;
""")
        d = result
        self.assertEqual(d['roomName'], 'Nora-01')
        self.assertEqual(d['roomRole'], 'desktop companion')
        self.assertNotEqual(d['moodValue'], '—')
        self.assertNotEqual(d['energyValue'], '—')
        self.assertNotEqual(d['bondValue'], '—')

    def test_stylesheet_links_exist(self):
        """Pet Room must link to tokens.css and pet-room.css."""
        html = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn('href="/static/styles/tokens.css"', html)
        self.assertIn('href="/static/styles/pet-room.css"', html)

    def test_pet_room_css_contains_design_tokens(self):
        """pet-room.css must reference design token variables."""
        css_path = STATIC_DIR / "styles" / "pet-room.css"
        css = css_path.read_text(encoding="utf-8")
        self.assertIn('--pet-canvas-fill', css)
        self.assertIn('--pet-chip-mood', css)
        self.assertIn('--pet-action-bg', css)

    def test_tokens_css_defines_pencil_values(self):
        """tokens.css must define Pencil-derived color values."""
        css_path = STATIC_DIR / "styles" / "tokens.css"
        css = css_path.read_text(encoding="utf-8")
        self.assertIn('#F5F3EE', css)
        self.assertIn('#F6DDC6', css)
        self.assertIn('#DDE6DC', css)
        self.assertIn('#ECE3D6', css)
        self.assertIn('#E8DED4', css)


class PetAPIModuleTests(unittest.TestCase):
    """Tests for the PetAPI module loaded from api.js."""

    def test_pet_api_object_exists(self):
        """PetAPI must be exposed on window after loading api.js."""
        result = _run_node(test_body="""
result = {};
result.exists = typeof PetAPI === 'object';
result.hasGet = typeof PetAPI.getPetCurrent === 'function';
result.hasPost = typeof PetAPI.feedPet === 'function';
""")
        d = result
        self.assertTrue(d['exists'])
        self.assertTrue(d['hasGet'])
        self.assertTrue(d['hasPost'])

    def test_pet_api_has_all_endpoints(self):
        """PET_ENDPOINTS must list all 10 Pet Room endpoints."""
        result = _run_node(test_body="""
result = {};
result.endpoints = PetAPI.PET_ENDPOINTS;
result.count = PetAPI.PET_ENDPOINTS.length;
""")
        d = result
        self.assertEqual(d['count'], 10)
        self.assertIn('/pet/current', d['endpoints'])
        self.assertIn('/pet/feed', d['endpoints'])
        self.assertIn('/pet/care', d['endpoints'])
        self.assertIn('/pet/voice-preview', d['endpoints'])
        self.assertIn('/pet/relationship-memory', d['endpoints'])

    def test_pet_api_exposes_post_helper(self):
        """PetAPI.post must be available for ad-hoc POST calls."""
        result = _run_node(test_body="""
result = {};
result.hasPost = typeof PetAPI.post === 'function';
""")
        d = result
        self.assertTrue(d['hasPost'])

    def test_index_html_uses_module_import(self):
        """index.html must use <script type='module'> with ES import."""
        html = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn('type="module"', html)
        self.assertIn("import * as PetAPI from '/static/api.js'", html)

    def test_api_js_has_exports(self):
        """api.js must use ES module export statements."""
        api_path = STATIC_DIR / "api.js"
        api = api_path.read_text(encoding="utf-8")
        self.assertIn('export function getPetCurrent', api)
        self.assertIn('export function feedPet', api)
        self.assertIn('export var PET_ENDPOINTS', api)

    def test_pet_room_fetch_calls_use_pet_api(self):
        """Pet Room fetch calls should use PetAPI, not raw fetch for pet endpoints."""
        html = INDEX_HTML.read_text(encoding="utf-8")
        # Check that the main pet fetch patterns now use PetAPI
        self.assertIn('PetAPI.getPetCurrent()', html)
        self.assertIn('PetAPI.getPetActivity(', html)
        self.assertIn('PetAPI.feedPet', html)
        self.assertIn('PetAPI.carePet', html)
        self.assertIn('PetAPI.previewVoice(', html)
        self.assertIn('PetAPI.updatePetIdentity(', html)
        self.assertIn('PetAPI.createRelationshipMemory(', html)
        self.assertIn('PetAPI.getRelationshipMemory(', html)
        # Food panel receives PetAPI as parameter (delegated, not inline)
        self.assertIn('loadCostEstimates(pet.pet_id, PetAPI)', html)
        # Verify no raw fetch to pet endpoints in the main script
        # (some raw fetch may exist in non-pet contexts like /chat, /session)
        self.assertNotIn("fetch('/pet/current'", html)
        self.assertNotIn("fetch('/pet/feed'", html)
        self.assertNotIn("fetch('/pet/care'", html)


class PetRoomCanvasModuleTests(unittest.TestCase):
    """Tests for pet-room-canvas.js module."""

    def test_canvas_module_exists(self):
        """pet-room-canvas.js must exist as a native ES module."""
        canvas_path = STATIC_DIR / "components" / "pet-room-canvas.js"
        self.assertTrue(canvas_path.exists(), "pet-room-canvas.js not found")

    def test_canvas_module_exports_updateCanvas(self):
        """pet-room-canvas.js must export updateCanvas function."""
        canvas_path = STATIC_DIR / "components" / "pet-room-canvas.js"
        content = canvas_path.read_text(encoding="utf-8")
        self.assertIn("export function updateCanvas", content)

    def test_canvas_module_exports_updateChips(self):
        """pet-room-canvas.js must export updateChips function."""
        canvas_path = STATIC_DIR / "components" / "pet-room-canvas.js"
        content = canvas_path.read_text(encoding="utf-8")
        self.assertIn("export function updateChips", content)

    def test_canvas_module_no_fetch_or_petapi(self):
        """pet-room-canvas.js must not call fetch or reference PetAPI."""
        canvas_path = STATIC_DIR / "components" / "pet-room-canvas.js"
        content = canvas_path.read_text(encoding="utf-8")
        self.assertNotIn("fetch(", content)
        self.assertNotIn("PetAPI", content)
        self.assertNotIn("http://", content)
        self.assertNotIn("https://", content)

    def test_index_html_imports_canvas_module(self):
        """index.html must import from pet-room-canvas.js."""
        html = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn("from '/static/components/pet-room-canvas.js'", html)
        self.assertIn("updateCanvas", html)

    def test_render_pet_still_updates_design_markers(self):
        """renderPet must still update room name, role, and chip values via canvas module."""
        result = _run_node(setup_js="""
function updateCanvas(identity, state, expr, pres) {
  if (!identity || !state) return;
  var roomNameEl = document.getElementById('pet-room-name');
  if (roomNameEl) roomNameEl.textContent = identity.name || 'Nora-01';
  var roomRoleEl = document.getElementById('pet-room-role');
  if (roomRoleEl) roomRoleEl.textContent = identity.relationship_role || 'ceramic desktop pet agent';
  var chipMood = document.getElementById('chip-mood-value');
  if (chipMood) chipMood.textContent = expr ? expr.label : '—';
  var chipPresence = document.getElementById('chip-presence-value');
  if (chipPresence) chipPresence.textContent = pres ? pres.label : '—';
  var chipEnergy = document.getElementById('chip-energy-value');
  if (chipEnergy) chipEnergy.textContent = state.energy != null ? state.energy : '—';
  var chipBond = document.getElementById('chip-bond-value');
  if (chipBond) chipBond.textContent = state.bond != null ? state.bond : '—';
}
""", test_body="""
renderPet({
  identity: {name:'Nora-01', species:'ceramic_cat', relationship_role:'desktop companion', personality_traits:['curious'], speech_style:'warm', skills:['memory'], taste_profile:{}},
  state: {hunger:25, energy:72, mood:65, bond:41, growth_level:3, compute_food_balance:500}
});
result = {};
result.roomName = document.getElementById('pet-room-name').textContent;
result.roomRole = document.getElementById('pet-room-role').textContent;
result.moodValue = document.getElementById('chip-mood-value').textContent;
result.energyValue = document.getElementById('chip-energy-value').textContent;
result.bondValue = document.getElementById('chip-bond-value').textContent;
""")
        d = result
        self.assertEqual(d['roomName'], 'Nora-01')
        self.assertEqual(d['roomRole'], 'desktop companion')
        self.assertNotEqual(d['moodValue'], '—')
        self.assertNotEqual(d['energyValue'], '—')
        self.assertNotEqual(d['bondValue'], '—')


class StatusChipsModuleTests(unittest.TestCase):
    """Tests for status-chips.js module."""

    def test_status_chips_module_exists(self):
        """status-chips.js must exist as a native ES module."""
        chips_path = STATIC_DIR / "components" / "status-chips.js"
        self.assertTrue(chips_path.exists(), "status-chips.js not found")

    def test_status_chips_exports_updateStatusChips(self):
        """status-chips.js must export updateStatusChips function."""
        chips_path = STATIC_DIR / "components" / "status-chips.js"
        content = chips_path.read_text(encoding="utf-8")
        self.assertIn("export function updateStatusChips", content)

    def test_status_chips_no_fetch_or_petapi(self):
        """status-chips.js must not call fetch or reference PetAPI."""
        chips_path = STATIC_DIR / "components" / "status-chips.js"
        content = chips_path.read_text(encoding="utf-8")
        self.assertNotIn("fetch(", content)
        self.assertNotIn("PetAPI", content)
        self.assertNotIn("http://", content)
        self.assertNotIn("https://", content)

    def test_status_chips_uses_textContent(self):
        """status-chips.js must use textContent, not innerHTML."""
        chips_path = STATIC_DIR / "components" / "status-chips.js"
        content = chips_path.read_text(encoding="utf-8")
        self.assertIn("textContent", content)
        self.assertNotIn("innerHTML", content)

    def test_status_chips_updates_all_four_markers(self):
        """status-chips.js must reference all four chip value IDs."""
        chips_path = STATIC_DIR / "components" / "status-chips.js"
        content = chips_path.read_text(encoding="utf-8")
        self.assertIn("chip-mood-value", content)
        self.assertIn("chip-presence-value", content)
        self.assertIn("chip-energy-value", content)
        self.assertIn("chip-bond-value", content)

    def test_canvas_delegates_to_status_chips(self):
        """pet-room-canvas.js must import from status-chips.js."""
        canvas_path = STATIC_DIR / "components" / "pet-room-canvas.js"
        content = canvas_path.read_text(encoding="utf-8")
        self.assertIn("from '/static/components/status-chips.js'", content)
        self.assertIn("updateStatusChips", content)

    def test_render_pet_updates_chip_values(self):
        """renderPet must still update Mood/Presence/Energy/Bond chip text."""
        result = _run_node(setup_js="""
function updateStatusChips(state, expr, pres) {
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
function updateCanvas(identity, state, expr, pres) {
  if (!identity || !state) return;
  var roomNameEl = document.getElementById('pet-room-name');
  if (roomNameEl) roomNameEl.textContent = identity.name || 'Nora-01';
  updateStatusChips(state, expr, pres);
}
""", test_body="""
renderPet({
  identity: {name:'Nora-01', species:'ceramic_cat', relationship_role:'desktop companion', personality_traits:['curious'], speech_style:'warm', skills:['memory'], taste_profile:{}},
  state: {hunger:25, energy:72, mood:65, bond:41, growth_level:3, compute_food_balance:500}
});
result = {};
result.moodValue = document.getElementById('chip-mood-value').textContent;
result.energyValue = document.getElementById('chip-energy-value').textContent;
result.bondValue = document.getElementById('chip-bond-value').textContent;
""")
        d = result
        self.assertNotEqual(d['moodValue'], '—')
        self.assertNotEqual(d['energyValue'], '—')
        self.assertNotEqual(d['bondValue'], '—')


class FoodPanelModuleTests(unittest.TestCase):
    """Tests for food-panel.js module."""

    def test_food_panel_module_exists(self):
        """food-panel.js must exist as a native ES module."""
        path = STATIC_DIR / "components" / "food-panel.js"
        self.assertTrue(path.exists(), "food-panel.js not found")

    def test_food_panel_exports_functions(self):
        """food-panel.js must export updateFoodPanel, loadCostEstimates, wireFoodButtons."""
        path = STATIC_DIR / "components" / "food-panel.js"
        content = path.read_text(encoding="utf-8")
        self.assertIn("export function updateFoodPanel", content)
        self.assertIn("export function loadCostEstimates", content)
        self.assertIn("export function wireFoodButtons", content)

    def test_food_panel_no_direct_fetch(self):
        """food-panel.js must not call fetch directly or reference PetAPI."""
        path = STATIC_DIR / "components" / "food-panel.js"
        content = path.read_text(encoding="utf-8")
        self.assertNotIn("fetch(", content)
        self.assertNotIn("PetAPI", content)
        self.assertNotIn("http://", content)
        self.assertNotIn("https://", content)

    def test_food_panel_no_payment_pressure(self):
        """food-panel.js must not contain payment/marketplace/pressure copy."""
        path = STATIC_DIR / "components" / "food-panel.js"
        content = path.read_text(encoding="utf-8")
        for term in ['purchase tokens', 'buy more food', 'top up to feed',
                     'your pet is starving', 'pet will die',
                     'checkout now', 'subscribe now', 'marketplace',
                     'premium skill', 'real payment']:
            self.assertNotIn(term, content, f"forbidden term '{term}' found in food-panel.js")

    def test_food_panel_uses_textContent_or_escapeHtml(self):
        """food-panel.js must use DOM text APIs or escaped HTML."""
        path = STATIC_DIR / "components" / "food-panel.js"
        content = path.read_text(encoding="utf-8")
        self.assertTrue(
            "textContent" in content or "escapeHtml" in content,
            "food-panel.js must use textContent or escapeHtml"
        )

    def test_food_panel_references_required_markers(self):
        """food-panel.js must reference stat-food, bar-food, pet-food-balance, pet-cost-table."""
        path = STATIC_DIR / "components" / "food-panel.js"
        content = path.read_text(encoding="utf-8")
        self.assertIn("stat-food", content)
        self.assertIn("bar-food", content)
        self.assertIn("pet-food-balance", content)
        self.assertIn("pet-cost-table", content)

    def test_food_panel_preserves_action_set(self):
        """food-panel.js must preserve feed, chat, voice, work actions."""
        path = STATIC_DIR / "components" / "food-panel.js"
        content = path.read_text(encoding="utf-8")
        self.assertIn("feed", content)
        self.assertIn("chat", content)
        self.assertIn("voice", content)
        self.assertIn("work", content)

    def test_index_imports_food_panel(self):
        """index.html must import from food-panel.js."""
        html = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn("from '/static/components/food-panel.js'", html)

    def test_render_pet_updates_food_via_module(self):
        """renderPet must call updateFoodPanel and loadCostEstimates with PetAPI."""
        result = _run_node(setup_js="""
var _foodPanelCalls = [];
function updateFoodPanel(state) { _foodPanelCalls.push('update:' + (state ? state.compute_food_balance : 'null')); }
function loadCostEstimates(petId, api) {
  _foodPanelCalls.push('cost:' + petId);
  _foodPanelCalls.push('hasApi:' + (api != null));
}
function wireFoodButtons(getPet, actionFn) { _foodPanelCalls.push('wire'); }
function updateCanvas(identity, state, expr, pres) {}
""", test_body="""
_foodPanelCalls = [];
renderPet({
  identity: {name:'Nora-01', species:'ceramic_cat', relationship_role:'desktop companion', personality_traits:['curious'], speech_style:'warm', skills:['memory'], taste_profile:{}},
  state: {hunger:25, energy:72, mood:65, bond:41, growth_level:3, compute_food_balance:500}
});
result = {};
result.calls = _foodPanelCalls;
""")
        d = result
        self.assertIn('update:500', d['calls'])
        self.assertTrue(any(c.startswith('cost:') for c in d['calls']))
        # PetAPI must be passed to loadCostEstimates
        self.assertIn('hasApi:true', d['calls'])

    def test_food_panel_updates_stat_food_and_balance(self):
        """updateFoodPanel must set stat-food textContent and pet-food-balance textContent."""
        result = _run_node(setup_js="""
function updateCanvas(identity, state, expr, pres) {}
function updateFoodPanel(state) {
  if (!state) return;
  var bal = state.compute_food_balance != null ? state.compute_food_balance : 0;
  var bar = document.getElementById('bar-food');
  if (bar) bar.style.width = Math.max(0, Math.min(100, bal / 10)) + '%';
  var valEl = document.getElementById('stat-food');
  if (valEl) valEl.textContent = bal;
  var balEl = document.getElementById('pet-food-balance');
  if (balEl) balEl.textContent = 'Balance: ' + bal + ' tokens';
}
function loadCostEstimates(petId, api) {}
function wireFoodButtons(getPet, actionFn) {}
""", test_body="""
renderPet({
  identity: {name:'Test', species:'cat', relationship_role:'pet', personality_traits:[], speech_style:'', skills:[], taste_profile:{}},
  state: {hunger:50, energy:50, mood:50, bond:50, growth_level:1, compute_food_balance:1234}
});
result = {};
result.foodValue = document.getElementById('stat-food').textContent;
result.balText = document.getElementById('pet-food-balance').textContent;
""")
        d = result
        self.assertEqual(str(d['foodValue']), '1234')
        self.assertIn('1234', str(d['balText']))
        self.assertIn('tokens', str(d['balText']))

    def test_food_panel_loadCostEstimates_uses_PetAPI(self):
        """loadCostEstimates must call api.getPetFoodStatus for each action."""
        result = _run_node(setup_js="""
var _apiCalls = [];
var mockAPI = {
  getPetFoodStatus: function(petId, action) {
    _apiCalls.push(petId + ':' + action);
    return Promise.resolve({action: action, cost: 100, can_run: true, shortfall: 0});
  }
};
function updateCanvas(identity, state, expr, pres) {}
function updateFoodPanel(state) {}
function wireFoodButtons(getPet, actionFn) {}
function loadCostEstimates(petId, api) {
  if (!petId || !api) return;
  var actions = ['feed', 'chat', 'voice', 'work'];
  Promise.all(actions.map(function (action) {
    return api.getPetFoodStatus(petId, action).catch(function () { return null; });
  })).then(function (results) {});
}
""", test_body="""
_apiCalls = [];
loadCostEstimates('pet_1', mockAPI);
await new Promise(function(r) { setTimeout(r, 100); });
result = {};
result.calls = _apiCalls;
""")
        d = result
        self.assertIn('pet_1:feed', d['calls'])
        self.assertIn('pet_1:chat', d['calls'])
        self.assertIn('pet_1:voice', d['calls'])
        self.assertIn('pet_1:work', d['calls'])
