from web3 import Web3, _utils as utils

#from web3.auto import w3 as w3_local
w3_local = None # my node hasn't synced yet, is slow to respond

w3_cloud = Web3(Web3.HTTPProvider('https://cloudflare-eth.com'))

try:
    if w3_local.isConnected() and not w3_local.eth.is_syncing():
        w3 = w3_local
    else:
        raise Exception()
except:
    w3 = w3_cloud

while True:
    try:
        if w3.isConnected():
            print('connected')
            break
    except Exception:
        pass
    print('not connected yet, waiting...')
    import time
    time.sleep(0.5)
