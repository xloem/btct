#include <iostream>
#include <deque>

using namespace std;

template <typename T>
void metrics(T start, T const & end)
{
	auto min = *start;
	auto max = *start;
	double avg = 0;
	unsigned long ct = 0;
	for (; start != end; ++ start) {
		if (*start <min) min = *start;
		if (*start >max) max = *start;
		++ ct;
		avg += *start;
	}
	avg /= ct;
	//cout << min << " " << max << " " << avg;
	cout << avg;
}

void output(std::deque<unsigned long> & backlog, std::deque<unsigned long> & upcoming)
{
	metrics(upcoming.begin(), upcoming.end());
	for (auto back : backlog) {
		cout << " " << back;
	}
	cout << endl;
}

int main()
{
	std::deque<unsigned long> backlog;
	std::deque<unsigned long> upcoming;
	unsigned long unit_size = 24;
	while (cin) {
		unsigned long time;
		unsigned long activity;
		cin >> time >> activity;
		if (backlog.size() < unit_size*2) {
			backlog.push_back(activity);
		} else if (upcoming.size() < unit_size) {
			upcoming.push_back(activity);
			if (upcoming.size() == unit_size) output(backlog, upcoming);
		} else {
			backlog.pop_front();
			backlog.push_back(upcoming.front());
			upcoming.pop_front();
			upcoming.push_back(activity);
			output(backlog, upcoming);
		}
	}
}
