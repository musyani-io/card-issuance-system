# Power Supply Design — 12V→5V & 3.3V Buck Converters

> **Project:** Smart ID Card Distribution Kiosk  
> **Component:** Dual independent buck converters  
> **Input:** 12V 10A PSU  
> **Outputs:** 5V @ 3A (logic rail)
> **Technology:** THT (Through-Hole) components, breadboard-testable, PCB-ready  
> **Status:** Design phase — Phase 1 in progress

---

## Architecture Overview

```bash
12V 10A PSU (external power supply)
    │
    ├──→ [Reverse Polarity Protection MOSFET] ──→ [12V→5V Buck Converter] ← PROTECTS MCU RAIL
    │    Phase 0: 5A rated protection              PWM Controller + Switching Stage + Filtering
    │    (for microcontroller circuit only)         Output: 5V Rail (up to 6A available)
    │                                               Loads: STM32 Nucleo board (5V input)
    │
    │                                               └─→ STM32 Nucleo-F401RE (onboard 3.3V regulator)
    │                                                   Output: 3.3V Rail for GPIO, sensors
    │
    └──→ [Separate fuse 5A] ──→ Motor drivers & solenoid (12V direct, unprotected)
         (12V motors/solenoids connect here)
```

**Design Philosophy:**

- **Protection scope:** Phase 0 MOSFET protects ONLY the 5V buck converter rail (sensitive STM32 microcontroller circuits)
- **Motor rail:** 12V motors/solenoid connect directly to PSU with separate 5A fuse (motors are robust to reverse polarity; microcontroller is not)
- Same PWM frequency (100 kHz) → reduces switching noise coupling
- All THT components → breadboard-native, hand-solderable
- **Current budget:** ~3A buck converter input + ~2-4A motors = ~5-7A total from PSU (well within 10A supply)

---

## Phase 0: Reverse Polarity Protection for 5V Buck Converter (1.5–2 hrs)

> **Goal:** Protect ONLY the 12V→5V buck converter (5V MCU rail) from reverse polarity.  
> **Scope:** 5A-rated input protection (nominal 3A buck input + 1.67× transient margin).  
> **Method:** P-channel high-side reverse-polarity protection (gate-bias controlled).  
> **Protection:** Blocks reverse current; operates ~0Ω conduction loss in forward direction.  
> **Architecture note:** 12V motor rail (A4988, solenoid) connects directly to PSU with separate 5A fuse — motors are robust to polarity reversal, protection not needed.

### 0.1: Select Protection MOSFET

**Requirements:**

- Vds(max) ≥ **20** V (12V nominal + overshoot margin = 1.7× safety factor)
- Id(max) ≥ **5** A (protection rating: 3A nominal input + 1.67× transient headroom)
- Rds(on) @ Vgs=-10V ≤ **0.22** Ω (minimize conduction loss in forward path)
- Package: TO-220 (breadboard-friendly)
- Standard threshold voltage (Vgs(th) ~-2 to -4V) acceptable

**Candidates Considered:**

| MOSFET   | Vds  | Id  | Rds(on) @ -10V | Vgs(th)   |
| -------- | ---- | --- | -------------- | --------- |
| IRF9540N | 100V | 23A | 117mΩ          | -2 to -4V |
| FQP47P06 | 60V  | 47A | 26mΩ           | -2 to -4V |
| IRF4905  | 55V  | 74A | 20mΩ           | -2 to -4V |

**Selected MOSFET:** **IRF4905**

**Verification:**

- Vds margin: **55** V rated / 12V required = **4.583** × headroom ✓
- Id margin: **74** A rated / **5** A required = **14.8** × headroom ✓
- Conduction loss @ 5A: P = 5² × **20m** ≈ **0.5** W (check thermal limit) ✓

---

### 0.2: Design Gate Bias (P-Channel High-Side)

**Purpose:** Pull gate below source in forward polarity (keeping P-channel MOSFET ON) and force gate toward source in reverse polarity (turning MOSFET OFF).

**Gate-bias topology options:**

| Method                               | Purpose                                                           | Trade-offs                           |
| ------------------------------------ | ----------------------------------------------------------------- | ------------------------------------ |
| **Resistor pull-up + NPN pull-down** | Simple discrete high-side control for P-MOS gate                  | More parts, transistor sizing needed |
| **Zener-clamped gate network**       | Limits \|Vgs\| to safe value while enabling fast gate transitions | Clamp value selection is critical    |
| **Dedicated high-side gate driver**  | Strong gate drive and cleaner switching edges                     | Higher cost and complexity           |

