#include "WebSocket.hpp"

#include <string>
#include <chrono>
#include <deque>


class Pusher
{
public:

	Pusher(std::string key);
	~Pusher();

	void subscribe(std::string key);

	struct Data
	{
		std::chrono::high_resolution_clock::time_point recvd;
		std::string event;
		std::string data;
		std::string channel;
	};

	size_t available();
	void wait();
	Data get();

private:
	std::string socket_id;
	double activity_timeout;
	
	WebSocket ws;
	std::deque <Data> dataQueue;
};
