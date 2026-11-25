# CS110 Group 6 - Algorithmic Hiring Bias Simulator & Audit Tool
# File: bias_rules.py
# Contributor:
#
# Purpose: This is the "brain" of the app. It stores the hidden rules a biased
#          resume-screening algorithm might use, loads the applicants from
#          sample_applicants.txt, scores them, and builds the audit results.
#          main.py (the screen the user sees) imports this file.
#
# Concepts used: lists, dictionaries, functions, if/elif/else, loops,
#                text files, and JSON (the report export).
#
# Sources and assistance (see README Citations):
#   - Ideas about proxy variables and hiring: O'Neil (2016), Chapter 6.
#   - Disability and hiring-software background: EEOC (2022); CDT (2020).
#   - json (saving the audit report) and os (finding the data file's folder):
#     Python Software Foundation (n.d.-d, n.d.-e).

import json
import os

# ---------------------------------------------------------------------------
# THE ALGORITHM'S RULES
# ---------------------------------------------------------------------------

# ZIP codes the biased algorithm unfairly penalizes.
# NOTE: This list is a hypothetical choice made for the simulation. It shows how
# a ZIP code can act as a "proxy" for income. It is NOT a claim about the people
# who live there.
flagged_zip_codes = ["98584", "98402", "98108"]

# The numbers the screener uses. The sliders in main.py change these values.
# Contributors: Crystal R, Leilani G, Jasmine W & Frankie A.P.

algorithm_rules = {
    "max_gap_months": 6,   # employment gaps longer than this get penalized
    "zip_penalty": 20,     # points removed for living in a flagged ZIP code
    "gap_penalty": 25,     # points removed for a long employment gap
    "passing_score": 70,   # final score needed to reach a human recruiter
}

# Plain-English labels shown next to each slider.
rule_labels = {
    "max_gap_months": "Longest employment gap allowed (months)",
    "zip_penalty": "Penalty for a flagged ZIP code (points)",
    "gap_penalty": "Penalty for a long employment gap (points)",
    "passing_score": "Passing score needed (points)",
}

# Saved copies of the starting values so everything can be reset.
default_rules = {
    "max_gap_months": 6,
    "zip_penalty": 20,
    "gap_penalty": 25,
    "passing_score": 70,
}
default_zip_codes = ["98584", "98402", "98108"]

# ---------------------------------------------------------------------------
# EXPLANATION PANEL TEXT (Jasmine W. can edit these sentences)
# ---------------------------------------------------------------------------
simulation_note = (
    "About this simulation: the applicants are made-up sample profiles and the "
    "flagged ZIP codes are a hypothetical rule. Real screening software is "
    "private, so outsiders cannot see its actual rules."
)

bias_explanations = {
    "Medical gaps": (
        "A long employment gap often comes from medical leave, recovery, or "
        "caregiving. The Center for Democracy & Technology (2020) reports that "
        "people with disabilities can be disproportionately excluded when "
        "employers disfavor gaps in employment. A gap rule never measures "
        "whether the person can actually do the job."
    ),
    "Neurodivergent applicants": (
        "The EEOC (2022) explains that software can 'screen out' a person with "
        "a disability who could do the job with a reasonable accommodation. A "
        "fixed score cannot see accommodation needs or non-traditional career "
        "paths. O'Neil (2016) describes Kyle Behm, who was rejected from jobs "
        "after personality tests tied to his mental health history."
    ),
    "Low-income applicants": (
        "A ZIP code says nothing about skill. It is a proxy variable, an "
        "indirect stand-in that can quietly sort people by income. O'Neil "
        "(2016) warns that models built on proxies can punish people for "
        "where they come from while looking objective."
    ),
}


# ---------------------------------------------------------------------------
# FUNCTIONS
# ---------------------------------------------------------------------------
def reset_rules():
    """Put every rule and the flagged ZIP list back to the starting values."""
    for rule in default_rules:
        algorithm_rules[rule] = default_rules[rule]

    flagged_zip_codes.clear()
    for zip_code in default_zip_codes:
        flagged_zip_codes.append(zip_code)


def get_data_file_path(filename):
    """Find a data file in the same folder as this program.

    This way the app still works even if it is started from a different folder.
    """
    folder = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(folder, filename)


def make_applicant(name, zip_code, gap, score, note):
    """Check one applicant's information and build a dictionary for them.

    Returns (applicant, error). If everything is fine, error is an empty string.
    If something is wrong, applicant is None and error explains the problem.
    """
    name = name.strip()
    zip_code = zip_code.strip()
    gap = gap.strip()
    score = score.strip()

    if name == "":
        return None, "Please enter a name."
    if not zip_code.isdigit() or len(zip_code) != 5:
        return None, "The ZIP code must be exactly 5 digits."
    if not gap.isdigit():
        return None, "Gap months must be a whole number like 0, 3, or 12."
    if not score.isdigit() or int(score) > 100:
        return None, "The skills score must be a whole number from 0 to 100."

    applicant = {
        "name": name,
        "zip": zip_code,
        "gap_months": int(gap),
        "base_score": int(score),
        "note": note.strip(),
    }
    return applicant, ""