**Selected gate-bias method:** **Zener-clamped gate network**

**Gate-clamp Zener options (if Zener clamp method is used):**

| Vz       | Purpose                                               | Trade-offs                              |
| -------- | ----------------------------------------------------- | --------------------------------------- |
| **12** V | Conservative \|Vgs\| clamp for most P-channel devices | Slightly lower overdrive                |
| **15** V | Stronger gate overdrive while below common ±20V limit | Higher stress if transients are present |
| **18** V | Maximum overdrive near device limits                  | Tight transient margin required         |

**Selected clamp voltage:** **12** V

**Gate-clamp device options:**

- Component: **1N4742A**
- Package: DO-41 axial (THT)
- Power rating: ≥ **200** mW

**Gate-bias circuit power dissipation:**

Maximum current through the clamp path occurs when gate-to-source voltage is driven to its clamp level:

```bash
P_zener = Vz × I_zener_max
I_zener_max ≈ (Vs_max - Vz) / Rg
Rg = 0.62 kΩ (from section 0.3)

I_zener_max = (13.2 - 12) /  0.62k = 1.935 mA
P_zener = 12 × 1.935 = 23.225 mW
```

**Gate-bias selection verified:** **\_**

---

### 0.3: Calculate Gate Resistor (Rg)

**Purpose:** Limit gate transition current AND set gate-bias current in forward polarity.

**Formula:** Rg = (Vs_max - |Vgs_target|) / Ig_desired

Where:

- Vs_max = maximum source voltage = **13.2** V
- |Vgs_target| = target gate overdrive magnitude = **10** V
- Ig_desired = target gate current (typical 5–10 mA for fast turn-on)

**Design choice (Ig_desired):** **5** mA (select 5, 7, or 10)

**Calculation:**

```bash
Rg = (13.2 - 10) / (7 × 10⁻³)
Rg = 3.2 / (5 × 10⁻³)
Rg =  640 Ω
```

**Round to nearest standard resistor value:**

Rg (selected) = **0.62** kΩ (carbon film, ±5%, ≥0.5W)

**Gate charging time estimate** (affects reverse-polarity response speed):

```bash
τ_gate = Rg × Cg  [from section 0.7]
τ_gate = 0.62 kΩ × 4.7 nF = 2.914 µs (5τ ≈ reverse response time)
```

---

### 0.4: Calculate Forward-Conduction Loss

**In forward polarity, Q1_protect conducts the full input current.**

**Formula:** P_loss = I_in² × Rds(on)

Where:

- I_in = maximum input current = **5** A (protection rating; nominal ~3A for buck converter)
  - Nominal buck input: I_in_nom ≈ Pout / η = (5V × 3A) / 0.80 ≈ 18.75W / 12V ≈ 3.1A
  - **Protection rating:** **5A** (3A nominal + 1.67× transient margin for surge current)
- Rds(on) = on-resistance of selected MOSFET @ -10V gate drive = **20** mΩ

**Calculation:**

```bash
P_loss = (5)² × (20 × 10⁻³)
P_loss = 25 × 20 × 10⁻³
P_loss =  0.5 W
```

**Voltage drop across Q1_protect:**

```bash
V_drop = I_in × Rds(on) = 5 A × 20 mΩ =  0.1 V
```

**Interpretation:** This **0.1** V drop reduces available voltage for the buck converter:

```bash
Available input to buck = 12V - V_drop = 12 - 0.1 = 11.9 V (Acceptable)
```

---

### 0.5: Thermal Analysis (Protection MOSFET)

**Assumptions:**

- Thermal resistance (junction to ambient, free convection on breadboard): **Rth_j-a = 62 °C/W**
- Ambient temperature: **25 °C**
- Power dissipation (from 0.4): **P_loss = **0.5** W**

**Temperature rise:**

```bash
ΔT = P_loss × Rth_j-a
ΔT = 0.5 W × 62 °C/W
ΔT = 31 °C
```

**Junction temperature:**

```bash
Tj = T_ambient + ΔT
Tj = 25 + 31 = 56 °C
```

**Thermal margin to absolute maximum (Tj_max = **175**°C typical for selected P-channel MOSFET):**

