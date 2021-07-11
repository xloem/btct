from pyweb3 import w3, wrap_neterrs, web3
import abi
import db

import random, math

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
                    token = db.token(tokenaddr)
                    if token:
                        symbol = token.symbol
                    else:
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
                        token = db.token.ensure(tokenaddr, symbol)
                    tokens[tokenidx] = token
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
            yield trade(self, db.trade.ensure(
                    id=log.transactionHash,
                    blocknum=log.blockNumber,
                    blockidx=log.transactionIndex,
                    # it could be nice to convert txidx to be local to the transaction
                    txidx=log.logIndex,
                    pair=self.db,
                    block=db.block.ensure(log.blockHash, log.blockNumber),
                    trader0=db.acct.ensure(log.address),
                    trader1=db.acct.ensure(self.db.addr),
                    const0=log.args.reserve0,
                    const1=log.args.reserve1
            ))
    def reserves(self):
        # call(), inside wrap_neterrs, can take transaction params and a block identifier or number
        # note that these functions also have .estimateGas as well as .call
        reserve0, reserve1, unixtimestamp = wrap_neterrs(self.ct.functions.getReserves())
        return ((reserve0, reserve1), unixtimestamp)
    
    # returns bool whether a swap would be accepted
    @staticmethod
    def _swap_status(reserve_tup, bal_tup, out_tup):
        print('swap reserve =', reserve_tup, ' bal =', bal_tup, ' out =', out_tup)
        # copied from UniswapV2Pair.sol
        if out_tup[0] <= 0 and out_tup[1] <= 0:
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

    # returns bool whether a swap would be accepted
    @staticmethod
    def _swap_status_convenience(in_amt, out_amt, total_reserve = 10000000000, reserve_proportion_in = 0.5):
        reserve_portion_in = int(reserve_proportion_in * total_reserve)
        reserve_tup = (reserve_portion_in, total_reserve - reserve_portion_in)
        status0 = swap_status(reserve_tup, (reserve_tup[0] + in_amt, reserve_tup[1]), (0, out_amt))
        status1 = swap_status((reserve_tup[1],reserve_tup[0]), (reserve_tup[1], reserve_tup[0] + in_amt), (out_amt, 0))
        if status0 != status1:
            raise AssertionError('status differed for different directions')
        return status0

    # these equations appear to give a variable rate depending on how the amount given compares to the reserve
    # it's possibly possible to game that, arbitraging a sibling exchange forever
    # the system lets you borrow money to do that, too.  i may have calculated something wrong.
    # i'm guessing the gas fees and other limits prevent it from being meaningful, which would
    # be important to understand to know the effective price.
    ##### this could be clearly answered with a plot
    @staticmethod
    def calc_out(reserve_tup, in_0):
        # from uniswap library
        amountInWithFee = in_0 * 997
        numerator = amountInWithFee * reserve_tup[1]
        denominator = reserve_tup[0] * 1000 + amountInWithFee;

        # note that this can be fractional, in which case it gets rounded down
        # some amountIn can be wasted in that case.  calling calc_in on the result shows how much.
        return numerator // denominator

    @staticmethod
    def calc_in(reserve_tup, out_1):
        # from uniswap library
        numerator = reserve_tup[0] * out_1 * 1000
        denominator = (reserve_tup[1] - out_1) * 997
        # this can be fractional too, in which case adding 1 to the floored answer
        # provides enough in to cover the fraction
        if numerator % denominator:
            return numerator // denominator + 1
        else:
            return numerator // denominator

    @staticmethod
    def _test(in_0 = random.randint(1, 10**17), reserve0=random.randint(1,10**100), reserve1=random.randint(1,10**100)):
        reserves = (reserve0, reserve1)
        out_1 = int(pair.calc_out(reserves, in_0))
        balance = (
            reserves[0] + in_0,
            reserves[1]
        )
        if pair._swap_status(reserves, balance, (0, out_1)) == False:
            raise ArithmeticError('calc_out -> False')
        if pair._swap_status(reserves, balance, (0, out_1 + 1)) == True:
            raise ArithmeticError('calc_out + 1 -> True')
        in_0 = int(math.ceil(pair.calc_in(reserves, out_1)))
        balance = (
            reserves[0] + in_0,
            reserves[1]
        )
        if int(pair.calc_out(reserves, in_0)) != out_1:
            raise ArithmeticError('calc_out -> calc_in -> calc_out !=')
        if pair._swap_status(reserves, balance, (0, out_1)) == False:
            raise ArithmeticError('calc_in -> calc_out -> False')
        if pair._swap_status(reserves, balance, (0, out_1 + 1)) == True:
            raise ArithmeticError('calc_in -> calc_out + 1 -> True')
        balance = (
            reserves[0] + in_0 - 1,
            reserves[1]
        )
        if pair._swap_status(reserves, balance, (0, out_1)) == True:
            raise ArithmeticError('calc_in - 1 -> calc_out -> True')


# represents a price point
class trade:
    def __init__(self, pair, db):
        self.pair = pair
        self.db = db
    def reserves(self):
        return (self.db.const0, self.db.const1)
    def token0_possible(self, token1_have):
        reserve0, reserve1 = self.reserves()
        return self.pair.calc_out((reserve1, reserve0), token1_bal)
    def token1_possible(self, token0_have):
        return self.pair.calc_out(self.reserves(), token0_bal)
    def token0_needed(self, token1_want):
        return self.pair.calc_in(self.reserves(), token1_goal)
    def token1_needed(self, token0_want):
        reserve0, reserve1 = self.reserves()
        return self.pair.calc_in((reserve1, reserve0), token0_goal)

    def prices(self, investment_tup):
        # calculate the sellbuy rational prices
        # if rational objects are passed in investment_tup, hopefully the same will be output

        # start by combining the sides of investment_tup to have total balances
        starting_bal = (
                investment_tup[0] + self.token0_possible(investment_tup[1]),
                investment_tup[1] + self.token1_possible(investment_tup[0])
        )

        # calculate how much each trades for
        ending_bal = (
                self.token0_possible(starting_bal[1]),
                self.token1_possible(starting_bal[0])
        )
        # update starting_bal to reduce rounding error
        starting_bal = (
                self.token0_needed(ending_bal[1]),
                self.token1_needed(ending_bal[0])
        )

        # TODO: gas fees.
        # the best way to figure gas fees is to actually run a test transaction and discern
        # all the expenses.

        # calculate ((sell1_for_0, buy1_with_0),(sell0_for_1, buy0_with_1))
        return (
            (
                # sale price of token1 in token0: how much token0 we get for a single token1
                ending_bal[0]/starting_bal[1],
                # purcahse price of token1 in token0: how much token0 a single token1 costs
                starting_bal[0]/ending_bal[1]
            ),(
                # same price of token0 in token1
                ending_bal[1]/starting_bal[0],
                starting_bal[0]/ending_bal[1]
            )
        )
    def __str__(self):
        return str(self.pair.db) + ':' + self.db.block.hash + '/' + str(self.db.txidx) + ' ' + str(self.db.const0) + '/' + str(self.db.const1)

# i calculated this using pysym and it is quite wrong.
# i would like to recalculate using pysym to understand better.
def out_for_in(out_reserve, in_amt, in_reserve):
    return in_amt * out_reserve / ((3988/1977)*in_amt + in_reserve)


if __name__ == '__main__':
    pair._test()
