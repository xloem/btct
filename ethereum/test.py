import datetime
import db
import dex.uniswapv2
dex = dex.uniswapv2.dex()
earliest_synced_pair = next(db.pair().ascending('latest_synced_trade', subkey='blocknum', limit=1))
for tx in dex.logs_all(fromBlock=earliest_synced_pair.latest_synced_trade.blocknum):#_all():#fromBlock=12968693):
        pair = tx.pair
        investment_tup = (10**pair.db.token0.decimals, 10**pair.db.token1.decimals)
        reserves = tx.reserves()
        prices = tx.prices(investment_tup)
        decimals0 = pair.db.token0.decimals - pair.db.token1.decimals
        decimals1 = -decimals0
        prices = (
            (prices[0][0] / 10**decimals0, prices[0][1] / 10**decimals0),
            (prices[1][0] / 10**decimals1, prices[1][1] / 10**decimals1),
        )
        time = datetime.datetime.fromtimestamp(tx.db.block.time).isoformat()
        print(tx.db, time, tx.db.block.addr, prices)
#pair = dex.pair('AMPSWAP', 'AMPX')
#print(pair.db.addr)
