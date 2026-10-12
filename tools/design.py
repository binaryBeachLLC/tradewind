"""Tradewind TW-1 rev B — the circuit, as data.

One entry per part: reference, library symbol, value, footprint, sheet, schematic position (grid units of
2.54 mm), rotation, pin -> net, and BOM fields. gen_schematic.py turns this into the KiCad schematic and
gen_pcb.py into the board; both read only this file, so the schematic and the board can't disagree.
Net None = no-connect flag.
"""

G = 2.54  # schematic grid

FP = dict(
    R0402="Resistor_SMD:R_0402_1005Metric", C0402="Capacitor_SMD:C_0402_1005Metric",
    C0603="Capacitor_SMD:C_0603_1608Metric", C0805="Capacitor_SMD:C_0805_2012Metric",
    L0402="Inductor_SMD:L_0402_1005Metric", L1008="Inductor_SMD:L_1008_2520Metric",
    SOT23="Package_TO_SOT_SMD:SOT-23", SOT23_6="Package_TO_SOT_SMD:SOT-23-6", SMA="Diode_SMD:D_SMA",
    PH2="Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
    PH3="Connector_JST:JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal",
    PH4="Connector_JST:JST_PH_S4B-PH-SM4-TB_1x04-1MP_P2.00mm_Horizontal",
    UFL="Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical",
    TC2030="Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical",
    HDR4="Connector_PinHeader_1.27mm:PinHeader_1x04_P1.27mm_Vertical",
    BAT="Battery:BatteryHolder_Keystone_1042_1x18650", TP="TestPoint:TestPoint_Pad_D1.0mm",
    HOLE="MountingHole:MountingHole_3.2mm_M3", FID="Fiducial:Fiducial_1mm_Mask2mm",
    LED="LED_SMD:LED_0603_1608Metric", FUSE="Fuse:Fuse_0805_2012Metric", SW="Button_Switch_SMD:SW_SPST_B3U-1000P",
)

SHEETS = {
    "power": "Power: solar, charger, battery, 3.3 V",
    "mcu_rf": "LoRaWAN module, RF, debug, UI",
    "sensors_io": "Sensors and field I/O",
}

parts = []


def P(ref, lib, value, fp, sheet, x, y, pins, rot=0, mpn="", mfr="", desc="", dnp=False, bom=True, **extra):
    parts.append(dict(ref=ref, lib=lib, value=value, fp=fp, sheet=sheet, x=x * G, y=y * G, rot=rot,
                      pins=pins, mpn=mpn, mfr=mfr, desc=desc, dnp=dnp, bom=bom, extra=extra))


def R(ref, value, sheet, x, y, n1, n2, mpn, rot=0, fp="R0402", **kw):
    P(ref, "Device:R", value, FP[fp], sheet, x, y, {"1": n1, "2": n2}, rot=rot, mpn=mpn, mfr="Yageo",
      desc="Resistor, %s, 1%%, 0402" % value, **kw)


def Cap(ref, value, sheet, x, y, n1, n2, mpn, fp="C0402", desc="", rot=0, **kw):
    P(ref, "Device:C", value, FP[fp], sheet, x, y, {"1": n1, "2": n2}, rot=rot, mpn=mpn, mfr="Murata",
      desc=desc or "Capacitor, %s" % value, **kw)


# ---------------------------------------------------------------- power sheet
S = "power"
P("J1", "Connector_Generic:Conn_01x02", "SOLAR", FP["PH2"], S, 16, 20, {"1": "SOLAR_RAW", "2": "GND"},
  mpn="S2B-PH-SM4-TB(LF)(SN)", mfr="JST", desc="Solar panel input, JST PH 2-pin side entry")
P("D1", "Device:D_TVS", "SMAJ12CA", FP["SMA"], S, 26, 30, {"1": "SOLAR_RAW", "2": "GND"},
  mpn="SMAJ12CA", mfr="Littelfuse", desc="TVS, 12 V standoff, 400 W, bidirectional")
P("Q1", "Transistor_FET:DMP3099L", "DMP3099L", FP["SOT23"], S, 36, 20,
  {"1": "Q1_G", "3": "SOLAR_RAW", "2": "VIN_SOLAR"}, mpn="DMP3099L-7", mfr="Diodes Inc.",
  desc="P-MOSFET -30 V, reverse-polarity protection")
