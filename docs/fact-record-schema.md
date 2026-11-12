# Verified fact record: data schema (v0.2, 12 Nov 2026)

Aligned to the spec's Fact catalogue and Contradiction handling sections.
The voice agent quotes only a field whose current fact is `verified`. A field that is
`conflicting` or `pending` is never quoted.

## Entities

```
development 1──* unit (unit may have parent_unit_id; plots and house types are units)
development 1──* document 1──* page
source_record (non-PDF rows: Price Paid, portal listing, CRM note)
fact *──1 unit, fact *──1 (document+page OR source_record)
contradiction 1──* fact
verification *──1 fact / contradiction
fact_record_version 1──* fact  (snapshot of a unit's verified record)
```

---

### development
| column | type | notes |
|---|---|---|
| development_id | text PK | slug, e.g. `kelso-villa-ba1-3au` |
| name | text | |
| address_line | text | |
| postcode | text | |
| uprn | text null | for Land Registry and EPC register matching |

### unit
A unit is anything that can carry its own facts: a whole building, a floor, a flat, a plot, or a house type.
| column | type | notes |
|---|---|---|
| unit_id | text PK | `kelso-villa-ba1-3au:whole`, `...:lower-ground` |
| development_id | FK | |
| label | text | |
| unit_kind | enum | `development`, `whole_building`, `floor`, `flat`, `house`, `plot`, `house_type`, `land` |
| parent_unit_id | FK null | a floor's parent is the whole building; a plot's parent can be its house type |
| entity_match_status | enum | `matched`, `unmatched`, `ambiguous`. Rule: never merge plots or types. |

### document
| column | type | notes |
|---|---|---|
| doc_id | text PK | |
| development_id | FK | |
| doc_type | enum | see the doc_type list below |
| authority_tier | int 1–6 | from the hierarchy below; set at ingest from doc_type |
| issuer_org | text | "Carter Jonas", "HM Land Registry", "EPC register", "NHBC" |
| issuer_role | enum | `developer`, `architect`, `sales_agent`, `letting_agent`, `conveyancer`, `managing_agent`, `official_register`, `warranty_provider`, `broadband_provider` |
| doc_date | date null | Null when not known. Never guess. |
| doc_date_source | enum null | `printed`, `file_metadata`, `register`, `manual` |
| register_date | date null | for tier-2 extracts: the date the register was read or the certificate was issued |
| is_signed | bool | true means a signed legal instrument or a signed specification or price list |
| supersedes_doc_id | FK null | set when a later document of the same issuer and type replaces this one |
| version_label | text null | e.g. `april_2026`, `october_2026` |
| source | enum | `real` or `synthetic` |
| file_uri, page_count, has_text_layer, sha256, ingested_at | | |

doc_type → default authority_tier
| tier | doc_type |
|---|---|
| 1 | `title_register_current`, `lease`, `sale_contract`, `reservation_agreement`, `deed_of_grant` |
| 2 | `land_registry_title_extract`, `epc_certificate` (`price_paid_record` is tier 2 but carries `as_at` = sale date) |
| 3 | `signed_specification`, `schedule_of_finishes`, `measured_survey`, `floorplan_measured`, `access_statement`, `as_built_pack`, `ews1`, `building_safety_case`, `warranty_certificate`, `broadband_confirmation`, `parking_allocation_schedule` |
| 4 | `price_list_signed`, `developer_instruction` |
| 5 | `brochure`, `particulars`, `floorplan_marketing` |
| 6 | `portal_listing`, `crm_note`, `verbal_note` |

### page
| doc_id FK, page_no int (PK together) | text | text_method `pdf_text`/`ocr`/`vision` | image_uri |

### source_record (for evidence that isn't a PDF)
| column | type | notes |
|---|---|---|
| source_record_id | text PK | e.g. Price Paid transaction id, listing URL and row |
| record_type | enum | `price_paid_record`, `portal_listing`, `crm_note`, `verbal_note` |
| authority_tier | int | 2 for Price Paid, 6 for the others |
| as_at | date | Price Paid: the sale date. Listing: the date scraped. |
| raw | jsonb | the original row |

