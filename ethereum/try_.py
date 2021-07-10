#!/usr/bin/env python3

from web3.auto import w3
if not w3.isConnected():
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider('https://cloudflare-eth.com'))

tokenaddrs = {
    'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
    'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
}
accaddrs = {
    'Uniswap V2: Dai 2': '0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11'
}

import abi

#w3 = Web3(Web3.HTTPProvider

