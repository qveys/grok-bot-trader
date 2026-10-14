import asyncio, sys
_orig = asyncio.wait_for
async def _wf(aw, timeout=None):
    return await _orig(aw, timeout=1200)
asyncio.wait_for = _wf
import oauth_cli_kit.flow as flow
flow._should_open_browser = lambda: True
flow.webbrowser.open = lambda *a, **k: True
from src.providers.openai_codex import login_openai_codex
tok = login_openai_codex(print_fn=lambda s: print(s, flush=True), prompt_fn=lambda p: "")
print("LOGIN_OK", flush=True)
