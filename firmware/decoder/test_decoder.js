// node firmware/decoder/test_decoder.js
// 1. A JS mirror of the C packer (float32 maths, half-away-from-zero rounding) must produce the golden hex.
// 2. decodeUplink(golden hex) must give the golden decoded values.
// 3. encodeDownlink / decodeDownlink must agree with the golden downlink table.
"use strict";
const assert = require("assert");
const path = require("path");
const fs = require("fs");
const codec = require("./ttn_decoder.js");

const golden = JSON.parse(fs.readFileSync(path.join(__dirname, "../test/golden_vectors.json"), "utf8"));
const hex = (s) => Uint8Array.from(Buffer.from(s.replace(/\s+/g, ""), "hex"));
const toHex = (b) => Buffer.from(b).toString("hex").toUpperCase();

// ---- JS mirror of payload.cpp ----
const f32 = Math.fround;
const lround = (x) => (x < 0 ? -Math.round(-x) : Math.round(x));        // lroundf: half away from zero
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const q = (v, step, lo, hi) => clamp(lround(f32(f32(v) / f32(step))), lo, hi);
const vcode = (mv) => clamp(lround(f32((mv - 2500) / f32(10))), 0, 254);
const put16 = (a, v) => a.push((v >> 8) & 0xff, v & 0xff);

function packMeasurement(m) {
  const a = [m.flags];
  const airOk = m.flags & 0x10, soilOk = m.flags & 0x20, intOk = m.flags & 0x40;
  put16(a, (airOk ? q(m.air_t_c, 0.01, -32768, 32766) : 0x7fff) & 0xffff);
  a.push(airOk ? q(m.air_rh, 0.5, 0, 200) : 0xff);
  a.push(soilOk ? q(m.soil_pct, 0.5, 0, 200) : 0xff);
  put16(a, m.rain_tips);
  a.push(vcode(m.vbat_mv));
  a.push(intOk ? q(m.int_t_c, 0.5, -128, 126) & 0xff : 0x7f);
  a.push(intOk ? q(m.int_rh, 0.5, 0, 200) : 0xff);
  a.push(q(m.vsolar_mv, 25, 0, 255));
  return a;
}

function packHealth(h) {
  const a = [h.fw_major, h.fw_minor];
  put16(a, h.uptime_days);
  put16(a, h.uplinks);
  a.push(h.rejoins, clamp(h.last_rssi_dbm, -128, 127) & 0xff, q(h.last_snr_db, 0.25, -128, 127) & 0xff,
         vcode(h.vbat_min_mv), q(h.int_t_max_c, 0.5, -128, 127) & 0xff,
         clamp(Math.floor((h.charge_minutes + 5) / 10), 0, 255), h.interval_min, h.reset_reason);
  return a;
}

let n = 0;
function check(name, fn) {
  fn();
  n++;
  console.log("  ok  " + name);
}

for (const v of golden.measurement) {
  check(`measurement pack   : ${v.name}`, () => assert.strictEqual(toHex(packMeasurement(v.in)), toHex(hex(v.hex))));
  check(`measurement decode : ${v.name}`, () => {
    const res = codec.decodeUplink({ fPort: 1, bytes: hex(v.hex) });
    assert.ok(!res.errors, res.errors);
    assert.deepStrictEqual(res.data, v.out);
    assert.strictEqual(res.warnings.includes("battery low"), v.out.battery_low);
  });
}

for (const v of golden.health) {
  check(`health pack        : ${v.name}`, () => assert.strictEqual(toHex(packHealth(v.in)), toHex(hex(v.hex))));
  check(`health decode      : ${v.name}`, () => {
    const res = codec.decodeUplink({ fPort: 2, bytes: hex(v.hex) });
    assert.deepStrictEqual(res.data, v.out);
  });
}

for (const v of golden.downlink) {
  check(`downlink ${v.hex || "(empty)"} -> ${v.valid ? "valid" : "rejected"}`, () => {
    const res = codec.decodeDownlink({ fPort: 10, bytes: hex(v.hex) });
    if (!v.valid) return assert.ok(res.errors);
    assert.deepStrictEqual(res.data, v.js);
    const enc = codec.encodeDownlink({ data: v.js });
    assert.strictEqual(enc.fPort, 10);
    assert.strictEqual(toHex(enc.bytes), v.hex);
  });
}

check("wrong lengths and ports are errors", () => {
  assert.ok(codec.decodeUplink({ fPort: 1, bytes: new Uint8Array(10) }).errors);
  assert.ok(codec.decodeUplink({ fPort: 2, bytes: new Uint8Array(11) }).errors);
  assert.ok(codec.decodeUplink({ fPort: 7, bytes: new Uint8Array(11) }).errors);
  assert.ok(codec.encodeDownlink({ data: { set_interval_s: 30 } }).errors);
});

// Round trip over a sweep: every quantised value must decode within half a step of the input.
check("round-trip sweep (2 000 random frames)", () => {
  let seed = 7;
  const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
  for (let i = 0; i < 2000; i++) {
    const m = {
      flags: 0x70, air_t_c: -40 + rnd() * 100, air_rh: rnd() * 100, soil_pct: rnd() * 100,
      rain_tips: Math.floor(rnd() * 65536), vbat_mv: 2500 + Math.floor(rnd() * 2540),
      int_t_c: -40 + rnd() * 100, int_rh: rnd() * 100, vsolar_mv: Math.floor(rnd() * 6375),
    };
    const d = codec.decodeUplink({ fPort: 1, bytes: Uint8Array.from(packMeasurement(m)) }).data;
    assert.ok(Math.abs(d.air_temperature_c - m.air_t_c) <= 0.0051, "air t");
    assert.ok(Math.abs(d.air_humidity_pct - m.air_rh) <= 0.25 + 1e-6, "air rh");
    assert.ok(Math.abs(d.soil_moisture_pct - m.soil_pct) <= 0.25 + 1e-6, "soil");
    assert.strictEqual(d.rain_tips_total, m.rain_tips);
    assert.ok(Math.abs(d.battery_v * 1000 - m.vbat_mv) <= 5 + 1e-6, "vbat");
    assert.ok(Math.abs(d.internal_temperature_c - Math.min(m.int_t_c, 63)) <= 0.25 + 1e-6, "int t");
    assert.ok(Math.abs(d.solar_v * 1000 - m.vsolar_mv) <= 12.5 + 1e-6, "solar");
  }
});

console.log(`\n${n} checks passed`);