### fact (one row per value found in one place)
| column | type | notes |
|---|---|---|
| fact_id | uuid PK | |
| unit_id | FK | |
| scope | enum | `development`, `building`, `unit`, `plot`, `house_type`. This is the scope stated in the source, not the scope we wish it had. |
| doc_id, page_no | FK null | for a PDF source |
| source_record_id | FK null | for a non-PDF source (exactly one of the two is set) |
| field | enum | see the field catalogue |
| qualifier | jsonb | depends on the field |
| value_raw | text | exactly as printed |
| value | jsonb | parsed |
| normalised | jsonb null | e.g. both sq ft and sq m |
| quote | text null | verbatim span; null only for structured records |
| as_at | date null | the date the fact was true per its source (doc_date or register_date) |
| authority_tier | int | copied from the source at insert time |
| extraction_method | enum | `llm_text`, `llm_vision`, `regex`, `manual`, `structured_import` |
| confidence | numeric 0–1 | |
| doc_error | bool | true when the source is internally wrong, e.g. a bad conversion |
| status | enum | `extracted`, `pending`, `conflicting`, `verified`, `rejected`, `superseded` |
| created_at | timestamptz | |

### contradiction
| column | type | notes |
|---|---|---|
| contradiction_id | uuid PK | |
| unit_id | FK | |
| field | enum | |
| qualifier_key | text | hash of qualifier + scope, so only like is compared with like |
| fact_ids | uuid[] | |
| type | enum | `true_conflict`, `version_supersession`, `unit_or_measurement_mismatch`, `scope_difference`, `plot_or_type_variation`, `stale_listing`, `official_record_mismatch` |
| candidate_fact_id | FK null | the fact the rule proposes as the winner |
| rule_applied | text | e.g. `higher_tier_wins`, `same_issuer_later_supersedes`, `normalise_and_label`, `keep_both_scoped`, `human_required` |
| requires_human | bool | always true for `true_conflict`, `official_record_mismatch`, any override of a higher tier, and any material field (price, tenure, area) |
| resolved_fact_id | FK null | |
| status | enum | `open`, `pending_signoff`, `resolved` |
| agent_script_state | enum | `do_not_quote_conflicting`, `do_not_quote_pending`, `quote_with_scope`, `quote_verified` |
| downstream_action | text null | e.g. `flag_listing_for_update`, `check_current_title` |
| created_at | timestamptz | |

### verification (the audit trail: who, when and why)
| column | type | notes |
|---|---|---|
| verification_id | uuid PK | |
| fact_id | FK null | |
| contradiction_id | FK null | |
| action | enum | `verify`, `reject`, `override_higher_tier`, `edit` |
| verified_by | text | |
| verified_at | timestamptz | |
| reason | text | required. The losing fact stays in history as `superseded` or `rejected`. |

### fact_record_version (the versioned set of facts for each unit)
| column | type | notes |
|---|---|---|
| unit_id | FK | |
| version | int | the primary key is (unit_id, version) |
| published_at | timestamptz | |
| published_by | text | |
| fact_ids | uuid[] | the verified fact for each (field, qualifier, scope) at publish time |
| open_fields | text[] | fields that are conflicting or pending at publish time; the voice agent says it can't confirm these |

The voice agent reads the latest `fact_record_version` for the unit and cites `as_at` and the source.

---

## Field catalogue

Fields marked ★ are Person A's core fields for tonight. The others are in the spec's catalogue
and the table structure already handles them; they only need extraction later.

| category | field | qualifier | value |
|---|---|---|---|
| Price and incentives | ★`price` | `{type: guide\|asking\|offers_over\|offers_in_region\|poa\|contracted}` | `{amount, currency}` |
| | `rent` | `{period: annum\|month\|week, per: unit\|floor}` | `{amount, currency}` |
| | `incentive` | `{kind: stamp_duty\|deposit_contribution\|furniture\|other}` | `{text, amount?}` |
| Tenure | ★`tenure` | none | `{tenure: freehold\|leasehold\|share_of_freehold\|commonhold}` |
| | `transaction_type` | none | `{type: for_sale\|to_let\|for_sale_or_to_let}` |
| | `lease_length` | `{measure: years_remaining\|term_from}` | `{years, start_date?}` |
| | `ground_rent` | `{period}` | `{amount, currency, review_terms?}` |
| | `service_charge` | `{period, year?}` | `{amount, currency}` |
| Areas | ★`floor_area` | `{basis: NIA\|GIA\|IPMS\|EPC\|unspecified, scope: whole\|floor:<name>\|unit}` | `{amount, unit: sq_ft\|sq_m}`; normalised `{sq_ft, sq_m}` |
| | `site_area` | none | `{amount, unit: acre\|hectare\|sq_m}` |
| | `room_dimension` | `{room}` | `{length, width, unit}` |
| Specification | `bedrooms`, `bathrooms`, `bathroom_fixture` | `{room?}` | `{count}` or `{fixture: bath\|shower\|both}` |
| | `finish` | `{item}` | `{text}` |
| Energy | ★`epc_rating` | `{type: current\|potential}` | `{band, score?, certificate_date?}` |
| | `heating`, `solar` | none | `{text}` |
| Parking | ★`parking` | `{scope: total\|per_unit\|per_floor}` | `{spaces, kind: allocated\|garage\|on_street\|permit\|unspecified}` |
| | `ev_charging` | none | `{status: installed\|promised\|none, count?}` |
| Completion | `completion_date`, `build_stage` | `{basis: contract\|programme\|marketing}` | `{date?, text}` |
| Warranty | `warranty` | none | `{provider, years, certificate_in_place: bool}` |
| Building safety | `ews1`, `cladding` | none | `{rating?, date, text}`. Voice agent never guesses here. |
| Broadband | `broadband` | `{basis: confirmed\|predicted\|development_claim}` | `{type, speed?}` |
| Restrictions | `covenant`, `planning_condition` | none | `{text}` |
| Pets and subletting | `pets`, `subletting` | none | `{allowed: yes\|no\|with_consent, text}` |
| Availability | `availability` | none | `{status: available\|reserved\|under_offer\|sold\|let}` |
| Accessibility | `step_free`, `lift`, `door_width` | none | `{value, text}` |
| Management | `management_company` | `{basis: interim\|long_term}` | `{name, company_number?}` |

