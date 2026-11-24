# CS110 Group 6 - Algorithmic Hiring Bias Simulator & Audit Tool
# File: main.py  (RUN THIS FILE TO START THE APP)
# Contributors: Crystal R, Leilani G, Jasmine W & Frankie A.P.
#
# Purpose: Builds the app screen with tkinter (Python's built-in GUI library).
#          The app starts empty. Load Sample Applicants reads sample_applicants.txt.
#          The user can move sliders to change the algorithm's rules, flag ZIP codes,
#          add their own test applicant, run the audit, and export a JSON report.
#          All scoring math lives in bias_rules.py so this file only handles
#          what the user sees and clicks.
#
# Concepts used: GUI (tkinter), functions, dictionaries, lists, loops,
#                if/elif/else, text files, and JSON.
#
# Sources and assistance (see README Citations):
#   - tkinter (window, sliders, buttons), tkinter.ttk (results table), and
#     tkinter.messagebox (pop-up messages): Python Software Foundation
#     (n.d.-a, n.d.-b, n.d.-c).


import tkinter as tk
from tkinter import ttk, messagebox

import bias_rules

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
# Large, plain fonts and clear text labels make the app easier to read.
# Color is never the only signal: every result also says PASSED or FILTERED OUT.
FONT = ("Arial", 11)
BOLD_FONT = ("Arial", 11, "bold")
HEADING_FONT = ("Arial", 12, "bold")
TITLE_FONT = ("Arial", 18, "bold")

# The lowest and highest value each slider can have.
scale_ranges = {
    "max_gap_months": (0, 24),
    "zip_penalty": (0, 50),
    "gap_penalty": (0, 50),
    "passing_score": (0, 100),
}

# Data the program remembers while it is running.
applicants = []                                # list of applicant dictionaries
app_state = {"results": [], "summary": {}}     # newest audit results
scales = {}                                    # the four slider widgets
data_path = bias_rules.get_data_file_path("sample_applicants.txt")


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS (they update what is shown on the screen)
# ---------------------------------------------------------------------------
def set_status(message):
    """Show a short message in the status bar at the bottom of the window."""
    status_label.config(text=message)


def show_text(text_box, content):
    """Replace everything in a read-only text box."""
    text_box.config(state="normal")
    text_box.delete("1.0", tk.END)
    text_box.insert(tk.END, content)
    text_box.config(state="disabled")


def refresh_zip_list():
    """Redraw the list of flagged ZIP codes."""
    zip_listbox.delete(0, tk.END)
    for zip_code in bias_rules.flagged_zip_codes:
        zip_listbox.insert(tk.END, zip_code)


def set_sliders_from_rules():
    """Move each slider to match the current rule values."""
    for rule in scales:
        scales[rule].set(bias_rules.algorithm_rules[rule])


def read_sliders_into_rules():
    """Copy each slider's value into the rules the algorithm will use."""
    for rule in scales:
        bias_rules.algorithm_rules[rule] = scales[rule].get()


def fill_table():
    """Redraw the results table (applicants before the audit, results after)."""
    for row in results_table.get_children():
        results_table.delete(row)

    results = app_state["results"]

    if len(results) == 0:
        # Audit has not been run yet, so just list who was loaded.
        for applicant in applicants:
            results_table.insert("", tk.END, values=(
                applicant["name"], applicant["zip"], applicant["gap_months"],
                applicant["base_score"], "-", "Not screened yet", ""))
    else:
        for result in results:
            applicant = result["applicant"]

            if result["robot_passed"]:
                outcome = "PASSED"
                tag = "passed"
            else:
                outcome = "FILTERED OUT"
                tag = "filtered"

            audit_flag = bias_rules.outcome_labels[result["outcome"]]

            results_table.insert("", tk.END, tags=(tag,), values=(
                applicant["name"], applicant["zip"], applicant["gap_months"],
                applicant["base_score"], result["final_score"], outcome,
                audit_flag))


def build_diagnostics(summary, results):
    """Get the audit explanation text. The wording lives in bias_rules.py so the
    desktop app and the web preview always say the same thing."""
    return bias_rules.build_diagnostics_text(summary, results)


def clear_results():
    """Forget old audit results (used when applicants or rules are changed)."""
    app_state["results"] = []
    app_state["summary"] = {}


