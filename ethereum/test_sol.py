print('importing ...')
import asyncio, os
import solana
import dex.serumv3 as serumv3
if not os.path.exists('solana.seed'):
    key = solana.keypair.Keypair.generate()
    with open('solana.seed', 'wb') as keyfile:
        keyfile.write(key.seed)
else:
    with open('solana.seed', 'rb') as keyfile:
        key = solana.keypair.Keypair.from_seed(keyfile.read())
print('starting ..')

async def main():
    dex = serumv3.dex()
    for pair in dex.pairs():
        print(pair.db, pair.db.token0.symbol, pair.db.token1.symbol)
        if 'SOL' in pair.db.token0.symbol:
            print(pair.db.addr)
            await pair.pump()

asyncio.run(main())
