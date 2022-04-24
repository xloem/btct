from solana.publickey import b58decode, b58encode, PublicKey
from solana.rpc.websocket_api import connect as WSClient
import websockets.legacy.client
from solana.rpc.api import Client, types as solana_types
from solana.rpc.async_api import AsyncClient
from solana.rpc.core import RPCException
from spl.token.client import Token as TokenClient
from spl.token.async_client import AsyncToken as TokenAsyncClient
import spl
import pyserum
import pyserum.connection

import asyncio, base64, collections, datetime, time, json

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

# serum runs a faster api that likely gives more requests
API = 'solana-api.projectserum.com'
solana = Client(f'https://{API}')
asolana = AsyncClient(f'https://{API}')
if API == 'solana-api.projectserum.com':
    WS_API = 'ws://api.mainnet-beta.solana.com'
else:
    WS_API = f'ws://{API}'

#PROGRAM_ID = '9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin' # serum dex program v3 from atrix, works for me
#PROGRAM_ID = 'SwaPpA9LAaLfeLi3a68M4DjnLqgtticKg6CnyNwgAC8', # serum dex program from source code, no txs for me
PROGRAM_ID = str(pyserum.instructions.DEFAULT_DEX_PROGRAM_ID)

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
    def __init__(self, dexobj, db_or_addr):
        self.dexobj = dexobj
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
    def balance(self, account):
        value = solana.get_token_account_balance(account)['result']['value']
        # value['decimals']
        return value['amount']
    def account(self, keypair):
        accts = solana.get_token_accounts_by_owner(keypair.public_key, solana_types.TokenAccountOpts(mint=str(self.db.addr)), commitment='processed')['result']['value']
        if len(accts) == 0:
            client = TokenClient(solana, program_id=PublicKey(self.dexobj.db.addr), pubkey=PublicKey(self.db.addr), payer=keypair)
            print(f'Creating {self.db.symbol} account for {keypair.public_key} ...')
            while True:
                try:
                    acct = client.create_associated_token_account(keypair.public_key)
                    break
                except RPCException as exc:
                    data = exception.args[0]['data']
                    if data['unitsConsumed'] == 0:
                        if data['err'] == 'BlockhashNotFound':
                            continue
                    raise
            print(f'Created {accts}.')
            return acct
        else:
            return accts[0]['pubkey']

