#include "WebSocket.hpp"

#define _WEBSOCKETPP_CPP11_STL_
#include <websocketpp/config/asio_client.hpp>
#include <websocketpp/client.hpp>

#include <condition_variable>
#include <iostream>
#include <thread>

#include <boost/property_tree/json_parser.hpp>

typedef websocketpp::lib::shared_ptr<boost::asio::ssl::context> ssl_ctx_ptr;

using websocketpp::lib::placeholders::_1;
using websocketpp::lib::placeholders::_2;

static ssl_ctx_ptr on_tls_init(websocketpp::connection_hdl hdl) {
	ssl_ctx_ptr ctx(new boost::asio::ssl::context(boost::asio::ssl::context::tlsv1));
	ctx->set_options(boost::asio::ssl::context::default_workarounds | boost::asio::ssl::context::no_sslv2 | boost::asio::ssl::context::single_dh_use);
	return ctx;
}

template <typename config>
struct no_alog_config : public config {
	typedef no_alog_config<config> type;
	using config::base;
	using config::concurrency_type;
	using config::request_type;
	using config::response_type;
	using config::message_type;
	using config::con_msg_manager_type;
	using config::endpoint_msg_manager_type;
	using config::alog_type;
	using config::elog_type;
	using config::rng_type;

	using config::transport_config;
	using config::transport_type;

	static const websocketpp::log::level alog_level =
		websocketpp::log::alevel::none;
};

class WebSocketHandler {
public:
	virtual ~WebSocketHandler() {};
	virtual void send(std::string msg) = 0;

	struct Event {
		enum {
			MESSAGE,
			EXCEPTION
		} type;
		WebSocket::Message message;

		Event(std::string message)
		: type(MESSAGE), message(message)
		{ }

		Event(std::string message, decltype(type) type)
		: type(type), message(message)
		{ }
	};

	std::mutex msgsMtx;
	std::deque<Event> msgs;
	std::condition_variable msgsCv;

	static void notify() { WebSocket::notify(); }
};

template <typename config>
class Client : public WebSocketHandler {
public:
friend class WebSocket;

	typedef no_alog_config<config> Config;
	typedef websocketpp::client<Config> WSClient;

private:
	void setAlive(websocketpp::connection_hdl hdl) {
		std::lock_guard<std::mutex> lock(timeoutMtx);
		conHdl = hdl;
		timeout = std::chrono::steady_clock::now() + std::chrono::seconds(5);
	}

	void onMessage(websocketpp::connection_hdl hdl, typename Config::message_type::ptr msg)
	{
		Event res(msg->get_payload());

		setAlive(hdl);

		std::lock_guard<std::mutex> msgsLock(msgsMtx);
		msgs.emplace_back(res);
		msgsCv.notify_one();

		WebSocketHandler::notify();
	}

	void onOpen(websocketpp::connection_hdl hdl)
	{
		std::cerr << "Connected." << std::endl;
	
		if (timeoutTh.joinable())
			timeoutTh.join();

		setAlive(hdl);
	
		timeoutTh = std::thread(std::bind(&Client<config>::checkingTimeout,this));
	}
	void onClose(websocketpp::connection_hdl hdl)
	{
		auto ec = ws.get_con_from_hdl(hdl)->get_ec();
		Event res(ec ? ec.message() : "Connection closed", WebSocketHandler::Event::EXCEPTION);

		std::cerr << "Disconnected ... " << res.message.message << std::endl;
		
		std::lock_guard<std::mutex> msgsLock(msgsMtx);
		msgs.emplace_back(res);
		msgsCv.notify_one();

		WebSocketHandler::notify();
	}

	void onPong(websocketpp::connection_hdl hdl, std::string)
	{
		std::cerr << "Pong" << std::endl;

		if (timeoutTh.joinable())
			timeoutTh.join();

		setAlive(hdl);

		timeoutTh = std::thread(std::bind(&Client<config>::checkingTimeout,this));
	}

	std::thread th;

	std::thread timeoutTh;
	std::mutex timeoutMtx;
	std::chrono::steady_clock::time_point timeout;
	websocketpp::connection_hdl conHdl;

	WSClient ws;
	typename WSClient::connection_ptr con;

	void setHandlers();

