"""
Conversation Exporter Agent — exports conversations from MongoDB (via the
webapp REST API) to JSON, Markdown, CSV, or HTML.
"""
import csv
import io
import json
import os
from datetime import datetime

import httpx
from uagents import Agent, Context
from protocols.export_protocol import (
    ExportRequest, ExportResponse, export_protocol, ExportFormat, ExportTarget,
)
from config.agent_config import AgentConfig
from utils.webapp_dag_store import WebappDagStore

WEBAPP_API = os.getenv("WEBAPP_API_URL", "http://127.0.0.1:8000/api")
_TIMEOUT = 15.0


class TenetConversationExporter:
    """Exports conversations using live data from the webapp REST API."""

    def __init__(self):
        self.config = AgentConfig()
        self.agent = Agent(
            name="tenet-conversation-exporter",
            seed="tenet_conversation_exporter_seed_2024_secure",
            port=8011,
            mailbox=True,
            publish_agent_details=True,
        )
        self.dag_store = WebappDagStore()
        self.setup_handlers()

    def setup_handlers(self):
        @export_protocol.on_message(model=ExportRequest)
        async def handle_export_request(ctx: Context, sender: str, msg: ExportRequest):
            try:
                if msg.export_format == ExportFormat.JSON:
                    response = await self.export_json(msg)
                elif msg.export_format == ExportFormat.MARKDOWN:
                    response = await self.export_markdown(msg)
                elif msg.export_format == ExportFormat.CSV:
                    response = await self.export_csv(msg)
                elif msg.export_format == ExportFormat.HTML:
                    response = await self.export_html(msg)
                else:
                    response = {
                        "success": False, "export_url": None, "export_data": None,
                        "export_size_bytes": 0, "export_format": msg.export_format,
                        "items_exported": 0,
                        "message": f"Unsupported export format: {msg.export_format}",
                    }
                await ctx.send(sender, ExportResponse(**response))
            except Exception as e:
                await ctx.send(sender, ExportResponse(
                    success=False, export_url=None, export_data=None,
                    export_size_bytes=0, export_format=msg.export_format,
                    items_exported=0, message=f"Export failed: {e}",
                ))

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_nodes(self, msg: ExportRequest) -> list[dict]:
        if msg.target_type == ExportTarget.CONVERSATION:
            return self.dag_store.list_nodes(msg.target_id) or []
        elif msg.target_type == ExportTarget.NODE:
            node = self.dag_store.get_node(msg.target_id)
            return [node] if node else []
        return []

    def _fetch_conversation_meta(self, root_id: str) -> dict:
        try:
            r = httpx.get(f"{WEBAPP_API}/conversations/{root_id}", timeout=_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return {}

    # ------------------------------------------------------------------
    # Format converters
    # ------------------------------------------------------------------

    def _to_json(self, nodes: list[dict], meta: dict) -> str:
        payload = {
            "conversation": meta,
            "nodes": nodes,
            "exported_at": datetime.now().isoformat(),
        }
        return json.dumps(payload, indent=2, default=str)

    def _to_markdown(self, nodes: list[dict], meta: dict, include_metadata: bool) -> str:
        title = meta.get("title") or "Exported Conversation"
        lines = [f"# {title}\n"]
        nodes_sorted = sorted(nodes, key=lambda n: n.get("timestamp", ""))
        for node in nodes_sorted:
            prompt = node.get("prompt", "")
            response = node.get("response", "")
            if prompt and prompt not in ("⎇ Merge Synthesis",):
                lines.append(f"**User:** {prompt}\n")
            if response:
                lines.append(f"**AI:** {response}\n")
            if include_metadata and node.get("metadata"):
                lines.append(f"*metadata: {node['metadata']}*\n")
            lines.append("---\n")
        lines.append(f"\n*Exported {datetime.now().isoformat()}*")
        return "\n".join(lines)

    def _to_csv(self, nodes: list[dict]) -> str:
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["node_id", "parent_ids", "prompt", "response", "model_used", "timestamp"])
        for n in sorted(nodes, key=lambda x: x.get("timestamp", "")):
            writer.writerow([
                n.get("node_id", ""),
                ",".join(n.get("parent_ids", [])),
                n.get("prompt", ""),
                n.get("response", ""),
                n.get("model_used", ""),
                n.get("timestamp", ""),
            ])
        return out.getvalue()

    def _to_html(self, nodes: list[dict], meta: dict) -> str:
        title = meta.get("title") or "Exported Conversation"
        rows = []
        for n in sorted(nodes, key=lambda x: x.get("timestamp", "")):
            prompt = n.get("prompt", "").replace("<", "&lt;").replace(">", "&gt;")
            response = n.get("response", "").replace("<", "&lt;").replace(">", "&gt;")
            rows.append(
                f"<div class='node'>"
                f"<p class='prompt'><strong>User:</strong> {prompt}</p>"
                f"<p class='response'><strong>AI:</strong> {response}</p>"
                f"</div>"
            )
        body = "\n".join(rows)
        return (
            f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>{title}</title>"
            f"<style>body{{font-family:sans-serif;max-width:800px;margin:auto;padding:2rem}}"
            f".node{{border-bottom:1px solid #eee;padding:1rem 0}}"
            f".prompt{{color:#333}}.response{{color:#555}}</style></head>"
            f"<body><h1>{title}</h1>{body}"
            f"<p><em>Exported {datetime.now().isoformat()}</em></p></body></html>"
        )

    # ------------------------------------------------------------------
    # Export handlers
    # ------------------------------------------------------------------

    async def export_json(self, msg: ExportRequest) -> dict:
        nodes = self._fetch_nodes(msg)
        meta = self._fetch_conversation_meta(msg.target_id) if msg.target_type == ExportTarget.CONVERSATION else {}
        data = self._to_json(nodes, meta)
        return {
            "success": True, "export_url": None, "export_data": data,
            "export_size_bytes": len(data.encode()), "export_format": ExportFormat.JSON,
            "items_exported": len(nodes), "message": f"Exported {len(nodes)} nodes as JSON",
        }

    async def export_markdown(self, msg: ExportRequest) -> dict:
        nodes = self._fetch_nodes(msg)
        meta = self._fetch_conversation_meta(msg.target_id) if msg.target_type == ExportTarget.CONVERSATION else {}
        data = self._to_markdown(nodes, meta, getattr(msg, "include_metadata", False))
        return {
            "success": True, "export_url": None, "export_data": data,
            "export_size_bytes": len(data.encode()), "export_format": ExportFormat.MARKDOWN,
            "items_exported": len(nodes), "message": f"Exported {len(nodes)} nodes as Markdown",
        }

    async def export_csv(self, msg: ExportRequest) -> dict:
        nodes = self._fetch_nodes(msg)
        data = self._to_csv(nodes)
        return {
            "success": True, "export_url": None, "export_data": data,
            "export_size_bytes": len(data.encode()), "export_format": ExportFormat.CSV,
            "items_exported": len(nodes), "message": f"Exported {len(nodes)} nodes as CSV",
        }

    async def export_html(self, msg: ExportRequest) -> dict:
        nodes = self._fetch_nodes(msg)
        meta = self._fetch_conversation_meta(msg.target_id) if msg.target_type == ExportTarget.CONVERSATION else {}
        data = self._to_html(nodes, meta)
        return {
            "success": True, "export_url": None, "export_data": data,
            "export_size_bytes": len(data.encode()), "export_format": ExportFormat.HTML,
            "items_exported": len(nodes), "message": f"Exported {len(nodes)} nodes as HTML",
        }

    def run(self):
        self.agent.include(export_protocol)
        print("📤 Tenet Conversation Exporter Agent starting (webapp-backed)...")
        print(f"📍 Agent Address: {self.agent.address}")
        print("🔗 Export Protocol: Enabled")
        self.agent.run()


if __name__ == "__main__":
    TenetConversationExporter().run()
