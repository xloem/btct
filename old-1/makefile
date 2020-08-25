CPPFLAGS=-Isrc
CXXFLAGS=-std=c++1y -g -Wall
LDFLAGS=$(CXXFLAGS)
LDLIBS=-lboost_system -lcrypto -lssl -lPocoNet -lPocoNetSSL -lPocoFoundation -lpthread -lgmp
CC=$(CXX)
run: src/test/demoHitBTCMarketStreaming
	./$<
dbg: src/test/demoHitBTCMarketStreaming
	gdb $<
src/test/Main: src/test/Main.o src/util/Pusher.o src/util/WebSocket.o src/util/Waiter.o src/util/CSV.o src/util/URIFile.o
src/test/demoHitBTCMarketREST: src/test/demoHitBTCMarketREST.o src/hitbtc/MarketREST.o src/util/URIFile.o
src/test/demoHitBTCMarketStreaming: src/test/demoHitBTCMarketStreaming.o src/hitbtc/MarketStreaming.o src/util/WebSocket.o src/util/Waiter.o
clean:
	-rm src/*/*.o
	-rm src/test/Main src/test/demoHitBTCMarketREST src/test/demoHitBTCMarketStreaming
	-rm src/process/trade2weighted src/process/lastmonth src/process/weightedreg


data/api.bitcoincharts.com: /run/utmp
	-cd data && wget --ca-directory=../res -T 60 --mirror https://api.bitcoincharts.com/v1/csv/ && cd .. && touch $@

data/weeklyweighted.csv: src/process/trade2weighted data/api.bitcoincharts.com
	$< data/api.bitcoincharts.com/v1/csv/*USD.csv.gz |tee $@

data/lastmonthtrades.csv: src/process/lastmonth data/api.bitcoincharts.com
	$< data/api.bitcoincharts.com/v1/csv/*USD.csv.gz |tee $@

data/lastmonthhourly.csv: src/process/trade2weighted data/lastmonthtrades.csv
	$< $$((60*60)) data/lastmonthtrades.csv | tee $@

data/lines.csv: src/process/weightedreg data/weeklyweighted.csv
	$< data/weeklyweighted.csv |tee $@
