# 🧪 Peptide Dosage, Reconstitution & Multi-Person Tracker TUI

A high-performance, responsive Terminal User Interface (TUI) built with **Python**, **Textual**, and **SQLite**. Designed for calculating peptide reconstitution dilutions, U-100 insulin syringe draws, titration schedules, multi-person patient protocol management, and accredited PubMed scientific literature reference tracking.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Textual](https://img.shields.io/badge/UI-Textual-000000?style=flat)
![Database](https://img.shields.io/badge/Database-SQLite3-003B57?style=flat&logo=sqlite&logoColor=white)
![Package Manager](https://img.shields.io/badge/Manager-uv-DE5E97?style=flat)

---

## 🌟 Key Features

### 💉 1. Reconstitution & Syringe Calculator
- **Automated Calculations**: Calculates solution concentration ($\text{mg/mL}$ and $\text{mcg/mL}$), exact single dose volume ($\text{mL}$), U-100 insulin syringe markings (Units), and total available doses per vial.
- **Real-Time Syringe Visualizer**: Dynamic ASCII U-100 insulin syringe gauge updating instantly with capacity warnings ($>100\text{ Units}$).
- **Preset Quick-Buttons**: One-click preset buttons for common vial strengths ($5\text{mg}$, $10\text{mg}$, $25\text{mg}$, $30\text{mg}$, $50\text{mg}$) and BAC water dilution volumes ($1\text{mL}$, $2\text{mL}$, $2.5\text{mL}$, $3\text{mL}$).

### 👥 2. Multi-Person Patient Protocol Tracker
- **SQLite Database (`peptides.db`)**: Local persistent database storage for patient profiles and assigned protocols.
- **Profile Management**: Switch between patient profiles, create new patient profiles, or remove a profile (and its protocols/dose history) with a confirmation prompt.
- **Quick-Add & Edit Workflows**: Assign peptide templates directly to a selected patient profile with a single click, or load an existing saved protocol back into the calculator to edit its exact values.
- **🖨️ Export Printable Reference Sheets**: Generate formatted patient protocol summary text files (`patient_<name>_peptides_summary.txt`) detailing active medications, doses, syringe draws, notes, citations, and recent dose history.

### 🔬 3. Scientific PubMed Citations & Literature Reference
- **Clinical Literature Integration**: Embedded study titles, PubMed IDs (PMIDs), and direct URLs (`https://pubmed.ncbi.nlm.nih.gov/<PMID>/`) for every supported peptide.
- **In-App Reference Tab**: Dedicated tab rendering clinical guidelines, target dose ranges, reconstitution rules, and peer-reviewed citations using Rich formatting.

### 📅 4. Titration Schedule Planner
- **Multi-Phase Titration Schedules**: Generates multi-week step-up titration schedules for GLP-1/2/3 analogues and growth hormone secretagogues.
- **File Export**: Save standalone titration schedules to disk (`peptide_<name>_schedule.txt`).

### 💊 5. Dose History & Adherence Tracking
- **Dose Log**: Log each dose actually taken against a saved protocol, timestamped, with an optional note.
- **Adherence Summary**: Per-protocol adherence percentage, estimated from the protocol's frequency against how many doses have been logged since it was started.

---

## 📋 Supported Peptides Database

The application includes pre-configured master templates and accredited scientific literature citations for:

| Peptide | Type / Class | Standard Vial | Recommended BAC Water | Typical Target Dose |
| :--- | :--- | :--- | :--- | :--- |
| **BPC-157** | Tissue Repair / Healing | $5.0\text{ mg}$ | $2.0\text{ mL}$ | $250.0\text{ mcg}$ daily |
| **Tesamorelin** | GHRH Analogue / Fat Reduction | $2.0\text{ mg}$ | $2.0\text{ mL}$ | $2.0\text{ mg}$ daily (bedtime) |
| **Tirzepatide** | GIP / GLP-1 Dual Agonist | $10.0\text{ mg}$ | $2.0\text{ mL}$ | $2.5\text{ mg}$ weekly |
| **Semaglutide** | GLP-1 Receptor Agonist | $5.0\text{ mg}$ | $2.0\text{ mL}$ | $0.25\text{ mg}$ weekly |
| **Retatrutide** | GLP-1 / GIP / GCGR Triple Agonist | $5.0\text{ mg}$ | $2.0\text{ mL}$ | $2.0\text{ mg}$ weekly |
| **MOTS-c** | Mitochondrial-Derived Peptide | $10.0\text{ mg}$ | $2.0\text{ mL}$ | $5.0\text{ mg}$ (3x weekly) |
| **CJC-1295** | GHRH Secretagogue | $2.0\text{ mg}$ | $2.0\text{ mL}$ | $100.0\text{ mcg}$ daily |
| **Ipamorelin** | Selective GH Secretagogue | $5.0\text{ mg}$ | $2.5\text{ mL}$ | $200.0\text{ mcg}$ daily (bedtime) |
| **Sermorelin** | GHRH Analogue | $5.0\text{ mg}$ | $2.5\text{ mL}$ | $300.0\text{ mcg}$ daily |
| **AOD-9604** | Lipolytic GH Fragment | $5.0\text{ mg}$ | $2.0\text{ mL}$ | $300.0\text{ mcg}$ daily (morning) |
| **NAD+** | Cellular Coenzyme | $500.0\text{ mg}$ | $5.0\text{ mL}$ | $50.0\text{ mg}$ (2x weekly) |
| **GLOW Blend** | GHK-Cu / BPC-157 / TB-500 | $50.0\text{ mg}$ | $3.0\text{ mL}$ | $1.5\text{ mg}$ daily |
| **KLOW Blend** | GHK-Cu / BPC / TB / KPV | $50.0\text{ mg}$ | $3.0\text{ mL}$ | $1.5\text{ mg}$ daily |
| **DSIP** | Sleep-Regulating Nonapeptide | $5.0\text{ mg}$ | $2.0\text{ mL}$ | $100.0\text{ mcg}$ nightly |
| **Melanotan II** | Melanocortin Receptor Agonist | $10.0\text{ mg}$ | $2.0\text{ mL}$ | $250.0\text{ mcg}$ daily (loading) |
| **GHK-Cu** | Copper-Binding Tripeptide | $100.0\text{ mg}$ | $5.0\text{ mL}$ | $1.0\text{ mg}$ daily |
| **Cagrilintide** | Long-Acting Amylin Analogue | $5.0\text{ mg}$ | $2.0\text{ mL}$ | $0.25\text{ mg}$ weekly |
| **CJC-1295 with DAC** | Long-Acting GHRH Secretagogue | $5.0\text{ mg}$ | $2.0\text{ mL}$ | $1.0\text{ mg}$ weekly |
| **Selank** | Anxiolytic/Nootropic Peptide | $11.0\text{ mg}$ | $5.0\text{ mL}$ | $250.0\text{ mcg}$ daily |
| **Semax** | Nootropic/Neuroprotective Peptide | $11.0\text{ mg}$ | $5.0\text{ mL}$ | $300.0\text{ mcg}$ daily |
| **Pinealon** | Neuroprotective Bioregulator | $10.0\text{ mg}$ | $2.0\text{ mL}$ | $100.0\text{ mcg}$ daily |
| **PT-141** | Melanocortin Receptor Agonist (Libido) | $10.0\text{ mg}$ | $2.0\text{ mL}$ | $1.0\text{ mg}$ PRN |
| **Epithalon** | Telomerase-Activating Bioregulator | $10.0\text{ mg}$ | $2.0\text{ mL}$ | $5.0\text{ mg}$ daily (course) |
| **AICAR** | AMPK Activator | $50.0\text{ mg}$ | $2.0\text{ mL}$ | $50.0\text{ mg}$ (3x weekly) |
| **TB-500** | Thymosin Beta-4 Fragment | $5.0\text{ mg}$ | $2.0\text{ mL}$ | $2.5\text{ mg}$ (2x weekly) |
| **IGF-1 LR3** | Long-Acting IGF-1 Analogue | $0.1\text{ mg}$ | $1.0\text{ mL}$ | $20.0\text{ mcg}$ daily |

---

## 🚀 Installation & Setup

### Prerequisites
- **Python 3.10+**
- [`uv`](https://github.com/astral-sh/uv) package manager (recommended) or standard `pip`.

### Quickstart with `uv`

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/alinuxfan/peptide-dosage-tui.git
   cd peptide-dosage-tui
   ```

2. **Run the TUI Application**:
   ```bash
   uv run python main.py
   ```

### Standard Setup with `pip`

```bash
git clone https://github.com/alinuxfan/peptide-dosage-tui.git
cd peptide-dosage-tui
python3 -m venv .venv
source .venv/bin/activate
pip install textual rich
python main.py
```

---

## 💻 Usage Guide

### 1. Reconstitution Calculator Tab
1. Select a pre-configured peptide template from the dropdown (or select `Custom / Other`).
2. Adjust vial strength ($mg$) and bacteriostatic water volume ($mL$) using preset buttons or manual inputs.
3. View instant concentration calculations, dosage volumes, and the ASCII syringe draw gauge.
4. Click **💾 Save Protocol to Active Profile** to log the active medication to the selected patient profile.

### 2. Patient Tracker Tab
1. Select an existing person profile from the **Active Person Profile** dropdown (or enter a new name and click **+ Add Person**), or click **❌ Remove Person** to delete the active profile (blocked if it's the only one left, and confirmed before deleting).
2. Choose a peptide from the **Quick Add Peptide** dropdown and click **+ Add to Person** to assign protocols rapidly.
3. Select a row and click **✏️ Edit Selected** to load that protocol's exact values back into the Calculator tab, or **💊 Log Dose Taken** to record that the dose was taken just now.
4. Click **❌ Remove Selected** to delete a protocol (with a confirmation prompt), or **🖨️ Export Printable Sheet** to export a full printable summary report for that person.

### 3. Dosing Schedule Planner Tab
1. Review multi-week titration step-up phases for GLP-1/2/3 or GH secretagogues.
2. Click **Save Schedule to File** to export the schedule as a formatted text document.

### 4. Dose Log Tab
1. Review the adherence summary (expected vs. logged doses per protocol) and the raw chronological dose log for the active profile.
2. Select an entry and click **🗑️ Delete Entry** to remove it (with a confirmation prompt).

---

## 📁 Repository Structure

```
peptide-dosage-tui/
├── main.py        # Core Textual TUI application layout, widgets, & handlers
├── db.py          # SQLite database connection, schema seeding, & export helpers
├── calc.py        # Shared dosing-math and adherence-heuristic functions
├── tests/         # pytest suite (calc.py and db.py)
├── peptides.db    # Local SQLite database (created on first run)
├── pyproject.toml # Project dependencies & metadata
└── README.md      # Project documentation
```

---

## ⚠️ Disclaimer

This software application is developed strictly for **research, informational, and educational reference purposes**. It does not constitute medical advice, diagnosis, or treatment. Users must consult qualified medical healthcare professionals regarding any prescription medication or medical protocols.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
