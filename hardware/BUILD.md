# Power Supply Design — 12V→5V & 3.3V Buck Converters

> **Project:** Smart ID Card Distribution Kiosk  
> **Component:** Dual independent buck converters  
> **Input:** 12V 10A PSU  
> **Outputs:** 5V @ 3A (logic rail) + 3.3V @ 1.5A (IO rail)  
> **Technology:** THT (Through-Hole) components, breadboard-testable, PCB-ready  
> **Status:** Design phase — Phase 1 in progress

---

## Architecture Overview

```bash
12V 10A PSU (external power supply)
    │
    ├──→ [12V→5V Buck Converter]
    │    PWM Controller + Switching Stage + Filtering
    │    Output: 5V Rail (3A max)
    │    Loads: STM32 Nucleo VCC, 2× SG90 servos, IR sensors, Pi Camera
    │
    ├──→ [12V→3.3V Buck Converter]
    │    PWM Controller + Switching Stage + Filtering
    │    Output: 3.3V Rail (1.5A max)
    │    Loads: STM32 GPIO levels, A3144 hall sensor, USB camera
    │
    └──→ Motor drivers & solenoid (12V direct, separate fusing)
```

**Design Philosophy:**

- Separate converters (not cascaded) → no efficiency loss from rail-to-rail dropouts
- Same PWM frequency (100 kHz) → reduces switching noise coupling
- Identical topology → standardized design, reusable components
- All THT components → breadboard-native, hand-solderable

---

## Phase 1: Detailed Design & Calculation (6–8 hrs)

### 1.1: Define Electrical Specifications _(1 hr total)_

#### For 12V→5V Converter

**Input specification:**

- Nominal input voltage: **12** V
- Input range (±10% tolerance): **10.8** V to **13.2** V
- Expected PSU ripple contribution: **\_** mV

**Output specification:**

