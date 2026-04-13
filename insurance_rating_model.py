"""
Insurance Rating & Financial Risk Modeling Tool
Author: William Coney
Description:
    Simulates manual and experience-based rating to calculate premiums
    from loss history and exposure data. Applies frequency/severity
    adjustments and class factors to pricing outputs. Reflects real-world
    carrier rating worksheets with stepwise calculation flow.
"""

import json
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
#  DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class ExposureData:
    """Represents insured exposure inputs."""
    insured_name: str
    policy_year: int
    line_of_business: str          # e.g. "Auto", "General Liability", "Property"
    exposure_units: float          # e.g. vehicle count, payroll, square footage
    exposure_type: str             # e.g. "Vehicles", "Payroll ($000s)", "Sq Ft"
    class_code: str                # carrier class code
    territory: str                 # rating territory


@dataclass
class LossHistory:
    """Three-year loss history for experience rating."""
    year_1_losses: float
    year_1_claims: int
    year_2_losses: float
    year_2_claims: int
    year_3_losses: float
    year_3_claims: int
    loss_development_factor: float = 1.15   # IBNR development factor


@dataclass
class RatingFactors:
    """Carrier-defined rating factors applied stepwise."""
    base_rate: float               # Base rate per exposure unit
    class_factor: float            # Adjustment for class code risk
    territory_factor: float        # Geographic risk adjustment
    limit_factor: float            # Coverage limit adjustment
    deductible_credit: float       # Deductible discount (e.g. 0.85 = 15% credit)
    schedule_mod: float            # Underwriter schedule modification (+/- 25%)
    experience_mod: float = 1.0    # Calculated from loss history (EMod)


@dataclass
class PremiumBreakdown:
    """Full stepwise premium calculation output."""
    insured_name: str
    line_of_business: str
    exposure_units: float
    exposure_type: str

    base_premium: float = 0.0
    class_adjusted: float = 0.0
    territory_adjusted: float = 0.0
    limit_adjusted: float = 0.0
    deductible_adjusted: float = 0.0
    schedule_adjusted: float = 0.0
    experience_adjusted: float = 0.0
    final_premium: float = 0.0

    # Experience rating detail
    actual_losses_developed: float = 0.0
    expected_losses: float = 0.0
    loss_ratio: float = 0.0
    credibility_weight: float = 0.0
    experience_mod: float = 1.0

    # Frequency / severity detail
    avg_claim_frequency: float = 0.0
    avg_claim_severity: float = 0.0
    pure_premium: float = 0.0

    audit_notes: list = field(default_factory=list)


# ─────────────────────────────────────────────
#  CLASS FACTOR TABLES
# ─────────────────────────────────────────────

CLASS_FACTORS = {
    # Auto
    "CA-01": {"name": "Private Passenger Auto - Standard",    "factor": 1.00},
    "CA-02": {"name": "Private Passenger Auto - Preferred",   "factor": 0.88},
    "CA-03": {"name": "Light Commercial Truck (<10k lbs)",    "factor": 1.12},
    "CA-04": {"name": "Heavy Commercial Truck (>10k lbs)",    "factor": 1.38},
    "CA-05": {"name": "Fleet Auto - Mixed Use",               "factor": 1.22},
    # General Liability
    "GL-01": {"name": "Retail Store - Low Hazard",            "factor": 1.00},
    "GL-02": {"name": "Contractor - General Building",        "factor": 1.45},
    "GL-03": {"name": "Restaurant / Food Service",            "factor": 1.28},
    "GL-04": {"name": "Manufacturing - Light",                "factor": 1.55},
    "GL-05": {"name": "Professional Services",                "factor": 0.82},
    # Property
    "PR-01": {"name": "Frame Construction - Residential",     "factor": 1.00},
    "PR-02": {"name": "Masonry Construction - Commercial",    "factor": 0.92},
    "PR-03": {"name": "Fire Resistive - High Rise",           "factor": 0.78},
    "PR-04": {"name": "Wood Frame - Older Construction",      "factor": 1.35},
    "PR-05": {"name": "Mixed Use Commercial",                 "factor": 1.18},
}

