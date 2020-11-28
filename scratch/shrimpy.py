import shrimpy

# shrimpy only provides a little data in each request

shrimpy = shrimpy.ShrimpyApiClient('2355a9a6c9039220fbde8adb84c7d6bcf7cfcc233bf4bbe3','4408aa8e813c5e01464147bf61a2d10f9b0a21e383be16bb2734397f96c8018f75fa511221e6c9ebb08594b1ecf8472280c8452814899ea5c8b366fe9126e14f')

# data for a regression

lasttime = None
while True:
    candles = shrimpy.get_candles('coinbasepro', 'BTC', 'USD', '1h', lasttime)
    lasttime = None
    if isinstance(candles, dict):
        print(candles)
        break
    for candle in candles:
        if lasttime is None:
            lasttime = candle['time']
        print(candle)
