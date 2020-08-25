#include "util/CSV.cpp"
#include "util/URIFile.cpp"

#include <vector>
#include <string>
#include <cstring>

struct Trade
{
	unsigned long long time;
	double value;
	double volume;
	Trade(std::vector<std::string> const & line)
	: time{strtoull(line[0].c_str(),NULL,10)},
	  value{strtod(line[1].c_str(),0)},
	  volume{strtod(line[2].c_str(),0)}
	{ }
};

class TradeFerry
{
public:
	TradeFerry() {}
	void add(std::string name) {
		csvs.emplace_back(name);
		auto & c = csvs[csvs.size()-1];
		std::vector<std::string> line;
		do {
			line = c.get();
			if (c.eof()) {
				csvs.pop_back();
				return;
			} 
		} while (!line.size());
		trades.emplace_back(line);
	}
	bool eof() {
		return trades.size() == 0;
	}
	Trade get() {
		Trade ret = trades[0];
		int idx = 0;
		for (size_t i = 1; i < trades.size(); ++ i) {
			if (trades[i].time < ret.time) {
				ret = trades[i];
				idx = i;
			}
		}
		std::vector<std::string> line;
		do {
			line = csvs[idx].get();
			if (csvs[idx].eof()) {
				trades.erase(trades.begin()+idx);
				csvs.erase(csvs.begin()+idx);
				return ret;
			}
		} while(!line.size());
		trades[idx] = line;
		return ret;
	}
private:
	std::vector<CSV> csvs;
	std::vector<Trade> trades;
};

int main(int argc, const char ** argv)
{
	TradeFerry tradeFerry;
	for (int i = 1; i < argc; ++ i)
		tradeFerry.add(argv[i]);
	long long span = 60 * 60 * 24 * ((365.25)/12);
	std::deque<Trade> trades;
	while (!tradeFerry.eof()) {
		trades.push_back(tradeFerry.get());
		while (trades.front().time < trades.back().time - span)
			trades.pop_front();
	}
	for (auto & t : trades) {
		std::cout << t.time << "," << t.value << "," << t.volume << "," << (t.volume * t.value) << std::endl;
	}
}