# ---------------------------------------------------------------------------
# BUTTON FUNCTIONS (these run when the user clicks)
# ---------------------------------------------------------------------------
def run_audit_clicked():
    """Screen all applicants using the current slider settings."""
    if len(applicants) == 0:
        messagebox.showinfo("No applicants", "Add at least one applicant first.")
        return

    read_sliders_into_rules()
    results, summary = bias_rules.run_audit(applicants)
    app_state["results"] = results
    app_state["summary"] = summary

    fill_table()
    show_text(diagnostics_box, build_diagnostics(summary, results))
    set_status("Audit finished: " + str(summary["passed"]) + " passed, "
               + str(summary["filtered"]) + " filtered out.")


def add_zip_clicked():
    """Add a ZIP code to the flagged list."""
    zip_code = zip_entry.get().strip()

    if not zip_code.isdigit() or len(zip_code) != 5:
        messagebox.showerror("Check the ZIP code", "A ZIP code must be exactly 5 digits.")
    elif zip_code in bias_rules.flagged_zip_codes:
        messagebox.showinfo("Already flagged", zip_code + " is already on the list.")
    else:
        bias_rules.flagged_zip_codes.append(zip_code)
        refresh_zip_list()
        zip_entry.delete(0, tk.END)
        clear_results()
        fill_table()
        set_status("Flagged ZIP code " + zip_code + ". Click Run Audit to see the effect.")


def remove_zip_clicked():
    """Remove the selected ZIP code from the flagged list."""
    selection = zip_listbox.curselection()

    if len(selection) == 0:
        messagebox.showinfo("Pick a ZIP code", "Click a ZIP code in the list first.")
    else:
        zip_code = zip_listbox.get(selection[0])
        bias_rules.flagged_zip_codes.remove(zip_code)
        refresh_zip_list()
        clear_results()
        fill_table()
        set_status("Un-flagged ZIP code " + zip_code + ". Click Run Audit to see the effect.")


def add_applicant_clicked():
    """Add the applicant typed into the form (checks the entries first)."""
    applicant, error = bias_rules.make_applicant(
        name_entry.get(), applicant_zip_entry.get(), gap_entry.get(),
        score_entry.get(), "")

    if error != "":
        messagebox.showerror("Check the form", error)
        return

    applicants.append(applicant)
    for entry in (name_entry, applicant_zip_entry, gap_entry, score_entry):
        entry.delete(0, tk.END)

    clear_results()
    fill_table()
    set_status("Added " + applicant["name"] + ". Click Run Audit to screen everyone.")


def add_applicant_enter(event):
    """Lets the user press the Enter key in a text box instead of clicking Add."""
    add_applicant_clicked()


def remove_applicant_clicked():
    """Remove the applicant row that is selected in the results table."""
    selection = results_table.selection()

    if len(selection) == 0:
        messagebox.showinfo("Pick an applicant", "Click a row in the table first.")
        return

    # The table rows are in the same order as the applicants list.
    position = results_table.index(selection[0])
    removed = applicants.pop(position)

    clear_results()
    fill_table()
    set_status("Removed " + removed["name"] + ".")


def clear_all_clicked():
    """Empty the applicant list so the user can type in their own."""
    if len(applicants) == 0:
        return

    if messagebox.askyesno("Clear all applicants",
                           "Remove everyone from the table? You can bring the "
                           "samples back with 'Load Sample Applicants'."):
        applicants.clear()
        clear_results()
        fill_table()
        show_text(diagnostics_box, welcome_text)
        set_status("Table cleared. Type your own applicants in section 3.")
        name_entry.focus_set()


def load_sample_clicked():
    """Load the sample applicants from sample_applicants.txt and flag the sample
    ZIP codes, so the demo works with one click."""
    sample_applicants, sample_problems = bias_rules.load_applicants(data_path)

    if len(sample_applicants) == 0:
        messagebox.showwarning("Could not load samples",
                               "\n".join(sample_problems) or "No applicants found in the file.")
        return

    applicants.clear()
    applicants.extend(sample_applicants)

    bias_rules.flagged_zip_codes.clear()
    bias_rules.flagged_zip_codes.extend(bias_rules.default_zip_codes)
    refresh_zip_list()

    clear_results()
    fill_table()
    show_text(diagnostics_box, welcome_text)
    set_status("Loaded " + str(len(applicants)) + " sample applicants and flagged "
               + str(len(bias_rules.flagged_zip_codes)) + " ZIP codes. Click Run Audit.")

    if len(sample_problems) > 0:
        messagebox.showwarning("Problems loading applicants", "\n".join(sample_problems))


def reset_clicked():
    """Return to the empty starting screen: starting rules, no ZIP codes, no applicants."""
    bias_rules.reset_rules()
    bias_rules.flagged_zip_codes.clear()
    applicants.clear()
    set_sliders_from_rules()
    refresh_zip_list()
    clear_results()
    fill_table()
    show_text(diagnostics_box, welcome_text)
    set_status("Reset. Rules are back to the start and all applicants were cleared.")


