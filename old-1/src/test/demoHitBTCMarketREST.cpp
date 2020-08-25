#include "hitbtc/MarketREST.hpp"

#include <ctime>
#include <iomanip>
#include <iostream>

using namespace std;

std::string time_to_str(std::chrono::system_clock::time_point tp) {
	std::time_t time = std::chrono::system_clock::to_time_t(tp);
	//return std::put_time(std::localtime(&time), "%A %c %Z");
	char timestr[128];
	std::strftime(timestr, sizeof(timestr), "%A %c %Z", std::localtime(&time));
	return timestr;
};

int main()
{
	hitbtc::MarketREST hbmr;

	std::cout << time_to_str(hbmr.time()) << std::endl;

	for (auto & p : hbmr.tickers()) {
		std::cout << p.first << ": " << p.second.last << ",";
	}
	std::cout << endl;

	auto symbols = hbmr.symbols();
	for (auto & symbol : symbols ) {
		std::cout << symbol.name << ",";
	}
	std::cout << std::endl;

	auto symbol = symbols[2].name;

	std::cout << symbol << ": " << std::endl;
		
	std::cout << "\tlast: " << hbmr.ticker(symbol).last << std::endl;

	auto orderbook = hbmr.orderbook(symbol);
	std::cout << "\task: " << orderbook.asks[0].price << " bid: " << orderbook.bids[0].price << std::endl;
	
	auto trades = hbmr.trades( symbol, hbmr.time() - std::chrono::minutes(30));
	for (auto & trade : trades) {
		std::cout << "	" << trade.id << " " << time_to_str(trade.timestamp) << ": " << (trade.side == hitbtc::MarketREST::Trade::BUY ? "buy" : "sell") << " " << trade.amount << " BTC for $" << trade.price << std::endl;
	}

	trades = hbmr.trades( symbol, trades[0].id);
	for (auto & trade : trades) {
		std::cout << "	" << trade.id << " " << time_to_str(trade.timestamp) << ": " << (trade.side == hitbtc::MarketREST::Trade::BUY ? "buy" : "sell") << " " << trade.amount << " BTC for $" << trade.price << std::endl;
	}

	trades = hbmr.trades( symbol, -1, -1, trades.size());
	for (auto & trade : trades) {
		std::cout << "	" << trade.id << " " << time_to_str(trade.timestamp) << ": " << (trade.side == hitbtc::MarketREST::Trade::BUY ? "buy" : "sell") << " " << trade.amount << " BTC for $" << trade.price << std::endl;
	}
	

	return 0;
}
