import json, time, os, random
from web3 import Web3
from decimal import Decimal
from eth_abi import encode
from rich.console import Console
from dotenv import load_dotenv

console = Console()

# Load environment variables
load_dotenv()
PRIVATE_KEYS = os.getenv("PRIVATE_KEYS", "").split(",")

if not PRIVATE_KEYS or PRIVATE_KEYS == [""]:
    console.print("[red]❌ No PRIVATE_KEYS found in .env file[/red]")
    exit()

console.print("-" * 50)

# Load config
try:
    with open("network_config.json") as f:
        config = json.load(f)
except Exception as e:
    console.print(f"[red]❌ Failed to load config: {str(e)}[/red]")
    exit()

# Connect RPC
web3 = Web3(Web3.HTTPProvider(config["rpc"]))
if not web3.is_connected():
    console.print("[red]❌ Failed to connect to RPC[/red]")
    exit()
console.print("[green]✅ Connected to RPC[/green]")

CHAIN_ID = config["chain_id"]
TOKEN_MAPPING = {k: Web3.to_checksum_address(v["address"]) for k, v in config["tokens"].items()}

# Nonce tracker
nonce_tracker = {}

def get_managed_nonce(addr):
    global nonce_tracker
    if addr not in nonce_tracker:
        nonce_tracker[addr] = web3.eth.get_transaction_count(addr, "pending")
        console.print(f"[dim]🔢 Initial nonce for {short(addr)}: {nonce_tracker[addr]}[/dim]")
    else:
        nonce_tracker[addr] += 1
        console.print(f"[dim]🔢 Using nonce for {short(addr)}: {nonce_tracker[addr]}[/dim]")
    return nonce_tracker[addr]

def reset_nonce_tracker():
    global nonce_tracker
    nonce_tracker = {}

def get_gas_price(): return int(web3.eth.gas_price * Decimal(2))
def get_gas(): return web3.eth.gas_price + Web3.to_wei(5, 'gwei')
def short(addr): return f"{addr[:6]}...{addr[-4:]}"

def tx_delay(): time.sleep(2)

# --- Contract Helpers ---
def get_erc20(address, abi):
    return web3.eth.contract(address=address, abi=abi)

# Load ABIs
try:
    with open("token_abi.json") as f:
        erc20_abi = json.load(f)
    with open("router_swap_abi.json") as f:
        router_swap_abi = json.load(f)
except Exception as e:
    console.print(f"[red]❌ Failed to load ABI: {str(e)}[/red]")
    exit()

def show_status(action, sender, contract, status, tx_hash=None):
    if tx_hash:
        console.print(f"🔗 TX Hash    https://pharos-testnet.socialscan.io//tx/{tx_hash}")
    console.print("─" * 50)

# Example approve function (others remain unchanged)
def approve_token_swap(sender, spender, amount, privkey, token_addr, label):
    try:
        contract = get_erc20(token_addr, erc20_abi)
        allowance = contract.functions.allowance(sender, spender).call()
        if allowance >= amount:
            show_status(f"Approve {label}", sender, token_addr, "[green]Already Approved[/green]")
            return True

        tx = contract.functions.approve(spender, amount).build_transaction({
            "from": sender,
            "nonce": get_managed_nonce(sender),
            "gasPrice": get_gas(),
            "chainId": CHAIN_ID,
            "gas": 600000
        })
        signed = web3.eth.account.sign_transaction(tx, privkey)
        tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
        show_status(f"Approve {label}", sender, token_addr, "[yellow]Submitted[/yellow]", web3.to_hex(tx_hash))
        tx_delay()
        return True
    except Exception as e:
        show_status(f"Approve {label}", sender, token_addr, f"[red]{str(e)}[/red]")
        return False

# --- Main ---
def main():
    reset_nonce_tracker()
    for i, pk in enumerate(PRIVATE_KEYS, 1):
        try:
            acc = web3.eth.account.from_key(pk.strip())
            sender = acc.address
            console.print(f"\n[bold cyan]▶ Wallet {i}: {short(sender)}[/bold cyan]")
            console.print("─" * 50)

            # ... rest of your swap/stake logic here ...
            # approve_token_swap(sender, ... )

        except Exception as e:
            console.print(f"[red]❌ Wallet {i} Error: {str(e)}[/red]")
            console.print("─" * 50)

if __name__ == "__main__":
    while True:
        try:
            console.print("\n[bold yellow]⏳ R2 Testnet Full Auto  [/bold yellow]")
            main()
            console.print("[bold green]✅ All processes completed. Waiting 24 hours before restarting...[/bold green]")
            console.print("🕒 Next time: " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + 86400)))
            time.sleep(86400)
        except Exception as e:
            console.print(f"[red]❌ Error occurred during loop: {e}[/red]")
            console.print("[yellow]⏳ Retrying after 60 seconds...[/yellow]")
            time.sleep(60)
