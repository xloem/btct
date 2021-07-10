#!/usr/bin/env python3

from web3 import Web3
from web3.auto import w3 as w3_local
w3_cloud = Web3(Web3.HTTPProvider('https://cloudflare-eth.com'))
try:
    if w3_local.isConnected() and not w3_local.eth.is_syncing():
        w3 = w3_local
    else:
        raise Exception()
except:
    w3 = w3_cloud
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
    

tokenaddrs = {
    'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
    'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
}
accaddrs = {
    'Uniswap V2: Dai 2': '0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11'
}

import abi

# filters can be polled synchronously or asynchronously, see web3py docs
# filters only work on local nodes
#    daicontract.events.Transfer.createFilter(fromBlock='latest').get_all_entries()
# it looks like filters are likely to work if a contract is made with no address
# but it's possible work with the internals may be needed (the log_entry_formatter property)
#    if events that don't match the abi throw an error, halting filtering

# getLogs works on remote and local nodes, but appears to need a contract address

uniswapv2ct = w3.eth.contract(address=abi.uniswapv2_factory_addr,abi=abi.uniswapv2_factory)
pairs = uniswapv2ct.events.PairCreated.getLogs(fromBlock=w3.eth.block_number-127,toBlock='latest')
print(len(pairs),'recent new pairs')
for pair in pairs:
    token0 = w3.eth.contract(address=pair.args.token0, abi=abi.erc20)
    token1 = w3.eth.contract(address=pair.args.token1, abi=abi.erc20)
    print(f'{token0.functions.symbol().call()}-{token1.functions.symbol().call()}')

daicontract = w3.eth.contract(address=tokenaddrs['DAI'],abi=abi.erc20)
somelogs = daicontract.events.Transfer.getLogs(fromBlock=daicontract.web3.eth.block_number-127,toBlock='latest')

