#include <iostream>

using namespace std;

int main()
{
	unsigned long long lastTime = 0;
	unsigned long accumulatedActivity;

	while (cin) {
		unsigned long long time;
		unsigned long activity;
		cin >> time >> activity;
		time /= 60 * 60; // hours
		if (time == lastTime) {
			accumulatedActivity += activity;
		} else {
			if (lastTime) cout << lastTime << " " << accumulatedActivity << endl;
			accumulatedActivity = activity;
			lastTime = time;
		}
	}
	
	return 0;
}
