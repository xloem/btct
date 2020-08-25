/*
 * Exchange data is a looooong vectorish concept.
 * It's composed of data items like this:
 *  - bid/ask
 *  - start time
 *  - USD etc value
 *  - BTC etc value
 *  - end time or still present
 *  - trade ended with or closed by owner
 *
 *  note that a trade can partially close a bid or ask
 *  ie a bid could be initiated for v1btc @ v0usd/btc
 *  then for v2btc @ v0usd/btc
 *  and then a trade is made @ v0usd/btc for v3btc < v1btc+v2btc
 *
 *  there is no immediate way to know which bid is closed, partially or fully, by
 *  the trade.  One could simply be chosen, or it could be spread between them.
 *
 *  Perhaps a better model is order change events.
 *  - bid/ask
 *  - rate (eg usd/btc)
 *  - btc new value
 *  - time of value change
 *  - optionally associated trade
 *
 *  An investor is interested in human behavior.  What are people doing?
 *  - making bids, asks
 *  - removing bids, asks
 *  - trading and closing others' bids & asks
 *  - changing or moving bids & asks
 *
 *  Re storage of value:
 *  Form 1:
 *  - Rate/Price (currency/item)
 *  - Value/Size (#item willing to sell or purchase)
 *  But item is currency too.  Each entry has an associated amount of currency1
 *  and amount of currency2 involved in the exchange.  depending on a bid or ask,
 *  the person making the order may have the set amount of currency2 or of currency1 up
 *  for exchange for the other.
 *
 *  I think I'd like to multiply the rate out and store the total exchange amount.
 *  But that's harder to categorize and sort ....
 *
 *  Yeeesh man.
 */
class ExchangeData
{
	
};
