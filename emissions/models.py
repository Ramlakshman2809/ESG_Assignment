from django.db import models
from django.contrib.auth.models import User


class Tenant(models.Model):
    """Multi-tenant support - each client company is a tenant"""
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DataSource(models.Model):
    """Source system tracking - SAP, Utility Portal, Travel Platform"""
    SOURCE_TYPES = [
        ('sap', 'SAP (Fuel & Procurement)'),
        ('utility', 'Utility (Electricity)'),
        ('travel', 'Corporate Travel'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='data_sources')
    name = models.CharField(max_length=100)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    description = models.TextField(blank=True)
    config = models.JSONField(default=dict, help_text="Source-specific configuration")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['tenant', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


class Unit(models.Model):
    """Normalized units for emissions data"""
    UNIT_TYPES = [
        ('mass', 'Mass (kg, tonnes)'),
        ('energy', 'Energy (kWh, MJ)'),
        ('distance', 'Distance (km, miles)'),
        ('currency', 'Currency (USD, EUR)'),
        ('volume', 'Volume (liters, gallons)'),
    ]

    name = models.CharField(max_length=50, unique=True)
    symbol = models.CharField(max_length=20)
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPES)
    conversion_factor_to_base = models.DecimalField(
        max_digits=20, decimal_places=10,
        help_text="Factor to convert to base unit (e.g., kg for mass)"
    )
    base_unit_name = models.CharField(max_length=50)

    class Meta:
        ordering = ['unit_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.symbol})"


class EmissionCategory(models.Model):
    """Scope 1/2/3 categories for emissions classification"""
    SCOPE_CHOICES = [
        (1, 'Scope 1 - Direct emissions'),
        (2, 'Scope 2 - Indirect (energy)'),
        (3, 'Scope 3 - Other indirect'),
    ]

    CATEGORY_TYPES = [
        ('stationary_combustion', 'Stationary Combustion'),
        ('mobile_combustion', 'Mobile Combustion'),
        ('fugitive_emissions', 'Fugitive Emissions'),
        ('purchased_electricity', 'Purchased Electricity'),
        ('purchased_steam', 'Purchased Steam'),
        ('business_travel', 'Business Travel'),
        ('employee_commuting', 'Employee Commuting'),
        ('waste_generated', 'Waste Generated'),
        ('procurement', 'Procurement & Supply Chain'),
    ]

    scope = models.IntegerField(choices=SCOPE_CHOICES)
    category_type = models.CharField(max_length=50, choices=CATEGORY_TYPES)
    description = models.TextField(blank=True)
    default_unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ['scope', 'category_type']
        ordering = ['scope', 'category_type']

    def __str__(self):
        return f"Scope {self.scope} - {self.get_category_type_display()}"


class EmissionFactor(models.Model):
    """Emission conversion factors by category and source"""
    category = models.ForeignKey(EmissionCategory, on_delete=models.CASCADE)
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, null=True, blank=True)
    factor_value = models.DecimalField(max_digits=20, decimal_places=10)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    source_reference = models.CharField(
        max_length=255,
        help_text="Source of emission factor (e.g., EPA, DEFRA, GHG Protocol)"
    )
    year = models.IntegerField(help_text="Year the factor applies to")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year', 'category']

    def __str__(self):
        return f"{self.category} - {self.factor_value} {self.unit.symbol}/{self.year}"


class PlantCode(models.Model):
    """SAP plant code lookup table"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    plant_code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=50, blank=True)
    region = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['tenant', 'plant_code']
        ordering = ['plant_code']

    def __str__(self):
        return f"{self.plant_code} - {self.name}"


class EmissionRecord(models.Model):
    """Main emissions data record with full audit tracking"""

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspicious', 'Flagged Suspicious'),
    ]

    IMPORT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='emission_records')
    source = models.ForeignKey(DataSource, on_delete=models.PROTECT)
    category = models.ForeignKey(EmissionCategory, on_delete=models.PROTECT)

    # Source data (raw)
    source_record_id = models.CharField(
        max_length=255,
        help_text="Original ID from source system"
    )
    raw_data = models.JSONField(
        default=dict,
        help_text="Original raw data as imported"
    )

    # Normalized data
    activity_value = models.DecimalField(max_digits=20, decimal_places=5)
    activity_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='+')
    emission_value = models.DecimalField(
        max_digits=20, decimal_places=5, null=True, blank=True,
        help_text="Calculated emissions in tonnes CO2e"
    )
    emission_factor = models.ForeignKey(
        EmissionFactor, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Date tracking
    period_start = models.DateField()
    period_end = models.DateField()

    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    import_status = models.CharField(max_length=20, choices=IMPORT_STATUS_CHOICES, default='pending')
    import_batch_id = models.CharField(max_length=100, blank=True)
    import_errors = models.TextField(blank=True, help_text="Errors encountered during import")

    # Source tracking
    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='imported_records'
    )
    last_modified_at = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='modified_records'
    )

    # Notes
    analyst_notes = models.TextField(blank=True)
    flagged_reason = models.TextField(blank=True, help_text="Why record was flagged as suspicious")

    class Meta:
        ordering = ['-period_start', '-imported_at']
        indexes = [
            models.Index(fields=['tenant', 'period_start']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'source']),
        ]

    def __str__(self):
        return f"{self.tenant.name} - {self.source.name} - {self.period_start} ({self.status})"


class AuditTrail(models.Model):
    """Complete audit trail for all changes"""
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('flag', 'Flagged'),
        ('unflag', 'Unflagged'),
    ]

    record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='audit_trail')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    previous_value = models.JSONField(default=dict)
    new_value = models.JSONField(default=dict)
    notes = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.record.id} - {self.action} at {self.changed_at}"


class ImportBatch(models.Model):
    """Track data imports for traceability"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, help_text="SHA-256 hash of uploaded file")
    total_rows = models.IntegerField(default=0)
    success_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='pending')
    errors = models.JSONField(default=list)
    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-imported_at']

    def __str__(self):
        return f"{self.source.name} - {self.file_name} ({self.imported_at})"