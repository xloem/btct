#include <string>
#include "URIFile.hpp"

class CSV
{
public:
	CSV(std::string uri);
	bool available();
	std::vector<std::string> get();
	bool eof();
	
private:
	URIFile uriFile;
};
