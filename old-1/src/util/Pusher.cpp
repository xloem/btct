#include "Pusher.hpp"
#include "WebSocket.hpp"

#include <boost/property_tree/ptree.hpp>
#include <boost/property_tree/json_parser.hpp>
#include <cassert>
#include <future>
#include <sstream>

Pusher::Pusher(std::string key)
: ws(std::string("wss://ws.pusherapp.com:443/app/") + key + "?protocol=7")
{
	ws.wait(); available();
	std::cerr << "socket_id = " << socket_id << std::endl;
}

Pusher::~Pusher()
{ }

void Pusher::subscribe(std::string channel)
{
	std::string req = "{\"event\":\"pusher:subscribe\",\"data\":{\"channel\":\"";
	req += channel;
	req += "\"}}";
	ws.send(req);
	ws.wait(); available();
}

size_t Pusher::available()
{
	while (ws.available()) {
		auto data = ws.get();
		boost::property_tree::ptree pt;
		std::stringstream ss;

		ss << data.message;
		read_json(ss, pt);

		std::string event = pt.get<std::string>("event");
		if (event == "pusher:connection_established") {
			std::string data = pt.get<std::string>("data");
			ss.clear();
			ss << data;
			read_json(ss, pt);
			socket_id = pt.get<std::string>("socket_id");
			activity_timeout = pt.get<double>("activity_timeout");
		} else if (event == "pusher.error") {
			std::cerr << "PUSHER: " << pt.get<std::string>("data.message") << std::endl;
			throw(pt.get<std::string>("data.message"));
		} else if (event == "pusher_internal:subscription_succeeded") {
			std::string channel = pt.get<std::string>("channel");
		} else {
			try {
				Data d;
				std::string channel = pt.get<std::string>("channel");
				d.recvd = data.recvd;
				d.event = event;
				d.data = pt.get<std::string>("data");
				d.channel = channel;
				dataQueue.emplace_back(d);
			} catch(boost::property_tree::ptree_bad_path) {
				std::cerr << data.message << std::endl;
			}
		}
	}
	return dataQueue.size();
}

void Pusher::wait()
{
	while (!available())
		ws.wait();
}

Pusher::Data Pusher::get()
{
	if (!available()) wait();
	auto ret = dataQueue.front();
	dataQueue.pop_front();
	return ret;
}
