project_root/
├─ .env
├─ config.py
├─ trade_api.py          # your REST wrapper (from trade.py)
├─ erc3525_agent.py      # Agent2: CDP/ERC‑3525 logic
├─ indicators.py         # ML/TA feature extraction
├─ agent_base.py         # TradingAgent class & strategy engine
└─ main.py               # Orchestrator: loads config, spins up agents






#Centralized config loader (config.py)
#Use python‑decouple to pull everything from .env:

#-----------------------
#config.py
#------------------------

from decouple import config, Csv

# Coinbase API  
CB_API_KEY      = config("CB_API_KEY")  
CB_API_SECRET   = config("CB_API_SECRET")  
CB_API_PASSPHRASE = config("CB_API_PASSPHRASE")

# RPC & Wallet  
RPC_URL         = config("RPC_URL")  
ERC3525_ADDR    = config("ERC3525_CONTRACT_ADDRESS")  
CDP_KEY_NAME    = config("CDP_API_KEY_NAME")  
CDP_KEY_PRIV    = config("CDP_API_KEY_PRIVATE")  
PRIVATE_KEY     = config("PRIVATE_KEY")

# Trading params  
PAPER_MODE      = config("PAPER_TRADING", cast=bool, default=True)  
STRATEGY       = config("STRATEGY_MODE", default="default")  
ASSETS          = config("ASSETS", cast=Csv(), default="BTC-USD,ETH-USD,PEPE-USD")  
SIZE            = config("TRADE_SIZE", default="0.01")

# Strategy thresholds  
THRESHOLD_SHORT  = config("THRESHOLD_SHORT", cast=float, default=50.0)  
THRESHOLD_LONG   = config("THRESHOLD_LONG", cast=float, default=100.0)






#from config import CB_API_KEY, PAPER_MODE, ASSETS


#------------------------------------------
#Shared REST wrapper (trade_api.py)
#-------------------------------------------

import time, hmac, hashlib, json, requests
from config import CB_API_KEY, CB_API_SECRET, CB_API_PASSPHRASE

API_URL = "https://api.coinbase.com"


def _sign_request(method, path, body):
    timestamp = str(int(time.time()))
    payload = timestamp + method + path + (json.dumps(body) if body else "")
    signature = hmac.new(CB_API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {
        "CB-ACCESS-KEY": CB_API_KEY,
        "CB-ACCESS-SIGN": signature,
        "CB-ACCESS-TIMESTAMP": timestamp,
        "CB-ACCESS-PASSPHRASE": CB_API_PASSPHRASE,
        "Content-Type": "application/json"
    }

def place_order(side, product_id, size, price=None):
    path = "/v3/brokerage/orders"
    body = {"side": side, "product_id": product_id, "size": size}
    if price:
        body.update(type="limit", limit_price=price)
    resp = requests.post(API_URL + path, headers=_sign_request("POST", path, body), json=body)
    resp.raise_for_status()
    return resp.json()






#
#Keep your existing CDP + Web3 setup here, parameterized by config.py. Expose a simple #mint_if_needed(slot, threshold) function that Agent 2 can call each cycle.
#------------------------
#agent_base.py and STRATEGY ENGINE
#------------------------
import time
from decimal import Decimal
from trade_api import place_order
from indicators import compute_signals

class TradingAgent:
    def __init__(self, name, assets, paper_mode, strategy_params):
        self.name = name
        self.assets = assets
        self.paper_mode = paper_mode
        self.params = strategy_params

    def run_cycle(self):
        signals = compute_signals(self.assets, self.params)
        for sig in signals:
            side, product, size, price = sig.values()
            if self.paper_mode:
                print(f"[{self.name} PAPER] {side} {size} {product} @ {price}")
            else:
                resp = place_order(side, product, size, price)
                print(f"[{self.name} LIVE] order →", resp)

    def start(self, interval=10):
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                print(f"[{self.name} ERROR]", e)
            time.sleep(interval)

#------------------------------------
#main.py
#------------------------------------
from config import PAPER_MODE, STRATEGY, ASSETS, SIZE
from agent_base import TradingAgent
from erc3525_agent import ERC3525Agent
import json

def main():
    # Load dynamic strategy params from .env or a JSON blob
    strategy_params = json.loads(STRATEGY)
    
    # Agent 1: spot‑bot REST  
    agent1 = TradingAgent("Agent1‑REST", ASSETS, PAPER_MODE, strategy_params)
    
    # Agent 2: ERC‑3525 slot manager  
    agent2 = ERC3525Agent("Agent2‑Slot", PAPER_MODE)

    # In prod you may run these in separate processes/threads
    agent1.start(interval=5)
    # or spawn agent2.start(...)
    
if __name__ == "__main__":
    main()
