📋 5. Quick Start Guide
Installation:

# Install dependencies
pip install uagents fetchai httpx pydantic

# Create project structure
mkdir -p tenet-agents/{config,protocols,agents,utils}

# Copy all files to their respective locations
# (Copy the code above into the corresponding files)
Configuration:

# Set environment variables
export AGENTVERSE_API_KEY="your_agentverse_api_key"
export HARDWARE_API_URL="http://localhost:9000"  # Person 2's API
export BACKEND_API_URL="http://localhost:5000"   # Person 4's API
export OPENAI_API_KEY="your_openai_api_key"
Run All Agents:

# Make the script executable
chmod +x run_all_agents.py

# Run all agents at once
python run_all_agents.py
Run Individual Agents:

# Run specific agent
python agents/orchestrator_agent.py
python agents/privacy_router_agent.py
python agents/branch_manager_agent.py
python agents/model_coordinator_agent.py
python agents/context_keeper_agent.py