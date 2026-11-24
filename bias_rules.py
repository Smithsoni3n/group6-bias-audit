# CS110 Group 6 - Algorithmic Hiring Bias Simulator & Audit Tool
# File: bias_rules.py
# Contributor: Crystal R.
#
# Purpose: This is the "brain" of the app. It stores the hidden rules a biased
#          resume-screening robot might use, loads the applicants from
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
# THE ROBOT'S RULES
# ---------------------------------------------------------------------------

# ZIP codes the biased algorithm unfairly penalizes.
# NOTE: This list is a hypothetical choice made for the simulation. It shows how
# a ZIP code can act as a "proxy" for income. It is NOT a claim about the people
# who live there.
flagged_zip_codes = []

# The numbers the screener uses. The sliders in main.py change these values.
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

# ---------------------------------------------------------------------------
# EXPLANATION PANEL TEXT (Jasmine W. can edit these sentences)
# ---------------------------------------------------------------------------
simulation_note = (
    "About this simulation: the applicants are made-up sample profiles, and the "
    "flagged ZIP codes are a hypothetical rule. Real screening software is "
    "private, so no one outside the company can see its actual rules. That "
    "secrecy is part of the problem."
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
    """Put every algorithm rule back to the starting values."""
    for rule in default_rules:
        algorithm_rules[rule] = default_rules[rule]


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


def score_applicant(applicant):
    """Apply the robot's rules to one applicant and return the results."""
    rules = algorithm_rules
    final_score = applicant["base_score"]
    reasons = []

    # Rule 1: ZIP code proxy
    if applicant["zip"] in flagged_zip_codes:
        final_score = final_score - rules["zip_penalty"]
        reasons.append(
            "ZIP code " + applicant["zip"] + " is flagged (-"
            + str(rules["zip_penalty"]) + " points)"
        )

    # Rule 2: employment gap
    if applicant["gap_months"] > rules["max_gap_months"]:
        final_score = final_score - rules["gap_penalty"]
        reasons.append(
            str(applicant["gap_months"]) + "-month gap is over the "
            + str(rules["max_gap_months"]) + "-month limit (-"
            + str(rules["gap_penalty"]) + " points)"
        )

    robot_passed = final_score >= rules["passing_score"]
    # Would this person have passed if only their skills were judged?
    skills_passed = applicant["base_score"] >= rules["passing_score"]

    result = {
        "applicant": applicant,
        "final_score": final_score,
        "reasons": reasons,
        "robot_passed": robot_passed,
        "skills_passed": skills_passed,
        # Qualified on skills, but the robot rejected them anyway
        "wrongly_filtered": skills_passed and not robot_passed,
    }
    return result


def run_audit(applicants):
    """Screen every applicant. Returns (list of results, summary dictionary)."""
    results = []
    passed = 0
    qualified = 0
    wrongly_filtered = []

    for applicant in applicants:
        result = score_applicant(applicant)
        results.append(result)

        if result["robot_passed"]:
            passed += 1
        if result["skills_passed"]:
            qualified += 1
        if result["wrongly_filtered"]:
            wrongly_filtered.append(applicant["name"])

    percent_lost = 0.0
    if qualified > 0:
        percent_lost = len(wrongly_filtered) / qualified * 100

    summary = {
        "total": len(applicants),
        "passed": passed,
        "filtered": len(applicants) - passed,
        "qualified": qualified,
        "wrongly_filtered": wrongly_filtered,
        "percent_lost": round(percent_lost, 1),
    }
    return results, summary


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
            "qualified_but_filtered": result["wrongly_filtered"],
            "penalties": result["reasons"],
        })

    with open(path, "w") as file:
        json.dump(report, file, indent=4)

    return path
