# Data Source Research

## 1. SAP (Fuel and Procurement)

### Real-World Format Research
- **Typical Export**: Transaction SE16 or SE11 exports to CSV/Excel
- **Common Fields**:
  - Material/MATNR/Materialnr (material number)
  - Plant/WERKS/Werks (plant code)
  - Quantity/Menge/QTY (amount)
  - Unit/MEINS/Einheit (unit of measure)
  - Date/BUDAT/Datum (posting date)
  - Document/BELNR (document number)
- **German Configurations**: Some SAP systems use German field names
- **Units**: Often mixed (KG, T, L, M3)

### Sample Data Structure
```json
{
  "Material": "Diesel Fuel",
  "Plant": "US01",
  "Quantity": 5000,
  "Unit": "L",
  "Date": "2025-01-15",
  "Document": "DOC001"
}
```

### What Would Break in Production
- Unknown plant codes without lookup table entries
- Non-standard material types not mapped to emission categories
- Currency conversions for procurement (not Scope 1)
- Complex bill of materials (multi-level procurement)

## 2. Utility (Electricity)

### Real-World Format Research
- **Typical Export**: Portal CSV download from utility company
- **Common Fields**:
  - Account number
  - Meter number
  - Billing period (start/end dates)
  - Usage (kWh)
  - Tariff type
  - Cost (optional)
- **Challenges**: Billing periods don't always align with calendar months

### Sample Data Structure
```json
{
  "account_number": "ACCT001",
  "meter_number": "MTR001",
  "billing_period_start": "2025-01-01",
  "billing_period_end": "2025-01-31",
  "kwh": 150000,
  "tariff": "industrial"
}
```

### What Would Break in Production
- Multi-meter accounts requiring aggregation
- Estimated vs actual meter reads
- Time-of-use tariffs requiring hourly breakdown
- Net metering / solar credits

## 3. Corporate Travel

### Real-World Format Research
- **Sources**: Concur, Navan, TravelPerk APIs
- **Common Fields**:
  - Trip/booking ID
  - Employee name/email
  - Trip type (flight/hotel/ground)
  - Date
  - Origin/destination (airport codes or addresses)
  - Distance (sometimes provided, sometimes calculated)
- **Emission Factors**: Vary by trip type and sometimes class

### Sample Data Structure
```json
{
  "trip_id": "TRP001",
  "trip_type": "flight",
  "traveler": "John Smith",
  "date": "2025-03-15",
  "origin": "JFK",
  "destination": "LAX",
  "distance": 3983
}
```

### What Would Break in Production
- Missing distance (no airport codes) requiring geocoding
- Multi-leg trips needing segment breakdown
- Hotel stays without emission factor (typically excluded from Scope 3)
- Rail vs air alternatives
- Class-based factors (economy vs business vs first)

## Research Sources
- SAP transaction codes and export formats: SAP documentation
- Utility data: Typical US utility portal exports (PG&E, ConEd, etc.)
- Travel platforms: Concur API docs, Navan API reference
- Emission factors: EPA GHG Emission Factors Hub, DEFRA UK GHG Conversion Factors