import numpy as np

SELL = 0
BUY = 1

class unisrc:
    def __init__(self, pairidx = 0):
        from dex import uniswapv2
        self.dex = uniswapv2.dex()
        self.pair = self.dex.pair_by_index(pairidx)
        self.pricemul0 = 10 ** -(self.pair.db.token0.decimals - self.pair.db.token1.decimals)
        self.pricemul1 = 10 ** (self.pair.db.token0.decimals - self.pair.db.token1.decimals)
    def __iter__(self):
        for trade in self.pair.logs():
            prices = trade.prices((1000000, 1000000))
            prices = (
                (prices[0][0] * self.pricemul0, prices[0][1] * self.pricemul0),
                (prices[1][0] * self.pricemul1, prices[1][1] * self.pricemul1),
            )
            yield prices[0]

class price_tracker:
    def __init__(self, callback = lambda history: None):
        self.region = -1
        self.prices = np.array([np.inf, -np.inf])
        self.idxs = np.array([0,0])
        self.multipliers = np.array([1,-1])
        self.lastextreme = None
        self.lastcb = 0
        self.history = []
        self.callback = callback
    def _update(self, prices, region):
        idx = len(self.history)
        if prices[region] * self.multipliers[region] > self.prices[region]:
            # this price is more extreme; update
            self.prices[region] = prices[region] * self.multipliers[region]
            self.idxs[region] = idx
        nextregion = 1 - region
        if not np.isinf(self.prices[region]) and prices[nextregion] * self.multipliers[region] < self.prices[region]:
            # other price crossed our extreme price, switch regions
            extreme_idx = self.idxs[region]
            self.history[extreme_idx]["extreme"] = region
            self.history[extreme_idx]["lastextreme"] = self.lastextreme
            self.lastextreme = extreme_idx
            self.prices[nextregion] = prices[nextregion] * self.multipliers[nextregion]
            self.idxs[nextregion] = idx
            self.region = nextregion
            self.callback(self.history[self.lastcb:extreme_idx + 1])
            self.lastcb = extreme_idx + 1
    def update(self, prices):
        if self.region != SELL:
            self._update(prices, BUY)
        if self.region != BUY:
            self._update(prices, SELL)
        self.history.append({
            "prices": prices
        })

FIAT = 0
COMMODITY = 1
balance = None
#balance = np.array([None,None])
def output(history):
    global balance
    global offset
    for idx, row in enumerate(history):
        if row['prices'][0] > offset:
            rowtxt = ' ' * int(.5+row['prices'][0] - offset) + '#' * int(.5+row['prices'][1] - row['prices'][0])
        elif row['prices'][1] > offset:
            rowtxt = '#' * int(.5+row['prices'][1] - offset)
        else:
            rowtxt = ''
        if 'extreme' in row:
            fiatcommodity = buysell = row['extreme']
            otherfiatcommodity = 1 - fiatcommodity
            if balance is None:
                balance = np.array([None,None])
                otherbalance = 1.0
            else:
                otherbalance = balance[otherfiatcommodity]
            if fiatcommodity == FIAT:
                nextbalance = otherbalance * row['prices'][SELL]
            else:
                nextbalance = otherbalance / row['prices'][BUY]
            if balance[0] is None:
                profit = 0.0
            else:
                profit = nextbalance / balance[fiatcommodity] - 1.0
                if not (profit > 0):
                    raise Exception()
            balance[fiatcommodity] = nextbalance
            print(rowtxt, ['SELL','BUY'][row['extreme']], 'price =', row['prices'][fiatcommodity], 'balance =', nextbalance, int(profit*10000)/100, '%')
        elif idx % (len(history)/5) == 0:
            print(rowtxt)
    
txr = price_tracker(output)

WID=40
#start = np.random.randint(1,1 + WID,size=2)
offset = 1
for prices in unisrc():
    start = np.array(prices)
    print(start)
    #start += [np.random.randint(-1,3), np.random.randint(-1,3)]
    #start = start.clip(0, 70)
    start.sort()
    start[0] = np.max(start - [0,WID/2])
    start[1] = np.max(start + [1,0])
    if start[1] + offset > WID:
            offset = start[1] - WID
    txr.update(start + [0,0])
