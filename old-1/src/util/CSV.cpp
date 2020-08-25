#include "CSV.hpp"

CSV::CSV(std::string uri)
: uriFile(uri, uri[uri.size()-1] == 'z')
{ }


bool CSV::available()
{
	return uriFile.available();
}

std::vector<std::string> CSV::get()
{
	std::string str;
	std::getline(*uriFile.stream, str);
	std::stringstream ss; ss << str;
	std::vector<std::string> ret;
	std::string item;
	while (std::getline(ss, item, ','))
		ret.push_back(item);
	return ret;
}

bool CSV::eof()
{
	return uriFile.eof();
}
