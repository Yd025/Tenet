import asyncio

import httpx


async def test_gateway():
    print("🧪 Testing Gateway Connection")
    print("=" * 48)

    async with httpx.AsyncClient() as client:
        try:
            health = await client.get("http://localhost:9000/health", timeout=5.0)
            health.raise_for_status()
            print("✅ Gateway health:", health.json())
        except Exception as exc:
            print("❌ Gateway health check failed:", exc)
            return

        try:
            local = await client.get("http://localhost:9000/local-agents", timeout=5.0)
            local.raise_for_status()
            print("✅ Local agent status endpoint available")
        except Exception as exc:
            print("⚠️ Could not read /local-agents:", exc)

        request = {
            "request_type": "chat",
            "payload": {
                "prompt": "Hello from gateway connection test",
                "conversation_id": "gateway_connection_test",
                "privacy_level": "private",
            },
            "user_id": "test_user",
            "source": "test_gateway_connection",
        }
        try:
            response = await client.post("http://localhost:9000/process", json=request, timeout=20.0)
            response.raise_for_status()
            print("✅ Process response:", response.json())
        except Exception as exc:
            print("❌ Process request failed:", exc)


if __name__ == "__main__":
    asyncio.run(test_gateway())
