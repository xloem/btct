#include "util/CSV.cpp"
#include "util/URIFile.cpp"

#include <vector>
#include <string>
#include <cstring>

struct Tradeset
{
	unsigned long long time;
	double btcWeightedValue;
	double btcVolume;
	double valueWeightedValue;
	double valueVolume;
	double btcDeweightedValue;
	double btcDevolume;
	double valueDeweightedValue;
	double valueDevolume;
	void out() {
		btcWeightedValue = valueVolume / btcVolume;
		valueDeweightedValue = btcDevolume / valueDevolume;
		valueWeightedValue /= valueVolume;
		btcDeweightedValue /= btcDevolume;
		std::cout.precision(10);
		std::cout << time << "," <<
			btcWeightedValue << "," << btcVolume << "," <<
			valueWeightedValue << "," << valueVolume << "," <<
			btcDeweightedValue << "," << btcDevolume << "," <<
			valueDeweightedValue << "," << valueDevolume <<
			std::endl;
	}
};

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
	int argstart;
	unsigned long long span = strtoull(argv[1],NULL,0);
	if (span == 0) {
		argstart = 1;
		span = 60 * 60 * 24 * 7;
	} else {
		argstart = 2;
	}
	for (int i = argstart; i < argc; ++ i)
		tradeFerry.add(argv[i]);
	Tradeset ts;
	ts.time = 0;
	while (!tradeFerry.eof()) {
		Trade t = tradeFerry.get();
		if (t.time < 1272000000) continue;
		if (t.time >= ts.time + span) {
			if (ts.time && ts.btcVolume)
				ts.out();
			ts.time = t.time;
			ts.btcVolume = 0;
			ts.valueVolume = 0;
			ts.btcWeightedValue = 0;
			ts.valueWeightedValue = 0;
			ts.btcDevolume = 0;
			ts.valueDevolume = 0;
			ts.btcDeweightedValue = 0;
			ts.valueDeweightedValue = 0;
		}
		if (t.volume && t.value) {
			ts.btcVolume += t.volume;
			ts.valueVolume += t.volume * t.value;
			ts.btcDevolume += 1. / t.volume;
			ts.valueDevolume += 1. / (t.volume * t.value);
			ts.valueWeightedValue += t.value * t.volume * t.value;
			ts.btcDeweightedValue += t.value / t.volume;
		}
	}
	ts.out();
}
