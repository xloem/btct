#include "hitbtc/MarketREST.hpp"
#include "util/URIFile.hpp"


namespace hitbtc {

using integer = MarketREST::integer;
using number = MarketREST::number;
using server_clock = MarketREST::server_clock;
using duration = std::chrono::duration<unsigned long long, std::milli>;


static boost::property_tree::ptree request(std::string path)
{
	return URIFile("https://api.hitbtc.com/api/1/public/" + path).getJSON();
}


static server_clock::time_point parseTimestamp(boost::property_tree::ptree const & pt)
{
	duration ms(pt.get_value<duration::rep>());
	return server_clock::time_point(std::chrono::duration_cast<server_clock::duration>(ms));
}

server_clock::time_point MarketREST::time()
{
	return parseTimestamp(request("time").get_child("timestamp"));
}


std::vector<MarketREST::Symbol> MarketREST::symbols()
{
	std::vector<Symbol> ret;
	auto pt = request("symbols");
	for (auto & pts : pt.get_child("symbols")) {
		Symbol sym = {
			pts.second.get<std::string>("symbol"),
			pts.second.get<number>("step"),
			pts.second.get<number>("lot"),
			pts.second.get<std::string>("currency"),
			pts.second.get<std::string>("commodity"),
			pts.second.get<number>("takeLiquidityRate"),
			pts.second.get<number>("provideLiquidityRate")
		};
		ret.push_back(sym);
	}
	return ret;
};


static MarketREST::Ticker parseTicker(boost::property_tree::ptree const & pt)
{
	MarketREST::Ticker ret = {
		pt.get<number>("last"),
		pt.get<number>("bid"),
		pt.get<number>("ask"),
		pt.get<number>("high"),
		pt.get<number>("low"),
		pt.get<number>("volume"),
		pt.get<number>("open"),
		pt.get<number>("volume_quote"),
		parseTimestamp(pt.get_child("timestamp"))
	};
	return ret;
}

MarketREST::Ticker MarketREST::ticker(std::string symbol)
{
	return parseTicker(request(symbol + "/ticker"));
}

std::map<std::string,MarketREST::Ticker> MarketREST::tickers()
{
	std::map<std::string,Ticker> ret;
	for (auto & pt : request("ticker")) {
		ret.emplace(pt.first, parseTicker(pt.second));
	}
	return ret;
}

MarketREST::OrderBook MarketREST::orderbook(std::string symbol)
{
	OrderBook ret;
	auto pt = request(symbol + "/orderbook");
	for (auto & pts : pt.get_child("asks")) {
		auto it = pts.second.begin();
		number price = it->second.get_value<number>();
		number size = (++it)->second.get_value<number>();
		ret.asks.push_back({price, size});
	}
	for (auto & pts : pt.get_child("bids")) {
		auto it = pts.second.begin();
		number price = it->second.get_value<number>();
		number size = (++it)->second.get_value<number>();
		ret.bids.push_back({price, size});
	}
	return ret;
}

static std::vector<MarketREST::Trade> parseTrades(boost::property_tree::ptree const & pt)
{
	std::vector<MarketREST::Trade> ret;
	for (auto & pts : pt.get_child("trades")) {
		auto it = pts.second.begin();
		integer id = it->second.get_value<integer>();
		number price = (++it)->second.get_value<number>();
		number amount = (++it)->second.get_value<number>();
		server_clock::time_point timestamp = parseTimestamp((++it)->second);
		MarketREST::Trade::Side side = (++it)->second.data() == "buy" ? MarketREST::Trade::Side::BUY : MarketREST::Trade::Side::SELL;

		MarketREST::Trade trade = {id, price, amount, timestamp, side};
		ret.emplace_back(trade);
	}
	return ret;
}


std::vector<MarketREST::Trade> MarketREST::trades(std::string symbol,
                                                  integer begin,
						  integer end,
                                                  integer results,
                                                  integer start_index,
                                                  Trade::Sorting sorting)
{
	if (begin < 0) {
		if (start_index != 0 && results != 1000) {
			results += start_index;
			if (results > 1000)
				results = 1000;
		}
		auto ret = parseTrades(request(symbol + "/trades/recent?side=true" +
			"&max_results=" + results.str()
		));
		if (sorting == Trade::ASCENDING) {
			ret.resize(ret.size() - start_index.template convert_to<std::size_t>());
			std::reverse(ret.begin(), ret.end());
		} else {
			ret.erase(ret.begin(), ret.begin() + start_index.template convert_to<std::size_t>());
		}
		return ret;
	} else {
		-- begin;
		return parseTrades(request(symbol + "/trades?side=true&by=trade_id" +
			"&from=" + begin.str() +
			(end < 0 ? "" : "&till=" + end.str()) + 
			"&sort=" + (sorting == Trade::DESCENDING ? "desc" : "asc") +
			"&start_index=" + start_index.str() +
			"&max_results=" + results.str()
		));
	}
}
std::vector<MarketREST::Trade> MarketREST::trades(std::string symbol,
                                                  server_clock::time_point begin,
                                                  integer results,
                                                  integer start_index,
                                                  Trade::Sorting sorting)
{
	duration from = std::chrono::duration_cast<duration>(begin.time_since_epoch());
	return parseTrades(request(symbol + "/trades?side=true&by=ts" +
		"&from=" + std::to_string(from.count()) +
		"&sort=" + (sorting == Trade::DESCENDING ? "desc" : "asc") +
		"&start_index=" + start_index.str() +
		"&max_results=" + results.str()
	));
}
std::vector<MarketREST::Trade> MarketREST::trades(std::string symbol,
                                                  server_clock::time_point begin,
						  server_clock::time_point end,
                                                  integer results,
                                                  integer start_index,
                                                  Trade::Sorting sorting)
{
	duration from = std::chrono::duration_cast<duration>(begin.time_since_epoch());
	duration till = std::chrono::duration_cast<duration>(end.time_since_epoch());
	return parseTrades(request(symbol + "/trades?side=true&by=ts" +
		"&from=" + std::to_string(from.count()) +
		"&till=" + std::to_string(till.count()) +
		"&sort=" + (sorting == Trade::DESCENDING ? "desc" : "asc") +
		"&start_index=" + start_index.str() +
		"&max_results=" + results.str()
	));
}

}
