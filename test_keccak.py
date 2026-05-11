from Crypto.Hash import keccak as _keccak

def keccak256(data):
    k = _keccak.new(digest_bits=256)
    k.update(data)
    return k.digest()

# Test vector
data = b'\x00' * 64
h = keccak256(data)
print(f"Python keccak256(zeros): {h.hex()}")
