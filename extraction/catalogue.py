"""Field catalogue, doc types and authority tiers, mirroring docs/fact-record-schema.md."""

CORE_FIELDS = ("price", "rent", "tenure", "transaction_type", "floor_area", "epc_rating", "parking")

# field -> {qualifier_key: allowed values (None = free text)}
FIELDS: dict[str, dict[str, tuple | None]] = {
    "price": {"type": ("guide", "asking", "offers_over", "offers_in_region", "poa", "contracted")},
    "rent": {"period": ("annum", "month", "week"), "per": ("unit", "floor")},
    "incentive": {"kind": ("stamp_duty", "deposit_contribution", "furniture", "other")},
    "tenure": {},
    "transaction_type": {},
    "lease_length": {"measure": ("years_remaining", "term_from")},
    "ground_rent": {"period": ("annum", "month", "week")},
    "service_charge": {"period": ("annum", "month", "week"), "year": None},
    # scope: whole | floor:<name> | unit | part:<name> | house_type:<id> | plot:<id>
    "floor_area": {"basis": ("NIA", "GIA", "IPMS", "EPC", "unspecified"), "scope": None},
    "site_area": {},
    "room_dimension": {"room": None},
    "bedrooms": {"room": None},
    "bathrooms": {"room": None},
    "bathroom_fixture": {"room": None},
    "finish": {"item": None},
    "epc_rating": {"type": ("current", "potential")},
    "heating": {},
    "solar": {},
    "parking": {"scope": ("total", "per_unit", "per_floor")},
    "ev_charging": {},
    "completion_date": {"basis": ("contract", "programme", "marketing")},
    "build_stage": {"basis": ("contract", "programme", "marketing")},
    "warranty": {},
    "ews1": {},
    "cladding": {},
    "broadband": {"basis": ("confirmed", "predicted", "development_claim")},
    "covenant": {},
    "planning_condition": {},
    "pets": {},
    "subletting": {},
    "availability": {"scope": None},
    "step_free": {},
    "lift": {},
    "door_width": {},
    "management_company": {"basis": ("interim", "long_term")},
    "listed_status": {},
}

TENURES = ("freehold", "leasehold", "share_of_freehold", "commonhold")
TRANSACTION_TYPES = ("for_sale", "to_let", "for_sale_or_to_let")
EPC_BANDS = ("A+", "A", "B", "C", "D", "E", "F", "G")
PARKING_KINDS = ("allocated", "garage", "on_street", "permit", "unspecified")
AVAILABILITY = ("available", "reserved", "under_offer", "sold", "let")
FACT_SCOPES = ("development", "building", "unit", "plot", "house_type")

DOC_TYPE_TIER = {
    "title_register_current": 1, "lease": 1, "sale_contract": 1, "reservation_agreement": 1, "deed_of_grant": 1,
    "land_registry_title_extract": 2, "epc_certificate": 2, "price_paid_record": 2,
    "signed_specification": 3, "schedule_of_finishes": 3, "measured_survey": 3, "floorplan_measured": 3,
    "access_statement": 3, "as_built_pack": 3, "ews1": 3, "building_safety_case": 3,
    "warranty_certificate": 3, "broadband_confirmation": 3, "parking_allocation_schedule": 3,
    "price_list_signed": 4, "developer_instruction": 4,
    "brochure": 5, "particulars": 5, "floorplan_marketing": 5,
    "portal_listing": 6, "crm_note": 6, "verbal_note": 6,
}

MATERIAL_FIELDS = ("price", "rent", "tenure", "floor_area")

SQ_M_TO_SQ_FT = 10.7639
UNIT_MISMATCH_TOLERANCE = 0.02