class pair:
    def __init__(self, dexobj, dbpair_or_addr):
        self.dex = dexobj
        if type(dbpair_or_addr) is db.Table.Row:
            self.db = dbpair_or_addr
            addr = self.db.addr
            if not self.db:
                dbpair_or_addr = self.db.addr
        else:
            addr = dbpair_or_addr
        self.market = None
        if type(dbpair_or_addr) is not db.Table.Row:
            self.db = db.pair(addr)
            if not self.db:
                self.market = pyserum.market.Market.load(solana, addr)
                market_state = self.market.state
                token0addr = self.market.state.base_mint()._key
                token1addr = self.market.state.quote_mint()._key
                self.token0 = token(self.dex, token0addr)
                self.token1 = token(self.dex, token1addr)
                self.db = db.pair.ensure(
                        addr,
                        self.token0.db,
                        self.token1.db,
                        self.dex.db.addr
                )
        if self.market is None:
            bytes_data = pyserum.utils.load_bytes_data(str(self.db.addr), solana)
            parsed_market = pyserum.market.state.MarketState._make_parsed_market(bytes_data)
            market_state = pyserum.market.state.MarketState(parsed_market, PROGRAM_ID, self.db.token0.decimals, self.db.token1.decimals)
            self.market = pyserum.market.Market(solana, market_state)
            self.token0 = token(self.dex, self.db.token0)
            self.token1 = token(self.dex, self.db.token1)
        self.amarket = pyserum.market.AsyncMarket(asolana, market_state)

    #def logs(self, fromBlock=None, toBlock=None, **kwparams):
        # the available api is to walk txs backward based on account address. might check how this looks for the requests, asks, bids, events, and market accounts.
        # solana.getSignaturesForAddress()

        # this seems to basically mean parsing the binary parameters passed to the programs


    async def trade_0to1(self, keypair, amt, post_only = True, immediate_or_cancel = False):
        return self.trade(keypair, False, amt, post_only, immediate_or_cancel)
    async def trade_1to0(self, keypair, amt, post_only = True, immediate_or_cancel = False):
        return self.trade(keypair, True, amt, post_only, immediate_or_cancel)

    async def trade(self, keypair, trade_1to0 : bool, amt, post_only = True, immediate_or_cancel = False):
        pubkey = keypair.public_key
        if sell_quote_buy_bid:
            side = pyserum.enums.Side.SELL
        else:
            side = pyserum.enums.Side.BUY
        if immediate_or_cancel:
            if post_only:
                raise NotImplementedError('IOC post_only')
            type = pyserum.enums.OrderType.IOC
        elif post_only:
            type = pyserum.enums.OrderType.POST_ONLY
        else:
            type = pyserum.enums.OrderType.LIMIT

    async def pump(self, commitment = 'processed'):
        pair = self
        class Subscr:
            subscrs = {}
            def __init__(self, ws, name, decoder):
                self.name = name
                self.addr = getattr(pair.market.state, name)()
                self.decoder = decoder
                self.data = None
                self.slot = None
            async def __aenter__(self):
                await ws.account_subscribe(self.addr, commitment, 'base64')
                self.id = (await ws.recv()).result
                while type(self.id) is not int:
                    self.id = (await ws.recv()).result
                Subscr.subscrs[self.id] = self
                return self
            async def __aexit__(self, *params):
                await ws.account_unsubscribe(self.id)
                del Subscr.subscrs[self.id]
                del self.id
            @staticmethod
            def parse(rawstr):
                obj = json.loads(rawstr)
                params = obj['params']
                result = params['result']
                slot = result['context']['slot']
                value = result['value']
                addr = value['owner']
                id = params['subscription']
                data = base64.decodebytes(value['data'][0].encode())
                subscr = Subscr.subscrs[id]
                subscr.last_data = subscr.data
                subscr.last_slot = subscr.slot
                subscr.data = subscr.decoder(data)
                subscr.slot = slot
                return subscr
            @staticmethod
            async def next():
                raw_event = await websockets.legacy.client.WebSocketClientProtocol.recv(ws)
                return Subscr.parse(raw_event)
        def decode_orderbook(bytes):
            return pyserum.market.market.OrderBook.from_bytes(pair.market.state, bytes)

        async with (
                WSClient(WS_API) as ws,
                Subscr(ws, 'bids', decode_orderbook) as bids,
                Subscr(ws, 'asks', decode_orderbook) as asks,
                Subscr(ws, 'request_queue', pyserum.market.market.decode_request_queue) as requests,
                Subscr(ws, 'event_queue', pyserum.market.market.decode_event_queue) as events
            ):

            # fill enough initial data to start forming orderbooks
            while await Subscr.next() not in (bids, asks):
                pass

            mark_slot = None

            last_price = None
            while True:
                event = await Subscr.next()
                #if event.last_slot == event.slot:
                #    continue
                #print(event.name, event.slot)
                if event in (bids, asks) and bids.slot == asks.slot:
                    price = (bids.data.get_l2(1)[0].price, asks.data.get_l2(1)[0].price)
                    if price != last_price:
                        now = time.time()
                        if mark_slot is None or now - mark_now > 60:
                            mark_slot = bids.slot
                            mark_blocktime = solana.get_block_time(bids.slot)['result']
                            mark_now = now
                            ts = mark_blocktime
                        else:
                            ts = int(now - mark_now + mark_blocktime)
                        ts = datetime.datetime.utcfromtimestamp(ts).isoformat()
                        print(ts, bids.slot, str(self.db), price[0], '-', price[1])
                        last_price = price


    #async def stream(self):
    #    async with WSCLient(WS_API) as ws:
    #        await ws.program_subscribe(str(self.db.addr))
    #        resp = ws.recv()
    #        while True:
    #            resp = await websockets.legacy.client.WebSocketClientProtocol.recv(websocket)
    #            resp = json.loads(resp)
    #            pubkey = resp['params']['result']['value']['pubkey']
