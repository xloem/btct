import numpy as np

SELL = 0
BUY = 1

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
    for idx, row in enumerate(history):
        rowtxt = ' ' * row['prices'][0] + '#' * (row['prices'][1] - row['prices'][0])
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
            print(rowtxt, ['SELL','BUY'][row['extreme']], 'balance =', nextbalance, int(profit*10000)/100, '%')
        elif idx % (len(history)/5) == 0:
            print(rowtxt)
    
txr = price_tracker(output)

start = np.random.randint(80,size=2)
while True:
    start += np.random.randint(-1,2,size=2)
    start = start.clip(0, 80)
    start.sort()
    start[1] = np.max(start + [1,0])
    txr.update(start + [100])
