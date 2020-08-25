#include "Wallet.hpp"

#include <cassert>

Sum::Sum(Currency const currency, double const amount)
: currency{currency}
{
	value[currency] = amount;
}
Sum::Sum(Sum & source, double price, Currency currency, double amount)
: currency{currency}, value{source.value}
{
	auto sourceAmount = source.getAmount();
	assert(price <= sourceAmount);
	for (auto & v : value) {
		v.second = (v.second / sourceAmount) * price;
		source.value[v.first] -= v.second;
	}
	assert(value[source.currency] == price);
	this->source = source.currency;
	if (value.count(currency)) {
		delta = amount - getAmount();
		ratio = amount / getAmount();
	}
	value[currency] = amount;
}

Sum::Sum(Sum && one, Sum && two)
: currency{one.currency}, value{one.value}
{
	assert(one.mergeable(two));

	for (auto & c : value) {
		c.second += two.value[c.first];
	}
	one.value.clear();
	two.value.clear();
}

bool Sum::mergeable(Sum const & two)
{
	if (currency != two.currency) return false;
	if (value.size() != two.value.size()) return false;
	for (auto & kv : value)
		if (!two.value.count(kv.first))
			return false;
	return true;
}

bool Sum::empty()
{
	return !value.size() || !getAmount();
}

void Wallet::add(Currency c, double amount)
{
	balance.emplace_back(c, amount);
	mergeDown();
}

bool Wallet::mergeDown()
{
	auto & s = balance.back();
	for (auto it = balance.begin(); it != -- balance.end(); ++ it) {
		if (!s.mergeable(*it))
			continue;
		balance.emplace_back(std::move(s), std::move(*it));
		balance.erase(-- --balance.end());
		balance.erase(it);
		return true;
	}
	return false;
}

double Wallet::getBalance(Currency c)
{
	double ret = 0;
	for (auto & b : balance)
		if (b.getCurrency() == c)
			ret += b.getAmount();
	return ret;
}

void Wallet::trade(TradeTime time, Currency src, double srcAmount, Currency dst, double dstAmount)
{
	int pass = 0;
	for (auto it = balance.begin(); ; ++ it) {
	next:
		if (!pass) {
			if (it == balance.end()) {
				++ pass;
				it = balance.begin();
			}
		} else {
			assert(it != balance.end());
		}
		auto & s = *it;
		if (s.getCurrency() != src)
			continue;
		if (!pass && !s.hasValue(dst))
			continue;
		auto a = s.getAmount();
		if (a <= srcAmount) {
			auto d = dstAmount * a / srcAmount;
			balance.emplace_back(s, a, dst, d);
			trades.insert(std::pair<TradeTime,Sum>(time, balance.back()));
			srcAmount -= a;
			dstAmount -= d;
			auto old = it;
			++ it;
			assert(old->empty());
			balance.erase(old);
			goto next;
		}
		balance.emplace_back(s, srcAmount, dst, dstAmount);
		trades.insert(std::pair<TradeTime,Sum>(time, balance.back()));
		break;
	}
	for (;mergeDown(););
}

#include <sstream>

std::string Wallet::summary()
{
	std::stringstream ss;
	for (auto & s : balance) {
		ss << s.getAmount() << " " << s.getCurrency() << "  ";
	}
	ss << std::endl;
	for (auto & t : trades) {
		if (!t.second.getDelta())
			continue;
		ss << t.first << ": " << t.second.getDelta() << t.second.getCurrency() << " " << (t.second.getRatio()*100) << "%" << std::endl;
	}
	return ss.str();
}

std::string Wallet::recentSummary()
{
	std::stringstream ss;
	TradeTime time = trades.back().first;
	ss << time << ": ";
	for (auto it = trades.rend(); it->first == time; -- it) {
		if (!it->second.getDelta()) continue;
		ss << it->second->getDelta() << it->second->getCurrency() << " " << (it.second.getRatio()*100) << "%  ";
	}
	return ss.str();
}
