import asyncio
from solana.rpc.websocket_api import connect
import pyserum

import websockets.legacy.client
import json

pids = [
    '9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin', # serum dex program v3 from atrix
    #'2n2dsFSgmPcZ8jkmBZLGUM2nzuFqcBGQ3JEEj6RJJcEg',
    #'6pr836RnCpXYGaBAbvEW8dQWXJem87511yeRTPYeCB9r',
    #'DnXyn8dAR5fJdqfBQciQ6gPSDNMQSTkQrPsR65ZF5qoW',
    #'HYv7pNgHkkBGxfrnCre2pMgLpWm7LJPKxiyZVytN5HrM',
    #'BgSk6jX9qn9HhDPuGYVrHbLAfXJjvaKZkZ9F3MG5sG52',
    #'9qvG1zUp8xF1Bi4m6UdRNby1BAAuaDrUxSpv4CmRRMjL',
    #'SwaPpA9LAaLfeLi3a68M4DjnLqgtticKg6CnyNwgAC8',
    #'SWPUnynS7FHA1koTbvmRktQgCDs7Tf4RkqwH19e2qSP',
    #'3Y5p67PMT1EEo8M37UVbUaV8Z33nnWL52BS5S5ThEsZf',
]

async def main():
    async with connect('ws://api.mainnet-beta.solana.com') as websocket:
        subscription_ids = []
        for pid in pids:
            await websocket.program_subscribe(pid)
            subscription_ids.append(await websocket.recv())
        pubkeys = set()
        while True:
            resp = await websockets.legacy.client.WebSocketClientProtocol.recv(websocket)
            resp = json.loads(resp)
            pubkey = resp['params']['result']['value']['pubkey']
            if pubkey not in pubkeys:
                pubkeys.add(pubkey)
                try:
                    await order_table(pubkey)
                    print(pubkey)
                except:
                    continue

#asyncio.run(main())

from pyserum.connection import get_live_markets, get_token_mints
print("tokens: ")
print(get_token_mints())
print("markets: ")
print(get_live_markets())
import asyncio
from pyserum.async_connection import async_conn
from pyserum.market import AsyncMarket


async def order_table(market_address):
    #market_address = "5LgJphS6D5zXwUVPU7eCryDBkyta3AidrJ5vjNU6BcGW"  # Address for BTC/USDC
    async with async_conn("https://api.mainnet-beta.solana.com/") as cc:
        # Load the given market
        market = await AsyncMarket.load(cc, market_address)
        asks = await market.load_asks()
        # Show all current ask order
        print("Ask Orders:")
        for ask in asks:
            print(f"Order id: {ask.order_id}, price: {ask.info.price}, size: {ask.info.size}.")
        print("\n")
        # Show all current bid order
        print("Bid Orders:")
        bids = await market.load_bids()
        for bid in bids:
            print(f"Order id: {bid.order_id}, price: {bid.info.price}, size: {bid.info.size}.")


asyncio.run(main())
