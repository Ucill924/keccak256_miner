#!/usr/bin/env python3
import os, time, random, threading
from Crypto.Hash import keccak as _keccak
from web3 import Web3
from eth_account import Account
from colorama import Fore, init
init(autoreset=True)

RPC_URL     = os.getenv("ETH_RPC", "https://eth.llamarpc.com")
PRIVATE_KEY = os.getenv("PRIV_KEY", "0xYOUR_KEY")
CONTRACT    = "0xAC7b5d06fa1e77D08aea40d46cB7C5923A87A0cc"
THREADS     = 16

HASH_ABI = [
    {"name":"getChallenge","type":"function","stateMutability":"view","inputs":[{"name":"miner","type":"address"}],"outputs":[{"type":"bytes32"}]},
    {"name":"currentDifficulty","type":"function","stateMutability":"view","inputs":[],"outputs":[{"type":"uint256"}]},
    {"name":"genesisComplete","type":"function","stateMutability":"view","inputs":[],"outputs":[{"type":"bool"}]},
    {"name":"miningState","type":"function","stateMutability":"view","inputs":[],"outputs":[{"name":"era","type":"uint256"},{"name":"reward","type":"uint256"},{"name":"difficulty","type":"uint256"},{"name":"minted","type":"uint256"},{"name":"remaining","type":"uint256"},{"name":"epoch","type":"uint256"},{"name":"epochBlocksLeft_","type":"uint256"}]},
    {"name":"mine","type":"function","stateMutability":"nonpayable","inputs":[{"name":"nonce","type":"uint256"}],"outputs":[]},
]

w3       = Web3(Web3.HTTPProvider(RPC_URL))
acct     = Account.from_key(PRIVATE_KEY)
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT), abi=HASH_ABI)

found_nonce  = [None]
total_hashes = [0]
lock         = threading.Lock()

def keccak256(data: bytes) -> int:
    k = _keccak.new(digest_bits=256)
    k.update(data)
    return int.from_bytes(k.digest(), 'big')

def get_challenge():
    return bytes(contract.functions.getChallenge(acct.address).call())

def get_difficulty():
    return contract.functions.currentDifficulty().call()

def mine_thread(challenge, difficulty, nonce_start):
    nonce = nonce_start
    local_count = 0
    while found_nonce[0] is None:
        packed = challenge + nonce.to_bytes(32, 'big')
        h = keccak256(packed)
        local_count += 1
        if local_count % 10000 == 0:
            with lock:
                total_hashes[0] += local_count
            local_count = 0
        if h < difficulty:
            with lock:
                total_hashes[0] += local_count
                if found_nonce[0] is None:
                    found_nonce[0] = nonce
            return
        nonce += THREADS

def submit(nonce_val):
    print(f"\n{Fore.GREEN}[HIT] Nonce: {nonce_val} → submitting...")
    tx = contract.functions.mine(nonce_val).build_transaction({
        "from":  acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "gas":   150000,
        "maxFeePerGas":         int(20e9),
        "maxPriorityFeePerGas": int(2e9),
    })
    signed  = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"{Fore.GREEN}[TX] {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status == 1:
        print(f"{Fore.GREEN}[✓] MINTED! Block: {receipt.blockNumber}")
    else:
        print(f"{Fore.RED}[✗] Reverted")

print(f"{Fore.YELLOW}[INFO] Wallet : {acct.address}")
print(f"{Fore.YELLOW}[INFO] Threads: {THREADS}")

mints = 0
while True:
    try:
        challenge  = get_challenge()
        difficulty = get_difficulty()
        state      = contract.functions.miningState().call()
        print(f"\n{Fore.CYAN}[ERA {state[0]}] Reward: {state[1]//10**18} HASH | Diff: {hex(difficulty)[:18]}... | Epoch ends in {state[6]} blk")

        found_nonce[0]  = None
        total_hashes[0] = 0
        t0 = time.time()

        threads = []
        for i in range(THREADS):
            t = threading.Thread(target=mine_thread, args=(challenge, difficulty, random.randint(0,2**63)+i), daemon=True)
            t.start()
            threads.append(t)

        while found_nonce[0] is None:
            elapsed = time.time() - t0
            mhs = total_hashes[0] / elapsed / 1e6 if elapsed > 0 else 0
            print(f"\r{Fore.CYAN}[HASH] {mhs:.2f} MH/s | {total_hashes[0]:,} hashes | {elapsed:.1f}s", end="", flush=True)
            time.sleep(0.5)

        submit(found_nonce[0])
        mints += 1
        print(f"{Fore.GREEN}[TOTAL MINTS] {mints}")

    except Exception as e:
        print(f"\n{Fore.RED}[ERR] {e}")
        time.sleep(5)
