#pragma once

#include <condition_variable>
#include <mutex>

/**
 * A Waiter is an object which must wait on some incoming events in order to
 * process data.
 * By collecting all such behaviors together, it's possible some day to have
 * one condition variable per thread to wait on all events at once.
 */

class Waiter {
public:
	static void wait();

protected:
	static void notify();

private:
	static std::mutex mtx;
	static std::condition_variable cv;
};
