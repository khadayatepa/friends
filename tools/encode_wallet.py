"""Print the base64 of your ADB wallet .zip so it can be pasted into
Streamlit secrets as oracle.wallet_b64.

Usage:
    python tools/encode_wallet.py path/to/Wallet_prashant26ai.zip
"""
import base64
import sys

if len(sys.argv) != 2:
    print("Usage: python tools/encode_wallet.py <wallet.zip>")
    raise SystemExit(1)

with open(sys.argv[1], "rb") as f:
    print(base64.b64encode(f.read()).decode())
