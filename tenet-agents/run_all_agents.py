#!/usr/bin/env python3
"""
Run all Tenet agents simultaneously
"""
import subprocess
import sys
import time
import signal
from pathlib import Path

# Agent configurations
AGENTS = [
    {
        "name": "Orchestrator",
        "script": "agents/orchestrator_agent.py",
        "port": 8001,
        "color": "🚀"
    },
    {
        "name": "Privacy Router",
        "script": "agents/privacy_router_agent.py",
        "port": 8002,
        "color": "🔒"
    },
    {
        "name": "Branch Manager",
        "script": "agents/branch_manager_agent.py",
        "port": 8003,
        "color": "🌳"
    },
    {
        "name": "Model Coordinator",
        "script": "agents/model_coordinator_agent.py",
        "port": 8004,
        "color": "🤖"
    },
    {
        "name": "Context Keeper",
        "script": "agents/context_keeper_agent.py",
        "port": 8005,
        "color": "🧠"
    },
    {
        "name": "Branch Summarizer",
        "script": "agents/branch_summarizer_agent.py",
        "port": 8006,
        "color": "📝"
    },
    {
        "name": "Branch Merger",
        "script": "agents/branch_merger_agent.py",
        "port": 8007,
        "color": "🔀"
    },
    {
        "name": "Branch Pruner",
        "script": "agents/branch_pruner_agent.py",
        "port": 8008,
        "color": "✂️"
    },
    {
        "name": "Node Pruner",
        "script": "agents/node_pruner_agent.py",
        "port": 8009,
        "color": "🔪"
    },
    {
        "name": "Semantic Search",
        "script": "agents/semantic_search_agent.py",
        "port": 8010,
        "color": "🔍"
    },
    {
        "name": "Conversation Exporter",
        "script": "agents/conversation_exporter_agent.py",
        "port": 8011,
        "color": "📤"
    },
    {
        "name": "Tag Manager",
        "script": "agents/tag_manager_agent.py",
        "port": 8012,
        "color": "🏷️"
    },
    {
        "name": "Rollback Agent",
        "script": "agents/rollback_agent.py",
        "port": 8013,
        "color": "⏪"
    },
    {
        "name": "Diff Viewer",
        "script": "agents/diff_viewer_agent.py",
        "port": 8014,
        "color": "🧾"
    },
    {
        "name": "Branch Comparator",
        "script": "agents/branch_comparator_agent.py",
        "port": 8015,
        "color": "🧮"
    }
]

class AgentManager:
    """Manages running all Tenet agents"""
    
    def __init__(self):
        self.processes = {}
        self.running = True
    
    def start_agent(self, agent_config):
        """Start a single agent"""
        script_path = Path(agent_config["script"])
        if not script_path.exists():
            print(f"❌ Script not found: {script_path}")
            return None
        
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return process
    
    def start_all_agents(self):
        """Start all agents"""
        print("🎯 Starting Tenet Agent System...")
        print("=" * 50)
        
        for agent in AGENTS:
            print(f"{agent['color']} Starting {agent['name']} on port {agent['port']}...")
            process = self.start_agent(agent)
            if process:
                self.processes[agent['name']] = process
                time.sleep(1)  # Stagger starts
        
        print("=" * 50)
        print("✅ All agents started successfully!")
        print(f"📊 Running {len(self.processes)} agents")
        print("\nPress Ctrl+C to stop all agents\n")
        
        # Monitor agents
        self.monitor_agents()
    
    def monitor_agents(self):
        """Monitor running agents"""
        try:
            while self.running:
                time.sleep(5)
                
                # Check if any process has died
                for name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        print(f"⚠️  Agent {name} has stopped")
                        del self.processes[name]
                
                if not self.processes:
                    print("❌ All agents have stopped")
                    break
                    
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping all agents...")
            self.stop_all_agents()
    
    def stop_all_agents(self):
        """Stop all running agents"""
        self.running = False
        
        for name, process in self.processes.items():
            print(f"🛑 Stopping {name}...")
            process.terminate()
        
        # Wait for processes to stop
        time.sleep(2)
        
        # Force kill if needed
        for name, process in self.processes.items():
            if process.poll() is None:
                print(f"⚡ Force killing {name}...")
                process.kill()
        
        print("✅ All agents stopped")
    
    def get_status(self):
        """Get status of all agents"""
        status = {}
        for name, process in self.processes.items():
            status[name] = {
                "running": process.poll() is None,
                "pid": process.pid
            }
        return status

def main():
    """Main entry point"""
    manager = AgentManager()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        manager.stop_all_agents()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start all agents
    manager.start_all_agents()

if __name__ == "__main__":
    main()
