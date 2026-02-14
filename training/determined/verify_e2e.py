"""
End-to-end verification: serve the exported LoRA adapter, send a test
query, and validate the response.

Usage:
    python training/determined/verify_e2e.py --adapter-path training/artifacts/det-best-lora
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="E2E verification of trained model")
    parser.add_argument(
        "--adapter-path",
        default="training/artifacts/det-best-lora",
        help="Path to exported LoRA adapter directory",
    )
    parser.add_argument("--port", type=int, default=8001, help="Serving port")
    parser.add_argument(
        "--timeout", type=int, default=120, help="Max seconds to wait for server"
    )
    return parser.parse_args()


def wait_for_server(url: str, timeout: int) -> bool:
    """Poll health endpoint until server is ready."""
    import httpx

    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(f"{url}/health", timeout=5)
            if resp.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.ReadTimeout):
            pass
        time.sleep(2)
    return False


def main() -> None:
    args = parse_args()

    adapter_path = Path(args.adapter_path)
    if not adapter_path.exists():
        print(f"FAIL: Adapter path does not exist: {adapter_path}")
        raise SystemExit(1)

    if not (adapter_path / "adapter_config.json").exists():
        print(f"FAIL: adapter_config.json not found in {adapter_path}")
        raise SystemExit(1)

    server_url = f"http://localhost:{args.port}"
    serve_script = Path("training/scripts/serve_local_model.py")

    if not serve_script.exists():
        print(f"FAIL: Serve script not found: {serve_script}")
        raise SystemExit(1)

    # Start the model server
    print(f"Starting model server on port {args.port}...")
    server_proc = subprocess.Popen(
        [
            sys.executable,
            str(serve_script),
            "--adapter-path",
            str(adapter_path),
            "--port",
            str(args.port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Wait for server to be ready
        print(f"Waiting for server health (timeout={args.timeout}s)...")
        if not wait_for_server(server_url, args.timeout):
            print("FAIL: Server did not become healthy in time.")
            raise SystemExit(1)

        print("Server is healthy. Sending test query...")

        import httpx

        # Send a test mental health query
        test_message = "I am feeling very anxious about my exams and cannot sleep at night."
        response = httpx.post(
            f"{server_url}/v1/chat",
            json={
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful mental health counselling assistant.",
                    },
                    {"role": "user", "content": test_message},
                ]
            },
            timeout=60,
        )

        if response.status_code != 200:
            print(f"FAIL: Chat endpoint returned status {response.status_code}")
            print(f"Response: {response.text}")
            raise SystemExit(1)

        data = response.json()
        # Handle both response formats
        content = data.get("content", "")
        if not content and "choices" in data:
            content = data["choices"][0].get("message", {}).get("content", "")

        print(f"\nTest query: {test_message}")
        print(f"Model response: {content[:500]}")

        if len(content) < 30:
            print(f"\nFAIL: Response too short ({len(content)} chars, expected >= 30)")
            raise SystemExit(1)

        print("\nPASS: End-to-end verification succeeded.")

    finally:
        # Clean up server process
        print("Shutting down server...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server_proc.kill()


if __name__ == "__main__":
    main()
