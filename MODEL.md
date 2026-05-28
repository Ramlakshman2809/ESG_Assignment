# Data Model

## Overview

The ESG data model is designed to support multi-tenant emissions tracking with full audit trail, source tracking, and unit normalization. The model handles Scope 1/2/3 emissions from multiple source types (SAP, Utility, Travel).

## Core Entities

### Tenant
- **Purpose**: Multi-tenant isolation - each client company is a tenant
- **Fields**: name, created_at, updated_at

### DataSource
- **Purpose**: Track the origin of emissions data
- **Types**: SAP (fuel & procurement), Utility (electricity), Corporate Travel
- **Fields**: name, source_type, description, config (JSON for source-specific settings)
- **Relationships**: Belongs to Tenant

### EmissionCategory
- **Purpose**: Categorize emissions by Scope and type
- **Scopes**:
  - Scope 1: Direct emissions (stationary combustion, mobile combustion, fugitive)
  - Scope 2: Indirect energy (purchased electricity, steam)
  - Scope 3: Other indirect (business travel, commuting, waste, procurement)
- **Fields**: scope, category_type, description, default_unit

### Unit
- **Purpose**: Normalize units across different sources
- **Fields**: name, symbol, unit_type (mass/energy/distance/volume), conversion_factor_to_base, base_unit_name
- **Example**: litre (L) -> conversion 1 -> base litre; gallon (gal) -> conversion 3.78541 -> litre

### EmissionRecord
The main emissions data record with full audit tracking:

- **Source Tracking**:
  - source_record_id: Original ID from source system
  - raw_data: Complete JSON of original data as imported
  - imported_at, imported_by: When and who imported
  - last_modified_at, last_modified_by: Change tracking

- **Status Workflow**:
  - pending: Awaiting analyst review
  - approved: Reviewed and approved for audit
  - rejected: Rejected by analyst
  - suspicious: Flagged for investigation

- **Normalization**:
  - activity_value: Normalized activity amount
  - activity_unit: Normalized unit
  - emission_value: Calculated emissions (tonnes CO2e)
  - emission_factor: Reference to emission factor used

- **Period**: period_start, period_end for date tracking

### AuditTrail
- **Purpose**: Complete change history for compliance
- **Fields**: record, action (create/update/approve/reject/flag), changed_by, changed_at, previous_value, new_value, notes, ip_address

### ImportBatch
- **Purpose**: Track data imports for traceability
- **Fields**: tenant, source, file_name, file_hash (SHA-256), total_rows, success_rows, failed_rows, status, errors, imported_at

### EmissionFactor
- **Purpose**: Emission conversion factors by category
- **Fields**: category, source (optional), factor_value, unit, source_reference (EPA/DEFRA), year

### PlantCode
- **Purpose**: SAP plant code lookup table
- **Fields**: tenant, plant_code, name, country, region

## Justification for Design Choices

### Multi-Tenancy
- Used explicit Tenant foreign key rather than Django's content types
- Simpler to reason about, better query performance
- Enables tenant-specific plant code lookups and source configs

### Normalized Units
- Each source exports in different units (gallons vs litres, kWh vs MWh)
- Conversion happens at import time, stored in base unit
- Enables accurate calculations and reporting

### Raw Data Preservation
- Full raw_data JSON stored for audit purposes
- Allows reprocessing if emission factors change
- Supports debugging import issues

### Status Workflow
- Four-state workflow supports realistic analyst review
- Suspicious status allows flagging without full rejection
- All state changes tracked in audit trail

### Source-of-Truth Tracking
- Every record links back to source system via source_record_id
- ImportBatch groups records from single import
- Enables reconciliation with source systems