R("R1", "100k", S, 32, 30, "Q1_G", "GND", "RC0402FR-07100KL")
Cap("C1", "10µF", S, 42, 30, "VIN_SOLAR", "GND", "GRM21BR61E106KA73L", fp="C0805", desc="10 µF 25 V X5R 0805")
Cap("C2", "1µF", S, 47, 30, "VIN_SOLAR", "GND", "GRM188R61E105KA12D", fp="C0603", desc="1 µF 25 V X5R 0603")
P("TP5", "Connector:TestPoint", "VIN_SOLAR", FP["TP"], S, 36, 42, {"1": "VIN_SOLAR"}, bom=False)
P("#FLG01", "power:PWR_FLAG", "PWR_FLAG", "", S, 42, 42, {"1": "VIN_SOLAR"}, bom=False)
P("#FLG02", "power:PWR_FLAG", "PWR_FLAG", "", S, 48, 42, {"1": "GND"}, bom=False)

P("U2", "Battery_Management:BQ24074RGT", "BQ24074RGT", FP.get("QFN16", "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm"),
  S, 80, 30,
  {"15": None, "4": "GND", "14": "GND", "6": "VSYS", "5": "GND", "12": "ILIM", "16": "ISET", "13": "VIN_SOLAR",
   "17": "GND", "8": "GND", "10": "VSYS", "11": "VSYS", "2": "VBAT", "3": "VBAT", "1": "TS", "7": "PGOOD_N",
   "9": "CHG_N"},
  mpn="BQ24074RGTR", mfr="Texas Instruments", desc="1-cell Li-ion linear charger with power path, VIN-DPM")
R("R4", "1.78k", S, 70, 41, "ISET", "GND", "RC0402FR-071K78L")
R("R5", "1.62k", S, 75, 41, "ILIM", "GND", "RC0402FR-071K62L")
Cap("C4", "4.7µF", S, 85, 41, "VSYS", "GND", "GRM188R61A475KE15D", fp="C0603", desc="4.7 µF 10 V X5R 0603")
R("R15", "100k", S, 90, 41, "+3V3", "PGOOD_N", "RC0402FR-07100KL")
R("R16", "100k", S, 95, 41, "+3V3", "CHG_N", "RC0402FR-07100KL")

P("BT1", "Device:Battery_Cell", "18650", FP["BAT"], S, 120, 30, {"1": "VBAT", "2": "GND"},
  mpn="1042", mfr="Keystone", desc="18650 holder; protected Li-ion 3350 mAh cell")
Cap("C5", "4.7µF", S, 128, 30, "VBAT", "GND", "GRM188R61A475KE15D", fp="C0603", desc="4.7 µF 10 V X5R 0603")
P("RT1", "Device:Thermistor_NTC", "10k B3380", FP["R0402"], S, 136, 30, {"1": "TS", "2": "GND"},
  mpn="NCP15XH103F03RC", mfr="Murata", desc="NTC 10 kΩ 1 %, B 3380, against the cell")
P("TP3", "Connector:TestPoint", "VBAT", FP["TP"], S, 144, 25, {"1": "VBAT"}, bom=False)

P("U3", "Regulator_Switching:TPS63900", "TPS63900", "Package_SON:WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm_ThermalVias",
  S, 30, 76,
  {"10": "VSYS", "1": "VSYS", "2": "GND", "9": "LX1", "7": "LX2", "11": "GND", "8": "GND", "6": "+3V3",
   "3": "CFG1", "4": "CFG2", "5": "CFG3"},
  mpn="TPS63900DSKR", mfr="Texas Instruments", desc="Buck-boost 1.8–5.5 V in, 75 nA Iq")
Cap("C6", "10µF", S, 10, 86, "VSYS", "GND", "GRM188R61A106KE69D", fp="C0603", desc="10 µF 10 V X5R 0603")
P("L1", "Device:L", "2.2µH", FP["L1008"], S, 16, 86, {"1": "LX1", "2": "LX2"},
  mpn="DFE252012F-2R2M=P2", mfr="Murata", desc="2.2 µH, 2.5 × 2.0 mm, Isat 2.6 A")
