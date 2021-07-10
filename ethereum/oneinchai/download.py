from sqlitedict import SqliteDict
import numpy as np
import os
import sys
import time
curdir = os.path.abspath(os.curdir)
sys.path.extend([curdir, os.path.join(curdir, 'rl-baselines3-zoo'), os.path.join(curdir, 'one-inch-trades')])

# this the environment that one_inch_trades assumes
curdir=os.path.abspath(os.curdir)
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'one-inch-trades'))
if 'ETH_PROVIDER_URL' not in os.environ:
    os.environ['ETH_PROVIDER_URL'] = 'https://mainnet.infura.io/v3/27a61c91018d4bbb899154c8e72f9deb'
if 'BASE_ACCOUNT' not in os.environ:
    os.environ['BASE_ACCOUNT'] = '0x000be6292cf63b71909472211fd92e81efa96582'
import one_inch_trades as oit
os.chdir(curdir)

tokens = [oit.ethereum, oit.mcd_contract_address]
blocks = SqliteDict('./oit_{}.sqlite'.format('_'.join(tokens)), autocommit=True)
block = oit.web3.eth.block_number
def quote(from_token, to_token, amount, block):
        one_inch_join = oit.web3.eth.contract(address=oit.one_inch_split_contract, abi=oit.one_inch_split_abi)
        contract_response = one_inch_join.functions.getExpectedReturn(from_token, to_token, amount, 40, 0).call({'from': oit.base_account}, block_identifier = block)
        #print('quote', from_token, to_token, amount)
        #return oit.one_inch_get_quote(from_token, to_token, amount)[0]
        return contract_response[0]
while True:
        try:
            nonnormalised = np.array([
                 [
                     quote(tokens[from_token], tokens[to_token], int(1000000000000), block)
                     for to_token in range(len(tokens))
                 ]
                 for from_token in range(len(tokens))
            ])
        except ValueError as e:
            if e.args[0]['code'] == -32000:
                time.sleep(4)
                continue
            raise e
            

        blocks[block] = nonnormalised
        print(block)
        block += 1
