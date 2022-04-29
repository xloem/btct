from solana.exceptions import SolanaRpcException
from solana.publickey import b58decode, b58encode, PublicKey
from solana.rpc.websocket_api import connect as WSClient
import websockets.legacy.client
from solana.rpc.api import Client, types as solana_types
from solana.rpc.async_api import AsyncClient
from solana.rpc.core import RPCException, UnconfirmedTxError
from solana.transaction import AccountMeta, Transaction, TransactionInstruction
import solana.system_program as system_program
from spl.token.client import Token as TokenClient
from spl.token.async_client import AsyncToken as TokenAsyncClient
from spl.token.constants import TOKEN_PROGRAM_ID, WRAPPED_SOL_MINT
import spl.token.instructions
import spl
import pyserum
import pyserum.connection

import pyserum.open_orders_account, pyserum._layouts.open_orders

import asyncio, base64, collections, datetime, json, requests, time

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
#API = 'api.mainnet-beta.solana.com' # this server appears to have program account enumeration disabled
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

import construct

SYNC_NATIVE_INSTRUCTION_LAYOUT = construct.Struct("instruction_type" / construct.Int8ul)
SYNC_NATIVE = 17

def sync_native(pubkey, program_id = TOKEN_PROGRAM_ID) -> TransactionInstruction:
    data = SYNC_NATIVE_INSTRUCTION_LAYOUT.build(dict(instruction_type=SYNC_NATIVE))
    return TransactionInstruction(
        keys=[
            AccountMeta(pubkey=pubkey, is_signer=False, is_writable=True),
        ],
        program_id = program_id,
        data = data
    )


class dex:
    def __init__(self, program_id = PROGRAM_ID, name = 'SerumV3'):
        self.db = db.dex(program_id)
        if not self.db:
            self.db = db.dex.ensure(program_id, name)
    def tokens(self):
        for token_mint in pyserum.connection.get_token_mints():
            yield token(token_mint.address._key)
    def pairs(self):
        live_markets = {market.address for market in pyserum.connection.get_live_markets()}
        for _pair in db.pair(dex=self.db.addr):
            live_markets.discard(str(_pair.addr))
            yield pair(self, _pair)
        for live_market in live_markets:
            yield pair(self, live_market)
    async def awatch_pairs(self):
        pairs = set()
        #for _pair in db.pair(dex=self.db.addr):
        #    live_markets.discard(str(_pair.addr))
        #    pairs.add(str(_pair.addr))
        #    yield pair(self, _pair)
        async with WSClient(WS_API) as ws:
            ws.max_size = 1024*1024*64
            await ws.program_subscribe(str(self.db.addr))
            subscr_resp = await ws.recv()
            while True:
                event = await websockets.legacy.client.WebSocketClientProtocol.recv(ws)
                event = json.loads(event)
                addr = event['params']['result']['value']['pubkey']
                if addr not in pairs:
                    pairs.add(addr)
                    try:
                        yield pair(self, addr)
                    except:
                        continue

    #def pair(self, token0, token1):
    #    tokens=[token0,token1]

    def balance(self, address):
        return solana.get_balance(address, commitment = 'processed')['result']['value']

    def transfer(self, keypair, destination_address, amount):
       instructions = [
               system_program.transfer(system_program.TransferParams(from_pubkey=keypair.public_key, to_pubkey = PublicKey(destination_address), lamports=amount)),
       ]
       txn = Transaction().add(*instructions)
       return solana.send_transaction(txn, keypair)['result']

    def open_orders_accounts_for_owner(self, addr, commitment = 'processed'):
        resp = solana.get_program_accounts(
            str(self.db.addr),
            commitment,
            'base64',
            None,
            pyserum._layouts.open_orders.OPEN_ORDERS_LAYOUT.sizeof(),
            [
                solana_types.MemcmpOpts(
                    offset=5 + 8 + 32, # padding + account flag + market pubkey
                    bytes=str(addr),
                )
            ]
        )
        # result has .address, .market, .base_token_total, .quote_token_total
        return pyserum.open_orders_account.OpenOrdersAccount._process_get_program_accounts_resp(resp)


