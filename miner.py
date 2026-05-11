#!/usr/bin/env python3
import os, time, ctypes, random
from web3 import Web3
from eth_account import Account
from colorama import Fore, init
init(autoreset=True)

RPC_URL       = os.getenv("ETH_RPC", "https://rpc.mevblocker.io/fast")
PRIVATE_KEY   = os.getenv("PRIV_KEY", "0xYOUR_KEY")
CONTRACT_ADDR = "0xAC7b5d06fa1e77D08aea40d46cB7C5923A87A0cc"
GAS_LIMIT     = 200_000
MAX_FEE_GWEI  = 5
PRIORITY_GWEI = 3
BATCH_SIZE    = 50_000_000
SO_PATH       = "./keccak256_miner.so"
MIN_EPOCH_BLK = 5  # skip submit kalau epoch < 5 blk

HASH_ABI = [
    {"name":"getChallenge","type":"function","stateMutability":"view","inputs":[{"name":"miner","type":"address"}],"outputs":[{"type":"bytes32"}]},
    {"name":"currentDifficulty","type":"function","stateMutability":"view","inputs":[],"outputs":[{"type":"uint256"}]},
    {"name":"miningState","type":"function","stateMutability":"view","inputs":[],"outputs":[{"name":"era","type":"uint256"},{"name":"reward","type":"uint256"},{"name":"difficulty","type":"uint256"},{"name":"minted","type":"uint256"},{"name":"remaining","type":"uint256"},{"name":"epoch","type":"uint256"},{"name":"epochBlocksLeft_","type":"uint256"}]},
    {"name":"mine","type":"function","stateMutability":"nonpayable","inputs":[{"name":"nonce","type":"uint256"}],"outputs":[]},
]

lib = ctypes.CDLL(SO_PATH)
lib.launch_miner.restype  = ctypes.c_int
lib.launch_miner.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_uint64,
    ctypes.POINTER(ctypes.c_uint8),
]

w3       = Web3(Web3.HTTPProvider(RPC_URL))
acct     = Account.from_key(PRIVATE_KEY)
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDR), abi=HASH_ABI)

print(f"{Fore.YELLOW}[INFO] Wallet : {acct.address}")
print(f"{Fore.YELLOW}[INFO] RPC    : {RPC_URL}")
print(f"{Fore.YELLOW}[INFO] Batch  : {BATCH_SIZE:,} nonces/batch")

last_challenge = None
last_diff      = None
epoch_refresh  = 0
mints          = 0
start_time     = time.time()
total_hashes   = 0

c_challenge = (ctypes.c_uint8 * 32)()
c_diff      = (ctypes.c_uint8 * 32)()
c_nonce_in  = (ctypes.c_uint8 * 32)()
c_nonce_out = (ctypes.c_uint8 * 32)()

while True:
    try:
        now = int(time.time())
        if now - epoch_refresh > 30 or last_challenge is None:
            challenge  = bytes(contract.functions.getChallenge(acct.address).call())
            difficulty = contract.functions.currentDifficulty().call()
            diff_bytes = difficulty.to_bytes(32, 'big')
            state      = contract.functions.miningState().call()
            epoch_blk  = state[6]

            if challenge != last_challenge or diff_bytes != last_diff:
                last_challenge = challenge
                last_diff      = diff_bytes
                epoch_refresh  = now
                for i in range(32):
                    c_challenge[i] = challenge[i]
                    c_diff[i]      = diff_bytes[i]
                print(f"\n{Fore.YELLOW}[EPOCH] New challenge: {challenge.hex()[:16]}...")
                print(f"{Fore.YELLOW}[EPOCH] Difficulty:    0x{diff_bytes.hex()[:16]}...")
                print(f"{Fore.CYAN}[ERA {state[0]}] Reward: {state[1]//10**18} HASH | Epoch ends in {epoch_blk} blk")
            else:
                epoch_refresh = now

        # Random 256-bit base nonce
        base = random.randint(0, 2**256 - 1)
        base_bytes = base.to_bytes(32, 'big')
        for i in range(32): c_nonce_in[i] = base_bytes[i]

        found = lib.launch_miner(
            c_challenge, c_diff, c_nonce_in,
            ctypes.c_uint64(BATCH_SIZE), c_nonce_out
        )

        total_hashes += BATCH_SIZE
        uptime = time.time() - start_time
        mhs = total_hashes / uptime / 1e6
        print(f"\r{Fore.CYAN}[HASH] {mhs:.1f} MH/s | Total: {total_hashes/1e9:.2f} GH | Mints: {mints} | Uptime: {int(uptime)}s", end="", flush=True)

        if found:
            nonce_bytes = bytes(c_nonce_out)
            nonce_int   = int.from_bytes(nonce_bytes, 'big')

            # Cek epoch masih aman
            state2    = contract.functions.miningState().call()
            epoch_blk = state2[6]
            if epoch_blk < MIN_EPOCH_BLK:
                print(f"\n{Fore.YELLOW}[SKIP] Epoch tinggal {epoch_blk} blk, skip!")
                last_challenge = None
                continue

            mints += 1
            print(f"\n{Fore.GREEN}[SUBMIT] Nonce: {nonce_int} | Epoch: {epoch_blk} blk left")
            try:
                tx = contract.functions.mine(nonce_int).build_transaction({
                    "from":                 acct.address,
                    "nonce":                w3.eth.get_transaction_count(acct.address),
                    "gas":                  GAS_LIMIT,
                    "maxFeePerGas":         int(MAX_FEE_GWEI * 1e9),
                    "maxPriorityFeePerGas": int(PRIORITY_GWEI * 1e9),
                })
                signed  = acct.sign_transaction(tx)
                raw     = signed.raw_transaction
                tx_hash = w3.eth.send_raw_transaction(raw)
                # Broadcast ke RPC lain juga
                for rpc in ["https://rpc.ankr.com/eth","https://ethereum.publicnode.com"]:
                    try: Web3(Web3.HTTPProvider(rpc)).eth.send_raw_transaction(raw)
                    except: pass
                print(f"{Fore.GREEN}[TX] Sent: {tx_hash.hex()}")
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                if receipt.status == 1:
                    print(f"{Fore.GREEN}[✓] MINTED! Block: {receipt.blockNumber}")
                else:
                    print(f"{Fore.RED}[✗] Reverted")
            except Exception as e:
                print(f"{Fore.RED}[ERROR] {e}")
            last_challenge = None

    except Exception as e:
        print(f"\n{Fore.RED}[ERR] {e}")
        time.sleep(5)
