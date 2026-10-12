// Minimal stand-ins for the RUI3 Arduino API, only so `make check` can compile the sketch on a PC.
// They catch typos and type errors; they say nothing about runtime behaviour on the RAK3172.
#pragma once
#include <stdint.h>
#include <math.h>
enum { PA0, PA1, PA4, PA8, PA9, PA10, PB2, PB3, PB4, PB5, PB12 };
enum { LOW = 0, HIGH = 1, INPUT = 0, OUTPUT = 1, FALLING = 2, CHANGE = 3 };
uint32_t millis();
void delay(uint32_t);
void pinMode(int, int);
void digitalWrite(int, int);
int digitalRead(int);
int analogRead(int);
void analogReadResolution(int);
void attachInterrupt(int, void (*)(), int);
void noInterrupts();
void interrupts();
struct SerialStub { void begin(int); } extern Serial;

#define RAK_LORAMAC_STATUS_OK 0
#define RAK_REGION_US915 5
#define RAK_LORA_OTAA 1
typedef struct { uint8_t Port; uint8_t* Buffer; uint16_t BufferSize; int16_t Rssi; int8_t Snr; } SERVICE_LORA_RECEIVE_T;
struct Setter8 { bool set(uint8_t*, int); };
struct LoRaWan {
  struct { bool set(); } nwm;
  Setter8 deui, appeui, appkey;
  struct { bool set(int); } band, njm;
  struct { bool set(uint16_t*); } mask;
  struct { bool set(bool); } adr;
  struct { bool set(uint8_t); } rety;
  bool join();
  bool send(uint8_t, uint8_t*, uint8_t, bool, uint8_t);
  void registerJoinCallback(void (*)(int32_t));
  void registerSendCallback(void (*)(int32_t));
  void registerRecvCallback(void (*)(SERVICE_LORA_RECEIVE_T*));
};
struct SystemApi { struct { void all(uint32_t); } sleep; void reboot(); };
struct Api { LoRaWan lorawan; SystemApi system; } extern api;