R("R6", "36.5k", S, 40, 86, "CFG1", "GND", "RC0402FR-0736K5L")
R("R7", "0", S, 45, 86, "CFG2", "GND", "RC0402JR-070RL")
R("R8", "16.2k", S, 50, 86, "CFG3", "GND", "RC0402FR-0716K2L")
Cap("C7", "22µF", S, 56, 86, "+3V3", "GND", "GRM21BR61A226ME51L", fp="C0805", desc="22 µF 10 V X5R 0805")
Cap("C8", "22µF", S, 61, 86, "+3V3", "GND", "GRM21BR61A226ME51L", fp="C0805", desc="22 µF 10 V X5R 0805")
Cap("C9", "100nF", S, 66, 86, "+3V3", "GND", "GRM155R71C104KA88D", desc="100 nF 16 V X7R 0402")
P("TP1", "Connector:TestPoint", "+3V3", FP["TP"], S, 72, 80, {"1": "+3V3"}, bom=False)
P("TP2", "Connector:TestPoint", "VSYS", FP["TP"], S, 76, 80, {"1": "VSYS"}, bom=False)
P("TP4", "Connector:TestPoint", "GND", FP["TP"], S, 80, 80, {"1": "GND"}, bom=False)

P("Q2", "Transistor_FET:AO3401A", "AO3401A", FP["SOT23"], S, 106, 70,
  {"1": "VBAT_GATE", "2": "VBAT", "3": "VBAT_SW"}, mpn="AO3401A", mfr="AOS", desc="P-MOSFET, battery-sense high-side switch")
R("R9", "1M", S, 98, 66, "VBAT", "VBAT_GATE", "RC0402FR-071ML")
P("Q3", "Transistor_FET:BSS138", "BSS138", FP["SOT23"], S, 106, 84,
  {"1": "VBAT_SENSE_EN", "3": "VBAT_GATE", "2": "GND"}, mpn="BSS138LT1G", mfr="onsemi", desc="N-MOSFET, gate drive for Q2")
R("R10", "1M", S, 96, 88, "VBAT_SENSE_EN", "GND", "RC0402FR-071ML")
R("R11", "100k", S, 116, 70, "VBAT_SW", "VBAT_ADC", "RC0402FR-07100KL")
R("R12", "100k", S, 116, 89, "VBAT_ADC", "GND", "RC0402FR-07100KL")
Cap("C10", "10nF", S, 122, 89, "VBAT_ADC", "GND", "GRM155R71C103KA01D", desc="10 nF 16 V X7R 0402")
R("R2", "1M", S, 136, 70, "VIN_SOLAR", "SOLAR_SENSE", "RC0402FR-071ML")
R("R3", "330k", S, 136, 89, "SOLAR_SENSE", "GND", "RC0402FR-07330KL")
Cap("C3", "100nF", S, 142, 89, "SOLAR_SENSE", "GND", "GRM155R71C104KA88D", desc="100 nF 16 V X7R 0402")

# ---------------------------------------------------------------- MCU / RF sheet
S = "mcu_rf"
P("U1", "RF_Module:RAK3172-xx-8-SM-xI", "RAK3172-8-SM-I", "RF_Module:RAK3172", S, 45, 40,
  {"21": "BOOT0", "22": "NRST", "26": "SOLAR_SENSE", "32": "VBAT_ADC", "31": "SOIL_ADC", "4": None, "5": None,
   "30": "LED", "27": "CHG_N", "29": "RAIN_IN", "6": "HALL_N", "2": "UART2_TX", "1": "UART2_RX", "16": "PGOOD_N",
   "15": None, "14": None, "13": None, "19": "SENSOR_EN", "20": "VBAT_SENSE_EN", "25": "AUX_ADC", "10": "SDA",
   "9": "SCL", "7": "SWDIO", "8": "SWCLK", "3": None, "24": "+3V3", "11": "GND", "17": "GND", "18": "GND",
   "23": "GND", "28": "GND", "12": "RF_MOD"},
  mpn="RAK3172-8-SM-I", mfr="RAKwireless", desc="LoRaWAN module, STM32WLE5CC, US915, RF pad (IPEX via board)")
