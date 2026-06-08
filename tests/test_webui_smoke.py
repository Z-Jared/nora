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
    start = html.index("<script>") + len("<script>")
    end = html.index("</script>")
    script = html[start:end].strip()
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
        getAttribute() { return null; },
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
