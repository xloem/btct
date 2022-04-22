import asyncio
from solana.publickey import b58decode, b58encode
from solana.rpc.websocket_api import connect as WSClient
from solana.rpc.api import Client
import pyserum
import pyserum.connection
import websockets.legacy.client
import json

import db
def hex2b(hex):
    if type(hex) is str:
        return b58decode(hex.encode())
    else:
        return hex
def b2hex(bytes):
    if type(bytes) is str:
        return bytes
    else:
        return b58encode(bytes).decode()
db.b2hex = b2hex
db.hex2b = hex2b

API = 'api.mainnet-beta.solana.com'
solana = Client(f'https://{API}')
WS_API = f'ws://{API}'

PROGRAM_ID = '9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin' # serum dex program v3 from atrix, works for me
#PROGRAM_ID = 'SwaPpA9LAaLfeLi3a68M4DjnLqgtticKg6CnyNwgAC8', # serum dex program from source code, no txs for me

TOKEN_NAMES_BY_ADDRESSES = {token.address._key:token.name for token in pyserum.connection.get_token_mints()}

class dex:
    def __init__(self, programid = PROGRAM_ID, name = 'Serum V3'):
        self.db = db.dex(programid)
        if not self.db:
            self.db = db.dex.ensure(programid, name)
    def tokens(self):
        for token_mint in pyserum.connection.get_token_mints():
            yield token(token_mint.address._key)
    def pairs(self):
        for live_market in pyserum.connection.get_live_markets():
            name = live_market.name
            #if name.startswith('so') or name.startswith('st'):
            #    name = name[2:]
            base_name, quote_name = name.split('/')
            p = pair(self, live_market.address)
            if p.db.token0.symbol != base_name:
                p.db.token0.symbol = base_name
            if p.db.token1.symbol != quote_name:
                p.db.token1.symbol = quote_name
            yield p

    #def pair(self, token0, token1):
    #    tokens=[token0,token1]

class token:
    def __init__(self, db_or_addr):
        if type(db_or_addr) is db.Table.Row:
            self.db = db_or_addr
            addr = self.db.addr
        else:
            self.db = None
            addr = db_or_addr
        if not self.db:
            self.db = db.token(addr)
        if not self.db:
            symbol = TOKEN_NAMES_BY_ADDRESSES.get(addr, b2hex(addr))
            decimals = pyserum.utils.get_mint_decimals(solana, b2hex(addr))
            self.db = db.token.ensure(addr, symbol, decimals)

class pair:
    def __init__(self, dexobj, dbpair_or_addr):
        if type(dbpair_or_addr) is db.Table.Row:
            self.db = dbpair_or_addr
            addr = self.db.addr
            if not self.db:
                dbpair_or_addr = self.db.addr
        else:
            addr = dbpair_or_addr
        self.dex = dexobj
        if type(dbpair_or_addr) is not db.Table.Row:
            self.db = db.pair(addr)
            self.market = pyserum.market.Market.load(solana, addr)
            if not self.db:
                token0addr = self.market.state.base_mint()._key
                token1addr = self.market.state.quote_mint()._key
                self.db = db.pair.ensure(
                        addr,
                        token(token0addr).db,
                        token(token1addr).db,
                        self.dex.db.addr
                )

    async def stream(self):
        async with WSCLient(WS_API) as ws:
            await websocket.program_subscribe(str(self.db.addr))
            resp = ws.recv()
            while True:
                resp = await websockets.legacy.client.WebSocketClientProtocol.recv(websocket)
                resp = json.loads(resp)
                pubkey = resp['params']['result']['value']['pubkey']
