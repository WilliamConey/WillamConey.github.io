# William Coney — Insurance Risk & Analytics Portfolio

Live portfolio: **[william-coney.github.io](https://william-coney.github.io)**

Licensed Texas Personal Lines Agent (multi-state, 29 states via Progressive network) with a background in risk modeling, financial analysis, and insurance data tools. Targeting claims adjuster and underwriting roles at major carriers.

---

## Projects

### 1. Insurance Rating & Financial Risk Modeling Tool
`/projects/insurance_rating_model/`

Simulates manual and experience-based rating to calculate commercial insurance premiums from loss history and exposure data.

**What it does:**
- Stepwise premium calculation mirroring carrier rating worksheets
- Class factor and territory factor application (full TX tables included)
- Experience modification (EMod) calculation with credibility weighting
- Frequency / severity analysis and pure premium derivation
- JSON audit export for each rated risk

**Lines of business covered:** Commercial Auto, General Liability, Commercial Property

**Run it:**
```bash
cd projects/insurance_rating_model
python insurance_rating_model.py
```

**Sample output:**
```
════════════════════════════════════════════════════════════════════════
  INSURANCE RATING WORKSHEET — COMMERCIAL AUTO
════════════════════════════════════════════════════════════════════════
  Insured:      Lone Star Logistics LLC
  Exposure:     18 Vehicles
────────────────────────────────────────────────────────────────────────
  1. Base Premium                                  $  33,300.00
  2. After Class Factor                            $  40,626.00
  3. After Territory Factor                        $  45,501.12
  4. After Limit Factor                            $  53,691.32
  5. After Deductible Credit                       $  48,322.19
  6. After Schedule Mod                            $  45,906.08
  7. After Experience Mod                          $  43,589.87
────────────────────────────────────────────────────────────────────────
  FINAL PREMIUM                                    $  43,589.87
════════════════════════════════════════════════════════════════════════
```

---

### 2. Business Credit Risk Evaluation Model *(coming soon)*
`/projects/credit_risk_model/`

Scoring model using revenue stability, debt ratios, payment history, and industry risk to classify business risk tiers and simulate underwriting decisions.

---

### 3. Surety Risk & Contract Evaluation Simulation *(coming soon)*
`/projects/surety_risk/`

Models contractor risk, cash flow, leverage, and completion risk to simulate bond approval and capacity limits with scenario testing.

---

## Tech Stack

| Tool | Use |
|------|-----|
| Python 3.10+ | Core modeling and simulation |
| dataclasses | Structured data models |
| json | Audit output and export |
| HTML / CSS / JS | Interactive portfolio and live demo |

---

## Licenses & Certifications

- Texas Personal Lines Agent License — Active, April 2026
- Multi-State Insurance Licenses — 29 States (Progressive Carrier Network)
- Google Data Analytics Certificate

---

## Contact

**Email:** wconey.info@gmail.com  
**LinkedIn:** [linkedin.com/in/williamconey](#)  
**Location:** Dallas, TX · Remote Eligible
