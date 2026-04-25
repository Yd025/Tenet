from uagents import Agent, Context
from protocols.search_protocol import (
    SearchRequest, SearchResponse, SearchResult, search_protocol, SearchType
)
from config.agent_config import AgentConfig
from utils.local_runtime import dag_store

class TenetSemanticSearch:
    """Performs semantic search across conversations"""
    
    def __init__(self):
        self.config = AgentConfig()
        self.agent = Agent(
            name="tenet-semantic-search",
            seed="tenet_semantic_search_seed_2024_secure",
            port=8010
        )
        self.setup_handlers()

    def setup_handlers(self):
        """Setup search handlers"""
        @search_protocol.on_message(model=SearchRequest)
        async def handle_search_request(ctx: Context, sender: str, msg: SearchRequest):
            """Handle search requests"""
            try:
                if msg.search_type == SearchType.SEMANTIC:
                    response = await self.semantic_search(msg)
                elif msg.search_type == SearchType.KEYWORD:
                    response = await self.keyword_search(msg)
                elif msg.search_type == SearchType.HYBRID:
                    response = await self.hybrid_search(msg)
                elif msg.search_type == SearchType.REGEX:
                    response = await self.regex_search(msg)
                else:
                    response = {
                        "success": False,
                        "results": [],
                        "total_results": 0,
                        "search_time_ms": 0,
                        "query_understood": False,
                        "suggestions": [],
                        "message": f"Unknown search type: {msg.search_type}"
                    }
                await ctx.send(sender, SearchResponse(**response))
            except Exception as e:
                error_response = {
                    "success": False,
                    "results": [],
                    "total_results": 0,
                    "search_time_ms": 0,
                    "query_understood": False,
                    "suggestions": [],
                    "message": f"Search failed: {str(e)}"
                }
                await ctx.send(sender, SearchResponse(**error_response))

    async def semantic_search(self, msg: SearchRequest) -> dict:
        """Perform semantic search using embeddings"""
        import time
        start_time = time.time()
        try:
            search_results = self.local_search(msg.query, msg.conversation_id, msg.branch_id, msg.limit)
            results = [
                SearchResult(
                    result_id=r["result_id"],
                    conversation_id=r["conversation_id"],
                    branch_id=r.get("branch_id"),
                    node_id=r["node_id"],
                    content=r["content"],
                    relevance_score=r["relevance_score"],
                    metadata=r.get("metadata")
                )
                for r in search_results
            ]
            
            search_time = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "results": results,
                "total_results": len(results),
                "search_time_ms": search_time,
                "query_understood": True,
                "suggestions": await self.generate_suggestions(msg.query),
                "message": f"Semantic search completed: {len(results)} results found"
            }
        except Exception:
            return await self.keyword_search(msg)

    async def keyword_search(self, msg: SearchRequest) -> dict:
        """Perform keyword search"""
        import time
        start_time = time.time()
        try:
            search_results = self.local_search(msg.query, msg.conversation_id, msg.branch_id, msg.limit)
            results = [
                SearchResult(
                    result_id=r["result_id"],
                    conversation_id=r["conversation_id"],
                    branch_id=r.get("branch_id"),
                    node_id=r["node_id"],
                    content=r["content"],
                    relevance_score=r.get("relevance_score", 0.8),
                    metadata=r.get("metadata")
                )
                for r in search_results
            ]
            
            search_time = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "results": results,
                "total_results": len(results),
                "search_time_ms": search_time,
                "query_understood": True,
                "suggestions": [],
                "message": f"Keyword search completed: {len(results)} results found"
            }
        except Exception as e:
            return {
                "success": False,
                "results": [],
                "total_results": 0,
                "search_time_ms": 0,
                "query_understood": False,
                "suggestions": [],
                "message": f"Keyword search failed: {str(e)}"
            }

    async def hybrid_search(self, msg: SearchRequest) -> dict:
        """Perform hybrid search (semantic + keyword)"""
        import time
        start_time = time.time()
        try:
            semantic_results = await self.semantic_search_internal(msg)
            keyword_results = await self.keyword_search_internal(msg)
            
            combined_results = self.combine_search_results(
                semantic_results, keyword_results, msg.limit
            )
            
            search_time = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "results": combined_results,
                "total_results": len(combined_results),
                "search_time_ms": search_time,
                "query_understood": True,
                "suggestions": await self.generate_suggestions(msg.query),
                "message": f"Hybrid search completed: {len(combined_results)} results found"
            }
        except Exception as e:
            return {
                "success": False,
                "results": [],
                "total_results": 0,
                "search_time_ms": 0,
                "query_understood": False,
                "suggestions": [],
                "message": f"Hybrid search failed: {str(e)}"
            }

    async def regex_search(self, msg: SearchRequest) -> dict:
        """Perform regex search"""
        import time
        import re
        start_time = time.time()
        try:
            pattern = re.compile(msg.query, re.IGNORECASE)
            
            search_results = self.local_search(msg.query, msg.conversation_id, msg.branch_id, msg.limit, regex=True)
            results = [
                SearchResult(
                    result_id=r["result_id"],
                    conversation_id=r["conversation_id"],
                    branch_id=r.get("branch_id"),
                    node_id=r["node_id"],
                    content=r["content"],
                    relevance_score=r.get("relevance_score", 0.7),
                    metadata=r.get("metadata")
                )
                for r in search_results
            ]
            
            search_time = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "results": results,
                "total_results": len(results),
                "search_time_ms": search_time,
                "query_understood": True,
                "suggestions": [],
                "message": f"Regex search completed: {len(results)} results found"
            }
        except Exception as e:
            return {
                "success": False,
                "results": [],
                "total_results": 0,
                "search_time_ms": 0,
                "query_understood": False,
                "suggestions": [],
                "message": f"Regex search failed: {str(e)}"
            }

    async def semantic_search_internal(self, msg: SearchRequest) -> list:
        """Internal semantic search without formatting"""
        return self.local_search(msg.query, msg.conversation_id, msg.branch_id, (msg.limit or 10) * 2)

    async def keyword_search_internal(self, msg: SearchRequest) -> list:
        """Internal keyword search without formatting"""
        return self.local_search(msg.query, msg.conversation_id, msg.branch_id, (msg.limit or 10) * 2)

    def local_search(self, query: str, conversation_id: str, branch_id: str, limit: int, regex: bool = False) -> list:
        import re
        graph = dag_store.get_graph(conversation_id, include_pruned=False)
        nodes = graph.get("nodes", [])
        results = []
        for node in nodes:
            if branch_id and node.get("branch_id") != branch_id:
                continue
            content = f"{node.get('prompt', '')}\n{node.get('response', '')}"
            matched = re.search(query, content, flags=re.IGNORECASE) if regex else query.lower() in content.lower()
            if matched:
                results.append(
                    {
                        "result_id": node["node_id"],
                        "conversation_id": node["conversation_id"],
                        "branch_id": node.get("branch_id"),
                        "node_id": node["node_id"],
                        "content": content[:400],
                        "relevance_score": min(1.0, 0.5 + len(query) / max(len(content), 1)),
                        "metadata": node.get("metadata", {}),
                    }
                )
            if len(results) >= limit:
                break
        return results

    def combine_search_results(self, semantic_results: list, keyword_results: list, limit: int) -> list:
        """Combine and rank results from multiple search types"""
        combined_map = {}
        
        for result in semantic_results:
            node_id = result["node_id"]
            combined_map[node_id] = {
                **result,
                "combined_score": result.get("relevance_score", 0.5) * 0.7 
            }
            
        for result in keyword_results:
            node_id = result["node_id"]
            keyword_score = result.get("relevance_score", 0.5) * 0.3 
            if node_id in combined_map:
                combined_map[node_id]["combined_score"] += keyword_score
            else:
                combined_map[node_id] = {
                    **result,
                    "combined_score": keyword_score
                }
                
        sorted_results = sorted(
            combined_map.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )[:limit]
        
        return [
            SearchResult(
                result_id=r["result_id"],
                conversation_id=r["conversation_id"],
                branch_id=r.get("branch_id"),
                node_id=r["node_id"],
                content=r["content"],
                relevance_score=r["combined_score"],
                metadata=r.get("metadata")
            )
            for r in sorted_results
        ]

    async def generate_suggestions(self, query: str) -> list:
        """Generate search suggestions"""
        suggestions = []
        query_lower = query.lower()
        if "branch" in query_lower:
            suggestions.append("Try searching for specific branch names")
        if "summary" in query_lower:
            suggestions.append("Use the summarizer agent for branch summaries")
        if "merge" in query_lower:
            suggestions.append("Use the branch merger agent to combine branches")
        return suggestions[:3]

    def run(self):
        """Start the semantic search agent"""
        self.agent.include(search_protocol)
        print("🔍 Tenet Semantic Search Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print(f"🔗 Search Protocol: Enabled")
        print("🎯 Search types: semantic, keyword, hybrid, regex")
        print("🧠 Embeddings: OpenAI text-embedding-ada-002")
        self.agent.run()

if __name__ == "__main__":
    semantic_search = TenetSemanticSearch()
    semantic_search.run()