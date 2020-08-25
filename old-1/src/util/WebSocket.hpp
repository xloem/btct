#pragma once

#include "util/Waiter.hpp"

#include <string>
#include <chrono>

#include <boost/property_tree/ptree.hpp>

class WebSocket : public Waiter
{
public:
friend class WebSocketHandler;
	WebSocket(std::string uri);
	~WebSocket();
	void reconnect();

	struct Message {
		std::chrono::high_resolution_clock::time_point recvd;
		std::string message;

		Message(std::string message);
		boost::property_tree::ptree getJSON() const;
	};

	class Exception : public std::runtime_error {
	public:
		Exception(std::string message);
	};

	void send(std::string message);

	Message get();
	size_t available();
	void wait();

private:
	static void notify() { Waiter::notify(); }
	std::string uri;
	class WebSocketHandler * wsh;
};

