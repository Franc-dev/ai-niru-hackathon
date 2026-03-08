"""Check if server has the updated code"""
import requests

response = requests.post(
    "http://localhost:8002/v1/chat",
    json={"messages": [{"role": "user", "content": "Find a counselor"}]}
)

data = response.json()
tools = data.get('tools_used', [])

print(f"Tools used: {tools}")
print(f"Confidence: {data.get('confidence')}")

if 'find_counselor' in tools:
    print("\n[SUCCESS] Server is using NEW code - counselor tool triggered!")
elif 'rag_search' in tools:
    print("\n[FAIL] Server is using OLD code - RAG triggered instead of counselor tool")
    print("Please RESTART the server: training_env/Scripts/python.exe training/scripts/4_serve_sklearn_rag.py")
