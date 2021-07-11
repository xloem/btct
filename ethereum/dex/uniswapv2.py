from pyweb3 import w3, wrap_neterrs, web3
import abi
import db

try:
    # i added this line to debug a strange mismatched abi error.  the line prevents the error =/  quick-workaround
    testrecpt = w3.eth.getTransactionReceipt('0xb31fcb852b18303c672b81d90117220624232801ad949bd4047e009eaed73403')
    #uniswapv2ct.events.PairCreated()#.processLog(testrecpt.logs[0])
except web3.exceptions.TransactionNotFound:
    pass

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

# note: balance of a pair is different from its reserves.  the balance is what is used to swap.
# the script calculates the amountIn as its balance minus its reserve, clamping to 0 for negative
def swap_status(reserve_tup, bal_tup, out_tup):
    # copied from UniswapV2Pair.sol
    if out_tup[0] <= 0 and out_tup[1] <= 0:
        return False
    if out_tup[0] >= reserve_tup[0] or out_tup[1] >= reserve_tup[1]:
        return False
    if out_tup[0] < 0 or out_tup[1] < 0:
        raise AssertionError('negative output')
    in_tup = (
        bal_tup[0] - (reserve_tup[0] - out_tup[0]) if bal_tup[0] > reserve_tup[0] - out_tup[0] else 0,
        bal_tup[1] - (reserve_tup[1] - out_tup[1]) if bal_tup[1] > reserve_tup[1] - out_tup[1] else 0
    )
    if in_tup[0] <= 0 and in_tup[1] <= 0:
        return False
    adj_tup = (
        bal_tup[0] * 1000 - in_tup[0] * 3,
        bal_tup[1] * 1000 - in_tup[1] * 3
    )
    if adj_tup[0] * adj_tup[1] < reserve_tup[0] * reserve_tup[1] * 1000000:
        return False
    # transmission of outs is followed through from _safeTransfer
    #           noting: price0 = reserve1 / reserve0, price1 = reserve1 / reserve0
    # reserve becomes balance
    # Sync(new_reserve0, new_reserve1) is sent
    # Swap(pair, in0, in1, out0, out1, recipient) is sent
    return True

def swap_status_convenience(in_amt, out_amt, total_reserve = 10000000000, reserve_proportion_in = 0.5):
    reserve_portion_in = int(reserver_proportion_in * total_reserve)
    reserve_tup = (reserve_portion_in, total_reserve - reserve_portion_in)
    status0 = swap_status(reserve_tup, (reserve_tup[0] + in_amt, reserve_tup[1]), (0, out_amt))
    status1 = swap_status((reserve_tup[1],reserve_tup[0]), (reserve_tup[1], reserve_tup[0] + in_amt), (out_amt, 0))
    if status0 != status2:
        raise AssertionError('status differed for different directions')
    return status0

def out_for_in(out_reserve, in_amt, in_reserve):
    # assuming large reserves and smaller but also large in amount?
    # if this is correct, we can put 10000 in when both reserves are at 10000000
    #   and get 9979 back.  the fee is only a little more than 2% under those conditions
    return in_amt * out_reserve / ((3988/1977)*in_amt + in_reserve)

# these equations appear to give a variable rate depending on how the amount given compares to the reserve
# it's possibly possible to game that, arbitraging a sibling exchange forever
# the system lets you borrow money to do that, too.  i may have calculated something wrong.
def getAmountOut(amountIn, reserveIn, reserveOut):
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
