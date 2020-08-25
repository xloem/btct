#include "util/Waiter.hpp"

std::mutex Waiter::mtx;
std::condition_variable Waiter::cv;

void Waiter::wait() {
	std::unique_lock<std::mutex> lk(mtx);
	cv.wait(lk);
}

void Waiter::notify() {
	std::lock_guard<std::mutex> lk(mtx);
	cv.notify_one();
}
