"""Simple test script for agentic tools"""
import requests

BASE_URL = "http://localhost:8002"

tests = [
    ("I need crisis help", "crisis_detection"),
    ("Find a counselor", "find_counselor"),
    ("Show me videos", "get_resources"),
]

print("Testing agentic tools...\n")

for message, expected_tool in tests:
    print(f"Test: {message}")
    
    response = requests.post(
        f"{BASE_URL}/v1/chat",
        json={"messages": [{"role": "user", "content": message}]}
    )
    
    if response.status_code == 200:
        data = response.json()
        tools_used = data.get('tools_used', [])
        
        if expected_tool in tools_used:
            print(f"  PASS - Tool used: {tools_used}")
        else:
            print(f"  FAIL - Expected: {expected_tool}, Got: {tools_used}")
    else:
        print(f"  ERROR - Status: {response.status_code}")
    
    print()

print("Done!")
