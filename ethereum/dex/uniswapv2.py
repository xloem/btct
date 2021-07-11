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
    def pairs(self, startidx = 0):
        idx = 0
        for _pair in db.pair(dex=self.db.addr):
            idx = _pair.index
            if idx >= startidx:
                yield pair(self, _pair)
        pairlen = wrap_neterrs(self.ct.functions.allPairsLength())
        for pairidx in range(max(idx+1,startidx), pairlen):
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
        for log in wrap_neterrs(self.ct.events.Sync(), 'getLogs', fromBlock=fromBlock,toBlock=toBlock,**kwparams):
            trade = db.trade.ensure(
                    id=log.transactionHash,
                    blocknum=log.blockNumber,
                    blockidx=log.transactionIndex,
                    # it could be nice to convert txidx to be local to the transaction
                    txidx=log.logIndex,
                    pair=self.db,
                    block=db.block.ensure(log.blockHash),
                    trader0=db.acct.ensure(log.address),
                    trader1=db.acct.ensure(self.db.addr),
                    const0=log.args.reserve0,
                    const1=log.args.reserve1
            )
            yield trade
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
### BOUNDS:
### in = 1000000, out = 996801, reserve = [5000000000] * 2
### in = 100000,  out = 99698,  reserve = [5000000000] * 2
def swap_status(reserve_tup, bal_tup, out_tup):
    print('swap reserve =', reserve_tup, ' bal =', bal_tup, ' out =', out_tup)
    # copied from UniswapV2Pair.sol
    if out_tup[0] <= 0 and out_tup[1] <= 0:
        print('no output')
        return False
    if out_tup[0] >= reserve_tup[0] or out_tup[1] >= reserve_tup[1]:
        return False
    if out_tup[0] < 0 or out_tup[1] < 0:
        raise AssertionError('negative output')
    bal_tup = (
        bal_tup[0] - out_tup[0],
        bal_tup[1] - out_tup[1]
    )
    in_tup = (
        bal_tup[0] - (reserve_tup[0] - out_tup[0]) if bal_tup[0] > reserve_tup[0] - out_tup[0] else 0,
        bal_tup[1] - (reserve_tup[1] - out_tup[1]) if bal_tup[1] > reserve_tup[1] - out_tup[1] else 0
    )
    print('in =', in_tup)
    if in_tup[0] <= 0 and in_tup[1] <= 0:
        return False
    adj_tup = (
        bal_tup[0] * 1000 - in_tup[0] * 3,
        bal_tup[1] * 1000 - in_tup[1] * 3
    )
    print('adj =', adj_tup)
    if adj_tup[0] * adj_tup[1] < reserve_tup[0] * reserve_tup[1] * 1000000:
        return False
    # transmission of outs is followed through from _safeTransfer
    #           noting: price0 = reserve1 / reserve0, price1 = reserve1 / reserve0
    # reserve becomes balance
    # Sync(new_reserve0, new_reserve1) is sent
    # Swap(pair, in0, in1, out0, out1, recipient) is sent
    return True

def swap_status_convenience(in_amt, out_amt, total_reserve = 10000000000, reserve_proportion_in = 0.5):
    reserve_portion_in = int(reserve_proportion_in * total_reserve)
    reserve_tup = (reserve_portion_in, total_reserve - reserve_portion_in)
    status0 = swap_status(reserve_tup, (reserve_tup[0] + in_amt, reserve_tup[1]), (0, out_amt))
    status1 = swap_status((reserve_tup[1],reserve_tup[0]), (reserve_tup[1], reserve_tup[0] + in_amt), (out_amt, 0))
    if status0 != status1:
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
        #amountIn * .997 * reserveOut / (reserveIn + amountIn * .997)

        #price = reserveIn / reserveOut
        #amountIn * .997 / (price + amountIn * .997 / reserveOut)

        #price = reserveOut / reserveIn
        #amountIn * .997 * price / (1 + amountIn * .997 / reserveIn)

        #price = amountIn / amountOut
        #amountIn / (amountIn * .997 * reserveOut / (reserveIn + amountIn * .997))
        #1 / (.997 * reserveOut / (reserveIn + amountIn * .997))

        #?
        #price=(reserveIn/.997 + amountIn) / reserveOut
            #convert to price + fees
            # (amountIn - subfee) * mulfee / price = amountOut
            # or
            # (amountIn * mulfee - subfee) / price = amountOut
            #amountOut = amountIn * reserveOut / (reserveIn / .997 + amountIn)
            ## might work better other direction unknown, hard to tell if it is reasonable to do
            #amountOut = amountIn * reserveOut / (reserveIn / .997 + amountIn)
            #amountOut * reserveIn / .997 + amountOut * amountIn = amountIn * reserveOut
            #amountOut * (reserveIn / .997 + amountIn) = amountIn * reserveOut
            #(reserveIn / .997 + amountIn) / amountIn = reserveOut / amountOut
            #reserveIn / .997 / amountIn + 1 = reserveOut / amountOut
            #reserveIn / .997 / amountIn = reserveOut / amountOut - 1
            #reserveIn / (.997 * amountIn) = reserveOut / amountOut - 1
            #reserveIn / (.997 * amountIn) = reserveOut / amountOut - amountOut / amountOut
            #reserveIn / (.997 * amountIn) = (reserveOut - amountOut) / amountOut
            #1 + reserveIn / (.997 * amountIn) = reserveOut / amountOut
            #amountOut * (1 + reserveIn / (.997 * amountIn)) = reserveOut
            #amountOut * (1 + reserveIn / (.997 * amountIn)) = reserveOut
            #amountOut = reserveOut / (1 + reserveIn / (.997 * amountIn))
            #amountOut = reserveOut / (1 + reserveIn / (.997 * amountIn))
            #amountOut = reserveOut / ((.997 * amountIn + reserveIn) / (.997 * amountIn))
            #amountOut = reserveOut * (amountIn * .997) / (.997 * amountIn + reserveIn)
            #amountOut = reserveOut/reserveIn * (amountIn * .997) / (.997 * amountIn/reserveIn + 1)

            #    # the price factor here is not simply a multiplication.
            #    # first the amount in is scaled down.
            #    # really you're buying into an algebraic expression
            #amountOut = reserveOut / (1 + reserveIn / (.997 * amountIn))
            #1 / amountOut = (1 + reserveIn / (.997 * amountIn)) / reserveOut
            #reserveOut / amountOut = 1 + reserveIn / (.997 * amountIn)

                # the amount you get back is a nonlinear function of how much you put in
                # we coudl cast as feeEq, utilising constants
                # row-specific constants

                    # the return equation is specific to all uniswapv2 pairs
                    # it's bounded in that you can't get more than the constants associated
                    # basically a supply.
                    # other markets have order tables defining the supply and price:
                    ### i.e. for other markets the situation is comparable, it just isn't
                    ### defined by one single equation.  it's defined by many placed orders.

                    ##### let's make the price functions methods of the pair object
                    ##### and store the reserve data.
                    ##### price is always a function of how much is put in.
                    ##### and only so much can be taken out.

            
            


    # note that this can be fractional, in which case the contract would round down
    # some amountIn can be discarded in that case
    return numerator / denominator

def getAmountIn(amountOut, reserveIn, reserveOut):
    numerator = reserveIn * amountOut * 1000
    denominator = (reserveOut - amountOut) * 997
    # this can be fractional too, in which case adding 1 to the floored answer
    # would be needed to provide enough in to cover the fraction
    return numerator / denominator