TERRITORY_FACTORS = {
    "TX-01": {"name": "Dallas / Fort Worth Metro",     "factor": 1.12},
    "TX-02": {"name": "Houston Metro",                 "factor": 1.18},
    "TX-03": {"name": "Austin / San Antonio Metro",    "factor": 1.05},
    "TX-04": {"name": "Rural / West Texas",            "factor": 0.88},
    "TX-05": {"name": "Gulf Coast / Coastal",          "factor": 1.32},
    "TX-06": {"name": "Panhandle / North Texas",       "factor": 0.94},
}

# Credibility table: % of experience to use based on 3-yr claim count
CREDIBILITY_TABLE = [
    (0,   5,   0.00),
    (5,   10,  0.15),
    (10,  20,  0.30),
    (20,  35,  0.50),
    (35,  50,  0.65),
    (50,  75,  0.80),
    (75,  100, 0.90),
    (100, 999, 1.00),
]


# ─────────────────────────────────────────────
#  CORE RATING ENGINE
# ─────────────────────────────────────────────

class InsuranceRatingEngine:
    """
    Stepwise premium calculation engine reflecting carrier rating worksheets.
    Supports manual rating and experience-based modification.
    """

    def calculate_experience_mod(
        self,
        loss_history: LossHistory,
        factors: RatingFactors,
        exposure: ExposureData
    ) -> tuple[float, dict]:
        """
        Calculate experience modification factor (EMod) from 3-year loss history.
        Uses credibility-weighted approach standard in commercial lines rating.
        """
        # Develop losses for IBNR (Incurred But Not Reported)
        y1_dev = loss_history.year_1_losses * loss_history.loss_development_factor
        y2_dev = loss_history.year_2_losses * loss_history.loss_development_factor
        y3_dev = loss_history.year_3_losses  # Most recent year - no development

        total_actual_developed = y1_dev + y2_dev + y3_dev
        total_claims = (
            loss_history.year_1_claims +
            loss_history.year_2_claims +
            loss_history.year_3_claims
        )

        # Expected losses: what carrier expects given exposure and base rate
        expected_losses = (
            factors.base_rate *
            exposure.exposure_units *
            CLASS_FACTORS.get(exposure.class_code, {}).get("factor", 1.0) *
            3  # 3-year period
        )

        # Credibility weight based on claim count
        credibility = 0.0
        for lo, hi, cred in CREDIBILITY_TABLE:
            if lo <= total_claims < hi:
                credibility = cred
                break

        # Blended loss ratio
        loss_ratio = total_actual_developed / expected_losses if expected_losses > 0 else 1.0
        blended_ratio = (credibility * loss_ratio) + ((1 - credibility) * 1.0)

        # Cap EMod: most carriers allow +/- 50% swing
        emod = max(0.50, min(1.50, blended_ratio))

        detail = {
            "year_1_losses_developed": round(y1_dev, 2),
            "year_2_losses_developed": round(y2_dev, 2),
            "year_3_losses_developed": round(y3_dev, 2),
            "total_actual_developed": round(total_actual_developed, 2),
            "total_claims_3yr": total_claims,
            "expected_losses": round(expected_losses, 2),
            "credibility_weight": credibility,
            "loss_ratio": round(loss_ratio, 4),
            "blended_ratio": round(blended_ratio, 4),
            "experience_mod": round(emod, 4),
        }

        return emod, detail

    def calculate_frequency_severity(
        self,
        loss_history: LossHistory,
        exposure: ExposureData
    ) -> tuple[float, float, float]:
        """
        Calculate pure premium from frequency and severity components.
        Pure Premium = Frequency × Severity
        """
        total_claims = (
            loss_history.year_1_claims +
            loss_history.year_2_claims +
            loss_history.year_3_claims
        )
        total_losses = (
            loss_history.year_1_losses +
            loss_history.year_2_losses +
            loss_history.year_3_losses
        )
        total_exposure_units = exposure.exposure_units * 3  # 3-year exposure base

        avg_frequency = total_claims / total_exposure_units if total_exposure_units > 0 else 0
        avg_severity = total_losses / total_claims if total_claims > 0 else 0
        pure_premium = avg_frequency * avg_severity

        return round(avg_frequency, 4), round(avg_severity, 2), round(pure_premium, 2)

    def rate(
        self,
        exposure: ExposureData,
        loss_history: LossHistory,
        factors: RatingFactors
    ) -> PremiumBreakdown:
        """
        Full stepwise premium calculation.
        Mirrors carrier rating worksheet flow used in commercial underwriting.
        """
        result = PremiumBreakdown(
            insured_name=exposure.insured_name,
            line_of_business=exposure.line_of_business,
            exposure_units=exposure.exposure_units,
            exposure_type=exposure.exposure_type,
        )

        notes = []

        # ── STEP 1: Base Premium ──────────────────────────────────────
        result.base_premium = round(factors.base_rate * exposure.exposure_units, 2)
        notes.append(
            f"Step 1 | Base Premium: ${factors.base_rate:.2f} × "
            f"{exposure.exposure_units} {exposure.exposure_type} = ${result.base_premium:,.2f}"
        )

        # ── STEP 2: Class Factor ──────────────────────────────────────
        class_info = CLASS_FACTORS.get(exposure.class_code, {"name": "Unknown", "factor": 1.0})
        factors.class_factor = class_info["factor"]
        result.class_adjusted = round(result.base_premium * factors.class_factor, 2)
        notes.append(
            f"Step 2 | Class Factor ({exposure.class_code} - {class_info['name']}): "
            f"× {factors.class_factor:.2f} = ${result.class_adjusted:,.2f}"
        )

        # ── STEP 3: Territory Factor ──────────────────────────────────
        territory_info = TERRITORY_FACTORS.get(exposure.territory, {"name": "Unknown", "factor": 1.0})
        factors.territory_factor = territory_info["factor"]
        result.territory_adjusted = round(result.class_adjusted * factors.territory_factor, 2)
        notes.append(
            f"Step 3 | Territory Factor ({exposure.territory} - {territory_info['name']}): "
            f"× {factors.territory_factor:.2f} = ${result.territory_adjusted:,.2f}"
        )

        # ── STEP 4: Coverage Limit Factor ────────────────────────────
        result.limit_adjusted = round(result.territory_adjusted * factors.limit_factor, 2)
        notes.append(
            f"Step 4 | Coverage Limit Factor: "
            f"× {factors.limit_factor:.2f} = ${result.limit_adjusted:,.2f}"
        )

        # ── STEP 5: Deductible Credit ─────────────────────────────────
        result.deductible_adjusted = round(result.limit_adjusted * factors.deductible_credit, 2)
        deductible_pct = round((1 - factors.deductible_credit) * 100, 1)
        notes.append(
            f"Step 5 | Deductible Credit ({deductible_pct}% credit): "
            f"× {factors.deductible_credit:.2f} = ${result.deductible_adjusted:,.2f}"
        )

        # ── STEP 6: Schedule Modification ────────────────────────────
        if factors.schedule_mod < 1.0:
            sched_desc = f"{round((1 - factors.schedule_mod)*100, 1)}% credit"
        elif factors.schedule_mod > 1.0:
            sched_desc = f"{round((factors.schedule_mod - 1)*100, 1)}% debit"
        else:
            sched_desc = "No modification"

        result.schedule_adjusted = round(result.deductible_adjusted * factors.schedule_mod, 2)
        notes.append(
            f"Step 6 | Schedule Modification ({sched_desc}): "
            f"× {factors.schedule_mod:.2f} = ${result.schedule_adjusted:,.2f}"
        )

        # ── STEP 7: Experience Modification ──────────────────────────
        emod, emod_detail = self.calculate_experience_mod(loss_history, factors, exposure)
        factors.experience_mod = emod
        result.experience_mod = emod
        result.actual_losses_developed = emod_detail["total_actual_developed"]
        result.expected_losses = emod_detail["expected_losses"]
        result.loss_ratio = emod_detail["loss_ratio"]
        result.credibility_weight = emod_detail["credibility_weight"]

        result.experience_adjusted = round(result.schedule_adjusted * emod, 2)

        emod_direction = "surcharge" if emod > 1.0 else "credit" if emod < 1.0 else "neutral"
        notes.append(
            f"Step 7 | Experience Modification (EMod {emod:.4f} - {emod_direction}, "
            f"credibility {emod_detail['credibility_weight']:.0%}): "
            f"× {emod:.4f} = ${result.experience_adjusted:,.2f}"
        )

        # ── STEP 8: Final Premium ─────────────────────────────────────
        result.final_premium = result.experience_adjusted
        notes.append(
            f"Step 8 | FINAL PREMIUM: ${result.final_premium:,.2f}"
        )

        # ── Frequency / Severity Analysis ────────────────────────────
        freq, sev, pure = self.calculate_frequency_severity(loss_history, exposure)
        result.avg_claim_frequency = freq
        result.avg_claim_severity = sev
        result.pure_premium = pure
        notes.append(
            f"Freq/Sev | Frequency: {freq:.4f} claims/unit | "
            f"Severity: ${sev:,.2f}/claim | Pure Premium: ${pure:,.2f}/unit"
        )

        result.audit_notes = notes
        return result


