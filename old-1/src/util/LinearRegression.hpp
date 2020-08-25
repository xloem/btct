#include <deque>

struct DataPoint
{
	double x;
	double y;
	double weight;
};

class LinearRegression
{
public:
	LinearRegression();
	void add(DataPoint dp);
	void remove(DataPoint dp);

	DataPoint front() const { return data.front(); }
	DataPoint back() const { return data.back(); }
	std::deque<DataPoint>::const_iterator begin() const { return data.begin(); }
	std::deque<DataPoint>::const_iterator end() const { return data.end(); }
	size_t size() const { return data.size(); }

	DataPoint mean() const;
	double slope() const;
	double y(double x) const;
	double stdDev() const;
	double avgDev() const;

	
private:
	std::deque<DataPoint> data;

	double sumX, sumY, sumWeight;
	double sumSlope, sumSlopeWeight;
};