- Target output voltage: 5.0V
- Allowed tolerance: ±**5**% → voltage range: **4.75** V to **5.25** V
- Rated load current (continuous): **2.5** A (Two servos won't work simultaneously)
- Maximum transient load (servo startup): **1.5** A
- Output ripple budget: **100** mV peak-to-peak
- Acceptable ripple percentage: **2** % of output (typically 2–5%)
- Thermal limit: MOSFET/diode junction <**100** °C @ ambient 25°C

#### For 12V→3.3V Converter

**Input specification:**

- Nominal input voltage: **12** V (same as 5V converter)
- Input range: **10.8** V to **13.2** V

**Output specification:**

- Target output voltage: 3.3V
- Allowed tolerance: ±**5** % → voltage range: **3.135** V to **3.465** V
- Rated load current (continuous): **1** A
- Maximum transient load: **2** A
- Output ripple budget: **\_** mV peak-to-peak
- Acceptable ripple percentage: **\_** %
- Thermal limit: <**100** °C

**Record** these specifications; use them as verification targets throughout all phases.

---

### 1.2: Select Switching Frequency & Topology _(0.5 hr)_

#### Design choice: Switching Frequency

Candidates: 50 kHz, 100 kHz, 200 kHz

Formula: L = (Vin - Vout) x D / (f x ΔI_L), while D = (Vout + Vf_diode) / Vin

- 50 kHz: **85.86** uH
- 100 kHz: **42.93** uH
- 200 kHz: **21.46** uH

**Selected frequency:** **100** kHz  
**Rationale:** Because, the inductor value are readily available in THT, and also, no thermal stress compared to higher frequency switching.

#### Design choice: Converter Topology

Candidates: Synchronous buck (high-side MOSFET + low-side MOSFET), Non-synchronous buck (MOSFET + passive diode freewheeling)

**Selected topology:** Non-synchronous buck (MOSFET + Passive diode)  
**Rationale:** Just enough efficiency (75-85%), all THT components, only one controller (not need of external IC)

---

### 1.3: Select PWM Controller IC _(1.25 hr)_

#### Controller Options Comparison

| **Controller** | **Package** | **Frequency**     | **Advantage**                                                                         | **Disadvantage**                                |
| -------------- | ----------- | ----------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------- |
| **SG3525**     | **DIP 16**  | **100 - 500** kHz | **Soft start, flexible freq, circuit protection, fine tolerance (1%)and THT package** | \*\*\*\*                                        |
| **TL494**      | **PDIP 16** | **1 - 300** kHz   | **Flexible freq and THT package**                                                     | **Fixed V<sub>out</sub>, wider tolerance (5%)** |
| **MC34063**    | **PDIP 8**  | **100** kHz       | **Flexible V<sub>out</sub>, higher output current (1.5A) and THT package**            | **Fixed frequency**                             |

**Selected controller:** SG3525

**Key parameters from datasheet:**

- Reference voltage (Vref): **\_** V
- Maximum frequency: **500** kHz
- Soft-start pin available: Yes
- Error amplifier gain (Aol): **\_** V/V
- Pin configuration: **DIP 16**

---

### 1.4: Design 12V→5V Buck Converter _(2.5 hrs total)_

#### 1.4.1 Calculate Duty Cycle (D)

**Formula:** D = (Vout + Vf_diode) / Vin

Where:

- Vout = desired output voltage = **5** V
- Vf_diode = diode forward drop ≈ **0.525** V (check datasheet)
- Vin = nominal input voltage = **12** V

**Calculation:**

```bash
D = (5 + 0.525) / 12 (1N5822 diode will used)
D = 5.525 / 12
D = 0.4604 (as decimal)
D = 46.04% (as percentage)
```

**Interpretation:** MOSFET is ON for **46.04% of each switching cycle, OFF for 53.96**%.

---

#### 1.4.2 Select High-Side MOSFET

**Requirements:**

- Vds(max) ≥ **13.2** V (input voltage)
- Id(max) ≥ **3** A (rated load current)
- Rds(on) @ Vgs=10V ≤ **0.22** Ω (low conduction loss)
- Package: TO-220 (breadboard-friendly)
- Readily available in THT

**Candidates considered:**

1. **IRFZ44N** (Vds=55V, Id=49A, Rds=17.5mΩ)
2. **IRF540N** (Vds=100V, Id=33A, Rds=44mΩ)
3. **IRLU024N** (Vds=55V, Id=17A, Rds=65mΩ) - Logic level

**Selected MOSFET:** **IRFZ44N**

**Verification:**

- Vds margin: **55** V chosen / **13.2** V required = **4.17** × headroom ✓
- Id margin: **49** A chosen / **2.5** A required = **19.6** × headroom ✓
- Rds(on) suitable for conduction loss budget? Yes

---

#### 1.4.3 Calculate MOSFET Conduction Loss

**Formula:** P_mosfet = I_out² × Rds(on) × D

Where:

- I_out = rated output current = **2.5** A
- Rds(on) = on-resistance @ Vgs = **17.5** mΩ
- D = duty cycle = **0.4604** (from 1.4.1)

**Calculation:**

```bash
P_mosfet = (2.5) ² × 17.5m × 0.4604
P_mosfet = 6.25 × 17.5m × 0.4604
P_mosfet = 0.05 W
```

**Estimate switching loss** (typically 10–30% of conduction loss at 100 kHz):

```bash
P_switching ≈ 0.015 W
Total MOSFET loss = 0.05 + 0.015 = 0.065 W
```

---

#### 1.4.4 Select Freewheeling Diode

**Calculate peak inductor current** (needed to size diode):

- I_pk_approx = I_out / (1 - D) = **\_** / (1 - **\_**) = **\_** A

**Requirements:**

- Vr(max) ≥ **\_** V (reverse voltage)
- If(max) ≥ **\_** A (peak forward current)
- Recovery time < **\_** ns (fast recovery preferred)
- Package: axial or DO-41 THT

**Candidates:**

1. **\_** (Vr=***V, If=***A, trr=\_\_\_ns)
2. **\_** (Vr=***V, If=***A, trr=\_\_\_ns) — Schottky option for lower loss
3. **\_** (Vr=***V, If=***A, trr=\_\_\_ns)

**Selected for breadboard:** \***\*\*\*\*\***\_\***\*\*\*\*\***  
**Planned upgrade for PCB:** \***\*\*\*\*\***\_\***\*\*\*\*\***

**Verification:**

- Vr margin: **\_** × headroom ✓
- If margin: **\_** × headroom ✓

---

#### 1.4.5 Calculate Diode Forward Loss

**Formula:** P_diode = Vf × I_diode_avg

Where:

- Vf = forward voltage drop ≈ **0.525** V (from datasheet)
- I_diode_avg = I_out × (1 - D) = **2.5** × (1 - **0.508**) = **1.23** A

**Calculation:**

```bash
P_diode = 0.525 V × 1.23 A
P_diode = 0.645 W
```

---

#### 1.4.6 Calculate Inductor Value & Current Ripple

**Choose desired current ripple percentage:**

- Ripple = **30** % of I_out (typical 20–50%)
- ΔI_L = **0.75** A (equals ripple fraction × output current)

**Formula:** L = (Vin - Vout) × D / (f × ΔI_L)

Where:

- Vin - Vout = voltage across inductor during ON time = **12** - **5** = **7** V
- D = duty cycle = **46.04** %
- f = switching frequency = **100** kHz
- ΔI_L = chosen ripple = **0.75** A

**Calculation:**

```bash
L = (7 × 0.4604) / (100k × 0.75)
L = 3.22 / 75k
L = 42.93 µH
```

**Round to nearest standard value:** L = **47** µH

**Calculate peak inductor current:**

```bash
I_L_peak = I_out + (ΔI_L / 2)
I_L_peak = 2.5 + (0.75 / 2)
I_L_peak = 1.67 A
```

**Inductor specification:**

- Inductance: **47** µH ±10%
- Current rating (continuous): ≥ **2.5** A (use I_L_peak with 1.5× margin)
- DCR (required): ≤ **\_** Ω (low resistance to minimize loss)
- Core material: ferrite preferred
- Package: THT or SMD with adapter if needed

---

#### 1.4.7 Calculate Output Filtering (Capacitors)

**Ripple budget split:** 50% capacitor + 50% ESR

**Capacitor ripple contribution:**

- Target: ΔV_cap = **50** mV (half of total budget)
- Formula: C ≥ (I_out × (1-D)) / (f × ΔV_cap)

**Calculation:**

```bash
C ≥ (2.5 × (1 - 0.4604)) / (100k × 100m)
C ≥ 1.62 / 10k
C ≥ 162 µF
```

**Round up to standard value:** C = **220** µF minimum

**Select capacitors:**

- Type: Aluminum electrolytic (bulk) + ceramic (low-ESR)
- Voltage rating: ≥ **10** V (recommend 1.5–2× output voltage)
- Quantity: **2** pieces of **220** µF aluminum + **2** piece of **100** nF ceramic

**ESR ripple contribution:**

- Target: ΔV_ESR = **100** mV
- Formula: ESR ≤ ΔV_ESR / ΔI_L

**Calculation:**

```bash
ESR ≤ 100 mV / 0.75 A
ESR ≤ 0.133 Ω
```

**Verify selected capacitors meet ESR target:**

- Aluminum ESR (each): **0.5** mΩ (from datasheet)
- Ceramic ESR: **\_** mΩ
- Parallel combination: **\_** mΩ ✓ (meets **\_** mΩ target?)

**Input filtering** (reduces PSU noise coupling to 3.3V converter):

- Capacitor 1: **\_** µF, **\_** V aluminum
- Capacitor 2: **\_** µF, **\_** V ceramic (fast transient response)
- Location: directly across 12V input connector

---

#### 1.4.8 Design Feedback Network (Voltage Divider)

**Formula:** Vout = Vref × (1 + R1/R2)

Where:

- Vref = internal reference voltage = **\_** V (from controller datasheet)
- Vout = desired output = 5.0V
- R1 = top resistor (from Vout to feedback pin)
- R2 = bottom resistor (from feedback pin to GND)

**Rearranged for R1/R2 ratio:**

```bash
5.0 = _____ × (1 + R1/R2)
_____ = 1 + R1/R2
R1/R2 = _____
```

**Choose R2:** **\_** Ω (typically 2–10 kΩ for low noise)

**Calculate R1:**

```bash
R1 = _____ × R2
R1 = _____ × _____
R1 = _____ Ω
```

**Select nearest 1% resistor value:** R1 = **\_** Ω 1%

**Verify output voltage:**

```bash
Vout_actual = _____ × (1 + _____ / _____)
Vout_actual = _____ × _____
Vout_actual = _____ V
```

**Error from target:** **\_** V (acceptable? Yes / No)

**Trimming strategy:**

- Install **\_** kΩ potentiometer in parallel with R1 for field calibration
- Or use **\_** kΩ fixed + **\_** kΩ trim potentiometer combination

---

#### 1.4.9 Design Compensation Network (Loop Stability)

**Goal:** Stable voltage regulation + fast transient response (<50ms recovery, <10% overshoot)

**Error amplifier feedback compensation:**

- Input impedance (Rin): **\_** Ω (feedback divider source)
- Desired loop crossover frequency (fc): **\_** kHz (typically 1/50 of switching freq)
- Feedback capacitor (Cfb): **\_** nF (reduces high-frequency gain)

**Output filter compensation:**

- Series resistor (Rc): **\_** Ω (part of ramp filter network)
- Capacitor to ground (Cc): **\_** nF

**Soft-start capacitor (inrush limiting):**

- Css: **\_** µF (limits startup ramp rate to prevent in-rush)

**Record selected values:**

- Cfb = **\_** nF **\_** V ceramic
- Rc = **\_** Ω **\_** W resistor
- Cc = **\_** nF **\_** V ceramic
- Css = **\_** µF **\_** V electrolytic

---

#### 1.4.10 Calculate Total Losses & Efficiency

**Summarize all loss contributions:**

| Loss Source              | Calculation                    | Power            |
| ------------------------ | ------------------------------ | ---------------- |
| MOSFET conduction        | (from 1.4.3)                   | **0.015** W      |
| MOSFET switching         | (estimated 1.4.3)              | **0.05** W       |
| Diode forward drop       | (from 1.4.5)                   | **0.645** W      |
| Inductor DC resistance   | I² × DCR = **\_**² × **\_**    | **\_** W         |
| Gate drive & control     | (typical 5–10% of MOSFET loss) | **0.065** W      |
| **Total converter loss** |                                | \***\*\_** W\*\* |

**Calculate efficiency:**

```bash
P_out = Vout × I_out = 5 × 2.5 = 12.5 W
η = P_out / (P_out + P_loss)
η = 12.5 / (12.5 + _____)
η = %
```

**Thermal analysis:**

Assume MOSFET as highest-temperature component:

- Thermal resistance MOSFET (junction to case): **\_** °C/W
- Thermal resistance case to ambient (free convection on breadboard): **\_** °C/W
- Total: **\_** °C/W

```bash
ΔT = P_mosfet × Rth_total
ΔT = _____ W × _____ °C/W
ΔT = _____°C rise

T_junction = T_ambient + ΔT = _____ + _____ = _____°C
Margin to Tj_max (125°C typical): _____ °C ✓ (safe?)
```

---

#### 1.4.11 Verify All Component Ratings

Create a table:

| **Component**       | **Design Value**       | **Rating Required**                  | **Selected Part** | **Safety Margin** | **Status** |
| ------------------- | ---------------------- | ------------------------------------ | ----------------- | ----------------- | ---------- |
| MOSFET              | I_out=**A, Tj=**°C     | Vds≥**V, Id≥**A, Tj≤125°C            | **\_**            | **\_** ×          | ✓          |
| Diode               | I_avg=**A, If_peak=**A | Vr≥**V, If≥**A                       | **\_**            | **\_** ×          | ✓          |
| Inductor            | L=**µH, I_peak=**A     | L=**µH ±10%, I_rating≥**A, DCR<\_\_Ω | **\_**            | **\_** ×          | ✓          |
| Capacitor (out)     | C≥**µF, V≥**V          | ESR<\_\_mΩ                           | **\_**            | **\_** ×          | ✓          |
| Capacitor (in)      | C≥**µF, V≥**V          | —                                    | **\_**            | **\_** ×          | ✓          |
| Resistors (divider) | R1=**Ω, R2=**Ω         | ±1%, 0.25W                           | **\_**            | **\_** ×          | ✓          |
| Compensation caps   | Cfb=**nF, Cc=**nF      | **\_** V                             | **\_**            | **\_** ×          | ✓          |

**Go/No-go:** All components within safe operating area? Yes / No

---

#### 1.4.12 Create LTspice Schematic

**Schematic file:** `hardware/schematics/Buck_12V_5V_SG3525.asc`

**Components to include:**

- Voltage source (12V) with **\_** Ω series ESR to model PSU
- SG3525 PWM controller (model from datasheet)
- MOSFET (model or subcircuit value)
- Diode (model value)
- Inductor (**\_** µH with **\_** Ω DCR)
- Output capacitors (**\_** µF + **\_** µF in parallel)
- Feedback divider (R1, R2 with pot for trim)
- Compensation network (Cfb, Rc, Cc, Css)
- Load resistor (variable 10Ω to 1.67Ω to simulate 0.5A → 3A)

**Simulations to run:**

1. **DC Operating Point:** Output voltage at no-load, half-load, full-load → verify ±5% regulation
2. **Transient Startup (0–1ms):** Verify soft-start ramp, settling time <100ms
3. **Load Step Response (t=10ms, 0.5A→3A):** Measure overshoot <10%, recovery time <50ms
4. **Output Ripple (FFT):** Verify peak-to-peak <100mV
5. **Efficiency Curve:** Plot Pout vs. η from 0.5A to 3A

**Results summary:**

- Voltage regulation: **\_** % at full load (target ±5%)
- Ripple: **\_** mV peak-to-peak (target <100mV)
- Transient recovery: **\_** ms (target <50ms)
- Efficiency @ 3A: **\_**% (target >80%)

---

### 1.5: Design 12V→3.3V Buck Converter _(2.5 hrs total)_

**Methodology:** Repeat all steps from 1.4 (1.4.1 through 1.4.12) with output voltage = 3.3V

**Key parameter differences:**

#### 1.5.1 Duty Cycle for 3.3V

```bash
D = (____ + ____) / _____
D = _____
```

#### 1.5.2 MOSFET (typically same as 5V)

**Selected:** \***\*\*\*\*\***\_\***\*\*\*\*\*** (same as 5V? Yes / No)

#### 1.5.3 Diode (typically same as 5V)

**Selected for breadboard:** \***\*\*\*\*\***\_\***\*\*\*\*\***  
**Planned upgrade for PCB:** \***\*\*\*\*\***\_\***\*\*\*\*\***

#### 1.5.4 Inductor Calculation

```bash
L = (_____ × _____) / (_____ × _____)
L = _____ µH
```

**Peak inductor current:**

```bash
I_L_peak = _____ A
```

**Selected inductor:** **\_** µH, **\_** A rated

#### 1.5.5 Output Capacitors

```bash
C ≥ (_____ × _____) / (_____ × _____)
C ≥ _____ µF
```

**Selected:** **\_** µF + **\_** µF ceramic

#### 1.5.6 Feedback Divider for 3.3V

```bash
3.3 = _____ × (1 + R1/R2)
R1/R2 = _____
R2 = _____
R1 = _____
```

**Selected values:** R1 = **\_** Ω, R2 = **\_** Ω (1% tolerance)

#### 1.5.7 Compensation Network

**Same as 5V converter?** Yes / No - Why? \***\*\*\*\*\***\_\_\_\***\*\*\*\*\***

**Selected values:**

- Cfb = **\_** nF
- Rc = **\_** Ω
- Cc = **\_** nF
- Css = **\_** µF

#### 1.5.8 Total Losses & Efficiency

| Loss      | Calculation | Power            |
| --------- | ----------- | ---------------- |
| MOSFET    |             | **\_** W         |
| Diode     |             | **\_** W         |
| Inductor  |             | **\_** W         |
| Other     |             | **\_** W         |
| **Total** |             | \***\*\_** W\*\* |

```bash
P_out = 3.3V × _____ A = _____ W
η = _____ / (_____ + _____) = _____ %
```

#### 1.5.9 Thermal Analysis

```bash
ΔT = _____ W × _____ °C/W = _____°C
T_junction = _____ + _____ = _____°C (safe? Yes/No)
```

#### 1.5.10 Component Verification Table

(Same format as 1.4.11)

#### 1.5.11 Create LTspice Schematic

**Schematic file:** `hardware/schematics/Buck_12V_3.3V_SG3525.asc`

**Load step test:** **\_** A → **\_** A (vs. 5V which uses 0.5A→3A)

**Results:**

- Voltage regulation: **\_** %
- Ripple: **\_** mV
- Transient recovery: **\_** ms
- Efficiency: **\_**%

---

### 1.6: Combine & Cross-Verify _(1 hr total)_

#### 1.6.1 Merge into Single KiCAD Schematic

**File:** `hardware/schematics/Power_Supply_Dual_Buck.sch`

**Schematic structure:**

- Top-level power distribution diagram
  - Sub-sheet 1: "12V→5V Buck Converter"
  - Sub-sheet 2: "12V→3.3V Buck Converter"
  - Sub-sheet 3: "Protection & Filtering" (fuses, inrush, decoupling — for PCB phase)
- Shared 12V input with common ground star point
- Test points labeled: TP_12V_IN, TP_5V_OUT, TP_3.3V_OUT, TP_GND

**Verify KiCAD schematic:**

- All nets connected (no floating wires)
- Voltage labels on all rails
- Component designators sequential (R1, R2, ... C1, C2, ... L1, L2, ... etc.)

#### 1.6.2 LTspice Cross-Coupling Analysis

**Simulation file:** Combine both converters in single circuit

**Test scenario:** 5V converter @ **\_** A + 3.3V converter @ **\_** A (simultaneous load)

**Measurements:**

- 5V output ripple: **\_** mV (target <100mV)
- 3.3V output ripple: **\_** mV (target <100mV)
- Input current (total 12V draw): **\_** A

**Stability check:**

- Oscillation present? Yes / No → if yes, adjust compensation
- Ripple coupling between rails? Yes / No → if yes, check ground return path

**Go/No-Go Decision:**

- Both ripples <100mV ✓
- No oscillation ✓
- Input current validates PSU capacity ✓
- **Decision:** **\_** → **Proceed to Phase 2 (Breadboard)**

---

## Phase 1 Deliverables Checklist

- [ ] Electrical specifications document (1.1) completed
- [ ] Switching frequency & topology selected (1.2)
- [ ] PWM controller evaluated & chosen (1.3)
- [ ] 12V→5V converter fully designed (1.4.1–1.4.12)
  - [ ] All component values calculated
  - [ ] LTspice schematic simulated & verified
- [ ] 12V→3.3V converter fully designed (1.5.1–1.5.11)
  - [ ] All component values calculated
  - [ ] LTspice schematic simulated & verified
- [ ] Dual converter KiCAD schematic created (1.6.1)
- [ ] Cross-coupling simulation complete & passed (1.6.2)
- [ ] Component bill of materials (BOM) compiled with part numbers & sources
- [ ] All calculation worksheets saved & documented

**Phase 1 Status:** **\_** / 100% complete

**Estimated effort:** 6–8 hours  
**Actual effort:** **\_** hours

---

## Phase 2: Breadboard Prototype & Testing _(3–4 hrs)_

(To be completed after Phase 1 design is finalized and LTspice sims pass)

### 2.1 Build 12V→5V Converter on Breadboard

- [ ] Mount SG3525 DIP-16 on breadboard (or use DIP adapter if SMD version)
- [ ] Place MOSFET, diode, inductor, capacitors per KiCAD schematic
- [ ] Solder leads or use breadboard jumpers carefully (watch for shorts)
- [ ] **Test:** Power on (no load first)
  - Measure output voltage: **\_** V (target **\_** ±5%)
  - Measure output ripple with oscilloscope: **\_** mV (target <100mV)
  - Load with resistor bank to **\_** A: measure voltage stability & ripple

### 2.2 Build 12V→3.3V Converter on Breadboard

- [ ] Repeat 2.1 with 3.3V-specific components
- [ ] **Test:** Same measurements as 2.1

### 2.3 Test Dual-Converter Interaction

- [ ] Load both converters simultaneously (5V @ **\_** A + 3.3V @ **\_** A)
- [ ] Verify no crosstalk or oscillation
- [ ] Measure total PSU input current: **\_** A (should match calculation)

### 2.4 Go/No-Go Decision

- [ ] All voltage specs met (±5%)
- [ ] All ripple specs met (<100mV)
- [ ] Transient response acceptable (<50ms)
- [ ] **Decision:** **\_** → **Proceed to Phase 3 (Perf Board)**

---

## Phase 3: Perf Board Assembly & Validation _(2–2.5 hrs)_

(To be completed after breadboard testing passes)

### 3.1 Layout Perf Board

- [ ] Establish ground star point at PSU negative terminal
- [ ] Keep switching loops tight (MOSFET → diode → inductor)
- [ ] Separate 5V and 3.3V output sections

### 3.2 Hand-Solder Components

- [ ] Solder in stages (input caps → ICs → switching stage → output caps)
- [ ] Visual inspection: no cold joints, no solder bridges
- [ ] Dry continuity check before power-up

### 3.3 Repeat All Phase 2 Tests

- [ ] Results should match breadboard ±5% (validates solder quality)
- [ ] **Go/No-Go:** **\_** → **Proceed to Phase 4 (PCB Design)**

---

## Phase 4: PCB Design & Manufacturing _(2–3 hrs preparation + fabrication)_

(To be completed after perf board validation)

### 4.1 KiCAD PCB Layout

- [ ] 4-layer stackup: Power / Ground / Signal / Signal
- [ ] Ground plane continuous on layer 2
- [ ] Switching loops <2cm, via stitching around loops
- [ ] Input filter near connector, output sections separated
- [ ] Thermal management for high-loss components
- [ ] Test points for oscilloscope probes

### 4.2 Add Protection Circuits

(Not on breadboard/perf board; PCB only)

- [ ] Input fuse (**\_** A slow-blow)
- [ ] NTC inrush thermistor (**\_** Ω @ 25°C)
- [ ] Output polyfuses (4A for 5V, 2A for 3.3V)
- [ ] Decoupling capacitors (100nF) near each IC power pin

### 4.3 Generate Manufacturing Files

- [ ] Gerber files (layers 1–4, outline, silkscreen, solder mask, drill)
- [ ] Bill of Materials (BOM) with part numbers
- [ ] Assembly drawing

### 4.4 Design Review

- [ ] KiCAD DRC: no errors
- [ ] Trace width & clearance: **\_** mm / **\_** mm
- [ ] Via size: **\_** mm diameter
- [ ] **Sign-off:** **\_** (ready for fabrication)

---

## Phase 5: PCB Validation & Integration _(1–2 hrs post-manufacturing)_

(To be completed after PCB fabrication & assembly)

### 5.1 Static Power-Up

- [ ] Power on with no load; measure 12V_IN, 5V_OUT, 3.3V_OUT
- [ ] Expected: 12V within ±0.5V, 5V within ±5%, 3.3V within ±5%

### 5.2 Load Sweep & Regulation

- [ ] Load 5V @ 0.5A, 1.5A, 3A: measure voltage & ripple
- [ ] Load 3.3V @ 0.5A, 1.5A: measure voltage & ripple
- [ ] Plot regulation curve (should be flat)

### 5.3 Transient Response & Thermal

- [ ] Step load test: 0.5A → **\_** A on each converter
- [ ] Measure recovery time: **\_** ms (target <50ms)
- [ ] Thermal imaging: no hot spots (< **\_**°C)

### 5.4 Integration Test

- [ ] Connect to STM32 circuit (5V rail) + motors (12V rail) + 3.3V sensors
- [ ] 1-hour soak test under realistic load
- [ ] No shutdowns, no smoke ✓

---

## Summary Table: Expected Values

| Parameter                | 12V→5V | 12V→3.3V | Unit |
| ------------------------ | ------ | -------- | ---- |
| Input voltage            | **\_** | **\_**   | V    |
| Output voltage (nominal) | 5.0    | 3.3      | V    |
| Output ripple (max)      | <100   | <100     | mV   |
| Rated current            | **\_** | **\_**   | A    |
| Duty cycle (D)           | **\_** | **\_**   | %    |
| Inductor                 | **\_** | **\_**   | µH   |
| Output capacitor         | **\_** | **\_**   | µF   |
| Efficiency @ rated       | **\_** | **\_**   | %    |
| MOSFET temp rise         | **\_** | **\_**   | °C   |

---