# ─────────────────────────────────────────────
#  OUTPUT FORMATTER
# ─────────────────────────────────────────────

def print_rating_worksheet(result: PremiumBreakdown):
    """Print a formatted rating worksheet mirroring carrier output."""
    width = 72
    print("\n" + "═" * width)
    print(f"  INSURANCE RATING WORKSHEET — {result.line_of_business.upper()}")
    print("═" * width)
    print(f"  Insured:      {result.insured_name}")
    print(f"  Exposure:     {result.exposure_units:,} {result.exposure_type}")
    print("─" * width)
    print(f"  {'RATING STEP':<48} {'PREMIUM':>12}")
    print("─" * width)

    steps = [
        ("1. Base Premium",            result.base_premium),
        ("2. After Class Factor",       result.class_adjusted),
        ("3. After Territory Factor",   result.territory_adjusted),
        ("4. After Limit Factor",       result.limit_adjusted),
        ("5. After Deductible Credit",  result.deductible_adjusted),
        ("6. After Schedule Mod",       result.schedule_adjusted),
        ("7. After Experience Mod",     result.experience_adjusted),
    ]

    for label, amount in steps:
        print(f"  {label:<48} ${amount:>11,.2f}")

    print("─" * width)
    print(f"  {'FINAL PREMIUM':<48} ${result.final_premium:>11,.2f}")
    print("═" * width)

    print("\n  EXPERIENCE RATING DETAIL")
    print("─" * width)
    print(f"  {'Actual Losses (Developed):':<40} ${result.actual_losses_developed:>11,.2f}")
    print(f"  {'Expected Losses:':<40} ${result.expected_losses:>11,.2f}")
    print(f"  {'Loss Ratio:':<40} {result.loss_ratio:>11.2%}")
    print(f"  {'Credibility Weight:':<40} {result.credibility_weight:>11.2%}")
    print(f"  {'Experience Modification (EMod):':<40} {result.experience_mod:>11.4f}")

    print("\n  FREQUENCY / SEVERITY ANALYSIS")
    print("─" * width)
    print(f"  {'Avg Claim Frequency (per unit):':<40} {result.avg_claim_frequency:>11.4f}")
    print(f"  {'Avg Claim Severity:':<40} ${result.avg_claim_severity:>11,.2f}")
    print(f"  {'Pure Premium (per unit):':<40} ${result.pure_premium:>11,.2f}")
    print("═" * width + "\n")