class token:
    def __new__(cls, dexobj, db_or_addr):
        if type(db_or_addr) is db.Table.Row:
            addr = db_or_addr.addr
        else:
            addr = db_or_addr
        if cls is token and str(addr) == str(WRAPPED_SOL_MINT):
            cls = wrapped_sol
        return super().__new__(cls)
    def __init__(self, dexobj, db_or_addr):
        if type(db_or_addr) is db.Table.Row:
            dbobj = db_or_addr
            addr = dbobj.addr
        else:
            dbobj = None
            addr = db_or_addr
        self.dex = dexobj
        self.db = dbobj
        if not self.db:
            self.db = db.token(addr)
        if not self.db:
            #import pdb; pdb.set_trace()
            saddr = b2hex(addr)
            symbol = token.addr2symbol(saddr)
            decimals = pyserum.utils.get_mint_decimals(solana, b2hex(saddr))
            self.db = db.token.ensure(addr, symbol, decimals)
    @staticmethod
    def addr2symbol(addr):
        saddr = str(addr)
        symbol = None
        symbol = TOKEN_NAMES_BY_ADDRESSES.get(addr)
        if symbol is None:
            resp = requests.get('https://github.com/solana-labs/token-list/raw/main/src/tokens/solana.tokenlist.json', stream = True)
            baddr = saddr.encode()
            lines = []
            found = False
            START_LINE = b'    {'
            END_LINE = b'    }'
            for line in resp.iter_lines():
                lines.append(line)
                if baddr in line:
                    found = True
                elif line == START_LINE:
                    found = False
                    lines = lines[-1:]
                elif line.startswith(END_LINE):
                    lines[-1] = END_LINE
                    if found:
                        break
            if found:
                token_data = json.loads(b''.join(lines).decode())
                symbol = token_data['symbol']
        if symbol is None:
            import pdb; pdb.set_trace()
            symbol = saddr
        return symbol


    def owner(self, account):
        client = TokenClient(solana, program_id=TOKEN_PROGRAM_ID, pubkey=PublicKey(self.db.addr), payer=None)
        token_info = client.get_account_info(PublicKey(account))
        return str(token_info.owner)
    def balance(self, account):
        value = solana.get_token_account_balance(account)['result']['value']
        # value['decimals']
        return int(value['amount'])
    def account(self, keypair):
        accts = solana.get_token_accounts_by_owner(keypair.public_key, solana_types.TokenAccountOpts(mint=str(self.db.addr)), commitment='processed')['result']['value']
        if len(accts) == 0:
            client = TokenClient(solana, program_id=PublicKey(TOKEN_PROGRAM_ID), pubkey=PublicKey(self.db.addr), payer=keypair)
            print(f'Creating {self.db.symbol} account for {keypair.public_key} ...')
            while True:
                try:
                    acct = client.create_associated_token_account(keypair.public_key)
                    break
                except RPCException as exc:
                    data = exc.args[0]['data']
                    if data['unitsConsumed'] == 0:
                        if data['err'] == 'BlockhashNotFound':
                            continue
                        elif 'already in use' in str(data['err']):
                            break
                    raise
                except UnconfirmedTxError:
                    print('no confirmation yet ...')
                    return self.account(keypair)
            print(f'Created {acct}.')
            return acct
        else:
            return accts[0]['pubkey']

