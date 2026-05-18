from rag.ingestion import ingest_document
from rag.retriever import get_or_create_collection

SEED_DOCUMENTS = [
    {
        "title": "AHA/ACC 2022 Heart Failure Management Guidelines",
        "document_type": "guideline",
        "source_url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001063",
        "collection": "clinical_guidelines",
        "content": """
Heart failure (HF) is a clinical syndrome caused by structural or functional cardiac abnormalities, resulting in elevated intracardiac pressures, reduced cardiac output, or both. It affects over 6.2 million Americans and is the leading cause of hospitalization in patients over 65.

CLASSIFICATION
Heart failure is classified by left ventricular ejection fraction (LVEF):
- HFrEF (Heart Failure with Reduced Ejection Fraction): LVEF <=40%
- HFmrEF (Heart Failure with Mildly Reduced EF): LVEF 41-49%
- HFpEF (Heart Failure with Preserved EF): LVEF >=50%

STAGES OF HEART FAILURE (ACC/AHA)
Stage A: At risk for HF but no structural heart disease or symptoms
Stage B: Structural heart disease but no symptoms of HF
Stage C: Structural heart disease with prior or current HF symptoms
Stage D: Refractory HF requiring advanced therapies

NYHA FUNCTIONAL CLASSIFICATION
Class I: No symptoms with ordinary activity
Class II: Slight limitation; comfortable at rest, symptoms with moderate exertion
Class III: Marked limitation; comfortable at rest, symptoms with minimal exertion
Class IV: Unable to perform any physical activity without symptoms; symptoms at rest

FIRST-LINE PHARMACOTHERAPY FOR HFrEF (Class I Recommendations)
The four pillars of guideline-directed medical therapy (GDMT) for HFrEF:

1. ACE Inhibitors (ACEi) or Angiotensin Receptor-Neprilysin Inhibitors (ARNI)
   - Sacubitril/valsartan (Entresto) is preferred over ACEi in ambulatory HFrEF patients
   - Target dose: sacubitril 97mg/valsartan 103mg twice daily
   - Do not use ARNI within 36 hours of ACEi due to angioedema risk
   - Alternative if ARNI not tolerated: lisinopril 20-40mg daily or enalapril 10-20mg twice daily

2. Beta-Blockers
   - Only three are proven to reduce mortality: carvedilol, metoprolol succinate (Toprol-XL), bisoprolol
   - Target: metoprolol succinate 200mg daily, carvedilol 25-50mg twice daily
   - Initiate at low dose during euvolemic state; do not start during acute decompensation

3. Mineralocorticoid Receptor Antagonists (MRA)
   - Spironolactone 25-50mg daily or eplerenone 50mg daily
   - Contraindicated if eGFR <30 mL/min/1.73m2 or potassium >5.0 mEq/L
   - Monitor potassium and renal function within 1-2 weeks of initiation

4. SGLT2 Inhibitors (new addition to GDMT, Class I 2022)
   - Dapagliflozin (Farxiga) 10mg daily or empagliflozin (Jardiance) 10mg daily
   - Reduce risk of CV death and worsening HF regardless of diabetes status
   - Benefit seen in HFrEF and HFmrEF; also beneficial in HFpEF (dapagliflozin)

DIURETICS FOR CONGESTION
- Loop diuretics (furosemide, torsemide, bumetanide) are the cornerstone for fluid management
- Furosemide starting dose: 20-40mg IV/PO; double dose if inadequate response in 2 hours
- Torsemide has superior bioavailability to furosemide (preferred in outpatient setting)
- Target: euvolemia with no orthopnea, minimal edema, dry weight at baseline

DEVICE THERAPY
- ICD implantation: LVEF <=35% on optimal GDMT for >=3 months, NYHA Class II-III, expected survival >1 year
- CRT: LVEF <=35%, LBBB with QRS >=150ms, NYHA Class II-IV on GDMT

MONITORING PARAMETERS
- BMP, BNP/NT-proBNP, and daily weights
- BNP <100 pg/mL or NT-proBNP <300 pg/mL suggests absence of acute HF
- Sodium restriction: <2g/day in symptomatic HF
- Fluid restriction: 1.5-2L/day in hyponatremia or refractory congestion
""",
    },
    {
        "title": "CDC/Sepsis Survivors Foundation: Sepsis Clinical Criteria and Management",
        "document_type": "guideline",
        "source_url": "https://www.cdc.gov/sepsis/clinical-tools/index.html",
        "collection": "clinical_guidelines",
        "content": """
Sepsis is a life-threatening organ dysfunction caused by a dysregulated host response to infection. It affects over 1.7 million adults annually in the United States, causing approximately 270,000 deaths.

DIAGNOSTIC CRITERIA

Sepsis (Sepsis-3 Definition, 2016):
Suspected or confirmed infection PLUS acute organ dysfunction, defined as:
- SOFA score increase of >=2 points from baseline
- SOFA accounts for: respiratory (PaO2/FiO2 ratio), coagulation (platelets), liver (bilirubin), cardiovascular (MAP/vasopressors), CNS (GCS), renal (creatinine/urine output)

Quick SOFA (qSOFA) - bedside screening tool:
- Altered mental status (GCS <15)
- Respiratory rate >=22 breaths/min
- Systolic blood pressure <=100 mmHg
qSOFA >=2 suggests high risk; proceed to full SOFA assessment

Septic Shock:
Sepsis PLUS vasopressor requirement to maintain MAP >=65 mmHg AND serum lactate >2 mmol/L despite adequate fluid resuscitation
In-hospital mortality exceeds 40%.

SURVIVING SEPSIS CAMPAIGN: 1-HOUR BUNDLE
Within the first hour of recognition:
1. Measure lactate level (remeasure if initial lactate >2 mmol/L)
2. Obtain blood cultures before antibiotics
3. Administer broad-spectrum antibiotics
4. Begin 30 mL/kg crystalloid for hypotension or lactate >=4 mmol/L
5. Apply vasopressors for hypotension during/after fluid resuscitation; target MAP >=65 mmHg

ANTIBIOTIC SELECTION
- Community-acquired sepsis: piperacillin-tazobactam 3.375g IV q6h OR cefepime 2g IV q8h
- Healthcare-associated/VAP risk: add vancomycin 25-30 mg/kg IV loading dose for MRSA coverage
- Fungal risk factors: add micafungin or fluconazole
- De-escalate based on culture results; target 7-10 days total duration for most infections

FLUID RESUSCITATION
- Initial bolus: 30 mL/kg balanced crystalloid (lactated Ringer's preferred over normal saline)
- Reassess after each 500 mL bolus using dynamic measures of fluid responsiveness
- Passive leg raise test: rise in cardiac output >10% predicts fluid responsiveness
- Avoid excess fluid: target CVP 8-12 mmHg (12-15 mmHg if mechanically ventilated)
- Albumin 4-5% may be considered if substantial crystalloid volumes required

VASOPRESSOR THERAPY
- First line: norepinephrine 0.01-3 mcg/kg/min; titrate to MAP >=65 mmHg
- Add vasopressin 0.03 units/min (fixed dose) to norepinephrine to reach MAP or reduce norepinephrine dose
- Epinephrine: add or substitute for norepinephrine if cardiac output remains low
- Dopamine: only in select patients with low risk of tachyarrhythmias; bradycardic septic shock

CORTICOSTEROIDS
- Hydrocortisone 200mg/day IV continuous infusion if norepinephrine >=0.25 mcg/kg/min for >=4 hours
- Taper steroids when vasopressors are no longer required

GLYCEMIC CONTROL
- Target glucose 140-180 mg/dL using insulin infusion protocol
- Avoid hypoglycemia; check glucose every 1-2 hours until stable, then every 4 hours

MECHANICAL VENTILATION IN SEPSIS-INDUCED ARDS
- Tidal volume: 6 mL/kg predicted body weight
- Plateau pressure <=30 cmH2O
- PEEP titrated to minimize FiO2 requirement while maintaining SpO2 88-95%
- Prone positioning >=16 hours/day if PaO2/FiO2 <150 on FiO2 >=0.6
""",
    },
    {
        "title": "NIH COVID-19 Treatment Guidelines: Antiviral and Therapeutic Agents",
        "document_type": "guideline",
        "source_url": "https://www.covid19treatmentguidelines.nih.gov/",
        "collection": "clinical_guidelines",
        "content": """
These guidelines are based on scientific evidence and expert opinion. They are updated frequently as new data emerge. The following reflects guidance for treatment of COVID-19 in non-hospitalized and hospitalized patients.

ANTIVIRAL THERAPY FOR NON-HOSPITALIZED PATIENTS

1. Nirmatrelvir/Ritonavir (Paxlovid) - Preferred First-Line
Indication: Mild-to-moderate COVID-19 in adults at high risk of progression to severe disease
Dosing: Nirmatrelvir 300mg + ritonavir 100mg orally twice daily for 5 days
Timing: Initiate within 5 days of symptom onset
Efficacy: 89% reduction in hospitalization/death in unvaccinated high-risk patients (EPIC-HR trial)
Contraindications and drug interactions:
  - Strong CYP3A inducers (rifampin, carbamazepine, phenytoin) are contraindicated
  - Significant interactions with: statins (hold simvastatin/lovastatin), immunosuppressants (tacrolimus, cyclosporine - monitor levels), anticoagulants (rivaroxaban - avoid; warfarin - monitor INR)
  - Renal dosing: eGFR 30-59: reduce nirmatrelvir to 150mg + ritonavir 100mg BID; eGFR <30: not recommended
Rebound: COVID-19 rebound occurs in ~10-15% of patients; re-treat if symptomatic, but not routinely

2. Remdesivir (Veklury) - Alternative for Non-Hospitalized Patients
Indication: High-risk non-hospitalized patients when nirmatrelvir/ritonavir is not suitable
Dosing: 200mg IV on Day 1, then 100mg IV on Days 2 and 3
Efficacy: 87% reduction in hospitalization/death (PINETREE trial)
Benefit requires administration within 7 days of symptom onset

3. Molnupiravir (Lagevrio) - Only if other agents unavailable
Less efficacious than nirmatrelvir/ritonavir; not recommended in pregnancy

TREATMENT FOR HOSPITALIZED PATIENTS

Patients Not Requiring Supplemental Oxygen:
- Remdesivir 200mg IV Day 1, then 100mg IV Days 2-5
- Duration: 5 days (can extend to 10 days if no clinical improvement)

Patients Requiring Conventional Oxygen:
- Remdesivir (as above) PLUS
- Dexamethasone 6mg IV/PO daily for up to 10 days
- RECOVERY trial: dexamethasone reduced 28-day mortality by 35% in ventilated patients and 18% in patients on oxygen

Patients Requiring High-Flow Oxygen, Non-Invasive Ventilation, or ICU:
- Dexamethasone 6mg daily (up to 10 days)
- Baricitinib 4mg PO daily for up to 14 days (COV-BARRIER trial: reduced mortality vs. standard of care)
- Alternative: tocilizumab 8mg/kg IV (max 800mg) for elevated inflammatory markers (CRP >=75 mg/L); most benefit in patients on dexamethasone with rapid oxygen escalation

ANTICOAGULATION
- All hospitalized COVID-19 patients: prophylactic anticoagulation (enoxaparin, fondaparinux, or UFH)
- Critically ill patients: prophylactic over therapeutic dosing (ATTACC/ACTIV-4a/REMAP-CAP)
- Therapeutic anticoagulation if new VTE diagnosed during hospitalization

MONITORING
- Monitor LFTs, renal function, CBC during remdesivir treatment
- Glucose monitoring with dexamethasone
- D-dimer, ferritin, CRP, IL-6 as inflammatory markers
""",
    },
    {
        "title": "WHO Model List of Essential Medicines - Anticoagulants, Antimicrobials and Selected Agents",
        "document_type": "guideline",
        "source_url": "https://www.who.int/publications/i/item/WHO-MHP-HPS-EML-2023.02",
        "collection": "clinical_guidelines",
        "content": """
The WHO Model List of Essential Medicines (EML) identifies medicines that satisfy priority health care needs. The following summarizes essential antimicrobials and selected critical care agents from the 23rd edition (2023).

MEDICINES AFFECTING THE BLOOD - MEDICINES AFFECTING COAGULATION
The WHO Model List of Essential Medicines includes several medicines affecting coagulation, including anticoagulants, reversal agents, and haemostatic agents. Listed anticoagulants include:
- Enoxaparin: listed with therapeutic alternatives dalteparin and nadroparin, including quality-assured biosimilars. Dosage forms include injection in ampoule or pre-filled syringe: 20 mg/0.2 mL, 40 mg/0.4 mL, 60 mg/0.6 mL, 80 mg/0.8 mL, 100 mg/1 mL, 120 mg/0.8 mL, and 150 mg/1 mL.
- Heparin sodium: listed as injection 1000 IU/mL, 5000 IU/mL, and 20 000 IU/mL in 1 mL ampoule.
- Warfarin: listed as tablet 1 mg, 2 mg, and 5 mg as sodium. Warfarin also appears on the complementary list with tablet strengths 0.5 mg, 1 mg, 2 mg, and 5 mg.
- Dabigatran is included among medicines affecting coagulation; apixaban, edoxaban, and rivaroxaban are noted as alternatives in this class.

Other medicines affecting coagulation on the WHO list include desmopressin, emicizumab, phytomenadione, protamine sulfate, and tranexamic acid. Protamine sulfate is used as a reversal agent for heparin effect, while phytomenadione is vitamin K therapy relevant to warfarin reversal. The WHO Model List is a selection and access document; it does not replace local anticoagulation protocols, renal dosing guidance, contraindication screening, or monitoring requirements such as INR monitoring for warfarin.

ANTIBACTERIALS - ACCESS GROUP (First-line, widely available)

Beta-Lactams:
- Amoxicillin: 250mg, 500mg tablets; 125mg/5mL suspension. Use: community-acquired pneumonia, otitis media, sinusitis, UTI
- Amoxicillin/clavulanic acid: 500mg/125mg tablets. Use: beta-lactamase producing organisms
- Ampicillin: 250mg capsules; 500mg powder for injection. Use: listeria, enterococcal infections, empiric meningitis coverage
- Benzylpenicillin (penicillin G): 600mg powder for injection. Use: streptococcal infections, syphilis, meningococcal meningitis
- Cloxacillin: 500mg capsules; 500mg powder for injection. Use: staphylococcal infections (non-MRSA)
- Piperacillin/tazobactam: 4g/0.5g powder for injection. Use: hospital-acquired infections, febrile neutropenia

Cephalosporins:
- Cefazolin: 1g powder for injection. Use: surgical prophylaxis, streptococcal/staphylococcal infections
- Ceftriaxone: 250mg, 1g powder for injection. Use: community-acquired pneumonia, meningitis, gonorrhea, typhoid
- Ceftazidime: 1g, 2g powder for injection. Use: Pseudomonas infections, nosocomial gram-negatives
- Cefepime: 1g powder for injection. Use: febrile neutropenia, nosocomial infections with Pseudomonas risk

Carbapenems (WATCH group - use with stewardship oversight):
- Imipenem/cilastatin: 500mg powder. Use: MDR gram-negative infections, ESBL-producing organisms
- Meropenem: 500mg, 1g powder. Use: severe nosocomial infections, meningitis (preferred over imipenem)

Macrolides:
- Azithromycin: 250mg, 500mg tablets; 200mg/5mL suspension. Use: atypical pneumonia, chlamydia, MAC prophylaxis
- Clarithromycin: 250mg, 500mg tablets. Use: H. pylori eradication, atypical pneumonia

Fluoroquinolones (WATCH group):
- Ciprofloxacin: 250mg, 500mg tablets; 2mg/mL IV solution. Use: UTI, typhoid, anthrax, traveler's diarrhea
- Levofloxacin: 250mg, 500mg tablets; 5mg/mL IV solution. Use: community-acquired pneumonia, complicated UTI

Glycopeptides (WATCH group):
- Vancomycin: 250mg capsules; 500mg powder for IV. Use: MRSA, C. difficile (oral), serious gram-positive infections
- Target trough (conventional dosing): 15-20 mg/L; or AUC/MIC-guided dosing preferred

Oxazolidinones (RESERVE group):
- Linezolid: 600mg tablets; 2mg/mL IV. Use: MRSA, VRE, MDR gram-positive infections refractory to vancomycin

ANTIFUNGALS:
- Fluconazole: 50mg, 200mg tablets; 2mg/mL IV. Use: candidiasis (not effective for non-albicans species), cryptococcal meningitis prophylaxis
- Amphotericin B (deoxycholate): 50mg powder. Use: invasive fungal infections, cryptococcal meningitis, leishmania
- Micafungin: 50mg powder. Use: invasive candidiasis, esophageal candidiasis; preferred in hepatic impairment
- Voriconazole: 50mg, 200mg tablets; 200mg powder for IV. Use: invasive aspergillosis (first-line), fluconazole-resistant Candida

ANTIVIRALS:
- Acyclovir: 200mg, 400mg, 800mg tablets; 250mg powder for IV. Use: HSV, VZV infections; IV for encephalitis
- Oseltamivir: 30mg, 45mg, 75mg capsules. Use: influenza treatment (within 48h onset) and prophylaxis
- Tenofovir disoproxil fumarate: 300mg tablet. Use: HIV/HBV treatment (component of first-line ART regimens)

ANTIMYCOBACTERIALS (TB treatment):
First-line: isoniazid, rifampicin, pyrazinamide, ethambutol
Standard 6-month regimen: 2 months HRZE + 4 months HR
Drug-resistant TB: bedaquiline + linezolid + pretomanid (BPaL regimen for XDR-TB)
""",
    },
    {
        "title": "ACC/AHA 2023 Guidelines on Atrial Fibrillation: Diagnosis and Management",
        "document_type": "guideline",
        "source_url": "https://www.jacc.org/doi/10.1016/j.jacc.2023.08.017",
        "collection": "clinical_guidelines",
        "content": """
Atrial fibrillation (AF) is the most common sustained cardiac arrhythmia, affecting over 5 million Americans. It is associated with a 5-fold increased risk of stroke and 3-fold increased risk of heart failure.

CLASSIFICATION
- Paroxysmal AF: terminates spontaneously or with intervention within 7 days of onset
- Persistent AF: continuous AF sustained >7 days
- Long-standing persistent AF: continuous AF of >12 months duration
- Permanent AF: AF accepted by patient and clinician; rhythm control no longer pursued

DIAGNOSIS
- 12-lead ECG: irregularly irregular rhythm, absence of distinct P waves, variable ventricular rate
- Holter monitoring (24-48h) or event monitor (14-30 days) for intermittent symptoms
- Smartwatch/wearable screening: single-lead ECG devices can detect AF; confirm with 12-lead ECG

STROKE RISK STRATIFICATION: CHA2DS2-VASc Score
- Congestive heart failure: 1 point
- Hypertension: 1 point
- Age >=75: 2 points
- Diabetes mellitus: 1 point
- Stroke/TIA/thromboembolism history: 2 points
- Vascular disease (prior MI, PAD, aortic plaque): 1 point
- Age 65-74: 1 point
- Sex category female: 1 point (does not add risk if no other factors)

Anticoagulation recommendations:
- Score >=2 in males, >=3 in females: anticoagulation recommended
- Score 1 in males: anticoagulation reasonable (individualize)
- Score 0 in males or 1 in females (female sex only): no anticoagulation

ANTICOAGULATION SELECTION
Direct Oral Anticoagulants (DOACs) - preferred over warfarin:
- Apixaban (Eliquis): 5mg twice daily; reduce to 2.5mg BID if >=2 of: age >=80, weight <=60kg, Cr >=1.5 mg/dL
- Rivaroxaban (Xarelto): 20mg daily with evening meal; reduce to 15mg daily if CrCl 15-50 mL/min
- Dabigatran (Pradaxa): 150mg twice daily; 75mg BID if CrCl 15-30 mL/min
- Edoxaban (Savaysa): 60mg daily; reduce to 30mg if CrCl 15-50 mL/min, weight <=60kg, or P-gp inhibitors

Warfarin: target INR 2.0-3.0; use if mechanical heart valve, severe mitral stenosis, or DOAC intolerance

RATE CONTROL
Target resting heart rate <110 bpm (lenient) or <80 bpm (strict, for symptomatic patients)
- Beta-blockers: metoprolol, carvedilol, bisoprolol (first-line; preferred in HFrEF)
- Non-dihydropyridine CCBs: diltiazem, verapamil (avoid in HFrEF with reduced EF)
- Digoxin: adjunct agent, especially in sedentary patients or HFrEF; target level 0.5-0.9 ng/mL
- Amiodarone: reserved for rate control when other agents fail

RHYTHM CONTROL
Cardioversion:
- Electrical cardioversion: biphasic shock 200J (synchronized); effective in 90% of cases
- Chemical cardioversion: flecainide or propafenone (pill-in-pocket, no structural heart disease)
- Anticoagulate for >=3 weeks before elective cardioversion if AF >48h or unknown duration

Antiarrhythmic drugs:
- No structural heart disease: flecainide, propafenone, dronedarone, sotalol
- With structural heart disease/HFrEF: amiodarone (most effective; toxicity limits long-term use)
- Dofetilide: in-hospital initiation required due to QT prolongation risk

Catheter Ablation:
- Pulmonary vein isolation (PVI) is the cornerstone
- Superior to antiarrhythmic drugs for maintaining sinus rhythm
- Recommended as first-line rhythm control in symptomatic AF with HFrEF
- Long-term success rate: ~70% single procedure, ~80% after repeat procedures
""",
    },
]


def seed_if_empty():
    collection = get_or_create_collection("clinical_guidelines")
    if collection.count() > 0:
        print(f"Collection already has {collection.count()} chunks. Skipping seed.")
        return

    print("Seeding clinical guidelines collection...")
    for doc in SEED_DOCUMENTS:
        result = ingest_document(
            title=doc["title"],
            content=doc["content"],
            document_type=doc["document_type"],
            source_url=doc["source_url"],
            collection_name=doc["collection"],
        )
        print(f"  Ingested '{doc['title']}': {result['chunks_created']} chunks")
    print("Seed complete.")
