import os

from uagents_core.utils.registration import (
    RegistrationRequestCredentials,
    register_chat_agent,
)


def main():
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
    print(f"Chat agent registration request sent for endpoint: {endpoint}")


if __name__ == "__main__":
    main()
