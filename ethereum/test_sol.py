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
    solana_balance = dex.balance(key.public_key)
    print('main account:', key.public_key, 'balance =', solana_balance, 'lamports', solana_balance / 1000000000, 'sol')
    for pair in dex.pairs():
        print(pair.db, pair.mintrade0() / 10**pair.token0.db.decimals, pair.db.token0.symbol, pair.mintrade1() / 10**pair.token1.db.decimals, pair.db.token1.symbol)
        #if (isinstance(pair.token0, serumv3.wrapped_sol) and pair.mintrade0() < solana_balance / 2) or (isinstance(pair.token1, serumv3.wrapped_sol) and pair.mintrade1() < solana_balance / 2):
        if isinstance(pair.token0, serumv3.wrapped_sol) or isinstance(pair.token1, serumv3.wrapped_sol):
            print('market = ', pair.db.addr)
            base_acct = pair.token0.account(key)
            base_balance = pair.token0.balance(base_acct)
            print(pair.db.token0.symbol, str(pair.db.token0.addr), 'acct =', base_acct, 'balance =', repr(base_balance))
            quote_acct = pair.token1.account(key)
            quote_balance = pair.token1.balance(quote_acct)
            print(pair.db.token1.symbol, str(pair.db.token1.addr), 'acct =', quote_acct, 'balance =', quote_balance)

            #if base_balance != 0:
            #    pair.token0.unwrap(key, token_account = base_acct)
            #if base_balance == 0:
            #    #txid = dex.transfer(key, base_acct, dex.balance(key.public_key) // 2)
            #    if dex.balance(base_acct) == 0:
            #        txid = pair.token0.wrap(key, deposit_amount = dex.balance(key.public_key) // 2, token_account = base_acct)
            #        print('transferred into base, txid =', txid)
            #    else:
            #        txid = pair.token0.wrap(key, token_account = base_acct)
            #        print('wrapped base, txid =', txid)
            #    base_balance = pair.token0.balance(base_acct)
            #else:
            #    print('base balance nonzero, not transferring')

            async for pair, ts, slot, price0, price1 in pair.pump():
                print(ts, slot, str(pair.db), price0, '-', price1)
                if quote_balance == 0 or base_balance == 0:
                    if quote_balance == 0:
                        txid = await pair.atrade_0to1(key, base_balance // 2, price1)
                    elif base_balance == 0:
                        txid = await pair.atrade_1to0(key, quote_balance // 2, price1)
                    base_balance = pair.token0.balance(base_acct)
                    quote_balance = pair.token1.balance(quote_acct)
                    print('performed a trade, txid =', txid, pair.db.token0.symbol, '=', base_balance, pair.db.token1.symbol, '=', quote_balance)

asyncio.run(main())
