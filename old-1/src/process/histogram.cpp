#include "URIFile.cpp"
#include "CSV.cpp"
#include "LinearRegression.cpp"

int main(int argc, const char **argv)
{
	CSV csv("weeklyweighted.csv");
	LinearRegression lr;
	auto line = csv.get();
	while (!csv.eof()) {
		auto line = csv.get();
		if (line.empty()) continue;
		unsigned long long time = strtoull(line[0].c_str(),NULL,10);
		double vvalue = strtod(line[3].c_str(),NULL);
		//double vvolume = strtod(line[4].c_str(),NULL);
		DataPoint dp;
		dp.x = time;
		dp.y = log10(vvalue);
		dp.weight = 1;//vvolume;
		lr.add(dp);
	}
	auto mean = lr.mean();
	auto stdDev = lr.stdDev();
	auto avgDev = lr.avgDev();
	std::cerr << "Mean X=" << mean.x << " Mean Y=" << mean.y << " Slope=" << (mean.weight*60*60*24*365.25/12) << "/yr" << std::endl;
	std::cerr << "StdDev=" << stdDev << " AvgDev=" << avgDev << std::endl;

	std::vector<double> buckets;
	buckets.resize(20);
	double max = 0, total = 0;
	double pre = 0, post = 0;


	for (auto it = lr.begin(); it != /*--*/ lr.end(); ++ it) {
		auto delta = it->y - lr.y(it->x);
		/*++ it;
		auto weight = it->x;
		-- it;
		weight -= it->x;*/
		auto weight = it->weight;
		delta = (delta * buckets.size()/4) / stdDev + buckets.size()/2;
		int bucket = std::round(delta);
		if (bucket < 0) {
			pre += weight;
		} else if (bucket >= (int)buckets.size()) {
			post += weight;
		} else {
			buckets[bucket] += weight;
			if (buckets[bucket] > max)
				max = buckets[bucket];
		}
		total += weight;
	}

	double sum = pre;
	
	for (size_t j = 0; j < buckets.size(); ++ j)
	{
		auto & bucket = buckets[j];
		if (j < 10) std::cerr << "0";
		std::cerr << j << ": ";
		for (int i = 0; i < bucket * 75 / max; ++ i)
			std::cerr << "#";
		sum += bucket;
		std::cerr << " " << std::round(sum * 100 / total) << "%";
		std::cerr << std::endl;
	}
	return 0;
}