Area and unit rules:
- Basis and scope are part of the qualifier, so net and gross area, and whole-building and per-floor area, are never compared.
- Store the stated unit in `value` and both converted units in `normalised` (1 sq m = 10.7639 sq ft, rounded to 1 decimal place).
- If a document prints both units and they disagree by more than 2% after conversion, set `doc_error = true` and open a `unit_or_measurement_mismatch`. It's one area with an error in the document, not two areas.
- If the basis isn't printed, use `unspecified`. Never default to net.

## Classification order (what the contradiction step runs)
1. Different scope (a development or block claim versus a unit) → `scope_difference`: keep both, never copy down.
2. Different plot or type → `plot_or_type_variation`: resolve the entity, never merge.
3. Same quantity in different units or on a different basis → `unit_or_measurement_mismatch`: normalise, flag any document error.
4. One side is tier 2 (official register) → `official_record_mismatch`: needs a human, check the current title.
5. One side is tier 6 (portal or CRM) and a verified document is newer → `stale_listing`: the document wins, and the listing is flagged for update.
6. Same issuer and doc_type, different dates → `version_supersession`: the later one becomes the candidate, and a human confirms if the field is material.
7. Otherwise, same tier, peers → `true_conflict`: a human signs off.
Across tiers, the higher tier wins. Within a tier, the more recent wins. Any override of a higher tier needs a human.

## Extractor output contract (Person A → data)
```json
{
  "doc_id": "carterjonas-f8692efa",
  "unit_hint": "whole building",
  "scope": "building",
  "field": "floor_area",
  "qualifier": { "basis": "NIA", "scope": "whole" },
  "value_raw": "1,990 sq ft (185m2) net offices",
  "value": { "amount": 1990, "unit": "sq_ft" },
  "normalised": { "sq_ft": 1990, "sq_m": 184.9 },
  "page": 1,
  "quote": "1,990 sq ft (185m2) net offices (2,700 sq ft GIA)",
  "doc_error": false,
  "confidence": 0.95
}
```

## Worked example: Kelso Villa
April 2026 particulars = `carterjonas-98889981` ("To Let"). October 2026 = `carterjonas-f8692efa` ("For Sale").
Both are tier 5, from the same issuer and doc_type. The dates come from the spec; neither PDF page shows a printed date, so `doc_date_source` is not `printed`.

| unit | field | April (98889981) | October (f8692efa) | type | result |
|---|---|---|---|---|---|
| whole | price | £700,000 freehold offers (p2) | £600,000 guide (p2) | version_supersession | October is the candidate; price is material, so a human confirms |
| whole | price | portal listing £700,000 | n/a | stale_listing | flag the listing for update |
| whole | floor_area GIA | "185 / 2,700" in one row (p2) | 2,700 sq ft GIA (p1) | unit_or_measurement_mismatch | April row has `doc_error`; October states both correctly |
| whole | floor_area NIA | 185 sq m (p2) | 1,990 sq ft / 185 sq m (p1, p2) | none | agree |
| lower ground | floor_area unspecified | 468 sq ft / 43.45 sq m | n/a | none | single source |
| lower ground | rent | £9,400 pa per floor (p2) | n/a | none | single source |
| whole | parking | 1 per floor (p1, p2), "six spaces" (p2) | 6 total (p1) | possibly agree | check with a human (scope per_floor vs total) |
| whole | transaction_type | to_let, freehold considered | for_sale_or_to_let | version_supersession | October is the candidate |
| whole | tenure | freehold | freehold | none | agree |
| whole | epc_rating | B | B | none | agree (tier 2 register check not done tonight) |
