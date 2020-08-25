#include "LinearRegression.hpp"

#include <cmath>
#include <cassert>

LinearRegression::LinearRegression()
: sumX(0), sumY(0), sumWeight(0), sumSlope(0), sumSlopeWeight(0)
{}

void LinearRegression::add(DataPoint dp)
{
	sumX += dp.x*dp.weight; sumY += dp.y*dp.weight; sumWeight += dp.weight;
	for (auto & d : data) {
		auto dx = dp.x - d.x;
		auto dy = dp.y - d.y;
		if (!dx) continue;
		sumSlope += (dy / dx) * d.weight * dp.weight;
		sumSlopeWeight += d.weight * dp.weight;
	}
	data.push_back(dp);
}

void LinearRegression::remove(DataPoint dp)
{
	for (auto it = data.begin(); assert(it != data.end()),true; ++ it)
	{
		if (it->x != dp.x || it->y != dp.y || it->weight != dp.weight) continue;
		data.erase(it);
		break;
	}
	sumX -= dp.x*dp.weight; sumY -= dp.y*dp.weight; sumWeight -= dp.weight;
	for (auto & d : data) {
		auto dx = dp.x - d.x;
		auto dy = dp.y - d.y;
		if (!dx) continue;
		sumSlope -= (dy / dx) * d.weight *dp.weight;
		sumSlopeWeight -= d.weight * dp.weight;
	}
}

DataPoint LinearRegression::mean() const
{
	DataPoint ret;
	ret.x = sumX / sumWeight;
	ret.y = sumY / sumWeight;
	ret.weight = slope();
	return ret;
}

double LinearRegression::slope() const
{
	return sumSlope / sumSlopeWeight;
}

double LinearRegression::y(double x) const
{
	auto mean = this->mean();
	return (x - mean.x) * mean.weight + mean.y;
}

double LinearRegression::stdDev() const
{
	double sumSquares = 0;
	double sumWeights = 0;
	for (auto & d : data)
	{
		double delta = (d.y - y(d.x)) * d.weight;
		sumSquares += delta * delta;
		sumWeights += d.weight * d.weight;
	}
	return sqrt(sumSquares / sumWeights);
}

double LinearRegression::avgDev() const
{
	double sumDev = 0;
	double sumWeight =0;
	for (auto & d : data)
	{
		double delta = d.y - y(d.x);
		sumDev += std::abs(delta) * d.weight;
		sumWeight += d.weight;
	}
	return sumDev / sumWeight;
}
