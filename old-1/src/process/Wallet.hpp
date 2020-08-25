#include <string>
#include <map>
#include <list>

typedef std::string Currency;

class Sum
{
public:
	Sum(Currency const currency, double const amount);
	Sum(Sum & source, double price, Currency currency, double amount);

	Sum(Sum const &) = default;

	Sum(Sum && one, Sum && two);
	bool mergeable(Sum const & two);
	bool empty();

	Currency getCurrency() const { return currency;}
	double getAmount() const { return value.at(currency); }
	bool hasValue(Currency c) const { return value.count(c); }
	double getValue(Currency c) const { return value.at(c); }

	Currency getSource() const { return source; }
	double getDelta() const { return delta; }
	double getRatio() const { return ratio; }

private:

	Currency currency;	

	Currency source;
	double delta;
	double ratio;

	std::map<Currency, double> value;
};

typedef unsigned long long TradeTime;

class Wallet
{
public:
	void add(Currency c, double amount);
	double getBalance(Currency c);
	void trade(TradeTime time, Currency src, double srcAmount, Currency dst, double dstAmount);

	std::string summary();
	std::string recentSummary();
private:
	bool mergeDown();

	std::list<Sum> balance;
	std::multimap<TradeTime, Sum> trades;
};
