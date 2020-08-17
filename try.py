#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging

### TO DOWNLOAD TRADES FROM PREVIOUS MONTHS
### WE MUST USE blockchain.rpc.get_trade_history_by_sequence
#### based on the sequence desired to start from

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

import datalad
import datalad.api
from datalad.support.locking import lock_if_check_fails
datalad.cfg.set('datalad.repo.backend', 'SHA3_512E', where='override') # otherwise it defaults to MD5E

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
        log.warn(self.name)
        path = 'data/' + self.name
        self.files = filebacked(path)
        self.dataset = datalad.api.Dataset(path)
        if not self.dataset.is_installed():
            datalad.api.create(path=path,dataset='.')
            self.dataset.repo.set_gitattributes([
                ('start', {'annex.largefiles': '(exclude=*)'}),
                ('end', {'annex.largefiles': '(exclude=*)'}),
            ])
            with self.files.lock():
                self.files['.gitignore'] = 'latest.csv'
        with self.files.lock():
            current_chunk = datechunk(time=datetime.now())
            end = self.files['end']
            if end != None:
                chunk = datechunk(id=end)
                while chunk.id() != current_chunk.id():
                    chunk = chunk.next()
                    self.download_chunk_needs_lock(chunk)
                chunk = datechunk(id=self.files['start'])
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
    def download_chunk_needs_lock(self, chunk = datechunk(datetime.now()).previous()):
        today_chunk = datechunk(time=datetime.now())
        starttime = chunk.time
        stoptime = datetime.fromtimestamp(chunk.next().time.timestamp() - 1)

        filepath = self.filepath_for_chunk(chunk)
        keepgoing = True
        try:
            log.warn(f'Writing {filepath} {starttime}-{stoptime}...')
            with open(filepath, 'w') as f:
                count = 0
                last_sequence = None
                while keepgoing:
                    # appears to give most recent trades first
                
                    history = self.market.trades(limit=1000000,start=starttime,stop=stoptime)
                    keepgoing = False;
                    for trade in history:
                        # trade.value is the base amount
                        # trade.amount is the quote amount
                        if last_sequence is not None and trade['sequence'] >= last_sequence:
                            continue
                        if trade['time'] < stoptime:
                            stoptime = trade['time']
                        f.write(f"{int(trade['time'].timestamp())},{trade['type']},{trade['value']},{trade['amount']},{trade['sequence']}\n")
                        last_sequence = trade['sequence']
                        keepgoing = True
                        count = count + 1
                    if keepgoing:
                        f.flush()
                        log.warn(f'Wrote {count} trades ...')
            if chunk.id() < today_chunk.id():
                if not 'start' in self.files or chunk.previous().id() == int(self.files['start']):
                    self.files['start'] = chunk.id()
                if not 'end' in self.files or chunk.next().id() == int(self.files['end']):
                    self.files['end'] = chunk.id()
            return True
        except FileExistsError:
            return False

          

log = logging.getLogger()
log.setLevel(logging.DEBUG) # this doesn't seem to work?  but info messages come out of datalad

import sys
sys.stdout.flush()
sys.stderr.flush()

bitshares = BitShares(node="wss://node.bitshares.eu", num_retries=-1)
bitshares.connect()

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

notify = Notify(bitshares=bitshares, markets=list(), on_tx=on_tx)
notify.listen()



block=bitshares.rpc.get_block(1)
print(block)

market = Market("BTC:BTS", blockchain_instance=bitshares)

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
