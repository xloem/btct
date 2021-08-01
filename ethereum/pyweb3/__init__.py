import web3
import eth_abi
import requests
import asyncio
from decimal import Decimal
from web3 import Web3, _utils as utils, middleware
import web3.gas_strategies.time_based

from web3.auto.websocket import w3 as w3_websocket
from web3.auto import w3 as w3_local
w3_cloud = Web3(Web3.HTTPProvider('https://cloudflare-eth.com'))

try:
    if w3_websocket.isConnected():
        w3 = w3_websocket
    elif w3_local.isConnected():
        w3 = w3_local
    else:
        raise Exception('local not connected')
    if w3.eth.is_syncing():
        raise Exception('local still syncing')
except Exception as e:
    w3 = w3_cloud
    print(str(e),'-> using a limited cloud provider instead.  note this is likely broken.')

while True:
    try:
        if w3.isConnected():
            print('connected')
            break
    except Exception:
        pass
    print('not connected yet, waiting...')
    import time
    time.sleep(0.5)

wei2eth = Decimal(10) ** -18
eth2wei = Decimal(10) ** 18
gwei2eth = Decimal(10) ** -9
eth2gwei = Decimal(10) ** 9
wei2gwei = Decimal(10) ** -(18 - 9)
gwei2wei = Decimal(10) ** (18 - 9)

# changing the deadline doesn't seem to change the gas price with below code
# additionally it doesn't seem to speed up on second request

#w3.middleware_onion.add(middleware.time_based_cache_middleware)
#w3.middleware_onion.add(middleware.latest_block_based_cache_middleware)
#w3.middleware_onion.add(middleware.simple_cache_middleware)
#
#def set_gas_deadline(secs, likelihood = 1.0, sample_last_blocks = 120, bias_towards_recent = True):
#    strategy = web3.gas_strategies.time_based.construct_time_based_gas_price_strategy(
#        max_wait_seconds = secs,
#        sample_size = sample_last_blocks,
#        probability = int(.5 + likelihood * 100),
#        weighted = bias_towards_recent
#    )
#    w3.eth.set_gas_price_strategy(strategy)
#
#def gas_price():
#    return w3.eth.generate_gas_price()

def blockfrom(fromBlock):
    block = fromBlock #kwparams.get('fromBlock')
    if block in (None, 'earliest'):
        block = 0
    if hasattr(w3, 'block_limit'):
        block = max(block, w3.block_limit + w3.eth.block_number)
    return block

def blockto(toBlock):
    block = toBlock #kwparams.get('toBlock')
    if block in (None, 'latest'):
        block = w3.eth.block_number
    return block

def wrap_neterrs(func, method = 'call', **kwparams):
    count = 0
    if kwparams.get('fromBlock',-1) is None and hasattr(func.web3, 'block_limit'):
        kwparams['fromBlock'] = func.web3.eth.block_number + func.web3.block_limit
    while True:
        try:
            return getattr(func, method)(**kwparams)
        except web3.exceptions.BadFunctionCallOutput as e:
            if type(e.__cause__) is eth_abi.exceptions.InsufficientDataBytes:
                if ' 0 ' in e.__cause__.args[0] and count < 512:
                    print('expecting a retryable insufficient data error:', e, e.__cause__, count, '/', 512)
                    count += 1
                    continue
            raise web3.exceptions.SolidityError(*e.args)
        except requests.exceptions.HTTPError as e:
            print('network error', e)
            continue
        except requests.exceptions.ConnectionError as e:
            print('network error', e)
            continue
        #except asyncio.exceptions.TimeoutError as e:
        #    if hasattr(func.web3.provider, 'websocket_timeout'):
        #        func.web3.provider.websocket_timeout *= 2
        #        print('request timed out; timeout lengthened to ' + str(func.web3.provider.websocket_timeout))
        #        continue
        #    raise
        except ValueError as e:
            if type(e.args[0]) is dict:
                count += 1
                if e.args[0]['code'] == -32000:
                    print('expecting a retryable network error, code -32000:', e, count)
                    continue
                if e.args[0]['code'] == -32602:
                    print('expecting an argument error stemming from a retryable network error, code -32602:', e, count)
                    continue
                if e.args[0]['code'] == -32600 and ' 128 ' in e.args[0]['message']:
                    print('warning: limited to past 128 blocks')
                    kwparams['fromBlock'] = func.web3.eth.block_number - 128
                    func.web3.block_limit = -128
                    continue
            raise e
        except OverflowError as e:
            raise web3.exceptions.SolidityError(*e.args)
