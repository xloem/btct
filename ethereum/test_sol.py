import asyncio
print('importing ...')
import dex.serumv3 as serumv3
print('starting ..')

async def main():
    dex = serumv3.dex()
    for pair in dex.pairs():
        print(pair.db, pair.db.token0.symbol, pair.db.token1.symbol)
        if 'SOL' in pair.db.token0.symbol:
            print(pair.db.addr)
            await pair.pump()

asyncio.run(main())
