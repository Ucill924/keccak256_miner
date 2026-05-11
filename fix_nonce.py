# Test: generate nonce seperti yang contract expect
import random
nonce = random.randint(0, 2**256 - 1)
print(f"256-bit nonce: {nonce}")
print(f"bytes: {nonce.to_bytes(32, 'big').hex()}")