def export_json(result: PremiumBreakdown, filepath: str):
    """Export full rating detail to JSON for audit and validation."""
    data = {
        "insured": result.insured_name,
        "line_of_business": result.line_of_business,
        "exposure": {"units": result.exposure_units, "type": result.exposure_type},
        "premium_steps": {
            "base_premium": result.base_premium,
            "class_adjusted": result.class_adjusted,
            "territory_adjusted": result.territory_adjusted,
            "limit_adjusted": result.limit_adjusted,
            "deductible_adjusted": result.deductible_adjusted,
            "schedule_adjusted": result.schedule_adjusted,
            "experience_adjusted": result.experience_adjusted,
            "final_premium": result.final_premium,
        },
        "experience_rating": {
            "actual_losses_developed": result.actual_losses_developed,
            "expected_losses": result.expected_losses,
            "loss_ratio": result.loss_ratio,
            "credibility_weight": result.credibility_weight,
            "experience_mod": result.experience_mod,
        },
        "frequency_severity": {
            "avg_frequency_per_unit": result.avg_claim_frequency,
            "avg_severity_per_claim": result.avg_claim_severity,
            "pure_premium_per_unit": result.pure_premium,
        },
        "audit_trail": result.audit_notes,
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  ✓ JSON audit export saved to: {filepath}")


# ─────────────────────────────────────────────
#  DEMO — THREE SAMPLE RISKS
# ─────────────────────────────────────────────

def run_demo():
    engine = InsuranceRatingEngine()

    # ── RISK 1: Commercial Auto Fleet ─────────────────────────────────
    expo1 = ExposureData(
        insured_name="Lone Star Logistics LLC",
        policy_year=2026,
        line_of_business="Commercial Auto",
        exposure_units=18,
        exposure_type="Vehicles",
        class_code="CA-05",
        territory="TX-01",
    )
    loss1 = LossHistory(
        year_1_losses=42_800, year_1_claims=6,
        year_2_losses=31_200, year_2_claims=4,
        year_3_losses=18_500, year_3_claims=3,
        loss_development_factor=1.12,
    )
    factors1 = RatingFactors(
        base_rate=1_850,
        class_factor=1.0,     # overridden by class table
        territory_factor=1.0, # overridden by territory table
        limit_factor=1.18,    # $1M CSL limit
        deductible_credit=0.90,
        schedule_mod=0.95,    # 5% credit: good safety program
    )

    result1 = engine.rate(expo1, loss1, factors1)
    print_rating_worksheet(result1)
    export_json(result1, "/home/claude/portfolio/projects/insurance_rating_model/output_auto_fleet.json")

    # ── RISK 2: General Liability — Contractor ─────────────────────────
    expo2 = ExposureData(
        insured_name="Apex Roofing & Construction",
        policy_year=2026,
        line_of_business="General Liability",
        exposure_units=2_400,
        exposure_type="Payroll ($000s)",
        class_code="GL-02",
        territory="TX-03",
    )
    loss2 = LossHistory(
        year_1_losses=88_400, year_1_claims=9,
        year_2_losses=61_000, year_2_claims=7,
        year_3_losses=74_200, year_3_claims=8,
        loss_development_factor=1.20,
    )
    factors2 = RatingFactors(
        base_rate=12.50,
        class_factor=1.0,
        territory_factor=1.0,
        limit_factor=1.22,    # $2M / $4M aggregate
        deductible_credit=0.85,
        schedule_mod=1.10,    # 10% debit: prior losses above expected
    )

    result2 = engine.rate(expo2, loss2, factors2)
    print_rating_worksheet(result2)
    export_json(result2, "/home/claude/portfolio/projects/insurance_rating_model/output_gl_contractor.json")

    # ── RISK 3: Commercial Property ───────────────────────────────────
    expo3 = ExposureData(
        insured_name="Meridian Office Partners",
        policy_year=2026,
        line_of_business="Commercial Property",
        exposure_units=145_000,
        exposure_type="Sq Ft",
        class_code="PR-02",
        territory="TX-01",
    )
    loss3 = LossHistory(
        year_1_losses=12_000, year_1_claims=2,
        year_2_losses=0,      year_2_claims=0,
        year_3_losses=8_500,  year_3_claims=1,
        loss_development_factor=1.08,
    )
    factors3 = RatingFactors(
        base_rate=0.38,
        class_factor=1.0,
        territory_factor=1.0,
        limit_factor=1.05,
        deductible_credit=0.92,
        schedule_mod=0.92,    # 8% credit: masonry, sprinklered, favorable history
    )

    result3 = engine.rate(expo3, loss3, factors3)
    print_rating_worksheet(result3)
    export_json(result3, "/home/claude/portfolio/projects/insurance_rating_model/output_property.json")


if __name__ == "__main__":
    run_demo()
