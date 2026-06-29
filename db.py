import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "peptides.db")

# Default peptides database with scientific PubMed citations
DEFAULT_PEPTIDES = [
    {
        "name": "BPC-157",
        "vial_mg": 5.0,
        "water_ml": 2.0,
        "dose": 250.0,
        "unit": "mcg",
        "freq": "daily",
        "notes": "Commonly used for joint/tendon healing. Standard dose: 250mcg - 500mcg daily or twice daily.",
        "schedule": [
            ("Week 1-2", 250.0, "mcg"),
            ("Week 3-4", 350.0, "mcg"),
            ("Week 5-6", 500.0, "mcg"),
        ],
        "sources": [
            {"title": "Emerging Use of BPC-157 in Orthopaedic Sports Medicine", "pmid": "40756949", "url": "https://pubmed.ncbi.nlm.nih.gov/40756949/"},
            {"title": "Role of BPC-157 in Tissue Repair and Pain Management", "pmid": "41898733", "url": "https://pubmed.ncbi.nlm.nih.gov/41898733/"}
        ]
    },
    {
        "name": "Ipamorelin",
        "vial_mg": 5.0,
        "water_ml": 2.5,
        "dose": 200.0,
        "unit": "mcg",
        "freq": "daily (before bed)",
        "notes": "Growth hormone secretagogue. Standard dose: 200mcg - 300mcg daily, 5 days on / 2 days off.",
        "schedule": [
            ("Week 1-4", 200.0, "mcg"),
            ("Week 5-8", 250.0, "mcg"),
            ("Week 9-12", 300.0, "mcg"),
        ],
        "sources": [
            {"title": "Ipamorelin, the first selective growth hormone secretagogue", "pmid": "9849822", "url": "https://pubmed.ncbi.nlm.nih.gov/9849822/"},
            {"title": "Pharmacokinetic-pharmacodynamic modeling of ipamorelin in human volunteers", "pmid": "10496658", "url": "https://pubmed.ncbi.nlm.nih.gov/10496658/"}
        ]
    },
    {
        "name": "CJC-1295",
        "vial_mg": 2.0,
        "water_ml": 2.0,
        "dose": 100.0,
        "unit": "mcg",
        "freq": "daily",
        "notes": "Often combined with Ipamorelin. Standard dose: 100mcg - 150mcg, 1-3 times daily.",
        "schedule": [
            ("Week 1-8", 100.0, "mcg"),
        ],
        "sources": [
            {"title": "Prolonged stimulation of GH and IGF-I secretion by CJC-1295 in healthy adults", "pmid": "16352683", "url": "https://pubmed.ncbi.nlm.nih.gov/16352683/"},
            {"title": "Pulsatile secretion of growth hormone during continuous stimulation by CJC-1295", "pmid": "17018654", "url": "https://pubmed.ncbi.nlm.nih.gov/17018654/"}
        ]
    },
    {
        "name": "Semaglutide",
        "vial_mg": 5.0,
        "water_ml": 2.0,
        "dose": 0.25,
        "unit": "mg",
        "freq": "weekly",
        "notes": "GLP-1 receptor agonist. Standard titration starts at 0.25mg weekly for 4 weeks.",
        "schedule": [
            ("Week 1-4 (Titration)", 0.25, "mg"),
            ("Week 5-8 (Titration)", 0.50, "mg"),
            ("Week 9-12 (Titration)", 1.00, "mg"),
            ("Week 13-16 (Titration)", 1.70, "mg"),
            ("Week 17+ (Maintenance)", 2.40, "mg"),
        ],
        "sources": [
            {"title": "Once-Weekly Semaglutide in Adults with Overweight or Obesity (STEP 1)", "pmid": "33567185", "url": "https://pubmed.ncbi.nlm.nih.gov/33567185/"},
            {"title": "Long-term weight loss effects of semaglutide in obesity (SELECT trial)", "pmid": "38740993", "url": "https://pubmed.ncbi.nlm.nih.gov/38740993/"}
        ]
    },
    {
        "name": "Tirzepatide",
        "vial_mg": 10.0,
        "water_ml": 2.0,
        "dose": 2.5,
        "unit": "mg",
        "freq": "weekly",
        "notes": "GIP/GLP-1 receptor agonist (often referred to as GLP-2 dual agonist). Titrated monthly.",
        "schedule": [
            ("Week 1-4 (Titration)", 2.5, "mg"),
            ("Week 5-8 (Titration)", 5.0, "mg"),
            ("Week 9-12 (Titration)", 7.5, "mg"),
            ("Week 13-16 (Titration)", 10.0, "mg"),
            ("Week 17-20 (Titration)", 12.5, "mg"),
            ("Week 21+ (Maintenance)", 15.0, "mg"),
        ],
        "sources": [
            {"title": "Tirzepatide Once Weekly for the Treatment of Obesity (SURMOUNT-1)", "pmid": "35658024", "url": "https://pubmed.ncbi.nlm.nih.gov/35658024/"},
            {"title": "Tirzepatide as Compared with Semaglutide for the Treatment of Obesity", "pmid": "40353578", "url": "https://pubmed.ncbi.nlm.nih.gov/40353578/"}
        ]
    },
    {
        "name": "Retatrutide",
        "vial_mg": 5.0,
        "water_ml": 2.0,
        "dose": 2.0,
        "unit": "mg",
        "freq": "weekly",
        "notes": "GLP-1/GIP/GCGR triple agonist (GLP-3). Standard titration starts at 2mg weekly.",
        "schedule": [
            ("Week 1-4 (Titration)", 2.0, "mg"),
            ("Week 5-8 (Titration)", 4.0, "mg"),
            ("Week 9-12 (Titration)", 8.0, "mg"),
            ("Week 13+ (Maintenance)", 12.0, "mg"),
        ],
        "sources": [
            {"title": "Triple-Hormone-Receptor Agonist Retatrutide for Obesity - A Phase 2 Trial", "pmid": "37366315", "url": "https://pubmed.ncbi.nlm.nih.gov/37366315/"},
            {"title": "Efficacy and safety of retatrutide, a novel GLP-1, GIP, and glucagon receptor agonist", "pmid": "40291085", "url": "https://pubmed.ncbi.nlm.nih.gov/40291085/"}
        ]
    },
    {
        "name": "MOTS-c",
        "vial_mg": 10.0,
        "water_ml": 2.0,
        "dose": 5.0,
        "unit": "mg",
        "freq": "3x weekly",
        "notes": "Mitochondria-derived peptide. Dosed 5mg three times weekly (e.g. Mon/Wed/Fri) for 4-6 weeks.",
        "schedule": [
            ("Week 1-4 (Active)", 5.0, "mg"),
        ],
        "sources": [
            {"title": "Mitochondrial-derived peptide MOTS-c promotes metabolic homeostasis and reduces obesity", "pmid": "25738459", "url": "https://pubmed.ncbi.nlm.nih.gov/25738459/"},
            {"title": "MOTS-c improves intrinsic muscle mitochondrial bioenergetic health", "pmid": "41520850", "url": "https://pubmed.ncbi.nlm.nih.gov/41520850/"}
        ]
    },
    {
        "name": "GLOW Blend",
        "vial_mg": 50.0,
        "water_ml": 3.0,
        "dose": 1.5,
        "unit": "mg",
        "freq": "daily",
        "notes": "Cosmetic cellular renewal blend containing GHK-Cu, BPC-157, and TB-500.",
        "schedule": [
            ("Week 1-4 (Daily)", 1.5, "mg"),
        ],
        "sources": [
            {"title": "Regenerative and Protective Actions of the GHK-Cu Peptide in Light of New Clinical Data", "pmid": "29986520", "url": "https://pubmed.ncbi.nlm.nih.gov/29986520/"}
        ]
    },
    {
        "name": "KLOW Blend",
        "vial_mg": 50.0,
        "water_ml": 3.0,
        "dose": 1.5,
        "unit": "mg",
        "freq": "daily",
        "notes": "Anti-inflammatory and skin/hair recovery blend containing GHK-Cu, BPC-157, TB-500, and KPV.",
        "schedule": [
            ("Week 1-4 (Daily)", 1.5, "mg"),
        ],
        "sources": [
            {"title": "The tripeptide GHK-Cu in prevention of oxidative stress and tissue repair", "pmid": "22616288", "url": "https://pubmed.ncbi.nlm.nih.gov/22616288/"}
        ]
    },
    {
        "name": "Sermorelin",
        "vial_mg": 5.0,
        "water_ml": 2.5,
        "dose": 300.0,
        "unit": "mcg",
        "freq": "daily",
        "notes": "GHRH analogue promoting natural GH release. Typically injected nightly.",
        "schedule": [
            ("Week 1-12 (Nightly)", 300.0, "mcg"),
        ],
        "sources": [
            {"title": "Sermorelin: a review of its use in diagnosis and treatment of GH deficiency", "pmid": "18031173", "url": "https://pubmed.ncbi.nlm.nih.gov/18031173/"},
            {"title": "Once daily subcutaneous growth hormone-releasing hormone therapy accelerates growth", "pmid": "8772599", "url": "https://pubmed.ncbi.nlm.nih.gov/8772599/"}
        ]
    },
    {
        "name": "AOD-9604",
        "vial_mg": 5.0,
        "water_ml": 2.0,
        "dose": 300.0,
        "unit": "mcg",
        "freq": "daily",
        "notes": "Anti-obesity peptide fragment. Administered in the morning on an empty stomach.",
        "schedule": [
            ("Week 1-12 (Morning)", 300.0, "mcg"),
        ],
        "sources": [
            {"title": "Effects of human GH and its lipolytic fragment (AOD9604) on lipid metabolism", "pmid": "11713213", "url": "https://pubmed.ncbi.nlm.nih.gov/11713213/"}
        ]
    },
    {
        "name": "NAD+",
        "vial_mg": 500.0,
        "water_ml": 5.0,
        "dose": 50.0,
        "unit": "mg",
        "freq": "twice weekly",
        "notes": "Nicotinamide Adenine Dinucleotide. Reconstituted at 100mg/mL. Subcutaneous injection.",
        "schedule": [
            ("Week 1-2 (Starting)", 25.0, "mg"),
            ("Week 3-4 (Target)", 50.0, "mg"),
            ("Week 5+ (Maintenance)", 100.0, "mg"),
        ],
        "sources": [
            {"title": "NAD+ metabolism and its roles in cellular physiology and disease", "pmid": "31548645", "url": "https://pubmed.ncbi.nlm.nih.gov/31548645/"}
        ]
    },
    {
        "name": "Custom / Other",
        "vial_mg": 5.0,
        "water_ml": 2.0,
        "dose": 250.0,
        "unit": "mcg",
        "freq": "daily",
        "notes": "Enter custom values below to calculate dilution and syringe markings.",
        "schedule": [
            ("Week 1-4", 250.0, "mcg")
        ],
        "sources": []
    }
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Table for profiles (people)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Table for master peptide templates
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS peptides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        vial_mg REAL,
        water_ml REAL,
        dose REAL,
        unit TEXT,
        freq TEXT,
        notes TEXT,
        schedule_json TEXT,
        sources_json TEXT
    )
    """)

    # Table for user/patient tracked protocols
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_protocols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL,
        peptide_name TEXT NOT NULL,
        vial_mg REAL NOT NULL,
        water_ml REAL NOT NULL,
        target_dose REAL NOT NULL,
        dose_unit TEXT NOT NULL,
        frequency TEXT,
        notes TEXT,
        schedule_json TEXT,
        sources_json TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
    )
    """)

    # Populate default profiles if none exist
    cursor.execute("SELECT COUNT(*) as count FROM profiles")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("INSERT INTO profiles (name, notes) VALUES ('Default User', 'Main user profile')")
        cursor.execute("INSERT INTO profiles (name, notes) VALUES ('Alice', 'Sample patient profile A')")
        cursor.execute("INSERT INTO profiles (name, notes) VALUES ('Bob', 'Sample patient profile B')")

    # Populate default master peptides if none exist
    cursor.execute("SELECT COUNT(*) as count FROM peptides")
    if cursor.fetchone()["count"] == 0:
        for p in DEFAULT_PEPTIDES:
            cursor.execute("""
            INSERT INTO peptides (name, vial_mg, water_ml, dose, unit, freq, notes, schedule_json, sources_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["name"],
                p["vial_mg"],
                p["water_ml"],
                p["dose"],
                p["unit"],
                p["freq"],
                p["notes"],
                json.dumps(p["schedule"]),
                json.dumps(p["sources"])
            ))

    conn.commit()
    conn.close()


# Profile Management Functions
def get_profiles():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_profile(name, notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO profiles (name, notes) VALUES (?, ?)", (name, notes))
        conn.commit()
        profile_id = cursor.lastrowid
        conn.close()
        return profile_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


# Master Peptide Functions
def get_peptides():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM peptides ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        d = dict(row)
        d["schedule"] = json.loads(d["schedule_json"]) if d["schedule_json"] else []
        d["sources"] = json.loads(d["sources_json"]) if d["sources_json"] else []
        result.append(d)
    return result


def get_peptide_by_name(name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM peptides WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["schedule"] = json.loads(d["schedule_json"]) if d["schedule_json"] else []
        d["sources"] = json.loads(d["sources_json"]) if d["sources_json"] else []
        return d
    return None


# Patient Protocol Functions
def get_user_protocols(profile_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_protocols WHERE profile_id = ? ORDER BY updated_at DESC", (profile_id,))
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        d = dict(row)
        d["schedule"] = json.loads(d["schedule_json"]) if d["schedule_json"] else []
        d["sources"] = json.loads(d["sources_json"]) if d["sources_json"] else []
        result.append(d)
    return result


def add_or_update_user_protocol(profile_id, peptide_name, vial_mg, water_ml, target_dose, dose_unit, frequency, notes, schedule, sources):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if this peptide already exists for the profile
    cursor.execute("SELECT id FROM user_protocols WHERE profile_id = ? AND peptide_name = ?", (profile_id, peptide_name))
    existing = cursor.fetchone()
    
    schedule_json = json.dumps(schedule)
    sources_json = json.dumps(sources)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if existing:
        cursor.execute("""
        UPDATE user_protocols 
        SET vial_mg = ?, water_ml = ?, target_dose = ?, dose_unit = ?, frequency = ?, notes = ?, schedule_json = ?, sources_json = ?, updated_at = ?
        WHERE id = ?
        """, (vial_mg, water_ml, target_dose, dose_unit, frequency, notes, schedule_json, sources_json, now, existing["id"]))
    else:
        cursor.execute("""
        INSERT INTO user_protocols (profile_id, peptide_name, vial_mg, water_ml, target_dose, dose_unit, frequency, notes, schedule_json, sources_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (profile_id, peptide_name, vial_mg, water_ml, target_dose, dose_unit, frequency, notes, schedule_json, sources_json, now))
        
    conn.commit()
    conn.close()


def delete_user_protocol(protocol_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_protocols WHERE id = ?", (protocol_id,))
    conn.commit()
    conn.close()


def export_person_reference_sheet(profile_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM profiles WHERE id = ?", (profile_id,))
    prof = cursor.fetchone()
    if not prof:
        conn.close()
        return None
    profile_name = prof["name"]
    
    protocols = get_user_protocols(profile_id)
    conn.close()
    
    filename = f"patient_{profile_name.lower().replace(' ', '_')}_peptides_summary.txt"
    filepath = os.path.join(os.getcwd(), filename)
    
    with open(filepath, "w") as f:
        f.write("=" * 72 + "\n")
        f.write(f" PATIENT PEPTIDE PROTOCOL REFERENCE SHEET: {profile_name.upper()}\n")
        f.write("=" * 72 + "\n")
        f.write(f"Date Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Tracked Peptides: {len(protocols)}\n")
        f.write("=" * 72 + "\n\n")
        
        if not protocols:
            f.write("No active peptide protocols assigned for this person.\n")
        else:
            for i, p in enumerate(protocols, 1):
                f.write(f"[{i}] PEPTIDE: {p['peptide_name'].upper()}\n")
                f.write("-" * 50 + "\n")
                conc_mg_ml = p['vial_mg'] / p['water_ml'] if p['water_ml'] > 0 else 0
                conc_mcg_ml = conc_mg_ml * 1000.0
                dose_mg = p['target_dose'] / 1000.0 if p['dose_unit'] == 'mcg' else p['target_dose']
                vol_ml = dose_mg / conc_mg_ml if conc_mg_ml > 0 else 0
                units = vol_ml * 100.0
                
                f.write(f"• Vial Size:           {p['vial_mg']:.1f} mg\n")
                f.write(f"• BAC Water Added:     {p['water_ml']:.1f} mL\n")
                f.write(f"• Solution Strength:   {conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL)\n")
                f.write(f"• Prescribed Dose:     {p['target_dose']} {p['dose_unit']} ({p['frequency']})\n")
                f.write(f"• U-100 Syringe Draw:  {units:.1f} Units ({vol_ml:.3f} mL)\n")
                f.write(f"• Clinical Notes:      {p['notes']}\n")
                
                if p['schedule']:
                    f.write("\n  Titration Schedule:\n")
                    f.write(f"  {'Phase':<20} | {'Dose':<10} | {'Syringe Draw':<15}\n")
                    f.write("  " + "-" * 48 + "\n")
                    for phase, d_val, u_unit in p['schedule']:
                        d_mg = d_val / 1000.0 if u_unit == 'mcg' else d_val
                        v_ml = d_mg / conc_mg_ml if conc_mg_ml > 0 else 0
                        u_draw = v_ml * 100.0
                        d_str = f"{d_val:.0f} mcg" if u_unit == 'mcg' else f"{d_val:.2f} mg"
                        f.write(f"  {phase:<20} | {d_str:<10} | {u_draw:.1f} Units\n")
                        
                if p['sources']:
                    f.write("\n  Scientific Citations & Literature:\n")
                    for s in p['sources']:
                        f.write(f"  - {s['title']} (PMID: {s['pmid']})\n")
                        f.write(f"    URL: {s['url']}\n")
                        
                f.write("\n" + "=" * 72 + "\n\n")
                
    return filename


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
