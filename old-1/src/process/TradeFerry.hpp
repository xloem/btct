#include "util/CSV.cpp"

#include <cstring>
#include <string>
#include <vector>

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
