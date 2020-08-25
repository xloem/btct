#include "hitbtc/MarketStreaming.hpp"

#include <iostream>

using namespace std;

int main()
{
	hitbtc::MarketStreaming hbms;

	int snapshotCount = 0;
	while (snapshotCount < 2) {
		auto update = hbms.get();
		if (update.symbol != "BTCUSD") {
			continue;
		}
		std::cout << (update.snapshot ? "Snapshot" : "Update") << ": " << std::endl;
		std::cout << "\tSeqNo: " << update.seqNo << " " << "timestamp: " << update.recvd.time_since_epoch().count() << "\t" << (update.exchangeWorking ? "working" : "not working") << std::endl;
		if (update.snapshot) {
			++ snapshotCount;
			std::cout << "\t" << update.asks.size() << " asks, " << update.bids.size() << " bids, " << update.trades.size() << " trades" << std::endl;
		} else {
			std::cout << "\t";
			if (!update.asks.empty()) {
				std::cout << "Asks: ";
				for (auto & ask : update.asks)
					std::cout << ask.size << " BTC for $" << ask.price << "/BTC" << ", ";
			}
			if (!update.bids.empty()) {
				std::cout << "Bids: ";
				for (auto & bid : update.bids)
					std::cout << bid.size << " BTC for $" << bid.price << "/BTC" << ", ";
			}
			if (!update.trades.empty()) {
				std::cout << "Trades: ";
				for (auto & trade : update.trades)
					std::cout << trade.size << " BTC for $" << trade.price << "/BTC" << ", ";
			}
			std::cout << std::endl;
		}
	}

	return 0;
}
