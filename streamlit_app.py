# CS110 Group 6 - Algorithmic Hiring Bias Simulator & Audit Tool
# File: streamlit_app.py  (web preview, built with Streamlit)
# 
# Purpose: The same simulator as the desktop app (main.py), but it runs in a web
#          browser. All scoring math and explanation text live in bias_rules.py,
#          so both versions always give the same answers.
#
# Sources and assistance (see README Citations):
#   - Streamlit documentation on Session State and Community Cloud: Streamlit (n.d.-a, n.d.-b).
# Contributors: Crystal R, Leilani G, Jasmine W & Frankie A.P.


import json
import sys
from pathlib import Path
import streamlit as st

# Make sure bias_rules.py in this same folder can always be imported.
sys.path.insert(0, str(Path(__file__).parent))
import bias_rules

st.set_page_config(page_title="Algorithmic Hiring Bias Simulator & Audit Tool", layout="wide")

# The lowest and highest value each slider can have.
SCALE_RANGES = {"max_gap_months": (0, 24), "zip_penalty": (0, 50), "gap_penalty": (0, 50), "passing_score": (0, 100)}

WELCOME_TEXT = (
    "Welcome! Move the sliders on the left to change the algorithm's rules, then click Run Audit. "
    "The table above shows who passes, and this panel explains who was unfairly filtered out and why. "
    "For a quick demo, click Load Sample Applicants.\n\n"
    "Created by Jasmine W., Crystal R., Leilani G., and Frankie A.P.\n\n" + bias_rules.simulation_note
)

# ---------------------------------------------------------------------------
# SESSION STATE: each visitor's applicants, flagged ZIPs, and results are kept
# separate in their own browser session.
# ---------------------------------------------------------------------------
for key, value in [("applicants", []), ("flagged_zips", []), ("results", []), ("summary", {}),
                   ("status_msg", "No applicants yet. Add an applicant in the form on the left, or click Load Sample Applicants.")]:
    if key not in st.session_state:
        st.session_state[key] = value

for rule_key, default_val in bias_rules.default_rules.items():
    if rule_key not in st.session_state:
        st.session_state[rule_key] = default_val


def sync_rules():
    """Copy this visitor's slider values and flagged ZIPs into bias_rules."""
    for rule_key in bias_rules.default_rules:
        bias_rules.algorithm_rules[rule_key] = st.session_state[rule_key]
    bias_rules.flagged_zip_codes.clear()
    bias_rules.flagged_zip_codes.extend(st.session_state.flagged_zips)


def clear_results():
    """Forget old audit results (used whenever applicants or rules change)."""
    st.session_state.results = []
    st.session_state.summary = {}


# ---------------------------------------------------------------------------
# TITLE AND BUTTON BAR
# ---------------------------------------------------------------------------
st.title("Algorithmic Hiring Bias Simulator & Audit Tool")
st.caption("Change the algorithm's rules, then see who it filters out.")

c1, c2, c3, c4, _ = st.columns((1.1, 1, 1.3, 1.5, 1.3))

with c1:
    if st.button("Run Audit", type="primary", use_container_width=True):
        if not st.session_state.applicants:
            st.toast("No applicants yet. Add one or click Load Sample Applicants.")
        else:
            sync_rules()
            results, summary = bias_rules.run_audit(st.session_state.applicants)
            st.session_state.results, st.session_state.summary = results, summary
            st.session_state.status_msg = f"Audit finished: {summary['passed']} passed, {summary['filtered']} filtered out."

with c2:
    if st.button("Reset Rules", use_container_width=True):
        bias_rules.reset_rules()
        for rule_key, default_val in bias_rules.default_rules.items():
            st.session_state[rule_key] = default_val
        st.session_state.flagged_zips = []
        st.session_state.applicants = []
        clear_results()
        st.session_state.status_msg = "Reset. Rules are back to the start and all applicants were cleared."
        st.rerun()

with c3:
    if st.session_state.results:
        sync_rules()
        report = {
            "rules_used": dict(bias_rules.algorithm_rules),
            "flagged_zip_codes": list(bias_rules.flagged_zip_codes),
            "summary": st.session_state.summary,
            "applicants": [],
        }
        for result in st.session_state.results:
            applicant = result["applicant"]
            report["applicants"].append({
                "name": applicant["name"],
                "zip": applicant["zip"],
                "gap_months": applicant["gap_months"],
                "skills_score": applicant["base_score"],
                "final_score": result["final_score"],
                "audit_result": bias_rules.outcome_labels[result["outcome"]],
                "points_lost": result["points_lost"],
                "outcome": "PASSED" if result["robot_passed"] else "FILTERED OUT",
                "qualified_but_filtered": result["wrongly_filtered"],
                "penalties": result["reasons"],
            })
        st.download_button("Export Report (JSON)", data=json.dumps(report, indent=4),
                           file_name="audit_report.json", mime="application/json",
                           use_container_width=True)
    elif st.button("Export Report (JSON)", use_container_width=True):
        st.toast("Click Run Audit first, then export the report.")

