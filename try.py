#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging

## for debugging connection errors
#import websocket
#websocket.enableTrace(True)

### TO DOWNLOAD TRADES FROM PREVIOUS MONTHS
### WE MUST USE Market.blockchain.rpc.get_trade_history_by_sequence(base, quote, sequence, starttime, limit)
####### each item of result has a "sequence" key.  a stoptime can be passed for the first.
#### based on the sequence desired to start from

# for quick fix, record earliest "sequence", and keep moving backwards, for past history
############# it looks like the last item is the earliest.
# i think self.market.trades calles get_trade_history under the hood,
# which returns only 100 trades.  then get_trade_history_by_sequence can get the rest.
# from bitshares.utils import formatTime # formats to unix timestamp
# base = self.market['base']['symbol']
# quote = self.market['quote']['symbol']
# trades = self.market.blockchain.rpc.get_trade_history(base, quote, formatTime(endtime), formatTime(starttime), 100)
# endsequence = trades[-1]['sequence'] # fields are strings and are 'sequence', 'date' (iso), 'price', 'amount', 'value', 'type' ('sell'/'buy'), 'side1_account_id', 'side2_account_id'; data is latest-to-earliest.
# nexttrades = self.market.blockchain.rpc.get_trade_history_by_sequence(base, quote, endsequence, formatTime(starttime), 100)

# for quick fix, record earliest sequence, and keep moving backwards, for past history
# could latest sequence could come from on_tx =S also trades gives it

from bitshares import BitShares
from bitshares.asset import Asset
from bitshares.amount import Amount
from bitshares.account import Account
from bitshares.price import Price, Order
from bitshares.market import Market
from bitshares.notify import Notify
from bitsharesbase.operations import getOperationClassForId,getOperationNameForId
import bitshares.utils as bitsharesutils

import grapheneapi.exceptions

import datalad
import datalad.api
from datalad.support.locking import lock_if_check_fails
datalad.cfg.set('datalad.repo.backend', 'SHA3_512E', where='override') # otherwise it defaults to MD5E

from delimitedfile import delimitedfile

from datetime import datetime,timedelta
import os

# a proposal exists to simply front the api, and not store a copy of the history.
# this would make for slow calculation over the history

class filebacked:
    def __init__(self, path, default=None):
        self.path = os.path.join(path,'')
    def lock(self):
        return lock_if_check_fails(check=False,lock_path=self.path)
    def __contains__(self, item):
        return os.path.exists(self.path + item)
    def __getitem__(self, item):
        try:
            with open(self.path + item, 'r') as file:
                return file.read()
                self.data = file.read()
        except FileNotFoundError:
            return None
    def __setitem__(self, item, value):
        with open(self.path + item, 'w') as file:
            file.write(str(value))
        return value
    def __delitem__(self, item):
        os.unlink(self.path + item)

class datechunk:
    def __init__(self, time=None, id=None):
        if time == None:
            if id != None:
                time = datetime.fromtimestamp(int(id))
            else:
                time = datetime.now()
            
        self.time = datetime(time.year, time.month, 1)

    def id(self):
        return int(self.time.timestamp())

    def name(self):
        return f'{self.time:%Y-%m}'

    def previous(self):
        year = self.time.year
        month = self.time.month - 1
        if month == 0:
            year = year - 1
            month = 12
        return datechunk(datetime(year, month, 1))

    def next(self):
        year = self.time.year
        month = self.time.month + 1
        if month == 13:
            year = year + 1
            month = 1
        return datechunk(datetime(year, month, 1))

