import ctypes

lib = ctypes.CDLL('./keccak256_miner.so')

# Dummy test: challenge=zeros, diff=max, base_nonce=zeros, batch=1
c_ch   = (ctypes.c_uint8 * 32)(*([0]*32))
c_diff = (ctypes.c_uint8 * 32)(*([0xff]*32))
c_nin  = (ctypes.c_uint8 * 32)(*([0]*32))
c_nout = (ctypes.c_uint8 * 32)()

lib.launch_miner.restype  = ctypes.c_int
lib.launch_miner.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_uint64,
    ctypes.POINTER(ctypes.c_uint8),
]

# Kita perlu expose fungsi K256 untuk test
# Tambah fungsi test ke .so dulu
print("Test: keccak256(zeros*64)")
print("Expected: ad3228b676f7d3cd4284a5443f17f1962b36e491b30a40b2405849e597ba5fb5")