```bash
Margin = Tj_max - Tj = 175 - 56 = 119 °C (Safe)
```

**If temperature margin < 30°C:** Consider adding heat sink or reducing Rds(on) via alternate MOSFET.

---

### 0.6: Design Gate Capacitor (Cg)

**Purpose:** Smooth gate voltage transitions; sets RC time constant with Rg to prevent oscillation.

**Desired time constant (τ):** Target **1–5 µs** for balanced fast response + noise immunity.

**Formula:** Cg = τ / Rg

Where:

- τ = chosen time constant = **3** µs (recommend **2–3 µs**)
- Rg = gate resistor = **0.62** kΩ (from section 0.3)

**Calculation:**

```bash
Cg = 3 µs / 0.62 kΩ
Cg = 4.84 nF
```

**Round to nearest standard capacitor:**

Cg (selected) = **4.7** nF (ceramic, ≥16V rated)

**Verify gate RC time constant:**

```bash
τ_actual = Rg × Cg = 620 × 4.7n = 2.914 µs (on target)
```

---

### 0.7: Component Verification Table (Phase 0)

**Summary of all protection components:**

| **Component**          | **Design Value**           | **Selected Part**       | **Rating Check**                          | **Status** |
| ---------------------- | -------------------------- | ----------------------- | ----------------------------------------- | ---------- |
| Protection MOSFET (Q1) | Vds≥**20**V, Id≥**5**A     | **IRF4905**             | **Vds=55V, Id=74A (pass)**                | **✓**      |
| Rds(on) @ -10V         | ≤**220**mΩ                 | **20mΩ**                | **11x better than limit**                 | **✓**      |
| Gate-clamp diode       | Vz=**12**V, P≥**23.225**mW | **1N4742A**             | **P_rating=1W >> P_diss=23.225mW**        | **✓**      |
| Gate resistor (Rg)     | **640**Ω, P≥**0.5**W       | **0.62kΩ ±5%**          | **Within tolerance of calc value**        | **✓**      |
| Gate capacitor (Cg)    | **4.84**nF, V≥16V          | **4.7nF ceramic**       | **Nearest standard value, V rating pass** | **✓**      |
| Forward P_loss         | **~0.5**W @ 5A rated       | (calculated)            | **Acceptable for TO-220 thermal budget**  | **✓**      |
| Tj @ 25°C ambient      | **56**°C                   | (calculated)            | **Below Tj_max=175°C with large margin**  | **✓**      |
| Gate RC time constant  | **2.914**µs                | **Rg=0.62kΩ, Cg=4.7nF** | **Within 1-5µs target**                   | **✓**      |

**Go/No-Go:** All protection components within design margin? **Yes**

---

### 0.8: Reverse-Polarity Response Timing Verification

**Scenario:** User accidentally connects +12V to negative terminal (reverse polarity).

**Expected response:**

1. **Gate pulled toward source (OFF state):** ~5τ = **14.57** µs

- Gate voltage approaches source voltage in roughly this time

1. **MOSFET turn-off:** ~**\_** µs after \|Vgs\| falls below threshold
2. **Body diode blocks reverse current:** MOSFET acts as check-valve

**Calculated response time:**

```bash
Response ≈ 5 × τ = 5 × 2.914 µs = 14/57 µs (< 100µs = safe)
```

**Load transient immunity:** If forward load step occurs (e.g., servo + stepper simultaneous), RC time constant prevents gate ringing. Target: **0-10% overshoot** on 5V rail.

**Verification:** Testing during Phase 2 (breadboard) will confirm actual response via oscilloscope.

---

## Phase 1: Detailed Design & Calculation (6–8 hrs)

### 1.1: Define Electrical Specifications _(1 hr total)_

#### For 12V→5V Converter

**Input specification:**

- Nominal input voltage: **12** V
- Input range (±10% tolerance): **10.8** V to **13.2** V
- Expected PSU ripple contribution: **100** mV

**Output specification:**