def load_applicants(path):
    """Read the text file and return (list of applicants, list of problems).

    Each line looks like: name, zip code, gap months, skills score, note
    """
    applicants = []
    problems = []

    try:
        with open(path, "r") as file:
            for line in file:
                line = line.strip()
                if line == "":
                    continue  # skip blank lines

                parts = line.split(",")
                if len(parts) != 5:
                    problems.append("Skipped a line that needs 5 parts: " + line)
                    continue

                applicant, error = make_applicant(
                    parts[0], parts[1], parts[2], parts[3], parts[4]
                )
                if error != "":
                    problems.append(error + " Line: " + line)
                else:
                    applicants.append(applicant)

    except FileNotFoundError:
        problems.append(
            "Could not find sample_applicants.txt. Keep it in the same folder "
            "as main.py."
        )

    return applicants, problems


# Plain labels for the four possible outcomes (shown in the "Audit flag" column).
outcome_labels = {
    "fair_pass": "Fair pass",
    "passed_despite_penalty": "Passed despite penalty",
    "fair_rejection": "Fair rejection (low skills)",
    "wrongly_rejected": "Wrongly rejected (bias)",
}


def score_applicant(applicant):
    """Apply the algorithm's rules to one applicant and return the results.

    The four possible outcomes (compare the algorithm to a fair, skills-only screen):
      fair_pass              - passed and lost no points
      passed_despite_penalty - lost points but still passed (penalty did no harm)
      fair_rejection         - rejected, and skills alone were below the bar too
      wrongly_rejected       - skills alone would have passed, but penalties
                               pushed the final score under the bar (the harm)
    """
    rules = algorithm_rules
    final_score = applicant["base_score"]
    reasons = []
    penalty_parts = []   # (label, points) pairs, used to show the math
    zip_hit = False
    gap_hit = False

    # Rule 1: ZIP code proxy (a penalty of 0 points changes nothing, so it is skipped)
    if applicant["zip"] in flagged_zip_codes and rules["zip_penalty"] > 0:
        final_score = final_score - rules["zip_penalty"]
        zip_hit = True
        penalty_parts.append(("flagged ZIP code " + applicant["zip"], rules["zip_penalty"]))
        reasons.append(
            "ZIP code " + applicant["zip"] + " is flagged (-"
            + str(rules["zip_penalty"]) + " points)"
        )

    # Rule 2: employment gap (a gap equal to the limit is allowed)
    if applicant["gap_months"] > rules["max_gap_months"] and rules["gap_penalty"] > 0:
        final_score = final_score - rules["gap_penalty"]
        gap_hit = True
        penalty_parts.append((str(applicant["gap_months"]) + "-month gap, limit "
                              + str(rules["max_gap_months"]), rules["gap_penalty"]))
        reasons.append(
            str(applicant["gap_months"]) + "-month gap is over the "
            + str(rules["max_gap_months"]) + "-month limit (-"
            + str(rules["gap_penalty"]) + " points)"
        )

    # A score cannot go below zero.
    raw_score = final_score
    if final_score < 0:
        final_score = 0

    penalized = zip_hit or gap_hit
    robot_passed = final_score >= rules["passing_score"]
    # Would this person have passed if only their skills were judged?
    skills_passed = applicant["base_score"] >= rules["passing_score"]

    if robot_passed and not penalized:
        outcome = "fair_pass"
    elif robot_passed:
        outcome = "passed_despite_penalty"
    elif not skills_passed:
        outcome = "fair_rejection"
    else:
        outcome = "wrongly_rejected"

    result = {
        "applicant": applicant,
        "final_score": final_score,
        "points_lost": applicant["base_score"] - final_score,
        "reasons": reasons,
        "penalty_parts": penalty_parts,
        "raw_score": raw_score,
        "zip_hit": zip_hit,
        "gap_hit": gap_hit,
        "penalized": penalized,
        "robot_passed": robot_passed,
        "skills_passed": skills_passed,
        "outcome": outcome,
        # Qualified on skills, but the algorithm rejected them anyway
        "wrongly_filtered": outcome == "wrongly_rejected",
    }
    return result


def percent(part, whole):
    """Return part/whole as a percent rounded to 1 decimal (None if whole is 0)."""
    if whole == 0:
        return None
    return round(part / whole * 100, 1)


