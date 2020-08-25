#include <vector>
#include <limits>

template <typename T>
class Statistic
{
public:
  T avg() const { return m_tAvg; }
  T min() const { return m_tMin; }
  T max() const { return m_tMax; }
  T stdDev() const { return sqrt(m_tVariance); }
  size_t size() const { return m_uiSize; }

  Statistic();
  void add(T value);
  void calculate();
  void clear();

private:
  std::vector<T> m_oValues;

  T m_tAvg;
  T m_tMin;
  T m_tMax;
  T m_tVariance;
  size_t m_uiSize;
};

template <typename T>
Statistic<T>::Statistic()
{
  clear();
}

template <typename T>
void Statistic<T>::add(T value)
{
  m_oValues.push_back(value);
}

template <typename T>
void Statistic<T>::calculate()
{
  size_t l_uiNewSize = m_uiSize + m_oValues.size();
  T l_tSum;

  l_tSum = m_tAvg * m_uiSize;
  for (T l_tVal : m_oValues)
  {
    l_tSum += l_tVal;
    if (l_tVal < m_tMin)
    {
      m_tMin = l_tVal;
    }
    if (l_tVal > m_tMax)
    {
      m_tMax = l_tVal;
    }
  }
  m_tAvg = l_tSum / l_uiNewSize;

  l_tSum = m_tVariance * m_uiSize;
  for (T l_tVal : m_oValues)
  {
    T l_tDelta = l_tVal - m_tAvg;
    l_tSum += l_tDelta * l_tDelta;
  }
  m_tVariance = l_tSum / l_uiNewSize;

  m_uiSize = l_uiNewSize;
  m_oValues.clear();
}

template <typename T>
void Statistic<T>::clear()
{
  m_tAvg = 0;
  m_tMin = std::numeric_limits<T>::max();
  m_tMax = std::numeric_limits<T>::min();
  m_tVariance = 0;
  m_uiSize = 0;
}
