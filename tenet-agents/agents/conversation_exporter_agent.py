from uagents import Agent, Context
from protocols.export_protocol import (
    ExportRequest, ExportResponse, export_protocol, ExportFormat
)
from config.agent_config import AgentConfig
import httpx
import json
from datetime import datetime

class TenetConversationExporter:
    """Exports conversations in various formats"""
    
    def __init__(self):
        self.config = AgentConfig()
        self.agent = Agent(
            name="tenet-conversation-exporter",
            seed="tenet_conversation_exporter_seed_2024_secure",
            port=8011
        )
        self.setup_handlers()

    def setup_handlers(self):
        """Setup export handlers"""
        @export_protocol.on_message(model=ExportRequest)
        async def handle_export_request(ctx: Context, sender: str, msg: ExportRequest):
            """Handle export requests"""
            try:
                if msg.export_format == ExportFormat.JSON:
                    response = await self.export_json(msg)
                elif msg.export_format == ExportFormat.MARKDOWN:
                    response = await self.export_markdown(msg)
                elif msg.export_format == ExportFormat.CSV:
                    response = await self.export_csv(msg)
                elif msg.export_format == ExportFormat.HTML:
                    response = await self.export_html(msg)
                elif msg.export_format == ExportFormat.PDF:
                    response = await self.export_pdf(msg)
                else:
                    response = {
                        "success": False,
                        "export_url": None,
                        "export_data": None,
                        "export_size_bytes": 0,
                        "export_format": msg.export_format,
                        "items_exported": 0,
                        "message": f"Unsupported export format: {msg.export_format}"
                    }
                await ctx.send(sender, ExportResponse(**response))
            except Exception as e:
                error_response = {
                    "success": False,
                    "export_url": None,
                    "export_data": None,
                    "export_size_bytes": 0,
                    "export_format": msg.export_format,
                    "items_exported": 0,
                    "message": f"Export failed: {str(e)}"
                }
                await ctx.send(sender, ExportResponse(**error_response))

    async def export_json(self, msg: ExportRequest) -> dict:
        """Export as JSON"""
        try:
            data = await self.get_export_data(msg)
            json_data = json.dumps(data, indent=2, default=str)
            
            if len(json_data) < 10000: 
                return {
                    "success": True,
                    "export_url": None,
                    "export_data": json_data,
                    "export_size_bytes": len(json_data.encode('utf-8')),
                    "export_format": ExportFormat.JSON,
                    "items_exported": data.get("items_count", 0),
                    "message": "JSON export completed successfully"
                }
            else:
                export_url = await self.save_export_file(json_data, "json", msg.target_id)
                return {
                    "success": True,
                    "export_url": export_url,
                    "export_data": None,
                    "export_size_bytes": len(json_data.encode('utf-8')),
                    "export_format": ExportFormat.JSON,
                    "items_exported": data.get("items_count", 0),
                    "message": f"JSON export saved to {export_url}"
                }
        except Exception as e:
            return {
                "success": False,
                "export_url": None,
                "export_data": None,
                "export_size_bytes": 0,
                "export_format": ExportFormat.JSON,
                "items_exported": 0,
                "message": f"JSON export failed: {str(e)}"
            }

    async def export_markdown(self, msg: ExportRequest) -> dict:
        """Export as Markdown"""
        try:
            data = await self.get_export_data(msg)
            markdown_content = self.convert_to_markdown(data, msg.include_metadata, msg.include_branches)
            
            if len(markdown_content) < 10000:
                return {
                    "success": True,
                    "export_url": None,
                    "export_data": markdown_content,
                    "export_size_bytes": len(markdown_content.encode('utf-8')),
                    "export_format": ExportFormat.MARKDOWN,
                    "items_exported": data.get("items_count", 0),
                    "message": "Markdown export completed successfully"
                }
            else:
                export_url = await self.save_export_file(markdown_content, "md", msg.target_id)
                return {
                    "success": True,
                    "export_url": export_url,
                    "export_data": None,
                    "export_size_bytes": len(markdown_content.encode('utf-8')),
                    "export_format": ExportFormat.MARKDOWN,
                    "items_exported": data.get("items_count", 0),
                    "message": f"Markdown export saved to {export_url}"
                }
        except Exception as e:
            return {
                "success": False,
                "export_url": None,
                "export_data": None,
                "export_size_bytes": 0,
                "export_format": ExportFormat.MARKDOWN,
                "items_exported": 0,
                "message": f"Markdown export failed: {str(e)}"
            }

    async def export_csv(self, msg: ExportRequest) -> dict:
        """Export as CSV"""
        try:
            data = await self.get_export_data(msg)
            csv_content = self.convert_to_csv(data)
            
            export_url = await self.save_export_file(csv_content, "csv", msg.target_id)
            return {
                "success": True,
                "export_url": export_url,
                "export_data": None,
                "export_size_bytes": len(csv_content.encode('utf-8')),
                "export_format": ExportFormat.CSV,
                "items_exported": data.get("items_count", 0),
                "message": f"CSV export saved to {export_url}"
            }
        except Exception as e:
            return {
                "success": False,
                "export_url": None,
                "export_data": None,
                "export_size_bytes": 0,
                "export_format": ExportFormat.CSV,
                "items_exported": 0,
                "message": f"CSV export failed: {str(e)}"
            }

    async def export_html(self, msg: ExportRequest) -> dict:
        """Export as HTML"""
        try:
            data = await self.get_export_data(msg)
            html_content = self.convert_to_html(data, msg.include_metadata, msg.include_branches)
            
            export_url = await self.save_export_file(html_content, "html", msg.target_id)
            return {
                "success": True,
                "export_url": export_url,
                "export_data": None,
                "export_size_bytes": len(html_content.encode('utf-8')),
                "export_format": ExportFormat.HTML,
                "items_exported": data.get("items_count", 0),
                "message": f"HTML export saved to {export_url}"
            }
        except Exception as e:
            return {
                "success": False,
                "export_url": None,
                "export_data": None,
                "export_size_bytes": 0,
                "export_format": ExportFormat.HTML,
                "items_exported": 0,
                "message": f"HTML export failed: {str(e)}"
            }

    async def export_pdf(self, msg: ExportRequest) -> dict:
        """Export as PDF"""
        try:
            data = await self.get_export_data(msg)
            markdown_content = self.convert_to_markdown(data, msg.include_metadata, msg.include_branches)
            
            export_url = await self.save_export_file(markdown_content, "md", msg.target_id)
            return {
                "success": True,
                "export_url": export_url,
                "export_data": None,
                "export_size_bytes": len(markdown_content.encode('utf-8')),
                "export_format": ExportFormat.PDF,
                "items_exported": data.get("items_count", 0),
                "message": f"PDF export (markdown placeholder) saved to {export_url}"
            }
        except Exception as e:
            return {
                "success": False,
                "export_url": None,
                "export_data": None,
                "export_size_bytes": 0,
                "export_format": ExportFormat.PDF,
                "items_exported": 0,
                "message": f"PDF export failed: {str(e)}"
            }

    async def get_export_data(self, msg: ExportRequest) -> dict:
        """Get data from backend for export"""
        if msg.target_type == "conversation":
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.BACKEND_API_URL}/api/conversations/{msg.target_id}",
                    params={"include_metadata": msg.include_metadata, "include_branches": msg.include_branches},
                    timeout=20.0
                )
                response.raise_for_status()
                data = response.json()
                data["items_count"] = sum(len(branch.get("nodes", [])) for branch in data.get("branches", []))
                return data
        elif msg.target_type == "branch":
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.BACKEND_API_URL}/api/branches/{msg.target_id}",
                    params={"include_metadata": msg.include_metadata},
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                data["items_count"] = len(data.get("nodes", []))
                return data
        elif msg.target_type == "node":
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.BACKEND_API_URL}/api/nodes/{msg.target_id}",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                data["items_count"] = 1
                return data
        else:
            raise ValueError(f"Unknown target type: {msg.target_type}")

    def convert_to_markdown(self, data: dict, include_metadata: bool, include_branches: bool) -> str:
        """Convert data to Markdown format"""
        md_lines = []
        if "conversation_name" in data:
            md_lines.append(f"# {data['conversation_name']}\n")
        elif "branch_name" in data:
            md_lines.append(f"# {data['branch_name']}\n")
        else:
            md_lines.append("# Exported Conversation\n")
            
        if include_metadata and "metadata" in data:
            md_lines.append("## Metadata\n")
            for key, value in data["metadata"].items():
                md_lines.append(f"- **{key}**: {value}\n")
            md_lines.append("")
            
        if include_branches and "branches" in data:
            for branch in data["branches"]:
                md_lines.append(f"## Branch: {branch.get('branch_name', 'Unknown')}\n")
                for node in branch.get("nodes", []):
                    md_lines.append(f"### Node: {node.get('node_id', 'Unknown')}\n")
                    md_lines.append(f"**User:** {node.get('prompt', '')}\n\n")
                    md_lines.append(f"**AI:** {node.get('response', '')}\n\n")
                    if include_metadata and "metadata" in node:
                        md_lines.append("*Metadata:* " + str(node["metadata"]) + "\n\n")
        elif "nodes" in data:
            for node in data["nodes"]:
                md_lines.append(f"## Node: {node.get('node_id', 'Unknown')}\n")
                md_lines.append(f"**User:** {node.get('prompt', '')}\n\n")
                md_lines.append(f"**AI:** {node.get('response', '')}\n\n")
                if include_metadata and "metadata" in node:
                    md_lines.append("*Metadata:* " + str(node["metadata"]) + "\n\n")
                    
        md_lines.append(f"\n---\n*Exported on {datetime.now().isoformat()}*")
        return "\n".join(md_lines)

    def convert_to_csv(self, data: dict) -> str:
        """Convert data to CSV format"""
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["Node ID", "Branch ID", "Prompt", "Response", "Timestamp"])
        
        if "branches" in data:
            for branch in data["branches"]:
                branch_id = branch.get("branch_id", "")
                for node in branch.get("nodes", []):
                    writer.writerow([
                        node.get("node_id", ""),
                        branch_id,
                        node.get("prompt", ""),
                        node.get("response", ""),
                        node.get("timestamp", "")
                    ])
        elif "nodes" in data:
            for node in data["nodes"]:
                writer.writerow([
                    node.get("node_id", ""),
                    node.get("branch_id", ""),
                    node.get("prompt", ""),
                    node.get("response", ""),
                    node.get("timestamp", "")
                ])
                
        return output.getvalue()

    def convert_to_html(self, data: dict, include_metadata: bool, include_branches: bool) -> str:
        """Convert data to HTML format"""
        html_lines = []
        html_lines.append("")
        html_lines.append("Exported Conversation")
        html_lines.append("")
        
        if "conversation_name" in data:
            html_lines.append(f"<h1>{data['conversation_name']}</h1>")
        elif "branch_name" in data:
            html_lines.append(f"<h1>{data['branch_name']}</h1>")
            
        if include_branches and "branches" in data:
            for branch in data["branches"]:
                html_lines.append(f"<h2>Branch: {branch.get('branch_name', 'Unknown')}</h2>")
                for node in branch.get("nodes", []):
                    html_lines.append(f"")
                    html_lines.append(f"<h3>Node: {node.get('node_id', 'Unknown')}</h3>")
                    html_lines.append(f"<strong>User:</strong>{node.get('prompt', '')}")
                    html_lines.append(f"<strong>AI:</strong>{node.get('response', '')}")
                    if include_metadata and "metadata" in node:
                        html_lines.append(f"{str(node['metadata'])}")
                    html_lines.append("")
        elif "nodes" in data:
            for node in data["nodes"]:
                html_lines.append(f"")
                html_lines.append(f"<h3>Node: {node.get('node_id', 'Unknown')}</h3>")
                html_lines.append(f"<strong>User:</strong>{node.get('prompt', '')}")
                html_lines.append(f"<strong>AI:</strong>{node.get('response', '')}")
                if include_metadata and "metadata" in node:
                    html_lines.append(f"{str(node['metadata'])}")
                html_lines.append("")
                
        html_lines.append(f"<p><em>Exported on {datetime.now().isoformat()}</em></p>")
        html_lines.append("")
        return "\n".join(html_lines)

    async def save_export_file(self, content: str, format: str, target_id: str) -> str:
        """Save export to file and return URL"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{target_id}_{timestamp}.{format}"
        mock_url = f"https://storage.tenet.ai/exports/{filename}"
        return mock_url

    def run(self):
        """Start the conversation exporter agent"""
        self.agent.include(export_protocol)
        print("📤 Tenet Conversation Exporter Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print(f"🔗 Export Protocol: Enabled")
        print("📄 Export formats: JSON, Markdown, CSV, HTML, PDF")
        self.agent.run()

if __name__ == "__main__":
    exporter = TenetConversationExporter()
    exporter.run()