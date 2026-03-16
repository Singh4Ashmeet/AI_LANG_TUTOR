import asyncio
import httpx
import sys

async def smoke_test():
    base_url = "http://localhost:8000"
    print(f"Starting smoke test against {base_url}...")
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Root check
            resp = await client.get(f"{base_url}/")
            print(f"Root: {resp.status_code} - {resp.json()}")
            
            # 2. Try to login with non-existent user
            resp = await client.post(f"{base_url}/auth/login", json={
                "email": "test@example.com",
                "password": "password123"
            })
            print(f"Login (fail expected): {resp.status_code} - {resp.json()}")
            
            # 3. Check stats (should be 401)
            resp = await client.get(f"{base_url}/users/me/stats")
            print(f"Me Stats (401 expected): {resp.status_code}")
            
            print("\nSmoke test passed basic connectivity checks!")
            
        except Exception as e:
            print(f"\nSmoke test FAILED: {str(e)}")
            print("Is the backend running? Run 'python app.py' in a separate terminal.")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(smoke_test())
