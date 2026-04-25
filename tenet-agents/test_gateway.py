import asyncio

import httpx


async def test_gateway():
    request = {
        "request_type": "chat",
        "payload": {
            "prompt": "Hello from gateway smoke test",
            "conversation_id": "gateway_test_conv",
            "branch_id": None,
            "privacy_level": "private",
        },
        "user_id": "test_user",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:9000/process", json=request, timeout=20.0)
        response.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    asyncio.run(test_gateway())
