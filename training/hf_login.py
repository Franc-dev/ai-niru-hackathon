"""
HuggingFace login helper.

Usage:
    python hf_login.py

You'll need to paste your HuggingFace token from https://huggingface.co/settings/tokens
"""

import os
import sys

def main():
    print("=" * 60)
    print("HuggingFace Login")
    print("=" * 60)
    print("\nTo get your token:")
    print("1. Go to https://huggingface.co/settings/tokens")
    print("2. Create a new token with 'read' access")
    print("3. Copy and paste it below\n")
    
    # Check if already logged in via environment
    if os.environ.get("HF_TOKEN"):
        print("HF_TOKEN environment variable is already set!")
        return
    
    try:
        from huggingface_hub import login
        
        token = input("Paste your HuggingFace token: ").strip()
        
        if not token:
            print("No token provided. Exiting.")
            return
        
        login(token=token, add_to_git_credential=True)
        print("\nLogin successful!")
        
        # Also set for current session
        os.environ["HF_TOKEN"] = token
        
    except Exception as e:
        print(f"\nError during login: {e}")
        print("\nAlternatively, you can set the HF_TOKEN environment variable:")
        print('  set HF_TOKEN=your_token_here  (in cmd)')
        print('  $env:HF_TOKEN="your_token_here"  (in PowerShell)')
        sys.exit(1)


if __name__ == "__main__":
    main()
