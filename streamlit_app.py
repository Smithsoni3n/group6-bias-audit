import json
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
import bias_rules

st.set_page_config(
    page_title="Algorithmic Hiring Bias Simulator & Audit Tool",
    layout="wide",
)

SCALE_RANGES = {
    "max_gap_months": (0, 24),
    "zip_penalty": (0, 50),
    "gap_penalty": (0, 50),
    "passing_score": (0, 100),
}

WELCOME_TEXT = (
    "Welcome! Move the sliders on the left to change the robot's rules, "
    "then click Run Audit. The table above shows who passes, and this "
    "panel explains who was unfairly filtered out and why.\n\n"
    "Created by Jasmine W., Crystal R., Leilani G., and Frankie A.P.\n\n"
    + bias_rules.simulation_note
)

if "applicants" not in st.session_state:
    st.session_state.applicants = []
if "flagged_zips" not in st.session_state:
    st.session_state.flagged_zips = []
if "results" not in st.session_state:
    st.session_state.results = []
if "summary" not in st.session_state:
    st.session_state.summary = {}
if "status_msg" not in st.session_state:
    st.session_state.status_msg = "No applicants yet. Add an applicant in the form on the left."

for rule_key, default_val in bias_rules.default_rules.items():
    if rule_key not in st.session_state:
        st.session_state[rule_key] = default_val


def sync_to_bias_rules():
    for rule_key in bias_rules.default_rules:
        bias_rules.algorithm_rules[rule_key] = st.session_state[rule_key]
    bias_rules.flagged_zip_codes.clear()
    bias_rules.flagged_zip_codes.extend(st.session_state.flagged_zips)


def clear_results():
    st.session_state.results = []
    st.session_state.summary = {}


def build_diagnostics(summary, results):
    lines = [
        "AUDIT SUMMARY",
        f"Total applicants: {summary.get('total', 0)}",
        f"Passed the robot: {summary.get('passed', 0)}",
        f"Filtered out by the robot: {summary.get('filtered', 0)}",
        f"Qualified on skills alone: {summary.get('qualified', 0)}",
        f"Qualified but wrongly filtered: {len(summary.get('wrongly_filtered', ()))}",
        f"{summary.get('percent_lost', 0.0)}% of qualified applicants were lost to proxy penalties.",
        "",
    ]

    if len(summary.get("wrongly_filtered", ())) > 0:
        lines.append("WHO WAS WRONGLY FILTERED, AND WHY")
        for result in results:
            if result.get("wrongly_filtered"):
                app = result.get("applicant", {})
                lines.append(
                    f"- {app.get('name', '')} (skills {app.get('base_score', 0)}, "
                    f"robot score {result.get('final_score', 0)})"
                )
                for reason in result.get("reasons", ()):
                    lines.append(f"    Penalty: {reason}")
                if app.get("note", "") != "":
                    lines.append(f"    Background: {app.get('note', '')}")
        lines.append("")

    lines.append("WHY THIS MATTERS")
    for topic, explanation in bias_rules.bias_explanations.items():
        lines.append(f"{topic}: {explanation}")
        lines.append("")
    lines.append(bias_rules.simulation_note)
    return "\n".join(lines)


st.title("Algorithmic Hiring Bias Simulator & Audit Tool")
st.caption("Change the robot's rules, then see who it filters out.")

btn_col1, btn_col2, btn_col3, _ = st.columns((1.1, 1, 1.3, 2.6))

with btn_col1:
    if st.button("Run Audit", type="primary", use_container_width=True):
        if len(st.session_state.applicants) == 0:
            st.toast("No applicants yet — add at least one applicant first.")
        else:
            sync_to_bias_rules()
            results, summary = bias_rules.run_audit(st.session_state.applicants)
            st.session_state.results = results
            st.session_state.summary = summary
            st.session_state.status_msg = (
                f"Audit finished: {summary.get('passed', 0)} passed, "
                f"{summary.get('filtered', 0)} filtered out."
            )

with btn_col2:
    if st.button("Reset Rules", use_container_width=True):
        bias_rules.reset_rules()
        for rule_key, default_val in bias_rules.default_rules.items():
            st.session_state[rule_key] = default_val
        st.session_state.flagged_zips = []
        st.session_state.applicants = []
        clear_results()
        st.session_state.status_msg = "Rules reset and all applicants and results cleared."
        st.rerun()

