// Interrupt-driven inputs (rain gauge, magnet on the lid) and the status LED.
#pragma once
#include <stdint.h>

enum HallEvent : uint8_t { HALL_NONE = 0, HALL_TAP, HALL_HOLD };

void      inputs_init();
uint16_t  rain_tips_total();     // cumulative, wraps at 65536 (the payload carries it as-is)
HallEvent hall_take_event();     // returns and clears the last event

// LED patterns (blocking, a few hundred ms at most, only on user-visible events)
void led_blink(uint8_t times, uint16_t on_ms, uint16_t off_ms);
inline void led_ack()      { led_blink(1, 40, 0); }      // magnet tap seen
inline void led_joining()  { led_blink(2, 30, 120); }    // join attempt started
inline void led_joined()   { led_blink(3, 60, 90); }     // network joined
inline void led_error()    { led_blink(1, 600, 0); }     // join/send failed