Cap("C12", "10µF", S, 30, 62, "+3V3", "GND", "GRM188R61A106KE69D", fp="C0603", desc="10 µF 10 V X5R 0603")
Cap("C13", "100nF", S, 35, 62, "+3V3", "GND", "GRM155R71C104KA88D", desc="100 nF 16 V X7R 0402")
R("R13", "10k", S, 40, 62, "BOOT0", "GND", "RC0402FR-0710KL")
Cap("C11", "100nF", S, 45, 62, "NRST", "GND", "GRM155R71C104KA88D", desc="100 nF 16 V X7R 0402")
P("SW1", "Switch:SW_Push", "RESET", FP["SW"], S, 55, 62, {"1": "NRST", "2": "GND"},
  mpn="B3U-1000P", mfr="Omron", desc="Tactile switch, reset (inside the case)")
P("TP6", "Connector:TestPoint", "AUX_ADC", FP["TP"], S, 65, 58, {"1": "AUX_ADC"}, bom=False)

P("J5", "Connector:Conn_Coaxial", "U.FL", FP["UFL"], S, 140, 20, {"1": "RF_ANT", "2": "GND"},
  mpn="U.FL-R-SMT-1(10)", mfr="Hirose", desc="U.FL receptacle to SMA bulkhead pigtail")
P("L2", "Device:L", "7.5nH", FP["L0402"], S, 118, 20, {"1": "RF_MOD", "2": "RF_ANT"}, rot=90,
  mpn="LQG15HS7N5J02D", mfr="Murata", desc="7.5 nH ±5 % 0402 (π-match series; rev A: 0 Ω)")
Cap("C14", "1.8pF", S, 108, 26, "RF_MOD", "GND", "GJM1555C1H1R8BB01D", desc="1.8 pF ±0.1 pF C0G 0402 (π-match shunt, module side)")
Cap("C15", "DNP", S, 128, 26, "RF_ANT", "GND", "", desc="π-match shunt, connector side (not fitted)", dnp=True)

P("J6", "Connector:Conn_ARM_SWD_TagConnect_TC2030", "TC2030-NL", FP["TC2030"], S, 105, 60,
  {"1": "+3V3", "2": "SWDIO", "3": "NRST", "4": "SWCLK", "5": "GND", "6": None}, bom=False,
  desc="SWD, Tag-Connect footprint (no part)")
P("J7", "Connector_Generic:Conn_01x04", "UART", FP["HDR4"], S, 135, 60,
  {"1": "GND", "2": "UART2_RX", "3": "UART2_TX", "4": "+3V3"}, dnp=True, bom=False,
  desc="UART2 pads (AT commands / bootloader), header not fitted")

P("D3", "Device:LED", "GREEN", FP["LED"], S, 30, 88, {"1": "GND", "2": "LED_A"},
  mpn="LTST-C191KGKT", mfr="Lite-On", desc="LED green 0603, seen through the lid light pipe")
R("R14", "2.2k", S, 44, 88, "LED_A", "LED", "RC0402FR-072K2L", rot=90)
P("U4", "tradewind:DRV5032FB", "DRV5032FB", FP["SOT23"], S, 60, 88, {"1": "+3V3", "2": "HALL_N", "3": "GND"},
  mpn="DRV5032FBDBZR", mfr="Texas Instruments", desc="Hall switch, omnipolar, 5 Hz, 0.54 µA (magnet tap)")
Cap("C16", "100nF", S, 76, 88, "+3V3", "GND", "GRM155R71C104KA88D", desc="100 nF 16 V X7R 0402")

for i, (x, y) in enumerate([(96, 90), (102, 90), (108, 90), (114, 90)]):
    P("H%d" % (i + 1), "Mechanical:MountingHole", "M3", FP["HOLE"], S, x, y, {}, bom=False)
for i, x in enumerate([124, 130, 136]):
    P("FID%d" % (i + 1), "Mechanical:Fiducial", "FID", FP["FID"], S, x, 90, {}, bom=False)

