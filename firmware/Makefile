# Host-side tests. The firmware itself builds with the RAK RUI3 Arduino core (see README.md).
CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -Werror

.PHONY: test test-c test-js check clean

test: test-c test-js check

# Compiles the sketch against test/stubs (RUI3 API stand-ins): catches typos and type errors only.
check:
	@mkdir -p build && cp -n tradewind/secrets.h.example build/secrets.h 2>/dev/null || true
	$(CXX) $(CXXFLAGS) -DARDUINO -Itest/stubs -Ibuild -Itradewind -fsyntax-only tradewind/sensors.cpp
	$(CXX) $(CXXFLAGS) -DARDUINO -Itest/stubs -Ibuild -Itradewind -fsyntax-only tradewind/inputs.cpp
	$(CXX) $(CXXFLAGS) -DARDUINO -Itest/stubs -Ibuild -Itradewind -include Arduino.h -fsyntax-only -x c++ tradewind/tradewind.ino
	@echo "sketch compiles against the RUI3 stubs"

test-c: build/test_payload
	./build/test_payload test/golden_vectors.json

test-js:
	node decoder/test_decoder.js

build/test_payload: test/test_payload.cpp tradewind/payload.cpp tradewind/payload.h tradewind/sensors.cpp tradewind/sensors.h
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ test/test_payload.cpp tradewind/payload.cpp tradewind/sensors.cpp

clean:
	rm -rf build
