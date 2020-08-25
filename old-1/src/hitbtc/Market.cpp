#include "hitbtc/Market.hpp"

namespace hitbtc {

Market::Market()
{
}

void Market::update()
{
	while (streaming.available()) {
		auto update = streaming.get();

	}
}

}
