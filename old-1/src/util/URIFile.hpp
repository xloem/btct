#pragma once

#include <memory>
#include <string>

#include <boost/property_tree/ptree.hpp>

class URIFile
{
public:
	URIFile(std::string uri, bool gz = false);
	bool available();
	bool eof();
	boost::property_tree::ptree getJSON();

	std::unique_ptr<std::istream> stream;

private:
	std::unique_ptr<std::istream> backstream;
};
