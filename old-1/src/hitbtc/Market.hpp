#pragma once

#include "hitbtc/MarketREST.hpp"
#include "hitbtc/MarketStreaming.hpp"

namespace hitbtc {

class Market : public Waiter
{
public:
	Market();
	void update();

private:
	MarketREST rest;
	MarketStreaming streaming;
};

}