def export_clicked():
    """Save the newest audit as a JSON file."""
    if len(app_state["results"]) == 0:
        messagebox.showinfo("Run the audit first", "Click Run Audit, then export the report.")
        return

    path = bias_rules.get_data_file_path("audit_report.json")
    bias_rules.save_report(path, app_state["results"], app_state["summary"])
    messagebox.showinfo("Report saved", "Saved the audit report to:\n" + path)
    set_status("Report exported to audit_report.json")


# ---------------------------------------------------------------------------
# BUILD THE SCREEN
# ---------------------------------------------------------------------------
root = tk.Tk()
root.title("Algorithmic Hiring Bias Simulator & Audit Tool")
root.geometry("1200x800")
root.minsize(1050, 700)

style = ttk.Style()
style.configure("Treeview", font=FONT, rowheight=28)
style.configure("Treeview.Heading", font=BOLD_FONT)

# Title bar
tk.Label(root, text="Algorithmic Hiring Bias Simulator & Audit Tool",
         font=TITLE_FONT).grid(row=0, column=0, columnspan=2, pady=(10, 0))
tk.Label(root, text="Change the algorithm's rules, then see who it filters out.",
         font=FONT).grid(row=1, column=0, columnspan=2, pady=(0, 8))

# Button bar: the main buttons stay at the top so they are always visible
button_bar = tk.Frame(root)
button_bar.grid(row=2, column=0, columnspan=2, pady=(0, 6))
tk.Button(button_bar, text="Run Audit", font=BOLD_FONT, command=run_audit_clicked,
          bg="#1f4e79", fg="white", padx=16).pack(side="left", padx=6)
tk.Button(button_bar, text="Reset Rules", font=FONT, command=reset_clicked,
          padx=10).pack(side="left", padx=6)
tk.Button(button_bar, text="Export Report (JSON)", font=FONT, command=export_clicked,
          padx=10).pack(side="left", padx=6)
tk.Button(button_bar, text="Load Sample Applicants", font=FONT, command=load_sample_clicked,
          padx=10).pack(side="left", padx=6)

# Left column: controls
left = tk.Frame(root)
left.grid(row=3, column=0, sticky="n", padx=10)

# Right column: results table and explanation panel
right = tk.Frame(root)
right.grid(row=3, column=1, sticky="nsew", padx=(0, 10))
root.columnconfigure(1, weight=1)
root.rowconfigure(3, weight=1)

# --- 1. Algorithm controls (sliders) ---
controls_box = tk.LabelFrame(left, text=" 1. Algorithm Controls ", font=HEADING_FONT, padx=8, pady=4)
controls_box.pack(fill="x", pady=(0, 6))

for rule in bias_rules.algorithm_rules:
    low, high = scale_ranges[rule]
    tk.Label(controls_box, text=bias_rules.rule_labels[rule],
             font=FONT, anchor="w").pack(fill="x")
    slider = tk.Scale(controls_box, from_=low, to=high, orient="horizontal",
                      font=FONT, length=320, width=14)
    slider.pack(fill="x")
    scales[rule] = slider
set_sliders_from_rules()

# --- 2. Flagged ZIP codes ---
zip_box = tk.LabelFrame(left, text=" 2. Flagged ZIP Codes ", font=HEADING_FONT, padx=8, pady=4)
zip_box.pack(fill="x", pady=6)

zip_listbox = tk.Listbox(zip_box, height=3, font=FONT, exportselection=False)
zip_listbox.grid(row=0, column=0, columnspan=3, sticky="ew")
tk.Label(zip_box, text="ZIP code:", font=FONT).grid(row=1, column=0, sticky="w", pady=4)
zip_entry = tk.Entry(zip_box, width=8, font=FONT)
zip_entry.grid(row=1, column=1, sticky="w")
tk.Button(zip_box, text="Add ZIP", font=FONT, command=add_zip_clicked).grid(row=1, column=2, padx=4)
tk.Button(zip_box, text="Remove selected ZIP", font=FONT,
          command=remove_zip_clicked).grid(row=2, column=0, columnspan=3, sticky="ew")
refresh_zip_list()

# --- 3. Add an applicant ---
form_box = tk.LabelFrame(left, text=" 3. Test Your Own Applicant ", font=HEADING_FONT, padx=8, pady=4)
form_box.pack(fill="x", pady=6)