def run_audit(applicants):
    """Screen every applicant. Returns (list of results, summary dictionary)."""
    results = []
    counts = {"fair_pass": 0, "passed_despite_penalty": 0,
              "fair_rejection": 0, "wrongly_rejected": 0}
    passed = 0
    qualified = 0
    wrongly_filtered = []
    penalized_total = 0
    penalized_passed = 0
    clean_total = 0
    clean_passed = 0

    for applicant in applicants:
        result = score_applicant(applicant)
        results.append(result)
        counts[result["outcome"]] += 1

        if result["robot_passed"]:
            passed += 1
        if result["skills_passed"]:
            qualified += 1
        if result["wrongly_filtered"]:
            wrongly_filtered.append(applicant["name"])

        # Compare applicants who lost points with applicants who did not.
        if result["penalized"]:
            penalized_total += 1
            if result["robot_passed"]:
                penalized_passed += 1
        else:
            clean_total += 1
            if result["robot_passed"]:
                clean_passed += 1

    penalized_rate = percent(penalized_passed, penalized_total)
    clean_rate = percent(clean_passed, clean_total)

    # Impact ratio: pass rate of penalized applicants / pass rate of the rest.
    impact_ratio = None
    if penalized_rate is not None and clean_rate is not None and clean_rate > 0:
        impact_ratio = round(penalized_rate / clean_rate, 2)

    summary = {
        "total": len(applicants),
        "passed": passed,
        "filtered": len(applicants) - passed,
        "qualified": qualified,
        "wrongly_filtered": wrongly_filtered,
        "percent_lost": percent(len(wrongly_filtered), qualified) or 0.0,
        "counts": counts,
        "penalized_total": penalized_total,
        "penalized_passed": penalized_passed,
        "penalized_rate": penalized_rate,
        "clean_total": clean_total,
        "clean_passed": clean_passed,
        "clean_rate": clean_rate,
        "impact_ratio": impact_ratio,
    }
    return results, summary


def describe_math(result):
    """Show how one applicant's final score was worked out, step by step."""
    base = result["applicant"]["base_score"]
    if len(result["penalty_parts"]) == 0:
        return str(base) + ", no penalties"

    text = str(base)
    for label, points in result["penalty_parts"]:
        text += " - " + str(points) + " (" + label + ")"
    text += " = " + str(result["final_score"])
    if result["raw_score"] < 0:
        text += " (a score cannot go below 0)"
    return text


def describe_decision(result):
    """Say what the algorithm decided and what a skills-only screen would do."""
    base = result["applicant"]["base_score"]
    passing = algorithm_rules["passing_score"]

    if result["robot_passed"]:
        text = f"Passing score is {passing}, so the algorithm PASSED."
    else:
        text = f"Passing score is {passing}, so the algorithm REJECTED."

    if result["robot_passed"] == result["skills_passed"]:
        text += f" Skills alone ({base}) would reach the same decision."
    else:
        text += f" Skills alone ({base}) would have PASSED."
    return text