# ---------------------------------------------------------------- sensors / IO sheet
S = "sensors_io"
P("U5", "Sensor_Humidity:SHT4x", "SHT40-BD1B", "Sensor_Humidity:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad",
  S, 20, 22, {"1": "SDA", "2": "SCL", "3": "+3V3", "4": "GND"},
  mpn="SHT40-BD1B-R2", mfr="Sensirion", desc="T/RH sensor, I2C 0x45, inside the case (condensation / leak watch)")
Cap("C17", "100nF", S, 32, 24, "+3V3", "GND", "GRM155R71C104KA88D", desc="100 nF 16 V X7R 0402")
R("R17", "4.7k", S, 40, 24, "+3V3", "SDA", "RC0402FR-074K7L")
R("R18", "4.7k", S, 46, 24, "+3V3", "SCL", "RC0402FR-074K7L")

P("J4", "Connector_Generic:Conn_01x04", "AIR PROBE", FP["PH4"], S, 95, 20,
  {"1": "+3V3_EXT", "2": "GND", "3": "SDA_EXT", "4": "SCL_EXT"},
  mpn="S4B-PH-SM4-TB(LF)(SN)", mfr="JST", desc="External SHT45 probe (radiation shield)")
P("F1", "Device:Polyfuse", "100mA", FP["FUSE"], S, 62, 24, {"1": "+3V3", "2": "+3V3_EXT"},
  mpn="MF-PSMF010X-2", mfr="Bourns", desc="PTC resettable fuse, 0.1 A hold, 0805")
R("R19", "100", S, 75, 24, "SDA", "SDA_EXT", "RC0402FR-07100RL")
R("R20", "100", S, 80, 24, "SCL", "SCL_EXT", "RC0402FR-07100RL")

P("U6", "Power_Protection:TPD4E02B04DQA", "TPD4E02B04", "Package_SON:USON-10_2.5x1.0mm_P0.5mm", S, 130, 24,
  {"1": "SDA_EXT", "2": "SCL_EXT", "4": "SOIL_EXT", "5": "RAIN_EXT", "3": "GND", "8": "GND",
   "6": None, "7": None, "9": None, "10": None},
  mpn="TPD4E02B04DQAR", mfr="Texas Instruments", desc="4-ch ESD, ±12 kV contact, 0.25 pF")

P("U7", "Power_Management:TPS22917DBV", "TPS22917", FP["SOT23_6"], S, 30, 60,
  {"1": "+3V3", "2": "GND", "3": "SENSOR_EN", "4": "CT", "5": "QOD", "6": "+3V3_SW"},
  mpn="TPS22917DBVR", mfr="Texas Instruments", desc="Load switch, 2 A, 10 nA leakage (soil probe power)")
Cap("C19", "1µF", S, 14, 76, "+3V3", "GND", "GRM155R61A105KE15D", desc="1 µF 10 V X5R 0402")
Cap("C18", "1nF", S, 20, 76, "CT", "GND", "GRM155R71H102KA01D", desc="1 nF 50 V X7R 0402 (slew control)")
R("R25", "100", S, 32, 76, "QOD", "+3V3_SW", "RC0402FR-07100RL")
Cap("C20", "1µF", S, 26, 76, "+3V3_SW", "GND", "GRM155R61A105KE15D", desc="1 µF 10 V X5R 0402")
P("J3", "Connector_Generic:Conn_01x03", "SOIL", FP["PH3"], S, 62, 56, {"1": "+3V3_SW", "2": "GND", "3": "SOIL_EXT"},
  mpn="S3B-PH-SM4-TB(LF)(SN)", mfr="JST", desc="Capacitive soil-moisture probe")
R("R21", "1M", S, 42, 76, "SOIL_EXT", "GND", "RC0402FR-071ML")
R("R22", "1k", S, 52, 76, "SOIL_EXT", "SOIL_ADC", "RC0402FR-071KL", rot=90)
Cap("C21", "100nF", S, 62, 78, "SOIL_ADC", "GND", "GRM155R71C104KA88D", desc="100 nF 16 V X7R 0402")

P("J2", "Connector_Generic:Conn_01x02", "RAIN", FP["PH2"], S, 100, 56, {"1": "RAIN_EXT", "2": "GND"},
  mpn="S2B-PH-SM4-TB(LF)(SN)", mfr="JST", desc="Tipping-bucket rain gauge (reed)")
