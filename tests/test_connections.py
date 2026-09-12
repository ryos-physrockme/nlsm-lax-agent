"""Real SDK/stdio/HTTP plumbing with explicitly simulated model responses."""

import asyncio
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from nlsm_lax_agent import pcm_model
from nlsm_lax_agent.agent import BackendConfig, Limits, LiteLLMSource, run_agent
from nlsm_lax_agent.demo import DemoSource
from nlsm_lax_agent.storage import RunStore


def test_missing_gemini_key_stops_with_portable_record(tmp_path, monkeypatch):
    monkeypatch.delenv("NLSM_TEST_ABSENT_KEY", raising=False)
    cfg = BackendConfig(kind="gemini", model="gemini/test-model", api_key_env="NLSM_TEST_ABSENT_KEY")
    store = RunStore(tmp_path/"no-key.sqlite")
    run = store.create(pcm_model(), "Check missing-key handling without a network request.", Limits().model_dump(), cfg.model_dump())
    result = run_agent(store, run["run_id"], LiteLLMSource(cfg))
    assert result["status"] == "missing_api_key"
    assert result["history"] == []
    assert store.export(run["run_id"])["payload"]["state"]["status"] == "missing_api_key"


def test_mcp_stdio_tools_execute_independently_of_bundled_agent():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def exercise():
        params = StdioServerParameters(command=sys.executable, args=["-m", "nlsm_lax_agent.mcp_server"], env=dict(os.environ))
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                names = {t.name for t in (await session.list_tools()).tools}
                assert {"pcm_equations", "pcm_verify", "pcm_verify_scalar", "pcm_solve_scalar"} <= names
                model_result = await session.call_tool("pcm_equations", {"arguments": {}})
                assert model_result.structuredContent["result"]["model"] == pcm_model()
                result = await session.call_tool("pcm_verify_scalar", {"arguments": {"plus": "1/(1-z)", "minus": "1/(1+z)"}})
                assert not result.isError
                assert result.structuredContent["status"] == "completed"
                assert result.structuredContent["result"]["status"] == "verified"
    asyncio.run(exercise())


def test_litellm_http_and_langgraph_feedback_with_simulated_responses(tmp_path):
    requests = []
    fixture = DemoSource()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(request)
            answer = fixture.complete(request["messages"], timeout=10, max_tokens=512)
            content = json.dumps({"id": "simulated-http-response", "object": "chat.completion", "created": 0,
                                  "model": "simulated-local-model", "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": answer["content"]}}],
                                  "usage": {"prompt_tokens": 20, "completion_tokens": 30, "total_tokens": 50}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        cfg = BackendConfig(kind="local", model="openai/simulated-local-model", api_base=f"http://127.0.0.1:{server.server_port}/v1")
        store = RunStore(tmp_path/"http.sqlite")
        run = store.create(pcm_model(), "Test HTTP feedback, not model capability.", Limits().model_dump(), cfg.model_dump())
        result = run_agent(store, run["run_id"], LiteLLMSource(cfg))
        assert result["status"] == "verified"
        assert len(requests) == 2 and result["completion_tokens"] == 60
        assert "eom_recovery" in requests[1]["messages"][-1]["content"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
