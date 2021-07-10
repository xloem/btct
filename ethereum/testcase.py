from web3 import Web3
import abi
import time
w3 = Web3(Web3.HTTPProvider('https://cloudflare-eth.com'))
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
contract = w3.eth.contract(address=abi.uniswapv2_factory_addr,abi=abi.uniswapv2_factory)
txr = w3.eth.getTransactionReceipt('0xb31fcb852b18303c672b81d90117220624232801ad949bd4047e009eaed73403')
#contract.events.PairCreated.abi = contract.events.PairCreated._get_event_abi()
contract.events.PairCreated.processLog(txr.logs[0])
