# Deliberately Not Built

## 1. Real-time SAP Integration
**Why**: Full SAP integration would require:
- SAP RFC/BAPI connection handling
- Complex credential management
- IDoc parsing for different message types
- SAP system availability dependency

**Current approach**: Manual CSV export upload
**Trade-off**: Slightly more manual work, but dramatically simpler deployment and maintenance

## 2. Automated Emission Factor Updates
**Why**: Would require:
- Scheduled jobs to fetch latest EPA/DEFRA factors
- Version management and backward-compatibility
- More complex migration logic for reprocessing

**Current approach**: Manual factor management via admin
**Trade-off**: Analyst must periodically update factors, but full control over which factors apply to which periods

## 3. Advanced Analytics / BI Dashboard
**Why**: Would require:
- Additional charting library (Chart.js, Recharts)
- More complex frontend state management
- Separate dashboard-specific API endpoints
- Higher bundle size and complexity

**Current approach**: Simple statistics summary with tabular data
**Trade-off**: Less visual, but the core review workflow is functional. Analysts can export data for their own analysis.

## What Else Was Considered But Deferred

### API-based Data Pulls
- Would enable scheduled automatic imports
- Requires OAuth/scheduled job infrastructure
- Deferred to future iteration

### Complex Validation Rules Engine
- Would allow custom per-tenant validation
- Adds significant complexity to data model
- Deferred - current suspicious value detection is simple but functional

### Multi-file Upload Support
- Would enable bulk import of multiple files
- Requires file queue management
- Deferred - single-file JSON/CSV import works for prototype