with btn_col3:
    if len(st.session_state.results) > 0:
        sync_to_bias_rules()
        report_data = {
            "rules_used": dict(bias_rules.algorithm_rules),
            "flagged_zip_codes": list(bias_rules.flagged_zip_codes),
            "summary": st.session_state.summary,
            "applicants": [
                {
                    "name": res.get("applicant", {}).get("name", ""),
                    "zip": res.get("applicant", {}).get("zip", ""),
                    "gap_months": res.get("applicant", {}).get("gap_months", 0),
                    "skills_score": res.get("applicant", {}).get("base_score", 0),
                    "final_score": res.get("final_score", 0),
                    "outcome": "PASSED" if res.get("robot_passed") else "FILTERED OUT",
                    "qualified_but_filtered": res.get("wrongly_filtered", False),
                    "penalties": res.get("reasons", []),
                }
                for res in st.session_state.results
            ],
        }
        st.download_button(
            "Export Report (JSON)",
            data=json.dumps(report_data, indent=4),
            file_name="audit_report.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        if st.button("Export Report (JSON)", use_container_width=True):
            st.toast("Click Run Audit first, then export the report.")

st.divider()

left, right = st.columns((1, 2.1), gap="large")

with left:
    with st.container(border=True):
        st.subheader("1. Algorithm Controls")
        for rule_key, label_text in bias_rules.rule_labels.items():
            low, high = SCALE_RANGES.get(rule_key, (0, 100))
            st.slider(label_text, min_value=low, max_value=high, key=rule_key)

    with st.container(border=True):
        st.subheader("2. Flagged ZIP Codes")
        if st.session_state.flagged_zips:
            st.write("Flagged list:", ", ".join(st.session_state.flagged_zips))
        else:
            st.caption("No ZIP codes flagged yet.")

        z_col1, z_col2 = st.columns((2, 1))
        with z_col1:
            zip_input = st.text_input("ZIP code", placeholder="5-digit ZIP", label_visibility="collapsed")
        with z_col2:
            if st.button("Add ZIP", use_container_width=True):
                clean_zip = zip_input.strip()
                if not clean_zip.isdigit() or len(clean_zip) != 5:
                    st.error("A ZIP code must be exactly 5 digits.")
                elif clean_zip in st.session_state.flagged_zips:
                    st.info(f"{clean_zip} is already on the list.")
                else:
                    st.session_state.flagged_zips.append(clean_zip)
                    clear_results()
                    st.session_state.status_msg = f"Flagged ZIP code {clean_zip}. Click Run Audit to see the effect."
                    st.rerun()

        if st.session_state.flagged_zips:
            selected_zip = st.selectbox("Pick a ZIP code to remove", st.session_state.flagged_zips, label_visibility="collapsed")
            if st.button("Remove selected ZIP", use_container_width=True):
                st.session_state.flagged_zips.remove(selected_zip)
                clear_results()
                st.session_state.status_msg = f"Un-flagged ZIP code {selected_zip}. Click Run Audit to see the effect."
                st.rerun()

    with st.container(border=True):
        st.subheader("3. Test Your Own Applicant")
        with st.form("applicant_form", clear_on_submit=True):
            name_val = st.text_input("Name")
            zip_val = st.text_input("ZIP code")
            gap_val = st.text_input("Gap (months)")
            score_val = st.text_input("Skills score (0-100)")
            if st.form_submit_button("Add Applicant", use_container_width=True):
                applicant, error = bias_rules.make_applicant(
                    name_val, zip_val, gap_val, score_val, "Applicant added by the user"
                )
                if error != "":
                    st.error(error)
                else:
                    st.session_state.applicants.append(applicant)
                    clear_results()
                    st.session_state.status_msg = f"Added {applicant.get('name', '')}. Click Run Audit to screen everyone."
                    st.rerun()

with right:
    st.subheader("Screening Results")
    table_rows = []

    if len(st.session_state.results) == 0:
        for app in st.session_state.applicants:
            table_rows.append(
                dict(
                    Applicant=app.get("name", ""),
                    ZIP=app.get("zip", ""),
                    Gap_mo=app.get("gap_months", 0),
                    Skills=app.get("base_score", 0),
                    Final="-",
                    Result="Not screened yet",
                    Audit_flag="",
                )
            )
    else:
        for res in st.session_state.results:
            app = res.get("applicant", {})
            outcome = "PASSED" if res.get("robot_passed") else "FILTERED OUT"
            if res.get("wrongly_filtered"):
                audit_flag = "Qualified but rejected"
            elif not res.get("skills_passed"):
                audit_flag = "Below passing on skills"
            else:
                audit_flag = ""
            table_rows.append(
                dict(
                    Applicant=app.get("name", ""),
                    ZIP=app.get("zip", ""),
                    Gap_mo=app.get("gap_months", 0),
