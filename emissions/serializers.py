from rest_framework import serializers
from .models import (
    Tenant, DataSource, Unit, EmissionCategory, EmissionFactor,
    PlantCode, EmissionRecord, AuditTrail, ImportBatch
)


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class DataSourceSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)

    class Meta:
        model = DataSource
        fields = ['id', 'tenant', 'name', 'source_type', 'source_type_display',
                  'description', 'config', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'name', 'symbol', 'unit_type', 'conversion_factor_to_base', 'base_unit_name']


class EmissionCategorySerializer(serializers.ModelSerializer):
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    category_type_display = serializers.CharField(source='get_category_type_display', read_only=True)
    default_unit_details = UnitSerializer(source='default_unit', read_only=True)

    class Meta:
        model = EmissionCategory
        fields = ['id', 'scope', 'scope_display', 'category_type', 'category_type_display',
                  'description', 'default_unit', 'default_unit_details']


class EmissionFactorSerializer(serializers.ModelSerializer):
    category_details = EmissionCategorySerializer(source='category', read_only=True)
    unit_details = UnitSerializer(source='unit', read_only=True)

    class Meta:
        model = EmissionFactor
        fields = ['id', 'category', 'category_details', 'source', 'factor_value',
                  'unit', 'unit_details', 'source_reference', 'year', 'is_active', 'created_at']


class PlantCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantCode
        fields = ['id', 'tenant', 'plant_code', 'name', 'country', 'region', 'is_active']


class AuditTrailSerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = AuditTrail
        fields = ['id', 'record', 'action', 'action_display', 'changed_by', 'changed_by_username',
                  'changed_at', 'previous_value', 'new_value', 'notes', 'ip_address']


class ImportBatchSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    imported_by_username = serializers.CharField(source='imported_by.username', read_only=True)

    class Meta:
        model = ImportBatch
        fields = ['id', 'tenant', 'source', 'source_name', 'file_name', 'file_hash',
                  'total_rows', 'success_rows', 'failed_rows', 'status', 'errors',
                  'imported_at', 'imported_by', 'imported_by_username']


class EmissionRecordSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    category_details = EmissionCategorySerializer(source='category', read_only=True)
    activity_unit_details = UnitSerializer(source='activity_unit', read_only=True)
    emission_factor_details = EmissionFactorSerializer(source='emission_factor', read_only=True)
    imported_by_username = serializers.CharField(source='imported_by.username', read_only=True)
    last_modified_by_username = serializers.CharField(source='last_modified_by.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    audit_trail = AuditTrailSerializer(many=True, read_only=True)

    class Meta:
        model = EmissionRecord
        fields = ['id', 'tenant', 'source', 'source_name', 'category', 'category_details',
                  'source_record_id', 'raw_data', 'activity_value', 'activity_unit',
                  'activity_unit_details', 'emission_value', 'emission_factor',
                  'emission_factor_details', 'period_start', 'period_end', 'status',
                  'status_display', 'import_status', 'import_batch_id', 'import_errors',
                  'imported_at', 'imported_by', 'imported_by_username', 'last_modified_at',
                  'last_modified_by', 'last_modified_by_username', 'analyst_notes',
                  'flagged_reason', 'audit_trail']
        read_only_fields = ['imported_at', 'last_modified_at']


class EmissionRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating emission records"""
    class Meta:
        model = EmissionRecord
        fields = ['tenant', 'source', 'category', 'source_record_id', 'raw_data',
                  'activity_value', 'activity_unit', 'period_start', 'period_end']


class EmissionRecordStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating record status"""
    status = serializers.ChoiceField(choices=EmissionRecord.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_records = serializers.IntegerField()
    pending_review = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    suspicious = serializers.IntegerField()
    by_source = serializers.DictField()
    by_category = serializers.DictField()