tk.Label(form_box, text="Name:", font=FONT).grid(row=0, column=0, sticky="w")
name_entry = tk.Entry(form_box, width=22, font=FONT)
name_entry.grid(row=0, column=1, pady=2)
tk.Label(form_box, text="ZIP code:", font=FONT).grid(row=1, column=0, sticky="w")
applicant_zip_entry = tk.Entry(form_box, width=22, font=FONT)
applicant_zip_entry.grid(row=1, column=1, pady=2)
tk.Label(form_box, text="Gap (months):", font=FONT).grid(row=2, column=0, sticky="w")
gap_entry = tk.Entry(form_box, width=22, font=FONT)
gap_entry.grid(row=2, column=1, pady=2)
tk.Label(form_box, text="Skills score (0-100):", font=FONT).grid(row=3, column=0, sticky="w")
score_entry = tk.Entry(form_box, width=22, font=FONT)
score_entry.grid(row=3, column=1, pady=2)
tk.Button(form_box, text="Add Applicant", font=FONT,
          command=add_applicant_clicked).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 0))

# Pressing Enter in any of these boxes adds the applicant
for entry in (name_entry, applicant_zip_entry, gap_entry, score_entry):
    entry.bind("<Return>", add_applicant_enter)

# --- Right side: results table ---
tk.Label(right, text="Screening Results", font=HEADING_FONT, anchor="w").pack(fill="x")

table_frame = tk.Frame(right)
table_frame.pack(fill="x")
columns = ("applicant", "zip", "gap", "skills", "final", "result", "audit")
headings = ("Applicant", "ZIP", "Gap (mo)", "Skills", "Final", "Result", "Audit flag")
widths = (130, 70, 80, 70, 70, 130, 190)

results_table = ttk.Treeview(table_frame, columns=columns, show="headings", height=6)
for i in range(len(columns)):
    results_table.heading(columns[i], text=headings[i])
    results_table.column(columns[i], width=widths[i], anchor="w")
results_table.tag_configure("passed", background="#dff0e0", foreground="black")
results_table.tag_configure("filtered", background="#f8dede", foreground="black")
table_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=results_table.yview)
results_table.configure(yscrollcommand=table_scroll.set)
results_table.pack(side="left", fill="x", expand=True)
table_scroll.pack(side="right", fill="y")

# Buttons for managing who is in the table
table_buttons = tk.Frame(right)
table_buttons.pack(fill="x", pady=(6, 0))
tk.Button(table_buttons, text="Remove selected applicant", font=FONT,
          command=remove_applicant_clicked).pack(side="left", padx=(0, 6))
tk.Button(table_buttons, text="Clear all applicants", font=FONT,
          command=clear_all_clicked).pack(side="left", padx=6)

# --- Right side: bias diagnostics panel ---
tk.Label(right, text="Bias Diagnostics & Explanation", font=HEADING_FONT,
         anchor="w").pack(fill="x", pady=(10, 0))

diagnostics_frame = tk.Frame(right)
diagnostics_frame.pack(fill="both", expand=True)
diagnostics_box = tk.Text(diagnostics_frame, wrap="word", font=FONT, height=14,
                          state="disabled", padx=8, pady=6)
diagnostics_scroll = ttk.Scrollbar(diagnostics_frame, orient="vertical",
                                   command=diagnostics_box.yview)
diagnostics_box.configure(yscrollcommand=diagnostics_scroll.set)
diagnostics_box.pack(side="left", fill="both", expand=True)
diagnostics_scroll.pack(side="right", fill="y")

# --- Status bar ---
status_label = tk.Label(root, text="", font=FONT, anchor="w", relief="sunken")
status_label.grid(row=4, column=0, columnspan=2, sticky="ew")

# ---------------------------------------------------------------------------
# START THE APP
# ---------------------------------------------------------------------------
welcome_text = ("Welcome! Move the sliders on the left to change the algorithm's rules, then click "
                "Run Audit. The table above shows who passes, and this panel explains who was "
                "unfairly filtered out and why. For a quick demo, click Load Sample Applicants.\n\n"
                "Created by Jasmine W., Crystal R., Leilani G., and Frankie A.P.\n\n"
                + bias_rules.simulation_note)
show_text(diagnostics_box, welcome_text)

# Start with an empty screen. The data file is only read when the user clicks
# Load Sample Applicants.
bias_rules.flagged_zip_codes.clear()
refresh_zip_list()
fill_table()
set_status("No applicants yet. Add an applicant in the form on the left, "
           "or click Load Sample Applicants.")

name_entry.focus_set()   # start with the cursor in the Name box
root.mainloop()
