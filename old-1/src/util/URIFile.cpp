#include "URIFile.hpp"

#include <boost/property_tree/json_parser.hpp>

#include "Poco/Net/HTTPStreamFactory.h"
#include "Poco/Net/HTTPSStreamFactory.h"
#include "Poco/Net/FTPStreamFactory.h"
#include "Poco/Net/SSLManager.h"
#include "Poco/Net/KeyConsoleHandler.h"
#include "Poco/Net/ConsoleCertificateHandler.h"

using namespace Poco;
using namespace Poco::Net;

class PocoNet {
public:
	PocoNet() {
		//initializeSSL();
		HTTPStreamFactory::registerFactory();
		HTTPSStreamFactory::registerFactory();
		FTPStreamFactory::registerFactory();

		SharedPtr<InvalidCertificateHandler> ptrCert = new ConsoleCertificateHandler(false); // ask the user via console
		Context::Ptr ptrContext = new Context(Context::CLIENT_USE, "", "", ""/*"rootcert.pem"*/, Context::VERIFY_RELAXED, 9, true/*false*/, "ALL:!ADH:!LOW:!EXP:!MD5:@STRENGTH");
		SSLManager::instance().initializeClient(0, ptrCert, ptrContext);
	}
	~PocoNet() {
		//uninitializeSSL();
	}
} pocoNet;

#include <sstream>
#include <memory>
#include "Poco/URI.h"
#include "Poco/URIStreamOpener.h"
#include "Poco/StreamCopier.h"
#include "Poco/InflatingStream.h"

URIFile::URIFile(std::string uri, bool gz)
{
	auto & uriOpener = Poco::URIStreamOpener::defaultOpener();
	stream = std::unique_ptr<std::istream>(uriOpener.open(uri));
	if (gz) {
		backstream = std::move(stream);
		stream = std::unique_ptr<std::istream>(new Poco::InflatingInputStream(*backstream, InflatingStreamBuf::STREAM_GZIP));
	}
}


bool URIFile::available()
{
	return stream->rdbuf()->in_avail() != 0;
}

bool URIFile::eof()
{
	return stream->eof();
}

boost::property_tree::ptree URIFile::getJSON()
{
	boost::property_tree::ptree pt;
	read_json(*stream, pt);
	return pt;
}
