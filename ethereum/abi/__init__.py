""" uniswap is composed of many contracts that work together.  the factory interface is a core one. """

def _loadjson(name):
    import os.path
    import json
    with open(os.path.join(__path__[0], name + '.json')) as file:
        return json.load(file)

erc20 = _loadjson('erc20')
uniswapv1_factory = _loadjson('uniswapv1_factory')
uniswapv2_factory = _loadjson('uniswapv2_factory')
uniswapv2_factory_addr = '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f'
uniswapv2_pair = _loadjson('uniswapv2_pair')
uniswapv2_erc20 = _loadjson('uniswapv2_erc20')
uniswapv3_factory = _loadjson('uniswapv3_factory')
