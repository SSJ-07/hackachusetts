# sources.md — fact-check list for FINAL-slot-to-stop.md

Every `(verify)` claim in `final_plan/FINAL-slot-to-stop.md`, with a candidate
authoritative source and a verification status. Guardrail: every on-screen number
must carry a source + vintage, or be flagged `unsourced`. Nothing here is asserted
as a finding until status = `verified` by a human against the primary source.

Status values: `verified` · `needs-manual-verification` · `unsourced`

---

## 1. FIT-positive colonoscopy follow-up rate
- **Claim (line 53):** "Many patients never complete the follow-up colonoscopy
  (published estimates often around half within 6 months)."
- **Candidate source:** *Delays in Diagnostic Colonoscopy After Positive FIT in an
  Integrated Healthcare System*, PubMed 39843790 — "Among 2157 patients with positive
  FIT, 50% received diagnostic colonoscopy within 6 months." See also PubMed 33452083
  (46.7% within 6 months) and the usual-care arm in AACR CEBP (65%).
- **URL:** https://pubmed.ncbi.nlm.nih.gov/39843790/
- **Vintage:** 2025 (indexed). Corroborated by multiple 2016–2025 cohorts.
- **Status:** needs-manual-verification
- **Note:** The "~half within 6 months" framing is well-supported, but the exact rate
  varies by cohort (46.7%–65% usual care). A human must pick ONE citable figure + its
  population and label it, not quote "half" as a universal finding.

## 2. Escort rule for sedated procedures
- **Claim (line 71):** "Most endoscopy units won't discharge a sedated patient to a
  bus, or even a taxi, alone (verify per clinic)."
- **Candidate source:** Facility-level discharge policies (ASGE/ambulatory-surgery
  sedation discharge guidance is the general basis; each endoscopy unit sets its own).
- **URL:** (none asserted — policy is per-facility)
- **Vintage:** n/a
- **Status:** needs-manual-verification
- **Note:** The escort requirement is already encoded in `planner/visit_rules.yaml`
  (colonoscopy escort_required=true). It is a logistics rule, not a clinical claim.
  Verify the exact discharge policy per target clinic (Baystate GI, etc.).

## 3. Baystate CHNA transport mention
- **Claim (line 80):** "Access to care and transportation show up again and again in
  western MA CHNAs (verify the Baystate CHNA text)."
- **Candidate source:** Baystate Health Community Health Needs Assessment (most recent
  cycle) + implementation strategy, published under IRS 501(r).
- **URL:** (locate the current CHNA PDF on baystatehealth.org — do not assume the URL)
- **Vintage:** most recent CHNA cycle (confirm year)
- **Status:** needs-manual-verification
- **Note:** A human must open the specific Baystate CHNA PDF and cite the page where
  transportation/access is named. Do not paraphrase as a finding without the page cite.

## 4. MassHealth ACO flexible-services scope
- **Claim (line 81):** "MassHealth ACOs ... run health-related social needs programs
  (verify the current flexible-services scope)."
- **Candidate source:** MassHealth ACO program documentation / Flexible Services
  program materials on mass.gov.
- **URL:** (locate current program page on mass.gov — do not assume the URL)
- **Vintage:** confirm current program year (scope changes between waiver periods)
- **Status:** needs-manual-verification
- **Note:** Flexible-services scope changes by 1115 waiver period. A human must confirm
  the CURRENT scope and its effective date before citing.

## 5. CMS Dialysis Facility data — shift fields
- **Claim (line 237):** CMS Dialysis Facility data provides "shift info (e.g., evening
  shifts) (verify which shift fields are present)."
- **Candidate source:** CMS Provider Data Catalog — Dialysis Facility datasets
  (data.cms.gov).
- **URL:** https://data.cms.gov (locate the exact Dialysis Facility dataset + its data
  dictionary — do not assume the file URL)
- **Vintage:** confirm dataset release date
- **Status:** needs-manual-verification
- **Note:** A human must open the dataset's data dictionary and confirm which shift
  columns actually exist (e.g. whether evening-shift availability is a field) before the
  planner relies on it for dialysis trip timing.

---

## MISSING / MANUAL-CHECK — what a human must verify and why

1. **FIT follow-up rate (claim 1):** needs a human to pick ONE citable figure + its
   population from the candidate studies. WHY MANUAL: "around half" spans 46.7%–65%
   across cohorts; stating a single rate as a finding requires choosing and labelling it.
2. **Escort rule (claim 2):** verify the discharge policy per target endoscopy unit.
   WHY MANUAL: policies are per-facility and not published as one citable number; may
   need a phone call to the clinic.
3. **Baystate CHNA (claim 3):** open the current Baystate CHNA PDF and cite the page.
   WHY MANUAL: the claim is about specific document text; requires reading that PDF.
4. **MassHealth flexible services (claim 4):** confirm current scope + effective date.
   WHY MANUAL: scope changes by waiver period; only the live mass.gov program page is
   authoritative, and the current one must be read, not assumed.
5. **CMS dialysis shift fields (claim 5):** confirm the exact columns in the dataset's
   data dictionary. WHY MANUAL: requires opening the specific dataset release and reading
   its schema; field presence cannot be assumed from the dataset name.

No URLs above are fabricated. Where I did not confirm an exact page/file, the URL is left
as a domain-level pointer with an explicit "locate ... do not assume" instruction.
