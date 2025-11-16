TONE_OPTIONS = [
    "Non-technical and Accessible",
    "Formal and Objective",
    "Precise and Data-Driven",
    "Impartial and Compliant",
    "Concise and Analytical",
    "Professional and Scientific",
    "Narrative and Insightful",
    "Clinically Detailed but Relatable",
    "Evidence-Based and Persuasive"
]

CONTENT_HIERARCHY = {
    "Clinical Trial Report": {
        "Promotional - Commercial": {
            "Regulatory Authorities (e.g., FDA, EMA)": TONE_OPTIONS,
            "Clinical Research Organizations (CROs)": TONE_OPTIONS,
            "Medical Writers, Pharmacovigilance & Regulatory Affairs Teams": TONE_OPTIONS,
            "Sponsors/Pharma Companies": TONE_OPTIONS
        },
        "Non promotional - Commercial": {
            "Regulatory Authorities (e.g., FDA, EMA)": TONE_OPTIONS,
            "Clinical Research Organizations (CROs)": TONE_OPTIONS,
        },
        "Promotional - Scientific": {
            "Sponsors/Pharma Companies": TONE_OPTIONS,
            "Medical Writers, Pharmacovigilance & Regulatory Affairs Teams": TONE_OPTIONS
        },
        "Non promotional - Scientific": {
            "Regulatory Authorities (e.g., FDA, EMA)": TONE_OPTIONS,
            "CROs": TONE_OPTIONS
        }
    },
    "Clinical Summaries": {
        "Non promotional - Scientific": {
            "Regulatory Authorities (e.g., FDA, EMA)": TONE_OPTIONS,
            "Medical Affairs, Scientific Teams & MSLs": TONE_OPTIONS,
            "HTA Bodies (Health Technology Assessment)": TONE_OPTIONS
        }
    },
    "Patient Case Studies": {
        "Promotional - Scientific": {
            "Healthcare Professionals (HCPs)": TONE_OPTIONS,
            "Sales Representatives": TONE_OPTIONS,
            "Conference Attendees & Journal Readers": TONE_OPTIONS
        }
    },
    "Plain Language Summaries": {
        "Non promotional - Scientific": {
            "Patients & Caregivers": TONE_OPTIONS,
            "Patient Advocacy Groups": TONE_OPTIONS,
            "General Public & Media": TONE_OPTIONS,
            "Ethics Committees": TONE_OPTIONS
        }
    }
}
