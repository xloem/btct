from datetime import datetime
from dateutil.parser import isoparse
from dataclasses import dataclass

@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    time: float
    

class ShrimpyDatasource:
    _interval_map = {
        60: '1m',
        60*5: '5m',
        60*15: '15m',
        60*60: '1h',
        60*60*6: '6h',
        60*60*24: '1d'
    }
    _api = None
    def __init__(self, exchange = 'coinbasepro', base = 'BTC', quote = 'USD', interval = 60):
        import shrimpy
        # shrimpy only provides a little data in each request
        if ShrimpyDatasource._api is None:
            ShrimpyDatasource._api = shrimpy.ShrimpyApiClient('2355a9a6c9039220fbde8adb84c7d6bcf7cfcc233bf4bbe3','4408aa8e813c5e01464147bf61a2d10f9b0a21e383be16bb2734397f96c8018f75fa511221e6c9ebb08594b1ecf8472280c8452814899ea5c8b366fe9126e14f')
            self.api = ShrimpyDatasource._api

        self.exchange = exchange
        self.base = base
        self.quote = quote
        interval = int(interval)
        self.interval = interval
        self.interval_str = ShrimpyDatasource._interval_map[interval]

        self._cache = {}

    #def iterate(self):
        
    def _normalize(self, timestamp):
        return int(timestamp / self.interval) * self.interval # LIKELY NEED OFFSET HERE, TO MATCH CHUNKS ON SERVER

    # GRR SERVER INTERFACE
    # we need to find range, if we don't have chunks in range

    def candle(self, timestamp = None):
        candles = None
        if timestamp is None:
            timestamp = datetime.now().timestamp()
        normalized = self._normalize(timestamp)
        if normalized in self._candle_cache:
            candles = self._candle_cache[normalized]
        else:
            candles = [Candle(float(candle['open']), float(candle['high']), float(candle['low']), float(candle['close']), isoparse(candle['time']).timestamp()) for candle in self._candles(normalized)]
            self._cache[self._normalize(candles[-1].time)] = candles
        closest = None
        distance = self.interval
            self._candle_cache[candle.time] = candle
            if timestamp is None:
                # bug one: the latest candle is the last returned, not the first
                if closest is None:
                    closest = candle
            else:
                thisdistance = abs(timestamp - candle.time)
                if thisdistance < distance:
                    distance = thisdistance
                    closest = candle
        return closest

    def _candles(self, endtimestamp = None):
        if endtimestamp is not None:
            endtimestamp = datetime.fromtimestamp(endtimestamp).isoformat()
        return self.api.get_candles(self.exchange, self.base, self.quote, self.interval_str, endtimestamp)

datasource = ShrimpyDatasource()

lastcandle = datasource.candle()
while True:
    print(lastcandle)
    lastcandle = datasource.candle(lastcandle.time - datasource.interval)
