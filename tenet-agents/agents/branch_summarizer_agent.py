"""
Branch Summarizer Agent — summarizes conversations and nodes using
live data from the webapp REST API (MongoDB-backed).

For node-level summaries it delegates to the webapp's /nodes/summaries
endpoint which already calls Ollama, so we avoid duplicating that logic.
"""
import os

import httpx
from uagents import Agent, Context
from protocols.summary_protocol import (
    SummaryRequest, SummaryResponse, summary_protocol, SummaryTarget,
)
from config.agent_config import AgentConfig
from utils.webapp_dag_store import WebappDagStore

WEBAPP_API = os.getenv("WEBAPP_API_URL", "http://127.0.0.1:8000/api")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
_TIMEOUT = 60.0


class TenetBranchSummarizer:
    """Summarizes conversations and nodes using live webapp data."""

    def __init__(self):
        self.config = AgentConfig()
        self.agent = Agent(
            name="tenet-branch-summarizer",
            seed="tenet_branch_summarizer_seed_2024_secure",
            port=8006,
            mailbox=True,
            publish_agent_details=True,
        )
        self.dag_store = WebappDagStore()
        self.setup_handlers()

    def setup_handlers(self):
        @summary_protocol.on_message(model=SummaryRequest)
        async def handle_summary_request(ctx: Context, sender: str, msg: SummaryRequest):
            try:
                if msg.target_type == SummaryTarget.CONVERSATION:
                    response = await self.summarize_conversation(msg)
                elif msg.target_type == SummaryTarget.NODE:
                    response = await self.summarize_node(msg)
                else:
                    response = {
                        "success": False,
                        "summary": "",
                        "key_points": [],
                        "statistics": {},
                        "message": f"Unsupported target type: {msg.target_type}",
                    }
                await ctx.send(sender, SummaryResponse(**response))
            except Exception as e:
                await ctx.send(sender, SummaryResponse(
                    success=False, summary="", key_points=[], statistics={},
                    message=f"Summarization failed: {e}",
                ))

    async def summarize_conversation(self, msg: SummaryRequest) -> dict:
        """
        Fetch all nodes for a conversation and ask Ollama to summarize the
        full thread.  Falls back to a text-extraction summary if Ollama fails.
        """
        nodes = self.dag_store.list_nodes(msg.target_id)
        if not nodes:
            return {
                "success": False, "summary": "", "key_points": [], "statistics": {},
                "message": "No nodes found for conversation",
            }

        # Build a readable transcript (trunk order by timestamp)
        nodes_sorted = sorted(nodes, key=lambda n: n.get("timestamp", ""))
        lines = []
        for n in nodes_sorted:
            if n.get("prompt") and n["prompt"] not in ("⎇ Merge Synthesis",):
                lines.append(f"User: {n['prompt']}")
            if n.get("response"):
                lines.append(f"AI: {n['response']}")
        transcript = "\n".join(lines)

        summary_prompt = (
            "Summarize this AI conversation concisely.\n"
            "Return strict JSON only with keys: summary (2-4 sentences), key_points (list of up to 5 strings).\n\n"
            f"{transcript[:6000]}"
        )

        summary_text = ""
        key_points: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={"model": self.config.DEFAULT_LOCAL_MODEL, "prompt": summary_prompt, "stream": False},
                )
                resp.raise_for_status()
                import json
                raw = resp.json().get("response", "")
                # strip markdown fences if present
                raw = raw.strip()
                if raw.startswith("```"):
                    parts = raw.split("```")
                    for p in parts:
                        p = p.strip()
                        if p.startswith("json"):
                            raw = p[4:].strip()
                            break
                        if p.startswith("{"):
                            raw = p
                            break
                parsed = json.loads(raw)
                summary_text = str(parsed.get("summary", "")).strip()
                key_points = [str(k) for k in parsed.get("key_points", []) if k]
        except Exception:
            # Fallback: first few lines of transcript
            summary_text = "\n".join(lines[:6]) if lines else "No content."

        stats = {
            "total_nodes": len(nodes),
            "total_tokens": len(transcript.split()),
            "summary_tokens": len(summary_text.split()),
        }
        return {
            "success": True,
            "summary": summary_text,
            "key_points": key_points[:5],
            "statistics": stats,
            "message": f"Conversation summarized ({len(nodes)} nodes)",
        }

    async def summarize_node(self, msg: SummaryRequest) -> dict:
        """
        Delegate to the webapp's /nodes/summaries endpoint so we reuse the
        same Ollama call and the result gets persisted to MongoDB.
        """
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    f"{WEBAPP_API}/nodes/summaries",
                    json={
                        "root_id": msg.target_id,  # target_id is node_id here
                        "node_ids": [msg.target_id],
                        "model": self.config.DEFAULT_LOCAL_MODEL,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                summaries = data.get("summaries", [])
                if summaries:
                    s = summaries[0]
                    return {
                        "success": True,
                        "summary": f"{s.get('title', '')} — {s.get('subtitle', '')}",
                        "key_points": [s.get("title", ""), s.get("subtitle", "")],
                        "statistics": {"total_nodes": 1},
                        "message": "Node summarized via webapp",
                    }
        except Exception as e:
            pass

        return {
            "success": False, "summary": "", "key_points": [], "statistics": {},
            "message": "Node summary failed",
        }

    def run(self):
        self.agent.include(summary_protocol)
        print("📝 Tenet Branch Summarizer Agent starting (webapp-backed)...")
        print(f"📍 Agent Address: {self.agent.address}")
        print("🔗 Summary Protocol: Enabled")
        self.agent.run()


if __name__ == "__main__":
    TenetBranchSummarizer().run()
