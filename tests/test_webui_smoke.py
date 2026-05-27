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
        classList: {
          _classes: new Set(),
          add(cls) { this._classes.add(cls); },
          remove(cls) { this._classes.delete(cls); },
          contains(cls) { return this._classes.has(cls); },
        },
        querySelector() { return null; },
        querySelectorAll() { return []; },
        addEventListener(evt, fn) {
          if (!_listeners[id]) _listeners[id] = {};
          if (!_listeners[id][evt]) _listeners[id][evt] = [];
          _listeners[id][evt].push(fn);
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
    return {
      className: '',
      innerHTML: '',
      textContent: '',
      style: {},
      classList: { _classes: new Set(), add() {}, remove() {}, contains() { return false; } },
      appendChild() {},
      querySelector() { return null; },
      querySelectorAll() { return []; },
      addEventListener() {},
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


if __name__ == "__main__":
    unittest.main()
