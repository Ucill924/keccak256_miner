# ⛏️ keccak256 GPU Miner — $HASH Token

> High-performance GPU miner untuk [$HASH](https://hash256.org) token di Ethereum Mainnet menggunakan CUDA keccak256 brute-force.

---

## ✨ Features

- 🚀 CUDA keccak256 brute-force — 5-15 GH/s tergantung GPU
- 🎯 Address-bound challenge — solusi tidak bisa dicuri dari mempool
- 🔄 Auto refresh challenge setiap epoch (~20 menit)
- 📡 MEVblocker RPC — TX langsung ke validator tanpa mempool publik
- 🖥️ Support multi GPU via screen session

---

## 📁 File Structure

```
keccak256_miner/
├── keccak256_miner.cu    ← CUDA kernel (keccak256 brute-force)
├── miner.py              ← Python wrapper (fetch challenge, submit TX)
└── .env                  ← config wallet & RPC (jangan di-commit!)
```

---

## ⚙️ Requirements

- NVIDIA GPU (RTX 3090 / 4090 / 5090)
- CUDA Toolkit
- Python 3.10+
- Ubuntu 22.04 / 24.04

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Ucill924/keccak256_miner.git
cd keccak256_miner

python3 -m venv /root/venv
source /root/venv/bin/activate
pip install web3 eth-account colorama pycryptodome
```

### 2. Compile CUDA kernel

```bash
# RTX 3090 / 4090
nvcc -shared -Xcompiler -fPIC -arch=sm_86 -o keccak256_miner.so keccak256_miner.cu

# RTX 5090
nvcc -shared -Xcompiler -fPIC -arch=sm_90 -o keccak256_miner.so keccak256_miner.cu
```

### 3. Buat file `.env`

```
PRIV_KEY=0xYOUR_PRIVATE_KEY
ETH_RPC=https://rpc.mevblocker.io/fast
```

> ⚠️ Jangan pernah commit file `.env` ke GitHub!

> 💡 Untuk RPC, bisa pakai [MEVblocker](https://rpc.mevblocker.io/fast) atau [Alchemy](https://alchemy.com)

---

### Step 1 — Single GPU

```bash
source /root/venv/bin/activate
export $(cat .env | xargs)
python miner.py
```

Output yang diharapkan:
```
[INFO] Wallet : 0xYOUR_ADDRESS
[INFO] RPC    : https://rpc.mevblocker.io/fast
[INFO] Batch  : 50,000,000 nonces/batch

[EPOCH] New challenge: 64bb838fef161dfb...
[EPOCH] Difficulty:    0x0000000000ffffff...
[ERA 0] Reward: 100 HASH | Epoch ends in 97 blk
[HASH] 5090.9 MH/s | Total: 305.55 GH | Mints: 0 | Uptime: 60s
[SUBMIT] Nonce: 2417886311248... | Epoch: 95 blk left
[TX] Sent: 0x01fe6803c261fc22...
[✓] MINTED! Block: 25069135
```

---

### Step 2 — Multi GPU

Jalanin masing-masing GPU di screen terpisah:

```bash
screen -S miner0 -dm bash -c "CUDA_VISIBLE_DEVICES=0 . /root/venv/bin/activate && export \$(cat /root/hash256/.env | xargs) && cd /root/hash256 && python miner.py"
screen -S miner1 -dm bash -c "CUDA_VISIBLE_DEVICES=1 . /root/venv/bin/activate && export \$(cat /root/hash256/.env | xargs) && cd /root/hash256 && python miner.py"
screen -S miner2 -dm bash -c "CUDA_VISIBLE_DEVICES=2 . /root/venv/bin/activate && export \$(cat /root/hash256/.env | xargs) && cd /root/hash256 && python miner.py"
```

Cek semua screen jalan:
```bash
screen -ls
```

Masuk ke screen tertentu:
```bash
screen -r miner0
# Detach: Ctrl+A D
```

Kill semua screen:
```bash
screen -ls | grep miner | awk '{print $1}' | xargs -I{} screen -S {} -X quit
```

---

## 🔄 Full Flow

```
GPU (CUDA)
    │
    ├─► Fetch challenge dari contract
    │       getChallenge(miner_address) → bytes32
    │
    ├─► Brute-force 256-bit nonce
    │       keccak256(challenge ‖ nonce) < currentDifficulty
    │       ~5-15 GH/s tergantung GPU
    │
    └─► Submit TX ke Ethereum
            mine(uint256 nonce)
            → Contract verifikasi
            → Mint 100 HASH ke wallet ✅
```

---

## 📊 Performance

| GPU | Hashrate |
|-----|----------|
| RTX 3090 | ~5 GH/s |
| RTX 4090 | ~7 GH/s |
| RTX 5090 | ~7 GH/s per GPU |
| 3× RTX 5090 | ~15 GH/s |

---

## 🔧 Troubleshooting

| Error | Solusi |
|-------|--------|
| `cicc` compile lama | Tunggu 5-10 menit, jangan Ctrl+C |
| `TX reverted` | BlockCapReached (10 mint/block penuh) atau epoch expired |
| `TX not in chain` | Ganti RPC ke `https://rpc.mevblocker.io/fast` |
| `insufficient funds` | Top up ETH untuk gas fee (~0.0005 ETH per mint) |
| `ModuleNotFoundError` | Jalankan `pip install web3 eth-account colorama pycryptodome` |
| `sm_100 not defined` | Ganti ke `sm_90` untuk RTX 5090 |

---

## ⚠️ Security

- **Jangan share** file `.env`
- Tambahkan ke `.gitignore`:

```
.env
__pycache__/
*.pyc
*.so
```

- Selalu pastikan `.gitignore` ada sebelum `git push`!

---

## 📜 Contract

| Item | Detail |
|------|--------|
| Address | `0xAC7b5d06fa1e77D08aea40d46cB7C5923A87A0cc` |
| Network | Ethereum Mainnet (Chain ID: 1) |
| Hard Cap | 21,000,000 HASH |
| Reward Era 1 | 100 HASH / mint |
| Max mint/block | 10 |
| Etherscan | [Link](https://etherscan.io/address/0xAC7b5d06fa1e77D08aea40d46cB7C5923A87A0cc) |
