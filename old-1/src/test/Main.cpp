#include "util/Pusher.hpp"
#include "util/WebSocket.hpp"

#include <iostream>
#include <sstream>
#include <boost/property_tree/json_parser.hpp>

/*#include <openssl/hmac.h>

std::string hmacsha256(std::string secret, std::string input) {
	unsigned char md[EVP_MAX_MD_SIZE];
	unsigned int len;
	HMAC(EVP_sha256(), (const unsigned char *)secret.c_str(), secret.size(), (const unsigned char *)input.c_str(), input.size(), md, &len);
	std::string ret;
	for (unsigned int i = 0; i < len; ++ i) {
		int nybbles[2] = { md[i] >> 4, md[i] & 0xf };
		for (int j = 0; j < 2; ++ j) {
			unsigned char c = nybbles[j];
			if (c < 10)
				ret += ('0' + c);
			else
				ret += ('A' - 10 + c);
		}
	}
	return ret;
}*/


int main()
{
	std::chrono::high_resolution_clock::time_point epoch;
	std::chrono::high_resolution_clock::time_point start = std::chrono::high_resolution_clock::now();;

	Pusher pusherBitStamp("de504dc5763aeef9ff52");
	//pusherBitStamp.subscribe("order_book");
	pusherBitStamp.subscribe("live_trades");

	WebSocket websocketHitBTC("ws://api.hitbtc.com");

	//std::string maxSeqSymbol;
	//unsigned long long maxSeq = 0;

	for (;;) {
		Waiter::wait();

		//std::cout << ".";
		
		while (pusherBitStamp.available()) {
			Pusher::Data data = pusherBitStamp.get();
			std::cout << "Bitstamp: " << data.channel << " " << data.event << "(" << (data.recvd - start).count() << "): " << data.data << std::endl;
		}

		unsigned long long lastSeqNo;
		WebSocket::Message msg("");

		while (websocketHitBTC.available()) {
			boost::property_tree::ptree pt;
			std::stringstream ss;
			try {
				msg = websocketHitBTC.get();
			} catch(WebSocket::Exception e) {
				websocketHitBTC.reconnect();
				continue;
			}
			std::cout << "HitBTC: " << msg.message << std::endl;
			ss << msg.message;
			read_json(ss, pt);

			unsigned long long seqNo;
			std::string symbol = pt.begin()->second.get<std::string>("symbol");
			if (symbol != "BTCUSD") continue;

			if (pt.begin()->first == "MarketDataIncrementalRefresh") {
				seqNo = pt.begin()->second.get<unsigned long long>("seqNo");
				if (seqNo != lastSeqNo + 1) {
					std::cout << "Non-monotonic incremental refresh for " << symbol << ":" << std::endl;
					std::cout << "    " << lastSeqNo << " -> " << seqNo << std::endl;
				}
				std::cout << ".";
			} else {
				seqNo = pt.begin()->second.get<unsigned long long>("snapshotSeqNo");
				if (seqNo == lastSeqNo) {
					std::cout << seqNo << ".";
					std::flush(std::cout);
					//std::cout << "Correct snapshot " << seqNo << " for " << symbol << std::endl;
				} else {
					std::cout << "Incorrect snapshot " << seqNo << " != " << lastSeqNo << " for " << symbol << std::endl;
				}
			}
			//if (seqNo > maxSeq) {
			//	maxSeq = seqNo;
			//	maxSeqSymbol = symbol;
			//}
			//if (symbol == "BTCUSD") {
			//	std::cout << seqNo << "  " << pt.begin()->first << " " << pt.begin()->second.get<std::string>("symbol") << std::endl;
			//}
			lastSeqNo = seqNo;
		}
	}

	return 0;
}
