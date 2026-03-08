"""Test script for agentic tools"""
import requests
import json

BASE_URL = "http://localhost:8002"

def test_chat(message, expected_tool=None):
    print(f"\n{'='*60}")
    print(f"Testing: {message}")
    print(f"Expected tool: {expected_tool}")
    print(f"{'='*60}")
    
    response = requests.post(
        f"{BASE_URL}/v1/chat",
        json={
            "messages": [
                {"role": "user", "content": message}
            ]
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Status: {response.status_code}")
        print(f"[OK] Tools used: {data.get('tools_used', [])}")
        print(f"[OK] Crisis detected: {data.get('crisis_detected', False)}")
        print(f"\nResponse preview:")
        print(data.get('content', '')[:200] + "...")
        
        if expected_tool and expected_tool in data.get('tools_used', []):
            print(f"\n[SUCCESS] {expected_tool} was used!")
        elif expected_tool:
            print(f"\n[FAILED] Expected {expected_tool}, got {data.get('tools_used', [])}")
    else:
        print(f"[ERROR] {response.status_code}: {response.text}")

if __name__ == "__main__":
    # Test health endpoint
    print("Testing health endpoint...")
    health = requests.get(f"{BASE_URL}/health")
    print(json.dumps(health.json(), indent=2))
    
    # Test crisis detection
    test_chat("I need crisis help", expected_tool="crisis_detection")
    test_chat("nataka mkubwa", expected_tool="crisis_detection")
    
    # Test counselor search
    test_chat("Find a counselor", expected_tool="find_counselor")
    test_chat("Tafuta mshauri", expected_tool="find_counselor")
    
    # Test resource search
    test_chat("Show me videos", expected_tool="get_resources")
    test_chat("Video za afya ya akili", expected_tool="get_resources")
    
    print("\n" + "="*60)
    print("Tests complete!")
    print("="*60)
