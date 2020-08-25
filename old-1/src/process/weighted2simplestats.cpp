#include "util/CSV.cpp"
#include "util/URIFile.cpp"
#include "util/Statistic.hpp"

#include <cassert>
#include <cmath>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

struct SimpleStatistic
{
  unsigned long long time;
  Statistic<double> statistic;
};

int main(int argc, const char ** argv)
{
  std::vector<SimpleStatistic> statistics;

  CSV outer(argv[1]);
  for (auto outerLine = outer.get(); outerLine.size(); outerLine = outer.get())
  {
    unsigned long long outerTime = strtoull(outerLine[0].c_str(),NULL,10);
    double outerValue = strtod(outerLine[7].c_str(),NULL);
    outerValue = log(outerValue);

    CSV inner(argv[1]);
    size_t timeIndex = 0;
    for (auto innerLine = inner.get(); innerLine.size(); innerLine = inner.get())
    {
        unsigned long long innerTime = strtoull(innerLine[0].c_str(),NULL,10);
        if (innerTime <= outerTime) continue;
        double innerValue = strtod(innerLine[7].c_str(),NULL);
        innerValue = log(innerValue);
        assert( !isnan(innerValue) );

        if (statistics.size() <= timeIndex)
        {
          statistics.resize(timeIndex + 1);
          statistics[timeIndex].time = innerTime - outerTime;
        }

        statistics[timeIndex].statistic.add(innerValue - outerValue);

        if (statistics[timeIndex].time >= 60 * 60 * 24 * 365)
          break;

        ++ timeIndex;
    }
  }

  for (SimpleStatistic & s : statistics)
  {
    s.statistic.calculate();
    std::cout << s.time << "," << exp(s.statistic.avg()) << "," << exp(s.statistic.stdDev()) << "," << exp(s.statistic.min()) << "," << exp(s.statistic.max()) << "," << s.statistic.size() << std::endl;
  }
}
