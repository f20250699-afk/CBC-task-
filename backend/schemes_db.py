# Standard scheme definitions based on the KALAM architecture

AMBIGUITIES_TEXT = {
    "A01_LESSEE_FARMER": "PM-KISAN rules for lessee farmers are state-dependent and formally ambiguous at center.",
    "A04_SECC_STALENESS": "SECC 2011 data is outdated; families who became poor after 2011 may be missed.",
    "A10_WIDOW_REMARRIAGE_STATUS": "Remarriage status is often not updated in government records, leading to irregular benefits.",
    "A12_AADHAAR_NO_BANK": "User has Aadhaar but no linked bank account, blocking DBT payments."
}

FIELD_GUIDANCE = {
    "aadhaar": "Nearest Aadhaar centre ya post office mein enroll karein",
    "bank_account": "PMJDY ke liye kisi bhi nationalized bank mein zero-balance account kholein",
    "bank_account_linked_aadhaar": "Bank branch mein jakar Aadhaar link karwayein",
    "land_ownership_status": "Apne tehsil / patwari office se certified copy lein",
    "secc_2011_listed": "pmjay.gov.in par apna naam check karein ya 14555 call karein",
    "bpl_certificate": "Gram Panchayat / Ward office se BPL certificate lein",
    "disability_certificate": "Jile ke SADM office mein jaein",
    "age": "Janm praman patra ya school certificate pratyashit karein",
    "annual_household_income": "Tehsildar se income certificate banwayein",
    "marital_status": "Status confirm karein",
    "housing_status": "Ghar ki sthiti bataein",
    "occupation": "Apna occupation bataein"
}

