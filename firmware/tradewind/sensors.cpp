#include "sensors.h"
#include "board.h"
#include "config.h"

uint8_t sht_crc8(const uint8_t* data, int len) {  // Sensirion CRC-8: poly 0x31, init 0xFF
  uint8_t crc = 0xFF;
  for (int i = 0; i < len; i++) {
    crc ^= data[i];
    for (int b = 0; b < 8; b++) crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x31) : (uint8_t)(crc << 1);
  }
  return crc;
}

#ifdef ARDUINO
#include <Arduino.h>
#include <Wire.h>

namespace {

float adc_mv(uint8_t pin, int samples) {
  uint32_t sum = 0;
  for (int i = 0; i < samples; i++) sum += analogRead(pin);
  return (sum / (float)samples) * ADC_FULL_SCALE_MV / ((1 << ADC_BITS) - 1);
}

}  // namespace

void sensors_init() {
  pinMode(PIN_SENSOR_EN, OUTPUT);
  digitalWrite(PIN_SENSOR_EN, LOW);
  pinMode(PIN_VBAT_SENSE_EN, OUTPUT);
  digitalWrite(PIN_VBAT_SENSE_EN, LOW);
  pinMode(PIN_CHG_N, INPUT);    // external 100 k pull-ups, keep the internal ones off
  pinMode(PIN_PGOOD_N, INPUT);
  analogReadResolution(ADC_BITS);
  Wire.begin();
  Wire.setClock(100000);        // long probe cable: stay at 100 kHz
}

ShtReading sht4x_read(uint8_t addr) {
  ShtReading r{false, 0, 0};
  Wire.beginTransmission(addr);
  Wire.write(0xFD);             // measure T & RH, high precision
  if (Wire.endTransmission() != 0) return r;
  delay(10);                    // 8.3 ms max conversion
  if (Wire.requestFrom(addr, (uint8_t)6) != 6) return r;
  uint8_t b[6];
  for (int i = 0; i < 6; i++) b[i] = Wire.read();
  if (sht_crc8(&b[0], 2) != b[2] || sht_crc8(&b[3], 2) != b[5]) return r;
  uint16_t rt = (b[0] << 8) | b[1], rh = (b[3] << 8) | b[4];
  r.t_c = -45.0f + 175.0f * rt / 65535.0f;
  r.rh = -6.0f + 125.0f * rh / 65535.0f;
  if (r.rh < 0) r.rh = 0;
  if (r.rh > 100) r.rh = 100;
  r.ok = true;
  return r;
}

float soil_read_pct(bool& ok) {
  digitalWrite(PIN_SENSOR_EN, HIGH);
  delay(SOIL_WARMUP_MS);
  float mv = adc_mv(PIN_SOIL_ADC, 16);
  digitalWrite(PIN_SENSOR_EN, LOW);
  // R21 pulls a missing probe to 0 V; a real probe never reads that low.
  ok = mv > 300.0f && mv < 3100.0f;
  float pct = 100.0f * (SOIL_DRY_MV - mv) / (SOIL_DRY_MV - SOIL_WET_MV);
  return pct < 0 ? 0 : (pct > 100 ? 100 : pct);
}

uint16_t vbat_read_mv() {
  digitalWrite(PIN_VBAT_SENSE_EN, HIGH);
  delay(VBAT_SETTLE_MS);
  float mv = adc_mv(PIN_VBAT_ADC, 8) * VBAT_DIVIDER;
  digitalWrite(PIN_VBAT_SENSE_EN, LOW);
  return (uint16_t)(mv + 0.5f);
}

uint16_t vsolar_read_mv() { return (uint16_t)(adc_mv(PIN_SOLAR_SENSE, 8) * SOLAR_DIVIDER + 0.5f); }

bool charger_charging()   { return digitalRead(PIN_CHG_N) == LOW; }
bool charger_power_good() { return digitalRead(PIN_PGOOD_N) == LOW; }

#endif  // ARDUINO