class history:
    def __init__(self, market):
        self.market = market
        base = market["base"]["symbol"]
        quote = market["quote"]["symbol"]
        self.name = base + '-' + quote
        log.warning(self.name)
        path = 'data/' + self.name
        self.files = filebacked(path)
        self.dataset = datalad.api.Dataset(path)
        if not self.dataset.is_installed():
            datalad.api.create(path=path,dataset='.')
            self.dataset.repo.set_gitattributes([
                ('start-seconds', {'annex.largefiles': '(exclude=*)'}),
                ('start-sequence', {'annex.largefiles': '(exclude=*)'}),
                ('end-seconds', {'annex.largefiles': '(exclude=*)'}),
                ('end-sequence', {'annex.largefiles': '(exclude=*)'}),
            ])
            with self.files.lock():
                self.files['.gitignore'] = 'latest.csv'
        with self.files.lock():
            current_chunk = datechunk(time=datetime.now())
            end = self.files['end-seconds']
            if end != None:
                chunk = datechunk(id=end)
                while chunk.id() != current_chunk.id():
                    chunk = chunk.next()
                    self.download_chunk_needs_lock(chunk)
                chunk = datechunk(id=self.files['start-seconds'])
                chunk = chunk.previous()
                self.download_chunk_needs_lock(chunk)
            else:
                self.download_chunk_needs_lock(current_chunk)
                self.download_chunk_needs_lock(current_chunk.previous())
        self.dataset.save()
    def folder_for_chunk(self, chunk):
        return f'{self.dataset.path}/trades/'
    def filepath_for_chunk(self, chunk):
        today_chunk = datechunk(time=datetime.now())
        if today_chunk.id() == chunk.id():
            os.makedirs(self.dataset.path + '/trades/', exist_ok=True)
            return self.dataset.path + '/trades/latest.csv'
        path = self.folder_for_chunk(chunk)
        os.makedirs(path, exist_ok=True)
        return path + chunk.name() + '.csv'
    def get(self, chunk):
        return delimitedfile(self.filepath_for_chunk(chunk))

    def download_chunk_needs_lock(self, chunk = datechunk(datetime.now()).previous()):
        today_chunk = datechunk(time=datetime.now())
        starttime = bitsharesutils.formatTime(chunk.time)
        stoptime = bitsharesutils.formatTime(datetime.fromtimestamp(chunk.next().time.timestamp() - 1))

        filepath = self.filepath_for_chunk(chunk)
        keepgoing = True
        try:
            log.warning(f'Writing {filepath} {starttime}-{stoptime}...')
            #if chunk.id() == today_chunk.id():
            if True:
                with delimitedfile(filepath) as file:
                    file.clear()
                    count = 0
                    last_sequence = None
                    while keepgoing:
                        if last_sequence is None:
                            history = self.market.blockchain.rpc.get_trade_history(self.market['base']['symbol'], self.market['quote']['symbol'], stoptime, starttime, 100)
                        else:
                            history = self.market.blockchain.rpc.get_trade_history_by_sequence(self.market['base']['symbol'], self.market['quote']['symbol'], last_sequence, starttime, 100)
                        #last_sequence = history[-1]['sequence']
                        #history = self.market.trades(limit=1000000,start=starttime,stop=stoptime)
                        keepgoing = False;
                        for trade in history:
                            base_amount = trade['value']
                            quote_amount = trade['amount']
                            timestamp = bitsharesutils.formatTimeString(trade['date']).timestamp()
                            #if last_sequence is not None and trade['sequence'] >= last_sequence:
                            #    continue
                            #if trade['time'] < stoptime:
                            #    stoptime = trade['time']
                            file.append(f"{timestamp},{trade['type']},{base_amount},{quote_amount},{trade['sequence']}")
                            last_sequence = trade['sequence']
                            keepgoing = True
                            count = count + 1
                        if keepgoing:
                            log.warning(f'Wrote {count} trades ...')
                if not 'start-sequence' in self.files:
                    self.files['start-sequence'] = last_sequence
            #elif chunk.id() < today_chunk.id():
            #    # stub
            #    if not 'start-seconds' in self.files or chunk.next().id() == int(self.files['start-seconds']):
            #        self.files['start-seconds'] = chunk.id()
            #        self.files['start-sequence'] = last_sequence
            #    if not 'end-seconds' in self.files or chunk.previous().id() == int(self.files['end-seconds']):
            #        self.files['end-seconds'] = chunk.id()
            return True
        except FileExistsError:
            return False

          

log = logging.getLogger()
log.setLevel(logging.DEBUG) # this doesn't seem to work?  but info messages come out of datalad

import sys
sys.stdout.flush()
sys.stderr.flush()

## IF IT CONNECTS TO THE WRONG NODE, YOU CAN CHANGE DEFAULT NODE WITH
## THE CLI TOOL `uptick`: `uptick set node <url>`
## YOU CAN SEE WORKING NODES IN THE JS UI, e.g. at https://develop.bitshares.org/
#bitshares = BitShares(node="wss://node.bitshares.eu", num_retries=-1)
bitshares = BitShares(node='wss://api.bts.mobi/ws', num_retries=-1)
# connect is an internal function.  it expects the node passed.
#print('about-toconnect')
#bitshares.connect() # node= is not being passed here.  it defaults to node.bitshares.eu, which is down.
#print('connection-done')

