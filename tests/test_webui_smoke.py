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
