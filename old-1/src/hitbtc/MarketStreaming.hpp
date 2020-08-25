#pragma once

#include "util/WebSocket.hpp"

#include <boost/multiprecision/gmp.hpp>

namespace hitbtc {

class MarketStreaming : private WebSocket
{
public:
	typedef boost::multiprecision::mpf_float_50 number;
	typedef boost::multiprecision::mpz_int integer;

	struct Order {
		number price;
		number size;
	};

	struct Update {
		std::chrono::high_resolution_clock::time_point recvd;
		bool snapshot;
		integer seqNo;
		std::string symbol;
		bool exchangeWorking;
		std::vector<Order> asks;
		std::vector<Order> bids;
		std::vector<Order> trades;
	};

	MarketStreaming();

	Update get() const;

	using WebSocket::available;
	using WebSocket::wait;
};

}
