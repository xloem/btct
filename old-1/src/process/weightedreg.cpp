#include "util/CSV.cpp"
#include "util/URIFile.cpp"
#include <vector>
#include <string>
#include <cstring>
#include <cmath>

struct DataItem
{
	unsigned long long time;
	double value;
	double logValue;
	double volume;
	DataItem(unsigned long long time, double value, double volume)
	: time(time), value(value), logValue(log10(value)), volume(volume)
	{}
	DataItem()
	: time(0), value(0), logValue(0), volume(0)
	{}
};


struct Dataset
{
	std::vector<DataItem> data;

	bool weighted;

	Dataset(bool weighted)
	: weighted(weighted)
	{}
	
	double timeSum, lvSum, lvCount;
	double meanTime, meanLV;
	double timeOffset;

	double lvOverTimeSum;
	double lvOverTimeCount;
	double meanLvOverTime;

	void add(DataItem const &d) {
		for (auto & d2 : data)  {
			double lvDelta = d.logValue - d2.logValue;
			double timeDelta = d.time - d2.time;
			double weight = weighted ? (d.volume + d2.volume) : 1;
			lvOverTimeSum += (lvDelta / timeDelta) * weight;
			lvOverTimeCount += weight;
		}
		meanLvOverTime = lvOverTimeSum / lvOverTimeCount;
		data.emplace_back(d);
		if (data.size() > 1) {
			timeOffset = (data[1].time - data[0].time) / 2;
			if (weighted) {
				lvCount += d.volume;
				lvSum += d.volume * d.logValue;
				timeSum += d.volume * d.time;
			} else {
				lvCount ++;
				lvSum += d.logValue;
				timeSum += d.time;
			}
			meanLV = lvSum / lvCount;
			meanTime = timeSum / lvCount + timeOffset;
		} else {
			lvCount = weighted ? d.volume : 1;
			lvSum = lvCount * d.logValue;
			timeSum = lvCount * d.time;
			meanTime = d.time;
			meanLV = d.logValue;
			lvOverTimeCount = 0;
			lvOverTimeSum = 0;
		}
	}

	std::string summary() {
		std::stringstream ret;
		ret.precision(10);
		auto time = data[data.size()-1].time;
		ret << " time: " << time
			<< " expected: " << pow(10,meanLvOverTime * (time - meanTime) + meanLV)
			<< " oay: " << (1/meanLvOverTime)/60./60./24./365.25
			<< " slope: " << meanLvOverTime
			<< " meanTime: " << meanTime
			<< " mean: " << meanLV
		;
		return ret.str();
	}
	std::string csv() {
		std::stringstream ret;
		ret.precision(16);
		ret << meanLvOverTime << "," << meanTime << "," << meanLV;
		return ret.str();
	}
};

int main(int argc, const char** argv)
{
	CSV csv(argv[1]);
	Dataset btcWeightedWeighted(true);
	Dataset btcWeightedUnweighted(false);
	Dataset valueWeightedWeighted(true);
	Dataset valueWeightedUnweighted(false);
	Dataset btcDeweightedWeighted(true);
	Dataset btcDeweightedUnweighted(false);
	Dataset valueDeweightedWeighted(true);
	Dataset valueDeweightedUnweighted(false);
	for (;;) {
		auto line = csv.get();
		if (!line.size())
			break;
		unsigned long long time = strtoull(line[0].c_str(),NULL,10);
		double bvalue = strtod(line[1].c_str(),NULL);
		double bvolume = strtod(line[2].c_str(),NULL);
		double vvalue = strtod(line[3].c_str(),NULL);
		double vvolume = strtod(line[4].c_str(),NULL);
		double bdvalue = strtod(line[5].c_str(),NULL);
		double bdvolume = strtod(line[6].c_str(),NULL);
		double vdvalue = strtod(line[7].c_str(),NULL);
		double vdvolume = strtod(line[8].c_str(),NULL);
		btcWeightedUnweighted.add({time, bvalue, bvolume});
		btcWeightedWeighted.add({time, bvalue, bvolume});
		valueWeightedUnweighted.add({time, vvalue, vvolume});
		valueWeightedWeighted.add({time, vvalue, vvolume});
		btcDeweightedUnweighted.add({time, bdvalue, bdvolume});
		btcDeweightedWeighted.add({time, bdvalue, bdvolume});
		valueDeweightedUnweighted.add({time, vdvalue, vdvolume});
		valueDeweightedWeighted.add({time, vdvalue, vdvolume});
	}

	std::cerr << "BTC   weighted /   weighted" << btcWeightedWeighted.summary() << std::endl;
	std::cerr << "BTC   weighted / unweighted" << btcWeightedUnweighted.summary() << std::endl;
	std::cerr << "Value weighted /   weighted" << valueWeightedWeighted.summary() << std::endl;
	std::cerr << "Value weighted / unweighted" << valueWeightedUnweighted.summary() << std::endl;
	std::cerr << "BTC   deweighted /   weighted" << btcDeweightedWeighted.summary() << std::endl;
	std::cerr << "BTC   deweighted / unweighted" << btcDeweightedUnweighted.summary() << std::endl;
	std::cerr << "Value deweighted /   weighted" << valueDeweightedWeighted.summary() << std::endl;
	std::cerr << "Value deweighted / unweighted" << valueDeweightedUnweighted.summary() << std::endl;
	
	std::cout << btcWeightedWeighted.csv() << std::endl;
	std::cout << btcWeightedUnweighted.csv() << std::endl;
	std::cout << valueWeightedWeighted.csv() << std::endl;
	std::cout << valueWeightedUnweighted.csv() << std::endl;
	std::cout << btcDeweightedWeighted.csv() << std::endl;
	std::cout << btcDeweightedUnweighted.csv() << std::endl;
	std::cout << valueDeweightedWeighted.csv() << std::endl;
	std::cout << valueDeweightedUnweighted.csv() << std::endl;
}
