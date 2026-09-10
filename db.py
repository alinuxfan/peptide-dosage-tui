import sqlite3
import json
import os
from datetime import datetime, timezone

import calc

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
        "name": "Tesamorelin",
        "vial_mg": 2.0,
        "water_ml": 2.0,
        "dose": 2.0,
        "unit": "mg",
        "freq": "daily (at bedtime)",
        "notes": "GHRH analogue for visceral adipose reduction and growth hormone stimulation. Standard dose: 2mg daily.",
        "schedule": [
            ("Week 1-12 (Nightly)", 2.0, "mg"),
        ],
        "sources": [
            {"title": "Effects of Tesemorelin, a Growth Hormone-Releasing Hormone Analogue, in HIV Patients", "pmid": "17148701", "url": "https://pubmed.ncbi.nlm.nih.gov/17148701/"},
            {"title": "Tesemorelin for the treatment of visceral adiposity", "pmid": "21848416", "url": "https://pubmed.ncbi.nlm.nih.gov/21848416/"}
        ]
    },
    {
        "name": "DSIP",
        "vial_mg": 5.0,
        "water_ml": 2.0,
        "dose": 100.0,
        "unit": "mcg",
        "freq": "nightly (before bed)",
        "notes": "Nonapeptide studied for sleep regulation and stress/HPA-axis modulation. Standard research dose: 100mcg - 300mcg nightly before sleep.",
        "schedule": [
            ("Week 1-2", 100.0, "mcg"),
            ("Week 3-4", 200.0, "mcg"),
            ("Week 5+", 300.0, "mcg"),
        ],
        "sources": [
            {"title": "Effects of delta sleep-inducing peptide on sleep of chronic insomniac patients. A double-blind study", "pmid": "1299794", "url": "https://pubmed.ncbi.nlm.nih.gov/1299794/"},
            {"title": "Characterization, properties and multivariate functions of delta-sleep-inducing peptide (DSIP)", "pmid": "6548966", "url": "https://pubmed.ncbi.nlm.nih.gov/6548966/"}
        ]
    },
    {
        "name": "Melanotan II",
        "vial_mg": 10.0,
        "water_ml": 2.0,
        "dose": 250.0,
        "unit": "mcg",
        "freq": "daily (loading), then 2-3x weekly (maintenance)",
        "notes": "Non-selective melanocortin receptor agonist used for skin pigmentation/tanning and libido. Loading dose 250mcg - 500mcg daily until desired tan, then 500mcg 2-3x weekly maintenance.",
        "schedule": [
            ("Week 1-2 (Loading)", 250.0, "mcg"),
            ("Week 3-4 (Loading)", 500.0, "mcg"),
            ("Week 5+ (Maintenance)", 500.0, "mcg"),
        ],
        "sources": [
            {"title": "Evaluation of melanotan-II, a superpotent cyclic melanotropic peptide in a pilot phase-I clinical study", "pmid": "8637402", "url": "https://pubmed.ncbi.nlm.nih.gov/8637402/"},
            {"title": "Synthetic melanotropic peptide initiates erections in men with psychogenic erectile dysfunction: double-blind, placebo controlled crossover study", "pmid": "9679884", "url": "https://pubmed.ncbi.nlm.nih.gov/9679884/"}
        ]
    },
    {
        "name": "GHK-Cu",
        "vial_mg": 100.0,
        "water_ml": 5.0,
        "dose": 1.0,
        "unit": "mg",
        "freq": "daily",
        "notes": "Naturally occurring copper-binding tripeptide used both topically (cosmetic serums for skin remodeling/collagen synthesis) and via subcutaneous injection (systemic tissue repair, anti-inflammatory, wound healing). Standard injectable dose: 1mg - 2mg daily.",
        "schedule": [
            ("Week 1-4", 1.0, "mg"),
            ("Week 5-8", 1.5, "mg"),
            ("Week 9-12", 2.0, "mg"),
        ],
        "sources": [
            {"title": "GHK Peptide as a Natural Modulator of Multiple Cellular Pathways in Skin Regeneration", "pmid": "26236730", "url": "https://pubmed.ncbi.nlm.nih.gov/26236730/"}
        ]
    },
    {
        "name": "Cagrilintide",
        "vial_mg": 5.0,
        "water_ml": 2.0,
        "dose": 0.25,
        "unit": "mg",
        "freq": "weekly",
        "notes": "Long-acting amylin analogue, often paired with GLP-1 agonists (e.g. semaglutide) for weight management. Standard titration starts at 0.25mg weekly, following a semaglutide-style dose escalation.",
        "schedule": [
            ("Week 1-4 (Titration)", 0.25, "mg"),
            ("Week 5-8 (Titration)", 0.50, "mg"),
            ("Week 9-12 (Titration)", 1.00, "mg"),
            ("Week 13+ (Maintenance)", 2.40, "mg"),
        ],
        "sources": [
            {"title": "Development of Cagrilintide, a Long-Acting Amylin Analogue", "pmid": "34288673", "url": "https://pubmed.ncbi.nlm.nih.gov/34288673/"},
            {"title": "Safety, tolerability, pharmacokinetics, and pharmacodynamics of concomitant administration of multiple doses of cagrilintide with semaglutide 2.4 mg for weight management: a randomised, controlled, phase 1b trial", "pmid": "33894838", "url": "https://pubmed.ncbi.nlm.nih.gov/33894838/"}
        ]
    },
    {
        "name": "CJC-1295 with DAC",
        "vial_mg": 5.0,
        "water_ml": 2.0,
        "dose": 1.0,
        "unit": "mg",
        "freq": "weekly (or twice weekly)",
        "notes": "Long-acting GHRH analog conjugated to a Drug Affinity Complex (DAC) that binds serum albumin, extending its half-life to roughly 6-8 days -- distinct from CJC-1295 no-DAC, which requires daily dosing. Standard dose: 1mg - 2mg once or twice weekly.",
        "schedule": [
            ("Week 1-4", 1.0, "mg"),
            ("Week 5-8", 2.0, "mg"),
        ],
        "sources": [
            {"title": "Once-daily administration of CJC-1295, a long-acting growth hormone-releasing hormone (GHRH) analog, normalizes growth in the GHRH knockout mouse", "pmid": "16822960", "url": "https://pubmed.ncbi.nlm.nih.gov/16822960/"}
        ]
    },
    {
        "name": "Selank",
        "vial_mg": 11.0,
        "water_ml": 5.0,
        "dose": 250.0,
        "unit": "mcg",
        "freq": "daily (intranasal, split AM/PM)",
        "notes": "Synthetic heptapeptide analogue of tuftsin studied for anxiolytic/nootropic effects, typically administered intranasally. Standard dose: 250mcg - 500mcg daily, often cycled 2-4 weeks on.",
        "schedule": [
            ("Week 1-2", 250.0, "mcg"),
            ("Week 3-4", 500.0, "mcg"),
        ],
        "sources": [
            {"title": "Efficacy and possible mechanisms of action of a new peptide anxiolytic selank in the therapy of generalized anxiety disorders and neurasthenia", "pmid": "18454096", "url": "https://pubmed.ncbi.nlm.nih.gov/18454096/"},
            {"title": "Peptide-based Anxiolytics: The Molecular Aspects of Heptapeptide Selank Biological Activity", "pmid": "30255741", "url": "https://pubmed.ncbi.nlm.nih.gov/30255741/"}
        ]
    },
    {
        "name": "Semax",
        "vial_mg": 11.0,
        "water_ml": 5.0,
        "dose": 300.0,
        "unit": "mcg",
        "freq": "daily (intranasal, 1-3x/day)",
        "notes": "ACTH(4-10) fragment analogue studied as a nootropic/neuroprotective peptide, approved in Russia as an intranasal drug. Standard research dose: 300mcg - 600mcg daily, divided across 1-3 doses.",
        "schedule": [
            ("Week 1-2", 300.0, "mcg"),
            ("Week 3-4", 600.0, "mcg"),
        ],
        "sources": [
            {"title": "Therapy of peptic ulcer with semax peptide", "pmid": "12459874", "url": "https://pubmed.ncbi.nlm.nih.gov/12459874/"},
            {"title": "The Peptide Drug ACTH(4-7)PGP (Semax) Suppresses mRNA Transcripts Encoding Proinflammatory Mediators Induced by Reversible Ischemia of the Rat Brain", "pmid": "34097675", "url": "https://pubmed.ncbi.nlm.nih.gov/34097675/"}
        ]
    },
    {
        "name": "Pinealon",
        "vial_mg": 10.0,
        "water_ml": 2.0,
        "dose": 100.0,
        "unit": "mcg",
        "freq": "daily (short course)",
        "notes": "Short synthetic tripeptide bioregulator (Khavinson peptide) studied for neuroprotective/antioxidant effects. Standard protocol: 100mcg - 200mcg daily for a 10-20 day course, repeated periodically.",
        "schedule": [
            ("Days 1-10 (Course 1)", 100.0, "mcg"),
            ("Days 1-10 (Course 2, next cycle)", 200.0, "mcg"),
        ],
        "sources": [
            {"title": "Pinealon protects the rat offspring from prenatal hyperhomocysteinemia", "pmid": "22567179", "url": "https://pubmed.ncbi.nlm.nih.gov/22567179/"}
        ]
    },
    {
        "name": "PT-141",
        "vial_mg": 10.0,
        "water_ml": 2.0,
        "dose": 1.0,
        "unit": "mg",
        "freq": "as needed (PRN), 45 min before activity, max 1x/24hr",
        "notes": "FDA-approved (as Vyleesi) melanocortin receptor agonist for hypoactive sexual desire disorder; also used off-label for erectile dysfunction. Standard dose: 0.5mg - 1.75mg subcutaneously as needed, at least 45 minutes before activity, no more than once per 24 hours.",
        "schedule": [
            ("Initial/Trial Dose", 0.5, "mg"),
            ("Standard Dose", 1.0, "mg"),
            ("Max Dose", 1.75, "mg"),
        ],
        "sources": [
            {"title": "Bremelanotide for the Treatment of Hypoactive Sexual Desire Disorder: Two Randomized Phase 3 Trials", "pmid": "31599840", "url": "https://pubmed.ncbi.nlm.nih.gov/31599840/"},
            {"title": "Evaluation of the safety, pharmacokinetics and pharmacodynamic effects of subcutaneously administered PT-141, a melanocortin receptor agonist, in healthy male subjects and in patients with an inadequate response to Viagra", "pmid": "14999221", "url": "https://pubmed.ncbi.nlm.nih.gov/14999221/"}
        ]
    },
    {
        "name": "Epithalon",
        "vial_mg": 10.0,
        "water_ml": 2.0,
        "dose": 5.0,
        "unit": "mg",
        "freq": "daily (short course)",
        "notes": "Synthetic tetrapeptide bioregulator (Khavinson peptide) studied for telomerase activation and cellular senescence. Standard protocol: 5mg - 10mg daily for a 10-20 day course, typically 1-2 courses per year.",
        "schedule": [
            ("Days 1-10 (Course)", 5.0, "mg"),
            ("Days 1-20 (Extended Course)", 10.0, "mg"),
        ],
        "sources": [
            {"title": "Epithalon peptide induces telomerase activity and telomere elongation in human somatic cells", "pmid": "12937682", "url": "https://pubmed.ncbi.nlm.nih.gov/12937682/"},
            {"title": "Peptide promotes overcoming of the division limit in human somatic cell", "pmid": "15455129", "url": "https://pubmed.ncbi.nlm.nih.gov/15455129/"}
        ]
    },
    {
        "name": "AICAR",
        "vial_mg": 50.0,
        "water_ml": 2.0,
        "dose": 50.0,
        "unit": "mg",
        "freq": "3x weekly",
        "notes": "AMPK activator studied as an exercise-mimetic compound affecting fatty acid oxidation and glucose uptake in skeletal muscle. Standard research dose: 50mg - 100mg, 3 times weekly.",
        "schedule": [
            ("Week 1-2", 50.0, "mg"),
            ("Week 3-4", 100.0, "mg"),
        ],
        "sources": [
            {"title": "AICA riboside increases AMP-activated protein kinase, fatty acid oxidation, and glucose uptake in rat muscle", "pmid": "9435525", "url": "https://pubmed.ncbi.nlm.nih.gov/9435525/"},
            {"title": "Activity of LKB1 and AMPK-related kinases in skeletal muscle: effects of contraction, phenformin, and AICAR", "pmid": "15068958", "url": "https://pubmed.ncbi.nlm.nih.gov/15068958/"}
        ]
    },
    {
        "name": "TB-500",
        "vial_mg": 5.0,
        "water_ml": 2.0,
        "dose": 2.5,
        "unit": "mg",
        "freq": "2x weekly (loading)",
        "notes": "Synthetic fragment of Thymosin Beta-4 studied for tissue repair, angiogenesis, and reduced inflammation. Standard loading dose: 2mg - 2.5mg twice weekly for 4-6 weeks, then maintenance dose every 2-4 weeks.",
        "schedule": [
            ("Week 1-4 (Loading)", 2.5, "mg"),
            ("Week 5-6 (Loading)", 2.5, "mg"),
            ("Week 7+ (Maintenance)", 2.5, "mg"),
        ],
        "sources": [
            {"title": "The actin binding site on thymosin beta4 promotes angiogenesis", "pmid": "14500546", "url": "https://pubmed.ncbi.nlm.nih.gov/14500546/"},
            {"title": "Thymosin beta4 accelerates wound healing", "pmid": "10469335", "url": "https://pubmed.ncbi.nlm.nih.gov/10469335/"}
        ]
    },
    {
        "name": "IGF-1 LR3",
        "vial_mg": 0.1,
        "water_ml": 1.0,
        "dose": 20.0,
        "unit": "mcg",
        "freq": "daily (post-workout)",
        "notes": "Modified IGF-1 analog with reduced IGF-binding-protein affinity and extended half-life, used for its potent anabolic/anti-catabolic effects. Micro-dosed: 20mcg - 50mcg daily, typically injected locally post-workout in short 4-6 week cycles.",
        "schedule": [
            ("Week 1-2", 20.0, "mcg"),
            ("Week 3-4", 40.0, "mcg"),
            ("Week 5-6", 50.0, "mcg"),
        ],
        "sources": [
            {"title": "Long R3 insulin-like growth factor-I (IGF-I) infusion stimulates organ growth but reduces plasma IGF-I, IGF-II and IGF binding protein concentrations in the guinea pig", "pmid": "7561636", "url": "https://pubmed.ncbi.nlm.nih.gov/7561636/"},
            {"title": "Detection of LongR3-IGF-I, Des(1-3)-IGF-I, and R3-IGF-I using immunopurification and high resolution mass spectrometry for antidoping purposes", "pmid": "33587816", "url": "https://pubmed.ncbi.nlm.nih.gov/33587816/"}
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
    conn.execute("PRAGMA foreign_keys = ON")
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

    # created_at wasn't in the original schema; ALTER TABLE ADD COLUMN isn't
    # idempotent, so guard it with a table_info check before adding it.
    existing_columns = {row["name"] for row in cursor.execute("PRAGMA table_info(user_protocols)")}
    if "created_at" not in existing_columns:
        cursor.execute("ALTER TABLE user_protocols ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    # Table for logged dose-taken events (the actual adherence history, as
    # opposed to user_protocols which only tracks the planned protocol)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dose_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL,
        protocol_id INTEGER,
        peptide_name TEXT NOT NULL,
        dose_amount REAL NOT NULL,
        dose_unit TEXT NOT NULL,
        taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
    )
    """)

    # Populate default profiles if none exist
    cursor.execute("SELECT COUNT(*) as count FROM profiles")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("INSERT INTO profiles (name, notes) VALUES ('Default User', 'Main user profile')")
        cursor.execute("INSERT INTO profiles (name, notes) VALUES ('Alice', 'Sample patient profile A')")
        cursor.execute("INSERT INTO profiles (name, notes) VALUES ('Bob', 'Sample patient profile B')")

    # One-time rename migration: "Tesemorelin" was a misspelling of "Tesamorelin".
    # Rewrite both the master template and any already-saved patient protocols
    # so existing users don't get silently orphaned by the corrected name.
    cursor.execute("UPDATE peptides SET name = 'Tesamorelin' WHERE name = 'Tesemorelin'")
    cursor.execute("UPDATE user_protocols SET peptide_name = 'Tesamorelin' WHERE peptide_name = 'Tesemorelin'")

    # Populate default master peptides
    for p in DEFAULT_PEPTIDES:
        cursor.execute("""
        INSERT OR IGNORE INTO peptides (name, vial_mg, water_ml, dose, unit, freq, notes, schedule_json, sources_json)
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


def delete_profile(profile_id):
    """Delete a profile and (via FK cascade) its protocols and dose log.

    Refuses to delete the last remaining profile so the app always has at
    least one valid profile to fall back to. Returns False if refused.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM profiles")
    if cursor.fetchone()["count"] <= 1:
        conn.close()
        return False
    cursor.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    conn.commit()
    conn.close()
    return True


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


def get_user_protocol_by_id(protocol_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_protocols WHERE id = ?", (protocol_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["schedule"] = json.loads(d["schedule_json"]) if d["schedule_json"] else []
        d["sources"] = json.loads(d["sources_json"]) if d["sources_json"] else []
        return d
    return None


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


# Dose Log Functions
def log_dose(profile_id, protocol_id, peptide_name, dose_amount, dose_unit, notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO dose_log (profile_id, protocol_id, peptide_name, dose_amount, dose_unit, notes)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (profile_id, protocol_id, peptide_name, dose_amount, dose_unit, notes))
    conn.commit()
    conn.close()


def get_dose_log(profile_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dose_log WHERE profile_id = ? ORDER BY taken_at DESC", (profile_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_dose_log_entry(log_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dose_log WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()


def get_protocol_adherence(profile_id):
    """Compute a best-effort adherence percentage per protocol for a profile.

    Adherence is a heuristic: it parses the protocol's free-text frequency
    (e.g. "3x weekly") into an expected weekly dose count via
    calc.parse_weekly_frequency, and compares it to how many dose_log
    entries exist since the protocol was created. Unparseable frequencies
    or brand-new protocols report adherence_pct=None ("not measurable")
    rather than guessing.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, peptide_name, frequency, created_at FROM user_protocols WHERE profile_id = ? ORDER BY peptide_name ASC",
        (profile_id,)
    )
    protocols = cursor.fetchall()

    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive, to match SQLite's UTC CURRENT_TIMESTAMP strings
    result = []
    for p in protocols:
        cursor.execute("SELECT COUNT(*) as count FROM dose_log WHERE protocol_id = ?", (p["id"],))
        logged_count = cursor.fetchone()["count"]

        days_elapsed = 0.0
        if p["created_at"]:
            try:
                created_dt = datetime.strptime(p["created_at"], "%Y-%m-%d %H:%M:%S")
                days_elapsed = max(0.0, (now - created_dt).total_seconds() / 86400.0)
            except ValueError:
                days_elapsed = 0.0

        weekly_expected = calc.parse_weekly_frequency(p["frequency"] or "")
        adherence_pct = calc.adherence_percent(logged_count, weekly_expected, days_elapsed)

        result.append({
            "protocol_id": p["id"],
            "peptide_name": p["peptide_name"],
            "frequency": p["frequency"],
            "logged_count": logged_count,
            "adherence_pct": adherence_pct,
        })

    conn.close()
    return result


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
                conc_mg_ml = calc.concentration_mg_ml(p['vial_mg'], p['water_ml'])
                conc_mcg_ml = conc_mg_ml * 1000.0
                dose_mg = calc.dose_to_mg(p['target_dose'], p['dose_unit'])
                vol_ml = calc.draw_volume_ml(dose_mg, conc_mg_ml)
                units = calc.syringe_units(vol_ml)
                
                f.write(f"• Vial Size:           {p['vial_mg']:.1f} mg\n")
                f.write(f"• BAC Water Added:     {p['water_ml']:.1f} mL\n")
                f.write(f"• Solution Strength:   {conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL)\n")
                f.write(f"• Prescribed Dose:     {p['target_dose']} {p['dose_unit']} ({p['frequency']})\n")
                f.write(f"• U-100 Syringe Draw:  {units:.1f} Units ({vol_ml:.3f} mL)\n")
                f.write(f"• Clinical Notes:      {p['notes']}\n")
                
                if p['schedule']:
                    f.write("\n  Titration Schedule:\n")
                    phase_width = max(20, max((len(phase) for phase, _, _ in p['schedule']), default=20))
                    header = f"  {'Phase':<{phase_width}} | {'Dose':<10} | {'Syringe Draw':<15}"
                    f.write(header + "\n")
                    f.write("  " + "-" * (len(header) - 2) + "\n")
                    for phase, d_val, u_unit in p['schedule']:
                        d_mg = calc.dose_to_mg(d_val, u_unit)
                        v_ml = calc.draw_volume_ml(d_mg, conc_mg_ml)
                        u_draw = calc.syringe_units(v_ml)
                        d_str = f"{d_val:.0f} mcg" if u_unit == 'mcg' else f"{d_val:.2f} mg"
                        f.write(f"  {phase:<{phase_width}} | {d_str:<10} | {u_draw:.1f} Units\n")
                        
                if p['sources']:
                    f.write("\n  Scientific Citations & Literature:\n")
                    for s in p['sources']:
                        f.write(f"  - {s['title']} (PMID: {s['pmid']})\n")
                        f.write(f"    URL: {s['url']}\n")
                        
                f.write("\n" + "=" * 72 + "\n\n")

        dose_log = get_dose_log(profile_id)[:10]
        if dose_log:
            f.write("RECENT DOSE LOG (Last 10 Entries)\n")
            f.write("-" * 72 + "\n")
            for entry in dose_log:
                notes_suffix = f" — {entry['notes']}" if entry['notes'] else ""
                f.write(f"  {entry['taken_at']}  {entry['peptide_name']}: {entry['dose_amount']} {entry['dose_unit']}{notes_suffix}\n")
            f.write("\n" + "=" * 72 + "\n")

    return filename


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
