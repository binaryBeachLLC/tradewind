// Tradewind TW-1 payload codec for The Things Stack (v3) and ChirpStack v4.
// Paste the whole file into the device profile / application "Custom JavaScript formatter".
// ES5 only (both servers run a restricted JS engine). Format: firmware/PAYLOAD.md.

var RAIN_MM_PER_TIP = 0.2;  // standard 0.2 mm tipping bucket; change for your gauge

function u16(b, i) { return (b[i] << 8) | b[i + 1]; }
function s16(b, i) { var v = u16(b, i); return v > 32767 ? v - 65536 : v; }
function s8(v) { return v > 127 ? v - 256 : v; }
function r(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
function vbat(code) { return r((2500 + code * 10) / 1000, 3); }

function decodeMeasurement(b) {
  var f = b[0];
  var airOk = (f & 0x10) !== 0, soilOk = (f & 0x20) !== 0, intOk = (f & 0x40) !== 0;
  var tips = u16(b, 5);
  return {
    rapid: (f & 0x01) !== 0,
    charging: (f & 0x02) !== 0,
    power_good: (f & 0x04) !== 0,
    battery_low: (f & 0x08) !== 0,
    air_temperature_c: airOk ? r(s16(b, 1) * 0.01, 2) : null,
    air_humidity_pct: airOk ? b[3] * 0.5 : null,
    soil_moisture_pct: soilOk ? b[4] * 0.5 : null,
    rain_tips_total: tips,
    rain_mm_total: r(tips * RAIN_MM_PER_TIP, 1),
    battery_v: vbat(b[7]),
    internal_temperature_c: intOk ? s8(b[8]) * 0.5 : null,
    internal_humidity_pct: intOk ? b[9] * 0.5 : null,
    solar_v: r(b[10] * 0.025, 3)
  };
}

function decodeHealth(b) {
  return {
    fw_version: b[0] + "." + b[1],
    uptime_days: u16(b, 2),
    uplinks: u16(b, 4),
    rejoins: b[6],
    last_rssi_dbm: s8(b[7]),
    last_snr_db: s8(b[8]) * 0.25,
    battery_min_v: vbat(b[9]),
    internal_temperature_max_c: s8(b[10]) * 0.5,
    charge_minutes: b[11] * 10,
    interval_min: b[12],
    reset_reason: b[13] === 1 ? "downlink_reboot" : "power_on"
  };
}

// The Things Stack / ChirpStack v4 entry point.
function decodeUplink(input) {
  var b = input.bytes, warnings = [];
  if (input.fPort === 1) {
    if (b.length !== 11) return { errors: ["measurement frame must be 11 bytes, got " + b.length] };
    var m = decodeMeasurement(b);
    if (m.battery_low) warnings.push("battery low");
    if (m.air_temperature_c === null) warnings.push("air probe not answering");
    if (m.soil_moisture_pct === null) warnings.push("soil probe missing");
    return { data: m, warnings: warnings };
  }
  if (input.fPort === 2) {
    if (b.length !== 14) return { errors: ["health frame must be 14 bytes, got " + b.length] };
    return { data: decodeHealth(b), warnings: warnings };
  }
  return { errors: ["unknown fPort " + input.fPort] };
}

// Downlinks, fPort 10. One command per downlink:
//   { "set_interval_s": 600 } | { "rapid_minutes": 30 } | { "health_now": true } | { "reboot": true }
function encodeDownlink(input) {
  var d = input.data;
  if (d.set_interval_s !== undefined) {
    var s = d.set_interval_s;
    if (s < 60 || s > 3600) return { errors: ["set_interval_s must be 60..3600"] };
    return { fPort: 10, bytes: [0x01, (s >> 8) & 0xff, s & 0xff] };
  }
  if (d.rapid_minutes !== undefined) {
    if (d.rapid_minutes < 0 || d.rapid_minutes > 255) return { errors: ["rapid_minutes must be 0..255"] };
    return { fPort: 10, bytes: [0x02, d.rapid_minutes] };
  }
  if (d.health_now) return { fPort: 10, bytes: [0x03] };
  if (d.reboot) return { fPort: 10, bytes: [0x04, 0xb0, 0x07] };
  return { errors: ["unknown command"] };
}

function decodeDownlink(input) {
  var b = input.bytes;
  if (b.length === 3 && b[0] === 0x01) {
    var s = u16(b, 1);
    if (s >= 60 && s <= 3600) return { data: { set_interval_s: s } };
  }
  if (b.length === 2 && b[0] === 0x02) return { data: { rapid_minutes: b[1] } };
  if (b.length === 1 && b[0] === 0x03) return { data: { health_now: true } };
  if (b.length === 3 && b[0] === 0x04 && b[1] === 0xb0 && b[2] === 0x07) return { data: { reboot: true } };
  return { errors: ["invalid downlink"] };
}

// Node (tests) only; ignored by the network servers.
if (typeof module !== "undefined") {
  module.exports = { decodeUplink: decodeUplink, encodeDownlink: encodeDownlink, decodeDownlink: decodeDownlink };
}
