
 - 3525_agent_2.py…]()
 - #-----------script 2 of 2-------------------------------
 # file ERC3525_AGENT
 
 #env python3
 import os
 import time
 import json
 import logging
 import argparse
 from decimal import Decimal
 from dotenv import load_dotenv
 from web3 import Web3
 from cdp import Cdp, Wallet
 
 # Setup logging
 logging.basicConfig(
     filename="erc3525_agent.log",
     level=logging.INFO,
     format="%(asctime)s [%(levelname)s] %(message)s"
 )
 logger = logging.getLogger()
 
 def setup_env():
     load_dotenv()
     rpc_url = os.getenv("RPC_URL")
     erc3525_address = os.getenv("ERC3525_CONTRACT_ADDRESS")
     api_key_name = os.getenv("CDP_API_KEY_NAME")
     api_key_private = os.getenv("CDP_API_KEY_PRIVATE")
     private_key = os.getenv("PRIVATE_KEY")
     if not all([rpc_url, erc3525_address, api_key_name, api_key_private, private_key]):
         logger.error("One or more required environment variables are missing.")
         raise EnvironmentError("Missing environment variables.")
     return rpc_url, erc3525_address, api_key_name, api_key_private, private_key
 
 def parse_args():
     parser = argparse.ArgumentParser()
     parser.add_argument('--paper', action='store_true', help='Enable paper trading mode (simulate transactions)')
     parser.add_argument('--strategy', type=str, default='default', help='Select strategy mode (default, alternate)')
     args = parser.parse_args()
     return args.paper, args.strategy
 
 # Define wallet file location.
 WALLET_FILE = os.path.join(os.path.dirname(__file__), "wallet_seed.json")
 
 def load_or_create_wallet(api_key_name, api_key_private):
     Cdp.configure(api_key_name, api_key_private)
     if os.path.exists(WALLET_FILE):
         try:
             with open(WALLET_FILE, "r") as f:
                 wallet_data = json.load(f)
             wallet_id = wallet_data.get("id")
             if not wallet_id:
                 raise ValueError("Wallet ID not found in seed file.")
             wallet = Wallet.fetch(wallet_id)
             wallet.load_seed_from_file(WALLET_FILE)
             logger.info("Existing wallet loaded successfully.")
             return wallet
         except Exception as e:
             logger.error(f"Error loading wallet: {e}. Removing corrupt wallet file.")
             os.remove(WALLET_FILE)
     try:
         wallet = Wallet.create("base-mainnet")
         wallet.save_seed_to_file(WALLET_FILE, encrypt=True)
         logger.info(f"New wallet created with id {wallet.id}")
         return wallet
     except Exception as e:
         logger.error(f"Failed to create wallet: {e}")
         raise
 
 def init_web3(rpc_url):
     web3 = Web3(Web3.HTTPProvider(rpc_url))
     if not web3.isConnected():
         logger.error("Error connecting to Ethereum node.")
         raise ConnectionError("Web3 provider connection failed.")
     logger.info("Connected to Ethereum node.")
     return web3
 
 def load_contract(web3, contract_address):
     abi_file = os.path.join(os.path.dirname(__file__), "ERC3525_ABI.json")
     try:
         with open(abi_file, "r") as f:
             contract_abi = json.load(f)
     except Exception as e:
         logger.error(f"Failed to load contract ABI: {e}")
         raise
     try:
         contract = web3.eth.contract(
             address=Web3.toChecksumAddress(contract_address),
             abi=contract_abi
         )
         logger.info("ERC3525 contract loaded successfully.")
         return contract
     except Exception as e:
         logger.error(f"Failed to initialize contract: {e}")
         raise
 
 def get_account(web3, private_key, wallet):
     try:
         account = web3.eth.account.privateKeyToAccount(private_key)
     except Exception as e:
         logger.error(f"Failed to create account from PRIVATE_KEY: {e}")
         if hasattr(wallet, 'private_key'):
             account = web3.eth.account.privateKeyToAccount(wallet.private_key)
         else:
             raise
     web3.eth.default_account = account.address
     logger.info(f"Using account address: {account.address}")
     return account
 
 def simple_strategy(web3, contract, account, paper_mode):
     slot = 1
     threshold = Decimal("50")
     try:
         slot_balance = contract.functions.slotBalance(slot).call()
         logger.info(f"Current balance for slot {slot}: {slot_balance}")
     except Exception as e:
         logger.error(f"Error reading slot balance: {e}")
         slot_balance = 0
     if Decimal(slot_balance) < threshold:
         logger.info("Balance below threshold. Proceeding to mint additional tokens.")
         mint_value = threshold - Decimal(slot_balance)
         if paper_mode:
             logger.info(f"(Paper Trade) Simulate minting {mint_value} tokens in slot {slot}.")
         else:
             try:
                 txn = contract.functions._mint(account.address, slot, int(mint_value)).buildTransaction({
                     'from': account.address,
                     'nonce': web3.eth.getTransactionCount(account.address),
                     'gas': 300000,
                     'gasPrice': web3.toWei('5', 'gwei')
                 })
                 signed_txn = web3.eth.account.signTransaction(txn, private_key=account.privateKey)
                 tx_hash = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
                 logger.info(f"Mint transaction sent, tx hash: {web3.toHex(tx_hash)}")
             except Exception as e:
                 logger.error(f"Error sending mint transaction: {e}", exc_info=True)
     else:
         logger.info("Balance meets threshold. No minting necessary.")
 
 def alternate_strategy(web3, contract, account, paper_mode):
     slot = 2
     threshold = Decimal("100")
     try:
         slot_balance = contract.functions.slotBalance(slot).call()
         logger.info(f"(Alternate) Current balance for slot {slot}: {slot_balance}")
     except Exception as e:
         logger.error(f"Error reading slot balance for alternate strategy: {e}")
         slot_balance = 0
     if Decimal(slot_balance) < threshold:
         logger.info("(Alternate) Balance below threshold. Minting additional tokens.")
         mint_value = threshold - Decimal(slot_balance)
         if paper_mode:
             logger.info(f"(Paper Trade) (Alternate) Simulate minting {mint_value} tokens in slot {slot}.")
         else:
             try:
                 txn = contract.functions._mint(account.address, slot, int(mint_value)).buildTransaction({
                     'from': account.address,
                     'nonce': web3.eth.getTransactionCount(account.address),
                     'gas': 300000,
                     'gasPrice': web3.toWei('5', 'gwei')
                 })
                 signed_txn = web3.eth.account.signTransaction(txn, private_key=account.privateKey)
                 tx_hash = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
                 logger.info(f"(Alternate) Mint transaction sent, tx hash: {web3.toHex(tx_hash)}")
             except Exception as e:
                 logger.error(f"Error sending mint transaction in alternate strategy: {e}", exc_info=True)
     else:
         logger.info("(Alternate) Balance meets threshold. No action required.")
 
 def main_loop(web3, contract, account, paper_mode, strategy_mode):
     while True:
         try:
             if strategy_mode.lower() == 'default':
                 simple_strategy(web3, contract, account, paper_mode)
             elif strategy_mode.lower() == 'alternate':
                 alternate_strategy(web3, contract, account, paper_mode)
             else:
                 logger.warning("Unknown strategy mode specified. Defaulting to simple strategy.")
                 simple_strategy(web3, contract, account, paper_mode)
         except Exception as e:
             logger.error(f"Error in main loop: {e}", exc_info=True)
         time.sleep(10)  # Adjust the interval as needed
 
 def main():
     try:
         paper_mode, strategy_mode = parse_args()
         rpc_url, erc3525_address, api_key_name, api_key_private, private_key = setup_env()
         web3 = init_web3(rpc_url)
         wallet = load_or_create_wallet(api_key_name, api_key_private)
         account = get_account(web3, private_key, wallet)
         contract = load_contract(web3, erc3525_address)
         logger.info("Starting main loop for ERC3525 agent.")
         main_loop(web3, contract, account, paper_mode, strategy_mode)
     except Exception as e:
         logger.critical(f"Critical error encountered: {e}", exc_info=True)
         exit(1)
 
 if __name__ == "__main__":
     main()