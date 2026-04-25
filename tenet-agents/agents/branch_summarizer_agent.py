from uagents import Agent, Context
from protocols.summary_protocol import (
    SummaryRequest, SummaryResponse, SummaryStatistics, summary_protocol
)
from config.agent_config import AgentConfig
import httpx
import json

class TenetBranchSummarizer:
    """Summarizes branches and conversations"""
    
    def __init__(self):
        self.config = AgentConfig()
        self.agent = Agent(
            name="tenet-branch-summarizer",
            seed="tenet_branch_summarizer_seed_2024_secure",
            port=8006
        )
        self.setup_handlers()

    def setup_handlers(self):
        """Setup summarization handlers"""
        @summary_protocol.on_message(model=SummaryRequest)
        async def handle_summary_request(ctx: Context, sender: str, msg: SummaryRequest):
            """Handle summarization requests"""
            try:
                if msg.target_type == "branch":
                    response = await self.summarize_branch(msg)
                elif msg.target_type == "conversation":
                    response = await self.summarize_conversation(msg)
                elif msg.target_type == "node":
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
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.BACKEND_API_URL}/api/branches/{msg.target_id}",
                    timeout=15.0
                )
                response.raise_for_status()
                branch_data = response.json()
                
            content = self.extract_branch_content(branch_data)
            summary_data = await self.generate_summary(content, msg.summary_length)
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
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.BACKEND_API_URL}/api/conversations/{msg.target_id}",
                    timeout=20.0
                )
                response.raise_for_status()
                conversation_data = response.json()
                
            content = self.extract_conversation_content(conversation_data)
            summary_data = await self.generate_summary(content, msg.summary_length)
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
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.BACKEND_API_URL}/api/nodes/{msg.target_id}",
                    timeout=10.0
                )
                response.raise_for_status()
                node_data = response.json()
                
            content = f"Prompt: {node_data.get('prompt', '')}\nResponse: {node_data.get('response', '')}"
            summary_data = await self.generate_summary(content, "short")
            
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

    async def generate_summary(self, content: str, length: str) -> dict:
        """Generate AI summary of content"""
        try:
            length_instructions = {
                "short": "Provide a concise 2-3 sentence summary",
                "medium": "Provide a comprehensive summary with key points",
                "long": "Provide a detailed summary with all important information"
            }
            instruction = length_instructions.get(length, length_instructions["medium"])
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {
                                "role": "system",
                                "content": f"You are a expert at summarizing AI conversations. {instruction}. Extract key points and provide a clear summary."
                            },
                            {
                                "role": "user",
                                "content": f"Please summarize this conversation:\n\n{content[:4000]}"
                            }
                        ],
                        "max_tokens": 500 if length == "short" else 1000
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
            summary_text = result["choices"][0]["message"]["content"]
            key_points = self.extract_key_points(summary_text)
            
            return {
                "summary": summary_text,
                "key_points": key_points
            }
        except Exception as e:
            return {
                "summary": content[:500] + "..." if len(content) > 500 else content,
                "key_points": []
            }

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