#include "hitbtc/MarketStreaming.hpp"

#include <iostream>
#include <sstream>

#include <boost/property_tree/json_parser.hpp>

/*
The HitBTC streaming service produces two data records; a snapshot and an update.
A sequence number identifies every change to the state of the order book.  Hence, sequence numbers
do not increase for snapshots.

Additionally, every record has:
- symbol : exchange in question
- exchangeStatus : "working" if exchange is open
- ask : array of {price:,size:}
- bid : array of {price:,size:}

The protocol does not function as documented.  Some of the keywords are slightly different, and the timestamp field is missing.

The incremental updates have a further array named 'trade'.
*/

namespace hitbtc {

MarketStreaming::MarketStreaming()
: WebSocket("ws://api.hitbtc.com")
{
}

MarketStreaming::Update MarketStreaming::get()
{
	boost::property_tree::ptree pt;
	Update ret;

	do {
		try {
			auto msg = WebSocket::get();
			ret.recvd = msg.recvd;
			pt = msg.getJSON();
		} catch (Exception e) {
			std::cerr << "hitbtc: streaming connection lost: " << e.what() << std::endl;
			reconnect();
			continue;
		}
	} while(false);

	ret.symbol = pt.begin()->second.get<std::string>("symbol");
	ret.exchangeWorking = pt.begin()->second.get<std::string>("exchangeStatus") == "working";

	std::string type = pt.begin()->first;
	pt = pt.begin()->second;
	if (type == "MarketDataSnapshotFullRefresh") {
		ret.snapshot = true;
		ret.seqNo = pt.get<integer>("snapshotSeqNo");
	} else if (type == "MarketDataIncrementalRefresh") {
		ret.snapshot = false;
		ret.seqNo = pt.get<integer>("seqNo");
		for (auto & pts : pt.get_child("trade")) {
			Order order = {
				pts.second.get<number>("price"),
				pts.second.get<number>("size")
			};
			ret.trades.emplace_back(order);
		}
	} else {
		std::cerr << "hitbtc: Invalid streaming message type '" << type << "': ";
		boost::property_tree::json_parser::write_json(std::cerr, pt);
		std::cerr << std::endl;
	}

	for (auto & pts : pt.get_child("ask")) {
		Order order = {
			pts.second.get<number>("price"),
			pts.second.get<number>("size")
		};
		ret.asks.emplace_back(order);
	}
	for (auto & pts : pt.get_child("bid")) {
		Order order = {
			pts.second.get<number>("price"),
			pts.second.get<number>("size")
		};
		ret.bids.emplace_back(order);
	}

	return ret;
}

}
