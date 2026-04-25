import asyncio

from uagents import Agent, Context

from gateway_agent import GatewayRequest, GatewayResponse, gateway_protocol


client_agent = Agent(name="tenet-test-client", seed="tenet_test_client_seed_2024_secure", port=9030)


@gateway_protocol.on_message(model=GatewayResponse)
async def handle_response(ctx: Context, sender: str, msg: GatewayResponse):
    print("Received response from", sender)
    print(msg.model_dump())
    raise SystemExit(0)


async def send_request():
    # Replace with your Agentverse gateway address once registered.
    gateway_address = "replace_with_agentverse_gateway_address"
    request = GatewayRequest(
        request_type="chat",
        payload={
            "prompt": "Test from agentverse transport",
            "conversation_id": "agentverse_test_conv",
            "privacy_level": "private",
        },
        user_id="agentverse_test_user",
    )
    await client_agent.send(gateway_address, request)
    print("Request sent.")


if __name__ == "__main__":
    @client_agent.on_event("startup")
    async def _startup(ctx: Context):
        await send_request()

    client_agent.include(gateway_protocol)
    client_agent.run()