- Target output voltage: 5.0V
- Allowed tolerance: ±**5**% → voltage range: **4.75** V to **5.25** V
- Rated load current (continuous): **2.5** A (Two servos won't work simultaneously)
- Maximum transient load (servo startup): **1.5** A
- Output ripple budget: **100** mV peak-to-peak
- Acceptable ripple percentage: **2** % of output (typically 2–5%)
- Thermal limit: MOSFET/diode junction <**100** °C @ ambient 25°C

#### Level Shifting & Signal Safety

**Three voltage domains in this design:**

- **12V:** Motor power, solenoid coil, PSU
- **5V:** Servo power, sensor power, logic rail
- **3.3V:** STM32 GPIO inputs/outputs

**Component signal compatibility:**

| Component            | Power     | Signal Path                         | Level Shift | Solution                                        |
| -------------------- | --------- | ----------------------------------- | ----------- | ----------------------------------------------- |
| **SG90 Servo (2×)**  | 5V        | STM32 → 3.3V PWM → Servo            | ✓ NO        | Direct connection (3.3V > 1.4V servo threshold) |
| **IR Sensors (4×)**  | 5V        | Sensor 5V output → STM32 3.3V GPIO  | ❌ **YES**  | **IC Level Shifter (74LVC245 or BSS138)**       |
| **Hall A3144**       | 5V        | Open-drain sensor → STM32 GPIO      | ✓ NO        | 10kΩ pull-up resistor to 3.3V                   |
| **A4988 Driver**     | 12V motor | STM32 3.3V GPIO → A4988 logic input | ✓ NO        | Direct connection (TTL compatible)              |
| **Solenoid Control** | 12V       | STM32 3.3V GPIO → MOSFET gate       | ⚠️ PARTIAL  | **Logic-level MOSFET** for full saturation      |

**Critical notes:**

- **IR Sensors:** 5V output exceeds STM32 max input (3.6V) → **Mandatory IC shifter**
- **Hall Sensor:** Open-drain output naturally fits 3.3V logic → pull-up only
- **Solenoid:** Standard MOSFETs won't fully saturate at 3.3V gate drive → use logic-level type
- **Servo/A4988:** Both accept 3.3V logic natively (no shifters needed)

**BOM additions for signal interface:**

- 1× IC Level Shifter (74LVC245, 8-channel bidirectional) for IR sensors
- 1× 10kΩ resistor (pull-up for Hall sensor)
- 1× Logic-level MOSFET (AO3400A or 2N7000) for solenoid gate drive

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
| **SG3525**     | **DIP 16**  | **100 - 500** kHz | **Soft start, flexible freq, circuit protection, fine tolerance (1%)and THT package** |                                                 |
| **TL494**      | **PDIP 16** | **1 - 300** kHz   | **Flexible freq and THT package**                                                     | **Fixed V<sub>out</sub>, wider tolerance (5%)** |
| **MC34063**    | **PDIP 8**  | **100** kHz       | **Flexible V<sub>out</sub>, higher output current (1.5A) and THT package**            | **Fixed frequency**                             |

**Selected controller:** SG3525

**Key parameters from datasheet:**

- Reference voltage (Vref): **5.1** V
- Maximum frequency: **500** kHz
- Soft-start pin available: Yes
- Error amplifier gain (Aol): **500** V/V
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
- Id(max) ≥ **2.5** A (rated load current)
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

- I_pk_approx = I_out / (1 - D) = **2.5** / (1 - **0.4604**) = **4.633** A

**Requirements:**

- Vr(max) ≥ **13.2** V (reverse voltage)
- If(max) ≥ **4.633** A (peak forward current)
- Recovery time < **200** ns (fast recovery preferred)
- Package: axial or DO-41 THT

**Candidates:**

1. **\_** (Vr=***V, If=***A, trr=\_\_\_ns)
2. **\_** (Vr=***V, If=***A, trr=\_\_\_ns) — Schottky option for lower loss
3. **\_** (Vr=***V, If=***A, trr=\_\_\_ns)

**Selected:** \***\*\*\*\*\***\_\***\*\*\*\*\***

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
- Quantity: **2** pieces of **220** µF aluminum + **2** piece of **470** nF ceramic

**ESR ripple contribution:**

- Target: ΔV_ESR = **100** mV
- Formula: ESR ≤ ΔV_ESR / ΔI_L

**Calculation:**

```bash
ESR ≤ 100 mV / 0.75 A
ESR ≤ 0.133 Ω
```

**Verify selected capacitors meet ESR target:**

- Aluminum ESR (each): **220** mΩ (from datasheet)
- Ceramic ESR: **5** mΩ
- Parallel combination: **112.5** mΩ ✓ (meets **133** mΩ target?)

**Input filtering** (reduces PSU noise coupling):

- Capacitor 1: **220** µF, **16** V aluminum
- Capacitor 2: **470** nF, **16** V ceramic (fast transient response)
- Location: directly across 12V input connector

---

#### 1.4.8 Design Feedback Network (Voltage Divider)

**Formula:** Vout = Vref × (1 + R1/R2)

Where:

- Vref = internal reference voltage = **5.1** V (from controller datasheet)
- Vout = desired output = **5.1V** (equals Vref, so R1/R2 = 0)
- R1 = top resistor (from Vout to feedback pin)
- R2 = bottom resistor (from feedback pin to GND)

**Rearranged for R1/R2 ratio:**

```bash
5.1 = 5.1 × (1 + R1/R2)
1 = 1 + R1/R2
R1/R2 = 0
```

**Implication:** R1 should be **0 Ω** (omit R1, feedback traces directly to output)

**Practical implementation:**

- **Simplest:** No R1 resistor. Connect feedback line directly from output to COMP pin (pin 9)
- **Alternative:** R2 = **10 kΩ** (to ground), R1 = **0 Ω** (or bridge/jumper wire)

**Output voltage (direct reference):**

```bash
Vout_actual = Vref = 5.1 V
```

**Error from nominal 5V:** **+100 mV** (acceptable? Yes — within ±5% tolerance of 4.75–5.25V) ✓

**Trimming strategy (optional for fine-tuning):**

- Install **10 kΩ trim potentiometer** from output to feedback pin if exact 5.0V is required
- This allows adjustment of R1 from 0Ω to ~10kΩ, varying output from 5.1V down to ~2.55V
- **Recommended for breadboard:** Include the trim pot for flexibility during testing

---

#### 1.4.9 Design Compensation Network (Loop Stability)

**Goal:** Stable voltage regulation + fast transient response (<50ms recovery, <10% overshoot)

**Error amplifier feedback compensation:**

- Input impedance (Rin): **10** kΩ (feedback divider source)
- Desired loop crossover frequency (fc): **2** kHz (typically 1/50 of switching freq)
- Feedback capacitor (Cfb): **1.8** uF (reduces high-frequency gain)

**Output filter compensation:**

- Series resistor (Rc): **0.47** Ω (part of ramp filter network) - (2W wirewound)
- Capacitor to ground (Cc): **470** nF

**Soft-start capacitor (inrush limiting):**

- Css: **1** µF (limits startup ramp rate to prevent in-rush)

**Record selected values:**

- Cfb = **1.8** nF **25** V ceramic
- Rc = **0.47** Ω **2** W resistor
- Cc = **470** nF **25** V ceramic
- Css = **1** µF **25** V electrolytic

---

#### 1.4.10 Calculate Total Losses & Efficiency

**Summarize all loss contributions:**

| Loss Source              | Calculation                                | Power       |
| ------------------------ | ------------------------------------------ | ----------- |
| MOSFET conduction        | I² × Rds × D = 2.5² × 17.5m × 0.4604       | **0.050 W** |
| MOSFET switching         | ~15% of conduction loss (est.)             | **0.015 W** |
| Diode forward drop       | Vf × I_avg = 0.525V × 1.23A (from 1.4.5)   | **0.645 W** |
| Inductor DC resistance   | I² × DCR = 2.5² × 0.1Ω (47µH quality coil) | **0.625 W** |
| Gate drive & control     | ~10% of MOSFET loss                        | **0.065 W** |
| **Total converter loss** |                                            | **1.400 W** |

**Calculate efficiency:**

```bash
P_out = Vout × I_out = 5V × 2.5A = 12.5 W

η = P_out / (P_out + P_loss)
η = 12.5 / (12.5 + 1.400)
η = 12.5 / 13.9
η = 89.9% (Target: >80%) ✓
```

**Efficiency curve across load range:**

| Load Current | P_out | P_loss | η         | Note          |
| ------------ | ----- | ------ | --------- | ------------- |
| 0.5 A        | 2.5W  | 0.35W  | **87.7%** | Light load    |
| 1.5 A        | 7.5W  | 0.85W  | **89.8%** | Typical servo |
| 2.5 A        | 12.5W | 1.40W  | **89.9%** | Full rated    |
| 3.0 A        | 15.0W | 1.62W  | **90.3%** | Transient     |

**Thermal Analysis (MOSFET & Diode):**

| Component            | P_loss  | Rth_j-c        | Rth_c-a (free conv) | Rth_j-a (total) | ΔT @25°C   | Tj_max limit | Margin        |
| -------------------- | ------- | -------------- | ------------------- | --------------- | ---------- | ------------ | ------------- |
| **MOSFET (IRFZ44N)** | 0.065 W | 1.5°C/W        | 62°C/W              | 63.5°C/W        | **4.1°C**  | 150°C        | **145.9°C** ✓ |
| **Diode (MBR542)**   | 0.645 W | 1.0°C/W        | 50°C/W              | 51°C/W          | **32.9°C** | 125°C        | **92.1°C** ✓  |
| **Inductor (47µH)**  | 0.625 W | ~50°C/W (est.) | —                   | ~50°C/W         | **31.3°C** | 130°C        | **98.7°C** ✓  |

**Critical observation:** Diode is hottest component at ~58°C (ambient 25°C + 32.9°C rise).

**Recommendation for breadboard:** Place diode in airflow; consider small heatsink if thermal margin falls below 20°C during prolonged testing.

```bash
Tj_diode = T_ambient + ΔT = 25 + 32.9 = 57.9°C (Safe, well below 125°C limit)
```

---

#### 1.4.11 Verify All Component Ratings

| **Component**             | **Design Value**                   | **Rating Required**                  | **Selected Part**                          | **Datasheet Check**                      | **Safety Margin**                              | **Status** |
| ------------------------- | ---------------------------------- | ------------------------------------ | ------------------------------------------ | ---------------------------------------- | ---------------------------------------------- | ---------- |
| **MOSFET (Q1)**           | I=2.5A, Tj=58°C, Vds=13.2V         | Vds≥13.2V, Id≥2.5A, Tj≤150°C         | **IRFZ44N**                                | Vds=55V✓, Id=49A✓, Tj_max=150°C✓         | **4.17× voltage, 19.6× current, 92°C thermal** | ✓ PASS     |
| **Diode (D1)**            | I_pk=4.633A, Vr=13.2V, Tj=58°C     | Vr≥13.2V, If≥4.633A, Tj≤125°C        | **MBR542**                                 | Vr=40V✓, If=5A✓, Tj_max=125°C✓           | **3.03× voltage, 1.08× current, 67°C thermal** | ✓ PASS     |
| **Inductor (L1)**         | L=47µH±10%, I_peak=1.67A, DCR=0.1Ω | L=47µH±10%, I_rating≥2.5A, DCR≤0.15Ω | **Bourns 6300 Series 47µH THT**            | L=47µH✓, I_rating=3.3A✓, DCR=0.11Ω✓      | **1.97× current rating, 36% margin on DCR**    | ✓ PASS     |
| **Output Cap (C1, C2)**   | 2× 220µF, V≥16V, ESR<113mΩ         | C≥220µF, V≥10V, ESR<133mΩ            | **Panasonic FC 220µF 16V (2× parallel)**   | C=220µF✓, V=16V✓, ESR=110mΩ✓             | **1.6× voltage margin, 20% on ESR**            | ✓ PASS     |
| **Ceramic Cap (C3, C4)**  | 2× 470nF, V≥16V, ESR<5mΩ           | High-freq bypass, low ESR            | **TDK X7R 470nF 25V (2× parallel)**        | C=470nF✓, ESR≈2mΩ✓                       | **Excellent, 1.56× voltage margin**            | ✓ PASS     |
| **Input Cap (C5)**        | 220µF, 16V                         | Input filtering, ripple attenuation  | **Panasonic FC 220µF 16V**                 | Same as C1/C2✓                           | **Consistent with output caps**                | ✓ PASS     |
| **Input Ceramic (C6)**    | 470nF, 25V                         | Fast transient bypass on 12V rail    | **TDK X7R 470nF 25V**                      | Same as C3/C4✓                           | **Consistent**                                 | ✓ PASS     |
| **Cfb (Compensation)**    | 1.8µF, 25V, film preferred         | Error amp phase margin               | **Vishay MKS 1.8µF 25V (film)**            | ±5% tolerance✓, ESR<2Ω✓                  | **Tight tolerance critical**                   | ✓ PASS     |
| **Rc (Damping)**          | 0.47Ω, 2W wirewound                | LC resonance damping                 | **Vishay PWR163S 0.47Ω 2W**                | P=2W (actual: 4.23W @ 3A risky, monitor) | **Marginal—monitor in testing**                | ⚠️ CAUTION |
| **Cc (Compensation)**     | 470nF, 25V, ceramic                | LC resonance zero                    | **TDK X7R 470nF 25V**                      | ±10% tolerance acceptable✓               | **Good margin**                                | ✓ PASS     |
| **Css (Soft-Start)**      | 1.0µF, 25V                         | Startup inrush limiting              | **Panasonic ECA 1µF 25V (small aluminum)** | I_ss=50µA typical, t_ramp≈102ms✓         | **Acceptable for 5A protection**               | ✓ PASS     |
| **Feedback Divider (R2)** | 10kΩ, ±1%, 0.25W                   | Voltage divider to COMP pin          | **Yageo MFR 10kΩ 1% 0.25W (film)**         | Tolerance±1%✓, P<0.01W✓                  | **Excellent**                                  | ✓ PASS     |

**Go/No-Go:** All components within safe operating area? **YES** ✓

**Critical Notes:**

1. **Rc (0.47Ω 2W):** Dissipates 4.23W @ 3A rated current. 2W resistor will be hot but thermally safe for breadboard testing (short duration). For PCB phase, **upgrade to 5W wirewound or use 2× 0.94Ω in parallel** to split heat.
2. **Diode MBR542:** Hottest component (58°C junction). Ensure good airflow on breadboard.
3. **All capacitors:** Use low-ESR aluminum (Panasonic FC series, Nichicon UHE) and X7R ceramics for best performance.

---

#### 1.4.12 Create Proteus Schematic

**Components to include in simulation:**

### **Power Input Stage:**

- **Voltage source (V_in):** 12V DC with **0.15Ω series ESR** (models PSU internal resistance)
- **Input capacitor C5:** 220µF 16V aluminum (Panasonic FC)
- **Input ceramic C6:** 470nF 25V ceramic X7R

### **Switching Stage:**

- **MOSFET Q1:** IRFZ44N (TO-220, Vgs=10V pulse drive)
- **Gate drive resistor Rg:** Not included in simulation (PWM controller handles)
- **Freewheeling diode D1:** MBR542 (Schottky, Vr=40V, If=5A)
- **Inductor L1:** 47µH with **DCR = 0.1Ω** (critical for loss modeling)

### **Output Filtering:**

- **Output capacitor C1, C2:** 2× 220µF 16V aluminum (parallel)
- **Ceramic bypass C3, C4:** 2× 470nF 25V ceramic (parallel, high-freq decoupling)
- **Compensation network Rc-Cc:** 0.47Ω resistor (series) + 470nF capacitor (to GND)

### **Feedback & Control:**

- **Feedback divider R2:** 10kΩ (to GND from output)
- **Compensation capacitor Cfb:** 1.8µF (from error amp output to feedback node)
- **Soft-start capacitor Css:** 1.0µF (on Pin 8 of SG3525)
- **PWM Controller:** SG3525A model (DIP-16 behavioral subcircuit or ideal PWM source @ 100kHz, 46% duty cycle)

### **Load:**

- **Variable load resistor R_load:** From 1.67Ω (3A) to 10Ω (0.5A)
- **Alternatively:** Programmable current source for precise load steps

### **Test Points (TP):**

- **TP_12V_IN:** Monitor input voltage ripple
- **TP_5V_OUT:** Output voltage & ripple measurement
- **TP_GND:** Reference ground
- **TP_GATE:** MOSFET gate drive (for switching verification)
- **TP_COMP:** SG3525 compensation pin (for loop stability analysis)

**Simulations to run:**

**1. DC Operating Point Analysis** → Verify ±5% regulation at 0.5A, 1.5A, 2.5A
**2. Transient Startup (Soft-Start Ramp)** → Inrush < 3.5A, settling < 120ms
**3. Load Step Response** → Overshoot < 10%, recovery < 50ms
**4. Output Ripple & FFT** → Total ripple < 100mVpp
**5. Efficiency Curve** → η ≥ 85% across 0.5–3.0A range
**6. Loop Stability (Bode Plot)** → Phase margin > 45°, Gain margin > 12dB

**Expected Results Summary:**

| Test                      | Target | Expected   | Status |
| ------------------------- | ------ | ---------- | ------ |
| Voltage regulation @ 2.5A | ±5%    | 5.1V ±2.5% | ✓      |
| Output ripple             | <100mV | ~100mV     | ✓      |
| Soft-start settling       | <120ms | ~100ms     | ✓      |
| Load step overshoot       | <10%   | ~8%        | ✓      |
| Load step recovery        | <50ms  | ~20ms      | ✓      |
| Efficiency @ 2.5A         | >80%   | 89.9%      | ✓      |
| Phase margin (Bode)       | >45°   | ~55°       | ✓      |
| Gain margin (Bode)        | >12dB  | ~18dB      | ✓      |

---

### 1.5: 3.3V Supply (Onboard Regulator)

**Design Note:** STM32 Nucleo-F401RE includes onboard 3.3V LDO regulator.

- **Input:** 5V from buck converter
- **Output:** 3.3V (via internal regulator)
- **No external converter needed**

**Loads on 3.3V rail:**

- STM32 GPIO and microcontroller logic (~0.1A)
- Hall effect sensor (A3144) — **NO, this is 5V rated** (use 5V rail)
- Future 3.3V sensor expansions

**Verification:** Check Nucleo-F401RE datasheet for 3.3V output capacity. Typical: **≥500 mA available** for external loads.

---

### 1.6: Finalize Single-Converter Design _(0.5 hr)_

#### 1.6.1 Create KiCAD Schematic

**File:** `hardware/schematics/Power_Supply_5V_Buck.sch`

**Schematic structure:**

- Top-level power distribution diagram
  - Main sheet: "12V→5V Buck Converter"
  - Sub-sheet (optional): "Protection & Filtering" (fuses, inrush, decoupling — for PCB phase)
- 12V input with ground star point
- 5V output distribution to Nucleo board
- Test points labeled: TP_12V_IN, TP_5V_OUT, TP_GND

**Verify KiCAD schematic:**

- All nets connected (no floating wires)
- Voltage labels on all rails
- Component designators sequential (R1, R2, ... C1, C2, ... L1, L2, ... etc.)

#### 1.6.2 Proteus Verification (Single Converter)

**Simulation file:** 12V→5V buck converter standalone

**Test scenario:** 5V output loaded @ full 3A (STM32 Nucleo + external 5V devices)

**Measurements:**

- 5V output ripple: **\_** mV (target <100mV)
- Input current (12V draw): **\_** A
- Efficiency: **\_**%

**Stability check:**

- Oscillation present? Yes / No → if yes, adjust compensation
- Settling time after startup: **\_** ms (target <50ms)

**Go/No-Go Decision:**

- 5V ripple <100mV ✓
- No oscillation ✓
- Input current validates PSU capacity ✓
- **Decision:** **\_** → **Proceed to Phase 2 (Breadboard)**

---

## Phase 1 Deliverables Checklist

- [ ] Switching frequency & topology selected (1.2)
- [ ] PWM controller evaluated & chosen (1.3)
- [ ] 12V→5V converter fully designed (1.4.1–1.4.12)
  - [ ] All component values calculated
  - [ ] Proteus schematic simulated & verified
- [ ] 3.3V onboard regulator verified (Nucleo board capability: 1.5)
- [ ] Single converter KiCAD schematic created (1.6.1)
- [ ] Proteus verification complete & passed (1.6.2)
- [ ] Component bill of materials (BOM) compiled with part numbers & sources
- [ ] All calculation worksheets saved & documented

**Phase 1 Status:** **\_** / 100% complete

**Estimated effort:** 6–8 hours  
**Actual effort:** **\_** hours

---

## Phase 2: Breadboard Prototype & Testing _(3–4 hrs)_

(To be completed after Phase 1 design is finalized and Proteus sims pass)

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

| Parameter                | 12V→5V | Unit |
| ------------------------ | ------ | ---- |
| Input voltage            | **\_** | V    |
| Output voltage (nominal) | 5.1    | V    |
| Output ripple (max)      | <100   | mV   |
| Rated current            | **\_** | A    |
| Duty cycle (D)           | **\_** | %    |
| Inductor                 | **\_** | µH   |
| Output capacitor         | **\_** | µF   |
| Efficiency @ rated       | **\_** | %    |
| MOSFET temp rise         | **\_** | °C   |

---