class wrapped_sol(token):
    def balance(self, account):
        owner_balance = self.dex.balance(self.owner(account))
        solana_balance = self.dex.balance(account)
        if solana_balance != 0:
            print('Warning:', solana_balance, 'unwrapped lamports are held by', account)
        wrapped_balance = super().balance(account)
        if wrapped_balance != 0:
            print('Warning:', wrapped_balance, 'lamports are already wrapped in', account)
        return owner_balance + solana_balance + wrapped_balance
    def wrap(self, keypair, deposit_amount = None, token_account = None):
        instructions = []

        if token_account is None:
            token_account = self.account(keypair.public_key)

        if deposit_amount is not None:
            instructions.append(
               system_program.transfer(system_program.TransferParams(from_pubkey=keypair.public_key, to_pubkey = PublicKey(token_account), lamports=deposit_amount))
            )

        instructions.append(sync_native(token_account, program_id = TOKEN_PROGRAM_ID))

        txn = Transaction().add(*instructions)
        return solana.send_transaction(txn, keypair)['result']
    def unwrap(self, keypair, withdraw_to_addr = None, token_account = None):
        if token_account is None:
            token_account = self.account(keypair.public_key)
        instructions = []
        if withdraw_to_addr is None:
            withdraw_to_addr = keypair.public_key
        instructions.append(
            spl.token.instructions.close_account(spl.token.instructions.CloseAccountParams(
                program_id = PublicKey(TOKEN_PROGRAM_ID),
                owner = keypair.public_key,
                account = PublicKey(token_account),
                dest = PublicKey(withdraw_to_addr)
            ))
        )
        txn = Transaction().add(*instructions)
        return solana.send_transaction(txn, keypair)['result']

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
                self.market = pyserum.market.Market.load(solana, PublicKey(addr))
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
            market_state = pyserum.market.state.MarketState(parsed_market, PublicKey(str(self.dex.db.addr)), self.db.token0.decimals, self.db.token1.decimals)
            self.market = pyserum.market.Market(solana, market_state)
            self.token0 = token(self.dex, self.db.token0)
            self.token1 = token(self.dex, self.db.token1)
        self.amarket = pyserum.market.AsyncMarket(asolana, market_state)

    #def logs(self, fromBlock=None, toBlock=None, **kwparams):
        # the available api is to walk txs backward based on account address. might check how this looks for the requests, asks, bids, events, and market accounts.
        # solana.getSignaturesForAddress()

        # this seems to basically mean parsing the binary parameters passed to the programs


    def mintrade0(self):
        return self.amarket.state.base_lot_size()
    def mintrade1(self):
        return self.amarket.state.quote_lot_size()

    async def atrade_0to1(self, keypair, amt, price, post_only = True, immediate_or_cancel = False, token_account = None):
        return await self.atrade(keypair, False, amt, price, post_only, immediate_or_cancel, token_account)
    async def atrade_1to0(self, keypair, amt, price, post_only = True, immediate_or_cancel = False, token_account = None):
        return await self.atrade(keypair, True, amt, price, post_only, immediate_or_cancel, token_account)

    async def atrade(self, keypair, trade_1to0 : bool, amt, price, post_only = True, immediate_or_cancel = False, token_account = None):
        if trade_1to0:
            side = pyserum.enums.Side.BUY
            if token_account is None:
                token_account = PublicKey(self.token1.account(keypair))
            raise Exception('have not set amt yet for buy')
        else:
            side = pyserum.enums.Side.SELL
            if token_account is None:
                token_account = PublicKey(self.token0.account(keypair))
            if amt < self.amarket.state.base_lot_size():
                raise Exception('minimum lot size is ' + str(self.amarket.state.base_lot_size()))
            amt /= 10**self.db.token0.decimals
        if immediate_or_cancel:
            if post_only:
                raise NotImplementedError('IOC post_only')
            type = pyserum.enums.OrderType.IOC
        elif post_only:
            type = pyserum.enums.OrderType.POST_ONLY
        else:
            type = pyserum.enums.OrderType.LIMIT
        while True:
            try:
                resp = await self.amarket.place_order(
                    owner = keypair, 
                    payer = token_account,
                    side = side,
                    limit_price = price,
                    max_quantity = amt,
                    order_type = type,
                )
                return resp['result']
            except SolanaRpcException as e:
                raise e
                print('retrying, got exception:', repr(e.error_msg))
            except RPCException as e:
                if e.args[0]['data']['err'] == 'BlockhashNotFound':
                    print('retrying, got exception:', repr(e.args))
                else:
                    raise
        #raise NotImplementedError('oops did not finish trade code yet!')

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
            ws.max_size = 1024*1024*64

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
                    bids_l2 = bids.data.get_l2(1)
                    asks_l2 = asks.data.get_l2(1)
                    price = (bids_l2[0].price if len(bids_l2) else None, asks_l2[0].price if len(asks_l2) else None)
                    if price != last_price:
                        now = time.time()
                        if mark_slot is None or now - mark_now > 60:
                            mark_slot = bids.slot
                            while True:
                                mark_blocktime = solana.get_block_time(bids.slot)
                                if 'error' in mark_blocktime:
                                    if mark_blocktime['error']['code'] == -32004:
                                        continue
                                    raise Exception(mark_blocktime['error'])
                                mark_blocktime = mark_blocktime['result']
                                break
                            mark_now = now
                            ts = mark_blocktime
                        else:
                            ts = int(now - mark_now + mark_blocktime)
                        ts = datetime.datetime.utcfromtimestamp(ts).isoformat()
                        yield (self, ts, bids.slot, price[0], price[1])
                        #print(ts, bids.slot, str(self.db), price[0], '-', price[1])
                        last_price = price


    #async def stream(self):
    #    async with WSCLient(WS_API) as ws:
    #        await ws.program_subscribe(str(self.db.addr))
    #        resp = ws.recv()
    #        while True:
    #            resp = await websockets.legacy.client.WebSocketClientProtocol.recv(websocket)
    #            resp = json.loads(resp)
    #            pubkey = resp['params']['result']['value']['pubkey']