R("R23", "1M", S, 110, 56, "+3V3", "RAIN_EXT", "RC0402FR-071ML")
R("R24", "10k", S, 122, 66, "RAIN_EXT", "RAIN_IN", "RC0402FR-0710KL", rot=90)
Cap("C22", "22nF", S, 132, 70, "RAIN_IN", "GND", "GRM155R71C223KA01D", desc="22 nF 16 V X7R 0402 (debounce)")

# ---------------------------------------------------------------- drawing furniture
FRAMES = {
    "power": [
        ("SOLAR INPUT & PROTECTION", 7, 10, 54, 54),
        ("CHARGER + POWER PATH · BQ24074", 56, 10, 107, 54),
        ("BATTERY · PROTECTED 18650", 109, 10, 158, 54),
        ("3.3 V BUCK-BOOST · TPS63900", 7, 56, 89, 98),
        ("BATTERY & SOLAR SENSE", 91, 56, 158, 98),
    ],
    "mcu_rf": [
        ("LoRaWAN MODULE · RAK3172 (STM32WLE5)", 7, 10, 87, 72),
        ("RF MATCH & ANTENNA", 89, 10, 158, 44),
        ("DEBUG & PROGRAMMING", 89, 46, 158, 72),
        ("USER INTERFACE · LED + MAGNET WAKE", 7, 74, 87, 98),
        ("MECHANICAL", 89, 74, 158, 98),
    ],
    "sensors_io": [
        ("INTERNAL T/RH · SHT40 (0x45)", 7, 10, 52, 38),
        ("EXTERNAL AIR PROBE · J4 (SHT45, 0x44)", 54, 10, 106, 38),
        ("ESD · ALL FIELD LINES", 108, 10, 158, 38),
        ("SOIL PROBE · SWITCHED POWER", 7, 42, 80, 98),
        ("RAIN GAUGE · DEBOUNCED PULSE", 82, 42, 158, 98),
    ],
}

NOTES = {
    "power": [
        (9, 50, "Panel 5 V / 2 W (Voc 6.0 V). D1 clamps surges, Q1 blocks reverse polarity (Vgs ±20 V)."),
        (58, 51, "EN2=L, EN1=H: USB500, 475 mA limit, VIN-DPM 4.5 V (solar-friendly)."),
        (58, 53, "TMR=GND: timers off for slow solar charge. RISET 1.78k: 500 mA. ITERM open: 10 %."),
        (111, 48, "TS: 10k NTC, ITS 75 µA. Charging only 0 to 50 °C."),
        (111, 50, "BQ24074 drains 4.3 µA from BAT with no sun (largest sleep load)."),
        (9, 95, "RCFG3 16.2k: VO1 = 3.3 V. RCFG1 36.5k + RCFG2 0R: VO2 = 3.3 V, no input limit. SEL = L."),
        (93, 95, "Rev B: high-side switch. Rev A switched the low side, so VBAT leaked into the ADC clamp (+27 µA at 4.05 V)."),
        (93, 97, "Divider 1:2, settle 5 τ = 2.5 ms. Solar divider 1M/330k: ratio 0.248."),
    ],
    "mcu_rf": [
        (91, 40, "50 Ω CPWG on L1 over L2: 0.35 mm trace, 0.20 mm gap, 7628 prepreg 0.21 mm."),
        (91, 42, "π-match tuned in the closed case: C14 1.8 pF, L2 7.5 nH, C15 DNP (rev A: 0 Ω / DNP)."),
        (91, 68, "Flash over UART2 (BOOT0 high) or SWD via Tag-Connect TC2030-NL."),
        (9, 96, "Tap a magnet on the lid logo: send now. Hold 3 s: rejoin."),
    ],
    "sensors_io": [
        (56, 34, "Probe always powered (SHT45 idle 80 nA): a switched probe would clamp the shared I2C bus."),
        (9, 36, "SHT40 sits on a slotted island, away from the charger and regulator."),
        (9, 94, "Probe powered only while sampling: 100 ms warm-up, about 5 mA."),
        (84, 94, "Close: τ = 10k·22n = 0.22 ms. Open: τ = 1M·22n = 22 ms. Bounce under 2 ms is absorbed."),
    ],
}
