#pragma once

#include <boost/multiprecision/gmp.hpp>
#include <chrono>
#include <map>
#include <string>
#include <vector>

namespace hitbtc {

class MarketREST
{
public:
	typedef std::chrono::system_clock server_clock;
	typedef boost::multiprecision::mpf_float_50 number;
	typedef boost::multiprecision::mpz_int integer;

	server_clock::time_point time();

	struct Symbol
	{
		std::string name;
		number step;
		number lot;
		std::string currency;
		std::string commodity;
		number takeLiquidityRate; // taker fee
		number provideLiquidityRate; // provider rebate
	};
	std::vector<Symbol> symbols();

	struct Ticker
	{
		number last; // last price
		number bid; // highest buy order
		number ask; // lowest sell order
		number high; // highest price per last 24h + last incomplete minute
		number low; // lowest price per last 24h + last incomplete minute
		number volume; // currency volume per last 24h + last incomplete minute
		number open;
		number volume_quote; // commodity volume per last 24h + last incomplete minute
		server_clock::time_point timestamp;
	};
	Ticker ticker(std::string symbol);
	std::map<std::string, Ticker> tickers();

	struct OrderBook
	{
		struct Order {
			number price;
			number size;
		};
		std::vector<Order> asks;
		std::vector<Order> bids;
	};
	OrderBook orderbook(std::string symbol);

	struct Trade
	{
		enum Side {
			//UNKNOWN,
			BUY,
			SELL
		};
		enum Sorting {
			ASCENDING,
			DESCENDING
		};

		integer id;
		number price;
		number amount;
		server_clock::time_point timestamp;
		Side side;
	};
	std::vector<Trade> trades(std::string symbol, integer begin = -1, integer end = -1, integer results = 1000, integer start_index = 0, Trade::Sorting sorting = Trade::Sorting::ASCENDING);
	std::vector<Trade> trades(std::string symbol, server_clock::time_point begin, integer results = 1000, integer start_index = 0, Trade::Sorting sorting = Trade::Sorting::ASCENDING);
	std::vector<Trade> trades(std::string symbol, server_clock::time_point begin, server_clock::time_point end, integer results = 1000, integer start_index = 0, Trade::Sorting sorting = Trade::Sorting::ASCENDING);
};

}
