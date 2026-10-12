#pragma once
#include <stdint.h>
struct TwoWire {
  void begin(); void setClock(uint32_t); void beginTransmission(uint8_t); void write(uint8_t);
  uint8_t endTransmission(); uint8_t requestFrom(uint8_t, uint8_t); int read();
} extern Wire;