	void checkingTimeout() {
		std::chrono::steady_clock::time_point deadline;

		for(;;) {
			{ std::lock_guard<std::mutex> lock(timeoutMtx);
				deadline = timeout;
			}
			std::this_thread::sleep_until(deadline);
			{ std::lock_guard<std::mutex> lock(timeoutMtx);
				deadline = std::chrono::steady_clock::now();
				if (deadline > timeout) {
					// no contact for 5 seconds
					break;
				}
			}
		}

		// pong timeout handler is onClose()
		// so ping timeouts will be treated as connection closed
		ws.ping(conHdl, "");
	}
	
public:
	Client(std::string uri) {
		ws.init_asio();

		setHandlers();

		websocketpp::lib::error_code ec;
		con = ws.get_connection(uri, ec);
		if (ec)
			throw WebSocket::Exception(ec.message());

		ws.connect(con);

		th = std::thread(std::bind(&WSClient::run,&ws));
	}
	virtual ~Client() {
		ws.stop();
		th.join();
		if (timeoutTh.joinable())
			timeoutTh.join();
	}

	void send(std::string msg)
	{
		con->send(msg, websocketpp::frame::opcode::value::text);
	}
};

template <>
void Client<websocketpp::config::asio_tls_client>::setHandlers() {
	ws.set_message_handler(websocketpp::lib::bind(&Client::onMessage,this,::_1,::_2));
	ws.set_open_handler(websocketpp::lib::bind(&Client::onOpen,this,::_1));
	ws.set_fail_handler(websocketpp::lib::bind(&Client::onClose,this,::_1));
	ws.set_close_handler(websocketpp::lib::bind(&Client::onClose,this,::_1));
	//ws.set_ping_handler(websocketpp::lib::bind(&Client::setAlive,this,::_1));
	ws.set_pong_handler(websocketpp::lib::bind(&Client::onPong,this,::_1,::_2));
	ws.set_pong_timeout_handler(websocketpp::lib::bind(&Client::onClose,this,::_1));

	ws.set_tls_init_handler(on_tls_init);
}
template <>
void Client<websocketpp::config::asio_client>::setHandlers() {
	ws.set_message_handler(websocketpp::lib::bind(&Client::onMessage,this,::_1,::_2));
	ws.set_open_handler(websocketpp::lib::bind(&Client::onOpen,this,::_1));
	ws.set_fail_handler(websocketpp::lib::bind(&Client::onClose,this,::_1));
	ws.set_close_handler(websocketpp::lib::bind(&Client::onClose,this,::_1));
	//ws.set_ping_handler(websocketpp::lib::bind(&Client::setAlive,this,::_1));
	ws.set_pong_handler(websocketpp::lib::bind(&Client::onPong,this,::_1,::_2));
	ws.set_pong_timeout_handler(websocketpp::lib::bind(&Client::onClose,this,::_1));
}

WebSocket::Message::Message(std::string message)
: recvd(std::chrono::high_resolution_clock::now()),
  message(message)
{ }

boost::property_tree::ptree WebSocket::Message::getJSON() const
{
	boost::property_tree::ptree pt;
	std::stringstream ss;
	ss << message;
	read_json(ss, pt);
	return pt;
}

WebSocket::Exception::Exception(std::string message)
: runtime_error(message)
{ }


WebSocket::WebSocket(std::string uri)
: uri(uri),
  wsh(0)
{
	reconnect();
}

WebSocket::~WebSocket()
{
	delete wsh;
}

void WebSocket::reconnect()
{
	if (wsh)
		delete wsh;
	if (uri[2] == 's' || (uri[2] == 't' && uri[4] == 's'))
		wsh = (WebSocketHandler*)new Client<websocketpp::config::asio_tls_client>(uri);
	else
		wsh = (WebSocketHandler*)new Client<websocketpp::config::asio_client>(uri);
}

void WebSocket::send(std::string message)
{
	wsh->send(message);
}

WebSocket::Message WebSocket::get()
{
	wait();

	std::lock_guard<std::mutex> lock(wsh->msgsMtx);

	auto event = wsh->msgs.front();
	wsh->msgs.pop_front();

	if (event.type == WebSocketHandler::Event::EXCEPTION)
		throw Exception(event.message.message);

	return event.message;
}

size_t WebSocket::available()
{
	std::lock_guard<std::mutex> lock(wsh->msgsMtx);
	return wsh->msgs.size();
}

void WebSocket::wait()
{
	std::unique_lock<std::mutex> lk(wsh->msgsMtx);
	while (wsh->msgs.empty())
		wsh->msgsCv.wait(lk);
}

