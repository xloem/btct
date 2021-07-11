from pyweb3 import w3, wrap_neterrs, web3
import abi
import db

# i added this line to debug a strange mismatched abi error.  the line prevents the error =/  quick-workaround
testrecpt = w3.eth.getTransactionReceipt('0xb31fcb852b18303c672b81d90117220624232801ad949bd4047e009eaed73403')
#uniswapv2ct.events.PairCreated()#.processLog(testrecpt.logs[0])

class dex:
    def __init__(self, address=abi.uniswapv2_factory_addr, name='UNI-V2'):
        self.db = db.dex(address, name)
        self.ct = w3.eth.contract(
            address = address,
            abi = abi.uniswapv2_factory
        )

    ## pairs iterator for now, better to look up by attributes like tokens or volume or such i guess
    ## this could also be getitem[]
    ## but maybe what's important to think about is getting what's needed into the database, rather than accessing it
    def pairs(self):
        idx = 0
        for _pair in db.pair(dex=self.db.addr):
            idx = _pair.index
            yield pair(self, _pair)
        pairlen = wrap_neterrs(self.ct.functions.allPairsLength())
        for pairidx in range(idx, pairlen):
            pairaddr = wrap_neterrs(self.ct.functions.allPairs(pairidx))
            pairdb = db.pair[pairaddr]
            if not pairdb:
                pairct = w3.eth.contract(
                    address = pairaddr,
                    abi = abi.uniswapv2_pair
                )
                tokenaddrs = (pairct.functions.token0,pairct.functions.token1)
                tokens = [None, None]
                for tokenidx in range(2):
                    tokenaddr = wrap_neterrs(tokenaddrs[tokenidx]())
                    try:
                        symbol = wrap_neterrs(w3.eth.contract(
                            address=tokenaddr,
                            abi=abi.uniswapv2_erc20
                        ).functions.symbol())
                    except Exception as e: # this absorbs keyboard-interrupt, put error type in? .. the error is thrown from an underlying issue in the library, resulting from calling to the wrong spec.  other errors could be thrown, add 'em I guess.
                        if isinstance(e, OverflowError) or isinstance(e, web3.exceptions.ContractLogicError) or isinstance(e, web3.exceptions.BadFunctionCallOutput):
                            print('pairidx',pairidx,'token',tokenidx,tokenaddr,'raised an erc20 error:', e, e.__cause__)
                            symbol = tokenaddr
                        else:
                            raise e
                    tokens[tokenidx] = db.token.ensure(
                        tokenaddr,
                        symbol
                    )
                pairdb = db.pair(
                    pairaddr,
                    tokens[0].addr,
                    tokens[1].addr,
                    self.db.addr,
                    index=pairidx
                )
            yield pair(self, pairdb)

class pair:
    def __init__(self, dex, dbpair):
        self.dex = dex
        self.db = dbpair
        self.ct = w3.eth.contract(
            address = self.db.addr,
            abi = abi.uniswapv2_pair
        )
    # note that getLogs uses event filter params
    # under the hood.  web3/contract.py:1341
    def logs(self, fromBlock=None, toBlock=None, **kwparams):
        # the best timestamp granularity appears to be the timestamp of the block, which is well known
        # we could display them evenly distributed over the block, if desired
        
        #if fromBlock is None:
        #   fromBlock = 'earliest'
        if toBlock is None:
            toBlock = 'latest'
        # next: back by db. might mean calculating buy/sell prices
        # it looks like logIndex might be exchangeable with something similar to txOut
        return (
            ((log.args.reserve0, log.args.reserve1), log.blockHash, (log.transactionHash, log.logIndex))
            for log in
            wrap_neterrs(self.ct.events.Sync(), 'getLogs', fromBlock=fromBlock,toBlock=toBlock,**kwparams)
        )
    def reserves(self):
        # call(), inside wrap_neterrs, can take transaction params and a block identifier or number
        # note that these functions also have .estimateGas as well as .call
        reserve0, reserve1, unixtimestamp = wrap_neterrs(self.ct.functions.getReserves())
        return ((reserve0, reserve1), unixtimestamp)


# below functions calculate exchange amounts
# are in line with buy/sell prices
# can be moved to be methods
# approximation of held funds might be needed for calculation
# the solidity source code of the pair swap() function also shows exactly what happens



# these equations appear to give a variable rate depending on how the amount given compares to the reserve
# it's possibly possible to game that, arbitraging a sibling exchange forever
# the system lets you borrow money to do that, too.  i may have calculated something wrong.
def getAmountsForIn(amountIn, reserveIn, reserveOut):
    amountInWithFee = amountIn * 997
    numerator = amountInWithFee * reserveOut
    denominator = reserveIn * 1000 + amountInWithFee;
    # note that this can be fractional, in which case the contract would round down
    # some amountIn can be discarded in that case
    return numerator / denominator

def getAmountIn(amountOut, reserveIn, reserveOut):
    numerator = reserveIn * amountOut * 1000
    denominator = (reserveOut - amountOut) * 997
    # this can be fractional too, in which case adding 1 to the floored answer
    # would be needed to provide enough in to cover the fraction
    return numerator / denominator