SCHEMES = [
    {
        "scheme_id": "S01",
        "scheme_name": "PM-KISAN",
        "ministry": "Agriculture",
        "benefit_summary": "Rs. 6000/year",
        "hard_conditions": [
            {"field": "occupation", "op": "eq", "value": "farmer", "source_clause": "Must be farmer"},
            {"field": "land_ownership_status", "op": "in", "value": ["owner", "joint_owner"], "source_clause": "Must be a landowner"}
        ],
        "soft_conditions": [],
        "exclusions": [
            {"field": "income_tax_payer", "op": "eq", "value": True, "source_clause": "Income tax payers are excluded"}
        ],
        "required_docs": ["aadhaar", "land_record", "bank_account"],
        "prerequisites": [],
        "benefit_type": "cash_transfer",
        "next_action": "Apply at PM-KISAN Portal or local CSC",
        "ambiguity_flags": ["A01_LESSEE_FARMER"]
    },
    {
        "scheme_id": "S02",
        "scheme_name": "MGNREGA",
        "ministry": "Rural Development",
        "benefit_summary": "100 Job Days",
        "hard_conditions": [
            {"field": "residence_type", "op": "eq", "value": "rural", "source_clause": "Rural area only"},
            {"field": "age", "op": "gte", "value": 18, "source_clause": "Must be 18+"}
        ],
        "soft_conditions": [],
        "exclusions": [
            {"field": "residence_type", "op": "eq", "value": "urban", "source_clause": "Urban areas excluded"}
        ],
        "required_docs": ["aadhaar"],
        "prerequisites": [],
        "benefit_type": "employment",
        "next_action": "Visit Gram Panchayat for Job Card",
        "ambiguity_flags": []
    },
    {
        "scheme_id": "S03",
        "scheme_name": "PMJAY",
        "ministry": "Health",
        "benefit_summary": "Rs. 5L Insurance",
        "hard_conditions": [
            {"field": "secc_2011_listed", "op": "eq", "value": True, "source_clause": "Must be in SECC list"}
        ],
        "soft_conditions": [],
        "exclusions": [],
        "required_docs": ["aadhaar"],
        "prerequisites": [],
        "benefit_type": "insurance",
        "next_action": "Check pmjay.gov.in portal",
        "ambiguity_flags": ["A04_SECC_STALENESS"]
    },
    {
        "scheme_id": "S08",
        "scheme_name": "IGNWPS (Widow)",
        "ministry": "Rural Development",
        "benefit_summary": "Monthly Pension",
        "hard_conditions": [
            {"field": "age", "op": "gte", "value": 40, "source_clause": "Age must be 40+"},
            {"field": "marital_status", "op": "eq", "value": "widow", "source_clause": "Status must be widow"}
        ],
        "soft_conditions": [],
        "exclusions": [
            {"field": "remarried", "op": "eq", "value": True, "source_clause": "Remarriage terminates widow status"}
        ],
        "required_docs": ["aadhaar", "death_certificate"],
        "prerequisites": [],
        "benefit_type": "pension",
        "next_action": "Visit Block Development Officer",
        "ambiguity_flags": ["A10_WIDOW_REMARRIAGE_STATUS"]
    },
    {
        "scheme_id": "S04",
        "scheme_name": "PMAY-G",
        "ministry": "Rural Development",
        "benefit_summary": "Housing Subsidy",
        "hard_conditions": [
            {"field": "residence_type", "op": "eq", "value": "rural", "source_clause": "Rural only"},
            {"field": "housing_status", "op": "in", "value": ["houseless", "kaccha_house"], "source_clause": "Must not have pucca house"}
        ],
        "soft_conditions": [],
        "exclusions": [
            {"field": "housing_status", "op": "eq", "value": "pucca_house", "source_clause": "Pucca house owners excluded"}
        ],
        "required_docs": ["aadhaar", "bank_account"],
        "prerequisites": [],
        "benefit_type": "housing",
        "next_action": "Contact Gram Panchayat",
        "ambiguity_flags": []
    },
    {
        "scheme_id": "S05",
        "scheme_name": "PM-SVANidhi",
        "ministry": "Housing and Urban Affairs",
        "benefit_summary": "Working Capital Loan",
        "hard_conditions": [
            {"field": "occupation", "op": "eq", "value": "street_vendor", "source_clause": "Must be a street vendor"}
        ],
        "soft_conditions": [],
        "exclusions": [],
        "required_docs": ["aadhaar", "vending_certificate"],
        "prerequisites": [],
        "benefit_type": "loan",
        "next_action": "Apply at PM SVANidhi Portal",
        "ambiguity_flags": []
    },
    {
        "scheme_id": "S06",
        "scheme_name": "PM-MVY",
        "ministry": "Women and Child Development",
        "benefit_summary": "Maternity Benefit Rs. 5000",
        "hard_conditions": [
            {"field": "gender", "op": "eq", "value": "female", "source_clause": "Must be female"}
        ],
        "soft_conditions": [],
        "exclusions": [],
        "required_docs": ["aadhaar", "mcp_card"],
        "prerequisites": [],
        "benefit_type": "cash_transfer",
        "next_action": "Register at Anganwadi Centre",
        "ambiguity_flags": []
    },
    {
        "scheme_id": "S07",
        "scheme_name": "PM-SYM",
        "ministry": "Labour and Employment",
        "benefit_summary": "Pension Rs. 3000/month",
        "hard_conditions": [
            {"field": "age", "op": "gte", "value": 18, "source_clause": "Age 18-40"},
            {"field": "age", "op": "lte", "value": 40, "source_clause": "Age 18-40"}
        ],
        "soft_conditions": [],
        "exclusions": [
            {"field": "income_tax_payer", "op": "eq", "value": True, "source_clause": "Income tax payers excluded"}
        ],
        "required_docs": ["aadhaar", "savings_bank_account"],
        "prerequisites": [],
        "benefit_type": "pension",
        "next_action": "Visit nearest CSC",
        "ambiguity_flags": []
    },
    {
        "scheme_id": "S09",
        "scheme_name": "Atal Pension Yojana",
        "ministry": "Finance",
        "benefit_summary": "Guaranteed Pension",
        "hard_conditions": [
            {"field": "age", "op": "gte", "value": 18, "source_clause": "Age 18-40"},
            {"field": "age", "op": "lte", "value": 40, "source_clause": "Age 18-40"},
            {"field": "bank_account_linked_aadhaar", "op": "eq", "value": True, "source_clause": "Must have linked bank account"}
        ],
        "soft_conditions": [],
        "exclusions": [],
        "required_docs": ["aadhaar", "savings_bank_account"],
        "prerequisites": [],
        "benefit_type": "pension",
        "next_action": "Apply through your bank branch",
        "ambiguity_flags": []
    },
    {
        "scheme_id": "S10",
        "scheme_name": "PM-JDY",
        "ministry": "Finance",
        "benefit_summary": "Zero Balance Bank Account",
        "hard_conditions": [],
        "soft_conditions": [],
        "exclusions": [],
        "required_docs": ["aadhaar"],
        "prerequisites": [],
        "benefit_type": "financial_inclusion",
        "next_action": "Visit any nationalised bank branch",
        "ambiguity_flags": []
    },
    {
        "scheme_id": "S11",
        "scheme_name": "PMAY-U",
        "ministry": "Housing and Urban Affairs",
        "benefit_summary": "Urban Housing Subsidy",
        "hard_conditions": [
            {"field": "residence_type", "op": "eq", "value": "urban", "source_clause": "Urban only"},
            {"field": "housing_status", "op": "in", "value": ["houseless", "kaccha_house"], "source_clause": "Must not have pucca house"}
        ],
        "soft_conditions": [],
        "exclusions": [
            {"field": "housing_status", "op": "eq", "value": "pucca_house", "source_clause": "Pucca house owners excluded"}
        ],
        "required_docs": ["aadhaar", "income_certificate"],
        "prerequisites": [],
        "benefit_type": "housing",
        "next_action": "Apply at PMAY(U) Portal",
        "ambiguity_flags": []
    },
    {
        "scheme_id": "S12",
        "scheme_name": "ALIMCO Assistance",
        "ministry": "Social Justice",
        "benefit_summary": "Aids for Persons with Disabilities",
        "hard_conditions": [],
        "soft_conditions": [],
        "exclusions": [],
        "required_docs": ["aadhaar", "disability_certificate", "income_certificate"],
        "prerequisites": [],
        "benefit_type": "in_kind",
        "next_action": "Contact District Welfare Officer",
        "ambiguity_flags": []
    }
]