#def get_all_assets():
#    assets = {}
#    lastAsset = None
#    while True:
#        asset_chunk = bitshares.rpc.list_assets(lastAsset,64)
#        if 1 >= len(asset_chunk):
#            break
#        for asset in asset_chunk:
#            assets[asset['symbol']] = asset
#        lastAsset = asset_chunk[-1]

markets = {}

def on_tx(data):
    #print(data)
    for operation in data["operations"]:
        if getOperationNameForId(operation[0]) == 'limit_order_create':
            base = operation[1]['amount_to_sell']['asset_id']
            quote = operation[1]['min_to_receive']['asset_id']
            if base > quote:
                base, quote = quote, base
            basequote = base + '/' + quote
            if not basequote in markets:
                market = history(Market(basequote, blockchain_instance=bitshares))
                markets[basequote] = market

                #print("base=%s\n" % market.get("base"))
                #print("quote=%s\n" % market.get("quote"))
                #
                #ticker = market.ticker()
                #print("lowestAsk=%s\n" % ticker["lowestAsk"])
                #print("highestBid=%s\n" % ticker["highestBid"])
                #
                #volume = market.volume24h()
                #base = market["base"]["symbol"]
                #quote = market["quote"]["symbol"]
                #
                #print("volume24h %s=%s" %(base,volume[base]))
                #print("volume24h %s=%s" %(quote,volume[quote]))

                ## default ranges:
                ## stop = datetime.now()
                ## start = stop - timedelta(hours=24)
                #history = market.trades(limit=25,start=None,stop=None)
                #for trade in history:
                #        print(type(trade))
                #        print(trade)
                #        print(trade.json())

from random import shuffle
nodes = 'wss://node.bitshares.eu wss://nexus01.co.uk/ws wss://dex.iobanker.com/ws wss://ws.gdex.top wss://api.weaccount.cn wss://api.bts.mobi/ws wss://btsws.roelandp.nl/ws wss://api.bitshares.bhuz.info/ws wss://api.btsgo.net/ws wss://bts.open.icowallet.net/ws wss://freedom.bts123.cc:15138/ wss://bitshares.bts123.cc:15138/ wss://api.bts.ai wss://bts-seoul.clockwork.gr wss://api.61bts.com wss://api.dex.trading/ wss://api.bitshares.org/ws wss://us.api.bitshares.org/ws wss://asia.api.bitshares.org/ws wss://citadel.li/node wss://api-bts.liondani.com/ws wss://public.xbts.io/ws wss://cloud.xbts.io/ws wss://node.xbts.io/ws wss://api.gbacenter.org/ws wss://api.cnvote.vip:888/ wss://singapore.bitshares.im/ws wss://newyork.bitshares.im/ws wss://node.testnet.bitshares.eu wss://testnet.dex.trading/ wss://testnet.xbts.io/ws wss://testnet.bitshares.im/ws'.split(' ')
shuffle(nodes)
nodes[0:0] = ['ws://127.0.0.1:8090']
print('nodes', nodes)
for node in nodes:
    try:
        print('attempt', node)
        bitshares = BitShares(node=node, num_retries=2)
        bitshares.info()
        #bitshares.connect()
        break
    except grapheneapi.exceptions.NumRetriesReached as exception:
        print('NumRetriesReached')
        bitshares = exception
if bitshares is Exception:
    raise bitshares

notify = Notify(bitshares=bitshares, markets=list(), on_tx=on_tx, on_market=None)
notify.listen()



block=bitshares.rpc.get_block(1)
print(block)

market = Market("BTC:BTS", blockchain_instance=bitshares)
history(market)

async def test_orderbook(market, place_order):
    orderbook = await market.orderbook()
    assert "bids" in orderbook
    assert "asks" in orderbook
    assert len(orderbook["bids"]) > 0


async def test_get_limit_orders(market, place_order):
    orderbook = await market.get_limit_orders()
    assert len(orderbook) > 0
    assert isinstance(orderbook[0], Order)

async def test_core_quote_market(bitshares, assets, bitasset):
    market = await Market(
        "{}:USD".format(bitasset.symbol), blockchain_instance=bitshares
    )
    await market.core_quote_market()

async def test_core_base_market(bitshares, assets, bitasset):
    market = await Market(
        "USD:{}".format(bitasset.symbol), blockchain_instance=bitshares
    )
    await market.core_base_market()