def build_diagnostics_text(summary, results):
    """Write the audit explanation as plain text (used by both app screens).

    Only facts that are true for THIS run are printed, so the text changes
    when the rules or the applicants change.
    """
    rules = algorithm_rules
    total = summary["total"]
    wrong_count = summary["counts"]["wrongly_rejected"]

    if total == 0:
        return "There are no applicants to screen."

    lines = []

    # Count which penalties were behind the wrongful rejections.
    zip_harmed = 0
    gap_harmed = 0
    for result in results:
        if result["wrongly_filtered"]:
            if result["zip_hit"]:
                zip_harmed += 1
            if result["gap_hit"]:
                gap_harmed += 1

    # --- Bottom line: the main finding in plain words ---
    lines.append("BOTTOM LINE")
    lines.append(f"- The algorithm passed {summary['passed']} of {total} applicants. "
                 f"A skills-only screen (skills score of {rules['passing_score']} or higher) "
                 f"would have passed {summary['qualified']} of {total}.")
    if wrong_count > 0:
        lines.append(f"- The {wrong_count} applicant(s) in between were rejected only because "
                     "of penalties, not because of what they can do.")
        lines.append(f"- Penalties behind those rejections: flagged ZIP code "
                     f"({zip_harmed} applicant(s)), long employment gap ({gap_harmed} applicant(s)).")
    else:
        lines.append("- Nobody was rejected because of a penalty in this run.")
    lines.append("")

    # --- The bad side: where the algorithm got it wrong ---
    if wrong_count > 0:
        lines.append("WHERE THE ALGORITHM GOT IT WRONG (BIAS)")
        lines.append(f"- Qualified applicants rejected only because of penalties: "
                     f"{wrong_count} of {summary['qualified']} ({summary['percent_lost']}%).")
        for result in results:
            if result["wrongly_filtered"]:
                applicant = result["applicant"]
                lines.append(f"  * {applicant['name']}: {describe_math(result)}. "
                             f"{describe_decision(result)}")
                if applicant["note"] != "":
                    lines.append(f"    Background: {applicant['note']}")
        lines.append("")

    # --- The good side: where the algorithm got it right ---
    lines.append("WHERE THE ALGORITHM GOT IT RIGHT")
    lines.append("(Right means it made the same decision a skills-only screen would.)")
    right_count = 0
    for result in results:
        applicant = result["applicant"]
        if result["outcome"] == "fair_pass":
            lines.append(f"  * {applicant['name']}: {describe_math(result)}. "
                         f"{describe_decision(result)}")
            right_count += 1
        elif result["outcome"] == "passed_despite_penalty":
            lines.append(f"  * {applicant['name']}: {describe_math(result)}. "
                         f"{describe_decision(result)} The penalty lowered the score "
                         "but did not change the outcome.")
            right_count += 1
        elif result["outcome"] == "fair_rejection":
            lines.append(f"  * {applicant['name']}: {describe_math(result)}. "
                         f"{describe_decision(result)} This rejection is not caused by bias.")
            right_count += 1
    if right_count == 0:
        lines.append("  * None in this run.")
    lines.append("")

    # --- Pass rates ---
    lines.append("PASS RATES")
    if summary["penalized_total"] > 0:
        lines.append(f"- With at least one penalty: {summary['penalized_passed']} of "
                     f"{summary['penalized_total']} passed ({summary['penalized_rate']}%).")
    else:
        lines.append("- No applicant lost points in this run.")
    if summary["clean_total"] > 0:
        lines.append(f"- With no penalties: {summary['clean_passed']} of "
                     f"{summary['clean_total']} passed ({summary['clean_rate']}%).")
    else:
        lines.append("- Every applicant lost points in this run.")

    ratio = summary["impact_ratio"]
    if ratio is not None:
        if ratio < 0.8:
            verdict = ("That is below 0.80, which the U.S. 'four-fifths' rule of thumb "
                       "treats as a warning sign of adverse impact.")
        else:
            verdict = "That is 0.80 or higher, so the four-fifths rule of thumb would not flag it."
        lines.append(f"- Ratio of the two pass rates: {ratio}. {verdict}")
        lines.append("  (The four-fifths rule was written for race, sex and ethnic groups. "
                     "Here it is only an illustration.)")
    elif summary["penalized_total"] > 0 and summary["clean_total"] > 0:
        lines.append("- No applicant without a penalty passed, so no ratio can be calculated.")
    else:
        lines.append("- Both groups need at least one applicant to compare pass rates.")
    if total < 30:
        lines.append(f"- Small sample: with only {total} applicant(s), one person changes the "
                     "percentages a lot. Treat these numbers as an illustration, not proof.")
    lines.append("")

    # --- Why it happens (only the causes that actually hurt someone) ---
    if zip_harmed > 0 or gap_harmed > 0:
        lines.append("WHY THIS HAPPENS")
        if gap_harmed > 0:
            lines.append(bias_explanations["Medical gaps"])
            lines.append("")
            lines.append(bias_explanations["Neurodivergent applicants"])
            lines.append("")
        if zip_harmed > 0:
            lines.append(bias_explanations["Low-income applicants"])
            lines.append("")
    else:
        lines.append("TRY THIS")
        lines.append("Raise a penalty, lower the gap limit, or flag another ZIP code, "
                     "then run the audit again to see who starts getting hurt.")
        lines.append("")

    lines.append(simulation_note)
    return "\n".join(lines)


def save_report(path, results, summary):
    """Save the audit as a JSON file and return the path it was saved to."""
    report = {
        "rules_used": algorithm_rules,
        "flagged_zip_codes": flagged_zip_codes,
        "summary": summary,
        "applicants": [],
    }

    for result in results:
        applicant = result["applicant"]
        if result["robot_passed"]:
            outcome = "PASSED"
        else:
            outcome = "FILTERED OUT"

        report["applicants"].append({
            "name": applicant["name"],
            "zip": applicant["zip"],
            "gap_months": applicant["gap_months"],
            "skills_score": applicant["base_score"],
            "final_score": result["final_score"],
            "outcome": outcome,
            "audit_result": outcome_labels[result["outcome"]],
            "points_lost": result["points_lost"],
            "qualified_but_filtered": result["wrongly_filtered"],
            "penalties": result["reasons"],
        })

    with open(path, "w") as file:
        json.dump(report, file, indent=4)

    return path
