#include "inputs.h"
#include "board.h"
#include "config.h"
#include <Arduino.h>

namespace {

volatile uint16_t rain_tips = 0;
volatile uint32_t rain_last_ms = 0;
volatile uint32_t hall_down_ms = 0;
volatile uint8_t  hall_event = HALL_NONE;

// Rain: the RC network (1 M / 10 k / 22 nF) already turns reed bounce into one clean falling edge
// (sim/out/rain_debounce). The lockout is a second line of defense against a chattering reed.
void rain_isr() {
  uint32_t now = millis();
  if (now - rain_last_ms >= RAIN_LOCKOUT_MS) {
    rain_tips++;
    rain_last_ms = now;
  }
}

// Hall: DRV5032FB output is low while a magnet is near. Tap = shorter than HALL_HOLD_REJOIN_MS.
void hall_isr() {
  uint32_t now = millis();
  if (digitalRead(PIN_HALL_N) == LOW) {
    hall_down_ms = now;
  } else if (hall_down_ms != 0) {
    hall_event = (now - hall_down_ms >= HALL_HOLD_REJOIN_MS) ? HALL_HOLD : HALL_TAP;
    hall_down_ms = 0;
  }
}

}  // namespace

void inputs_init() {
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, LOW);
  pinMode(PIN_RAIN_IN, INPUT);   // 1 M external pull-up; the ~40 k internal one would draw ~80 uA if the reed rests closed
  pinMode(PIN_HALL_N, INPUT);    // push-pull output, no pull needed
  attachInterrupt(PIN_RAIN_IN, rain_isr, FALLING);
  attachInterrupt(PIN_HALL_N, hall_isr, CHANGE);
}

uint16_t rain_tips_total() {
  noInterrupts();
  uint16_t t = rain_tips;
  interrupts();
  return t;
}

HallEvent hall_take_event() {
  noInterrupts();
  HallEvent e = (HallEvent)hall_event;
  hall_event = HALL_NONE;
  interrupts();
  return e;
}


void led_blink(uint8_t times, uint16_t on_ms, uint16_t off_ms) {
  for (uint8_t i = 0; i < times; i++) {
    digitalWrite(PIN_LED, HIGH);
    delay(on_ms);
    digitalWrite(PIN_LED, LOW);
    if (i + 1 < times) delay(off_ms);
  }
}