with c4:
    if st.button("Load Sample Applicants", use_container_width=True):
        sample, problems = bias_rules.load_applicants(bias_rules.get_data_file_path("sample_applicants.txt"))
        if not sample:
            st.error("Could not load the sample applicants. " + " ".join(problems))
        else:
            st.session_state.applicants = sample
            st.session_state.flagged_zips = list(bias_rules.default_zip_codes)
            clear_results()
            st.session_state.status_msg = (f"Loaded {len(sample)} sample applicants and flagged "
                                           f"{len(st.session_state.flagged_zips)} ZIP codes. Click Run Audit.")
            st.rerun()

st.divider()
left, right = st.columns((1, 2.1), gap="large")

# ---------------------------------------------------------------------------
# LEFT SIDE: controls
# ---------------------------------------------------------------------------
with left:
    with st.container(border=True):
        st.subheader("1. Algorithm Controls")
        for rule_key, label in bias_rules.rule_labels.items():
            low, high = SCALE_RANGES.get(rule_key, (0, 100))
            st.slider(label, min_value=low, max_value=high, key=rule_key)

    with st.container(border=True):
        st.subheader("2. Flagged ZIP Codes")
        if st.session_state.flagged_zips:
            st.write("Flagged list: " + ", ".join(st.session_state.flagged_zips))
        else:
            st.write("No ZIP codes flagged yet.")
        z1, z2 = st.columns((2, 1))
        zip_text = z1.text_input("ZIP code", placeholder="5-digit ZIP", label_visibility="collapsed")
        if z2.button("Add ZIP", use_container_width=True):
            new_zip = zip_text.strip()
            if not new_zip.isdigit() or len(new_zip) != 5:
                st.error("A ZIP code must be exactly 5 digits.")
            elif new_zip in st.session_state.flagged_zips:
                st.info(f"{new_zip} is already on the list.")
            else:
                st.session_state.flagged_zips.append(new_zip)
                clear_results()
                st.session_state.status_msg = f"Flagged ZIP code {new_zip}. Click Run Audit to see the effect."
                st.rerun()
        if st.session_state.flagged_zips:
            pick = st.selectbox("Remove ZIP", st.session_state.flagged_zips, label_visibility="collapsed")
            if st.button("Remove selected ZIP", use_container_width=True):
                st.session_state.flagged_zips.remove(pick)
                clear_results()
                st.session_state.status_msg = f"Un-flagged ZIP code {pick}. Click Run Audit to see the effect."
                st.rerun()

    with st.container(border=True):
        st.subheader("3. Test Your Own Applicant")
        with st.form("app_form", clear_on_submit=True):
            name_text = st.text_input("Name")
            zip_field = st.text_input("ZIP code")
            gap_text = st.text_input("Gap (months)")
            score_text = st.text_input("Skills score (0-100)")
            if st.form_submit_button("Add Applicant", use_container_width=True):
                applicant, error = bias_rules.make_applicant(name_text, zip_field, gap_text, score_text, "")
                if error:
                    st.error(error)
                else:
                    st.session_state.applicants.append(applicant)
                    clear_results()
                    st.session_state.status_msg = f"Added {applicant['name']}. Click Run Audit to screen everyone."
                    st.rerun()

# ---------------------------------------------------------------------------
# RIGHT SIDE: results table and explanation panel
# ---------------------------------------------------------------------------
with right:
    st.subheader("Screening Results")
    if not st.session_state.results:
        rows = [{"Applicant": a["name"], "ZIP": a["zip"], "Gap (mo)": a["gap_months"], "Skills": a["base_score"],
                 "Final": "-", "Result": "Not screened yet", "Audit flag": ""}
                for a in st.session_state.applicants]
    else:
        rows = [{"Applicant": r["applicant"]["name"], "ZIP": r["applicant"]["zip"],
                 "Gap (mo)": r["applicant"]["gap_months"], "Skills": r["applicant"]["base_score"],
                 "Final": r["final_score"], "Result": "PASSED" if r["robot_passed"] else "FILTERED OUT",
                 "Audit flag": bias_rules.outcome_labels[r["outcome"]]}
                for r in st.session_state.results]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("Bias Diagnostics & Explanation")
    with st.container(border=True):
        if st.session_state.results:
            st.text(bias_rules.build_diagnostics_text(st.session_state.summary, st.session_state.results))
        else:
            st.text(WELCOME_TEXT)

st.caption("Status: " + st.session_state.status_msg)
