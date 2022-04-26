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
    print('main account:', key.public_key, 'balance =', dex.balance(key.public_key))
    for pair in dex.pairs():
        print(pair.db, pair.db.token0.symbol, pair.db.token1.symbol)
        if 'SOL' in pair.db.token0.symbol:
            print('market = ', pair.db.addr)
            base_acct = pair.token0.account(key)
            base_balance = pair.token0.balance(base_acct)
            print(pair.db.token0.symbol, str(pair.db.token0.addr), 'acct =', base_acct, 'balance =', repr(base_balance))
            quote_acct = pair.token1.account(key)
            quote_balance = pair.token1.balance(quote_acct)
            print(pair.db.token1.symbol, str(pair.db.token1.addr), 'acct =', quote_acct, 'balance =', quote_balance)

            if base_balance == 0:
                #txid = dex.transfer(key, base_acct, dex.balance(key.public_key) // 2)
                if dex.balance(base_acct) == 0:
                    txid = pair.token0.wrap(key, deposit_amount = dex.balance(key.public_key) // 2, token_account = base_acct)
                    print('transferred into base, txid =', txid)
                else:
                    txid = pair.token0.wrap(key, token_account = base_acct)
                    print('wrapped base, txid = ', txid)
            else:
                print('base balance nonzero, not transferring')


            await pair.pump()

asyncio.run(main())
