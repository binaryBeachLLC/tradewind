// Host unit test for the firmware's payload packer and downlink parser (make test).
// Reads the same golden_vectors.json as decoder/test_decoder.js, so the C packer and the
// JS decoder are checked against one set of hand-worked bytes.
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "../tradewind/payload.h"
#include "../tradewind/sensors.h"

// ---- minimal JSON reader (objects, arrays, numbers, strings, true/false/null) ----
struct J {
  enum T { NUL, BOOL, NUM, STR, ARR, OBJ } t = NUL;
  double n = 0;
  bool b = false;
  std::string s;
  std::vector<J> a;
  std::map<std::string, J> o;
  const J& operator[](const std::string& k) const { return o.at(k); }
  bool has(const std::string& k) const { return o.count(k) != 0; }
};

struct Parser {
  const std::string& s;
  size_t i = 0;
  void ws() { while (i < s.size() && isspace((unsigned char)s[i])) i++; }
  std::string str() {
    std::string r;
    i++;  // opening quote
    while (s[i] != '"') { if (s[i] == '\\') i++; r += s[i++]; }
    i++;
    return r;
  }
  J val() {
    ws();
    J v;
    char c = s[i];
    if (c == '{') {
      v.t = J::OBJ; i++; ws();
      if (s[i] == '}') { i++; return v; }
      for (;;) { ws(); std::string k = str(); ws(); i++; v.o[k] = val(); ws(); if (s[i++] == '}') break; }
    } else if (c == '[') {
      v.t = J::ARR; i++; ws();
      if (s[i] == ']') { i++; return v; }
      for (;;) { v.a.push_back(val()); ws(); if (s[i++] == ']') break; }
    } else if (c == '"') { v.t = J::STR; v.s = str(); }
    else if (s.compare(i, 4, "true") == 0) { v.t = J::BOOL; v.b = true; i += 4; }
    else if (s.compare(i, 5, "false") == 0) { v.t = J::BOOL; i += 5; }
    else if (s.compare(i, 4, "null") == 0) { i += 4; }
    else { v.t = J::NUM; char* e; v.n = strtod(s.c_str() + i, &e); i = e - s.c_str(); }
    return v;
  }
};

static std::vector<uint8_t> unhex(std::string h) {
  std::string t;
  for (char c : h) if (!isspace((unsigned char)c)) t += c;
  std::vector<uint8_t> out;
  for (size_t k = 0; k + 1 < t.size(); k += 2) out.push_back((uint8_t)std::stoul(t.substr(k, 2), nullptr, 16));
  return out;
}

static std::string tohex(const uint8_t* b, size_t n) {
  std::string r;
  char x[3];
  for (size_t k = 0; k < n; k++) { snprintf(x, 3, "%02X", b[k]); r += x; }
  return r;
}

static int fails = 0, passes = 0;
static void expect(bool ok, const std::string& what, const std::string& detail = "") {
  if (ok) { passes++; printf("  ok    %s\n", what.c_str()); }
  else { fails++; printf("  FAIL  %s %s\n", what.c_str(), detail.c_str()); }
}

int main(int argc, char** argv) {
  const char* path = argc > 1 ? argv[1] : "test/golden_vectors.json";
  std::ifstream f(path);
  if (!f) { fprintf(stderr, "cannot open %s\n", path); return 2; }
  std::stringstream ss;
  ss << f.rdbuf();
  std::string text = ss.str();
  Parser p{text};
  J g = p.val();

  for (const J& v : g["measurement"].a) {
    const J& in = v["in"];
    payload::Measurement m{};
    m.flags = (uint8_t)in["flags"].n;
    m.air_t_c = (float)in["air_t_c"].n;
    m.air_rh = (float)in["air_rh"].n;
    m.soil_pct = (float)in["soil_pct"].n;
    m.rain_tips = (uint16_t)in["rain_tips"].n;
    m.vbat_mv = (uint16_t)in["vbat_mv"].n;
    m.int_t_c = (float)in["int_t_c"].n;
    m.int_rh = (float)in["int_rh"].n;
    m.vsolar_mv = (uint16_t)in["vsolar_mv"].n;
    uint8_t buf[32];
    size_t len = payload::pack_measurement(m, buf);
    std::vector<uint8_t> want = unhex(v["hex"].s);
    std::string got = tohex(buf, len), exp = tohex(want.data(), want.size());
    expect(len == payload::MEASUREMENT_LEN && got == exp, "measurement: " + v["name"].s, "got " + got + " want " + exp);
  }

  for (const J& v : g["health"].a) {
    const J& in = v["in"];
    payload::Health h{};
    h.fw_major = (uint8_t)in["fw_major"].n;
    h.fw_minor = (uint8_t)in["fw_minor"].n;
    h.uptime_days = (uint16_t)in["uptime_days"].n;
    h.uplinks = (uint16_t)in["uplinks"].n;
    h.rejoins = (uint8_t)in["rejoins"].n;
    h.last_rssi_dbm = (int16_t)in["last_rssi_dbm"].n;
    h.last_snr_db = (float)in["last_snr_db"].n;
    h.vbat_min_mv = (uint16_t)in["vbat_min_mv"].n;
    h.int_t_max_c = (float)in["int_t_max_c"].n;
    h.charge_minutes = (uint16_t)in["charge_minutes"].n;
    h.interval_min = (uint8_t)in["interval_min"].n;
    h.reset_reason = (uint8_t)in["reset_reason"].n;
    uint8_t buf[32];
    size_t len = payload::pack_health(h, buf);
    std::vector<uint8_t> want = unhex(v["hex"].s);
    std::string got = tohex(buf, len), exp = tohex(want.data(), want.size());
    expect(len == payload::HEALTH_LEN && got == exp, "health: " + v["name"].s, "got " + got + " want " + exp);
  }

  for (const J& v : g["downlink"].a) {
    std::vector<uint8_t> b = unhex(v["hex"].s);
    payload::Downlink dl{};
    bool ok = payload::parse_downlink(b.data(), b.size(), dl);
    bool want = v["valid"].b;
    bool good = ok == want && (!ok || (dl.cmd == (int)v["cmd"].n && dl.value == (uint16_t)v["value"].n));
    expect(good, "downlink " + (v["hex"].s.empty() ? std::string("(empty)") : v["hex"].s) + (want ? " parsed" : " rejected"));
  }

  // Sensirion's datasheet example: CRC-8 of 0xBE 0xEF is 0x92.
  const uint8_t beef[2] = {0xBE, 0xEF};
  expect(sht_crc8(beef, 2) == 0x92, "SHT4x CRC-8 matches the datasheet example (0xBEEF -> 0x92)");

  printf("\n%d passed, %d failed\n", passes, fails);
  return fails ? 1 : 0;
}
