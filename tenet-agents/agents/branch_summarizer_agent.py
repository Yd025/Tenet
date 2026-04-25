from uagents import Agent, Context
from protocols.summary_protocol import (
    SummaryRequest, SummaryResponse, summary_protocol, SummaryTarget
)
from config.agent_config import AgentConfig
from utils.local_runtime import dag_store

class TenetBranchSummarizer:
    """Summarizes branches and conversations"""
    
    def __init__(self):
        self.config = AgentConfig()
        self.agent = Agent(
            name="tenet-branch-summarizer",
            seed="tenet_branch_summarizer_seed_2024_secure",
            port=8006,
            mailbox=True,
            publish_agent_details=True,
        )
        self.setup_handlers()

    def setup_handlers(self):
        """Setup summarization handlers"""
        @summary_protocol.on_message(model=SummaryRequest)
        async def handle_summary_request(ctx: Context, sender: str, msg: SummaryRequest):
            """Handle summarization requests"""
            try:
                if msg.target_type == SummaryTarget.BRANCH:
                    response = await self.summarize_branch(msg)
                elif msg.target_type == SummaryTarget.CONVERSATION:
                    response = await self.summarize_conversation(msg)
                elif msg.target_type == SummaryTarget.NODE:
                    response = await self.summarize_node(msg)
                else:
                    response = {
                        "success": False,
                        "summary": "",
                        "key_points": [],
                        "statistics": {},
                        "message": f"Unknown target type: {msg.target_type}"
                    }
                await ctx.send(sender, SummaryResponse(**response))
            except Exception as e:
                error_response = {
                    "success": False,
                    "summary": "",
                    "key_points": [],
                    "statistics": {},
                    "message": f"Summarization failed: {str(e)}"
                }
                await ctx.send(sender, SummaryResponse(**error_response))

    async def summarize_branch(self, msg: SummaryRequest) -> dict:
        """Summarize a branch"""
        try:
            branch_data = dag_store.get_branch(msg.target_id) or {}
            content = self.extract_branch_content(branch_data)
            summary_data = self.generate_summary(content, msg.summary_length)
            stats = self.calculate_statistics(content, summary_data["summary"])
            
            return {
                "success": True,
                "summary": summary_data["summary"],
                "key_points": summary_data["key_points"],
                "statistics": stats,
                "message": f"Branch '{branch_data.get('branch_name', 'Unknown')}' summarized successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "summary": "",
                "key_points": [],
                "statistics": {},
                "message": f"Failed to summarize branch: {str(e)}"
            }

    async def summarize_conversation(self, msg: SummaryRequest) -> dict:
        """Summarize an entire conversation"""
        try:
            conversation_data = dag_store.get_graph(msg.target_id, include_pruned=False)
            branches = []
            for branch in conversation_data.get("branches", []):
                payload = dag_store.get_branch(branch["branch_id"]) or branch
                branches.append(payload)
            conversation_data["branches"] = branches
            content = self.extract_conversation_content(conversation_data)
            summary_data = self.generate_summary(content, msg.summary_length)
            stats = self.calculate_statistics(content, summary_data["summary"])
            
            return {
                "success": True,
                "summary": summary_data["summary"],
                "key_points": summary_data["key_points"],
                "statistics": stats,
                "message": f"Conversation summarized successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "summary": "",
                "key_points": [],
                "statistics": {},
                "message": f"Failed to summarize conversation: {str(e)}"
            }

    async def summarize_node(self, msg: SummaryRequest) -> dict:
        """Summarize a single node"""
        try:
            node_data = dag_store.get_node(msg.target_id) or {}
            content = f"Prompt: {node_data.get('prompt', '')}\nResponse: {node_data.get('response', '')}"
            summary_data = self.generate_summary(content, "short")
            
            return {
                "success": True,
                "summary": summary_data["summary"],
                "key_points": summary_data["key_points"],
                "statistics": {
                    "total_nodes": 1,
                    "total_tokens": len(content.split()),
                    "summary_tokens": len(summary_data["summary"].split()),
                    "compression_ratio": len(content.split()) / len(summary_data["summary"].split())
                },
                "message": "Node summarized successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "summary": "",
                "key_points": [],
                "statistics": {},
                "message": f"Failed to summarize node: {str(e)}"
            }

    def extract_branch_content(self, branch_data: dict) -> str:
        """Extract content from branch data"""
        content_parts = []
        for node in branch_data.get("nodes", []):
            content_parts.append(f"User: {node.get('prompt', '')}")
            content_parts.append(f"AI: {node.get('response', '')}")
        return "\n".join(content_parts)

    def extract_conversation_content(self, conversation_data: dict) -> str:
        """Extract content from entire conversation"""
        content_parts = []
        for branch in conversation_data.get("branches", []):
            content_parts.append(f"=== Branch: {branch.get('branch_name', 'Unknown')} ===")
            content_parts.append(self.extract_branch_content(branch))
        return "\n".join(content_parts)

    def generate_summary(self, content: str, length: str) -> dict:
        """Generate AI summary of content"""
        sentences = [line.strip() for line in content.split("\n") if line.strip()]
        if length == "short":
            picked = sentences[:3]
        elif length == "long":
            picked = sentences[:12]
        else:
            picked = sentences[:6]
        summary_text = "\n".join(picked) if picked else "No content available for summary."
        return {"summary": summary_text, "key_points": self.extract_key_points(summary_text)}

    def extract_key_points(self, summary: str) -> list:
        """Extract key points from summary"""
        key_points = []
        lines = summary.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('-', '•', '*')) or (line and line[0].isdigit() and line[1] in '. '):
                key_points.append(line.lstrip('-•*0123456789. '))
        return key_points[:5]

    def calculate_statistics(self, original_content: str, summary: str) -> dict:
        """Calculate summary statistics"""
        original_tokens = len(original_content.split())
        summary_tokens = len(summary.split())
        return {
            "total_nodes": original_content.count("User:"),
            "total_tokens": original_tokens,
            "summary_tokens": summary_tokens,
            "compression_ratio": original_tokens / summary_tokens if summary_tokens > 0 else 0
        }

    def run(self):
        """Start the branch summarizer agent"""
        self.agent.include(summary_protocol)
        print("📝 Tenet Branch Summarizer Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print(f"🔗 Summary Protocol: Enabled")
        print("✨ Summary types: branch, conversation, node")
        self.agent.run()

if __name__ == "__main__":
    summarizer = TenetBranchSummarizer()
    summarizer.run()