# Design Decisions

## Ambiguity Resolution

### 1. SAP Export Format
**Decision**: Handled flat file CSV exports (typical SAP transaction export format)

**Rationale**: While SAP has IDocs, BAPIs, and OData services, the most common "quick export" is transaction SE16 CSV dump. This is what facilities teams typically receive.

**What we handle**:
- German column headers (Menge, Datum, WERKS) alongside English
- Multiple material number formats (Material, MATNR, Materialnr)
- Quantity in various units requiring normalization

**What we'd ask the PM**:
- Which specific SAP transaction generates these exports?
- Do you have a mapping table for materials to emission categories?
- Should we integrate directly with SAP via RFC/BAPI for real-time sync?

### 2. Utility Data Format
**Decision**: Portal CSV exports with billing period, meter number, consumption

**Rationale**: Most utilities don't offer APIs to commercial customers. The typical workflow is facilities downloading a monthly CSV from the utility portal.

**What we handle**:
- Account and meter numbers for deduplication
- Billing period (may not align with calendar months)
- kWh consumption with tariff types

**What we'd ask the PM**:
- Which utility company? Different utilities have different export formats
- Should we handle multiple meters per account?
- What's the expected data freshness (daily, monthly)?

### 3. Travel Data
**Decision**: Direct API integration with corporate travel platforms (Concur/Navan format)

**Rationale**: Travel platforms have well-documented REST APIs. Most enterprises use SSO integration.

**What we handle**:
- Trip ID, traveler, trip type (flight/hotel/ground)
- Airport codes (origin/destination) for distance calculation
- Direct distance if provided

**What we'd ask the PM**:
- Which travel platform (Concur, Navan, another)?
- Do they provide flight class (affects emission factor)?
- Should we calculate great-circle distance from airport codes?

### 4. Emission Factor Handling
**Decision**: Pre-loaded factors per category, with source/year tracking

**Rationale**: Emission factors change yearly. Need to track which factor version was used for each record.

**What we handle**:
- EPA, DEFRA, or GHG Protocol sources
- Year-specific factors
- Optional source-specific overrides

**What we'd ask the PM**:
- Which emission factor source should be default?
- How often should factors be updated?
- Should factors be tenant-configurable?

### 5. Multi-Tenancy Implementation
**Decision**: Foreign key to Tenant on all tenant-scoped models

**Rationale**: Simple, performant, explicit. Each record knows which tenant it belongs to.

**What we'd ask the PM**:
- Should tenants see each other's data in aggregate benchmarks?
- Is data isolation required at the database level (separate schemas)?
- Cross-tenant reporting for corporate groups?

## Trade-offs Made

### Simplicity over Comprehensive SAP Integration
- We handle CSV export only, not real-time SAP connection
- Trade-off: Requires manual export step
- Benefit: Avoids complex SAP authentication and IDoc parsing

### Manual Import over Automated API Pulls
- Users upload/paste data rather than scheduled API pulls
- Trade-off: More manual effort
- Benefit: Simpler, no API credential management, easier audit

### Flat File over Hierarchical Data
- Records stored as flat rows, not complex nested structures
- Trade-off: Some source-specific nuance may be lost
- Benefit: Simpler querying, consistent API, easier analytics