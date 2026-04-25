import json
import os
import subprocess
from pathlib import Path

from agent_metadata import AGENT_METADATA
from uagents_core.utils.registration import (
    RegistrationRequestCredentials,
    register_chat_agent,
)


def main():
    if os.getenv("AGENTVERSE_KEY") and os.getenv("AGENT_SEED_PHRASE"):
        endpoint = os.environ.get("TENET_AGENT_ENDPOINT", "http://127.0.0.1:9000/submit")
        register_chat_agent(
            "Tenet-agent",
            endpoint,
            active=True,
            credentials=RegistrationRequestCredentials(
                agentverse_api_key=os.environ["AGENTVERSE_KEY"],
                agent_seed_phrase=os.environ["AGENT_SEED_PHRASE"],
            ),
        )
        print(
            "✅ Registered chat agent using AGENTVERSE_KEY + AGENT_SEED_PHRASE "
            f"(endpoint={endpoint})"
        )
        return

    api_key = os.getenv("AGENTVERSE_API_KEY")
    metadata_path = Path(__file__).parent / "agent_metadata.json"
    metadata_path.write_text(json.dumps(AGENT_METADATA, indent=2), encoding="utf-8")

    print("Generated agent metadata at:", metadata_path)
    if not api_key:
        print("AGENTVERSE_API_KEY is not set.")
        print("Set it and run the following command:")
        print(
            "agentverse register --name tenet-gateway --description "
            "\"Gateway for Tenet local agents\" --protocols gateway "
            f"--metadata {metadata_path}"
        )
        return

    print("Detected AGENTVERSE_API_KEY. Attempting CLI registration...")
    try:
        subprocess.run(
            [
                "agentverse",
                "register",
                "--name",
                AGENT_METADATA["name"],
                "--description",
                AGENT_METADATA["description"],
                "--protocols",
                "gateway",
                "--metadata",
                str(metadata_path),
            ],
            check=True,
        )
    except FileNotFoundError:
        print("agentverse CLI not found. Install with `pip install agentverse-cli`.")
    except subprocess.CalledProcessError as exc:
        print("Registration command failed:", exc)


if __name__ == "__main__":
    main()
