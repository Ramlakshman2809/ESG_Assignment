"""
Data ingestion module for SAP, Utility, and Travel data sources.

Based on research of real-world data formats:
- SAP: Typically exports as flat files (CSV) or IDocs
- Utility: Portal CSV exports or API responses
- Travel: API responses from platforms like Concur/Navan
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.utils import timezone

from .models import (
    Tenant, DataSource, EmissionCategory, EmissionRecord,
    EmissionFactor, ImportBatch, AuditTrail, PlantCode
)


def normalize_date(date_value):
    """Handle multiple date formats commonly found in exports"""
    if not date_value:
        return None

    if isinstance(date_value, datetime):
        return date_value.date()

    if isinstance(date_value, str):
        formats = [
            '%Y-%m-%d',
            '%d.%m.%Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y%m%d',
            '%d-%b-%Y',
            '%d %b %Y',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_value, fmt).date()
            except ValueError:
                continue

    return None


def normalize_decimal(value):
    """Convert various number formats to Decimal"""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    if isinstance(value, str):
        value = value.strip()
        # Handle European number format (1.234,56 -> 1234.56)
        if ',' in value and '.' in value:
            if value.rfind(',') > value.rfind('.'):
                value = value.replace('.', '').replace(',', '.')
            else:
                value = value.replace(',', '')
        # Handle just comma as decimal separator
        elif ',' in value:
            value = value.replace(',', '.')

        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None

    return None


def normalize_unit(value, unit_type='mass'):
    """Normalize unit to base unit"""
    conversions = {
        # Mass -> kg
        'kg': Decimal('1'),
        'kilograms': Decimal('1'),
        't': Decimal('1000'),
        'tonnes': Decimal('1000'),
        'tons': Decimal('907.185'),
        'lb': Decimal('0.453592'),
        'lbs': Decimal('0.453592'),
        'pounds': Decimal('0.453592'),
        # Energy -> kWh
        'kwh': Decimal('1'),
        'kwhs': Decimal('1'),
        'mwh': Decimal('1000'),
        'mwhs': Decimal('1000'),
        'gwh': Decimal('1000000'),
        'mj': Decimal('0.277778'),
        # Volume -> liters
        'l': Decimal('1'),
        'liters': Decimal('1'),
        'litres': Decimal('1'),
        'gal': Decimal('3.78541'),
        'gallons': Decimal('3.78541'),
        # Distance -> km
        'km': Decimal('1'),
        'kms': Decimal('1'),
        'mi': Decimal('1.60934'),
        'miles': Decimal('1.60934'),
    }

    if isinstance(value, str):
        value = value.lower().strip()
        return conversions.get(value, Decimal('1'))

    return Decimal('1')


def get_or_create_plant_code(tenant, code, name='', country='', region=''):
    """Get or create plant code with lookup"""
    plant, created = PlantCode.objects.get_or_create(
        tenant=tenant,
        plant_code=code,
        defaults={
            'name': name or code,
            'country': country,
            'region': region
        }
    )
    return plant


def detect_suspicious_record(record_data, category_type):
    """Flag suspicious values based on expected ranges"""
    activity = record_data.get('activity_value')
    flag_reason = ''

    if activity:
        # Unreasonably high values
        if category_type == 'stationary_combustion' and activity > 1000000:
            flag_reason = f'Extremely high combustion value: {activity}'
        elif category_type == 'purchased_electricity' and activity > 50000000:
            flag_reason = f'Extremely high electricity consumption: {activity} kWh'
        elif category_type == 'business_travel' and activity > 200000:
            flag_reason = f'Extremely high travel distance: {activity} km'

    return flag_reason


@transaction.atomic
def ingest_sap_data(tenant_id, source_id, data, user):
    """Ingest SAP fuel and procurement data"""
    tenant = Tenant.objects.get(id=tenant_id)
    source = DataSource.objects.get(id=source_id)

    # Get or create categories for SAP data
    stationary_cat, _ = EmissionCategory.objects.get_or_create(
        scope=1,
        category_type='stationary_combustion',
        defaults={'description': 'Stationary combustion from SAP procurement data'}
    )
    mobile_cat, _ = EmissionCategory.objects.get_or_create(
        scope=1,
        category_type='mobile_combustion',
        defaults={'description': 'Mobile combustion from SAP fuel data'}
    )
    procurement_cat, _ = EmissionCategory.objects.get_or_create(
        scope=3,
        category_type='procurement',
        defaults={'description': 'Procurement and supply chain from SAP'}
    )

    # Create import batch
    batch = ImportBatch.objects.create(
        tenant=tenant,
        source=source,
        file_name='sap_import',
        file_hash='',
        total_rows=len(data),
        imported_by=user
    )

    success_count = 0
    error_rows = []

    for idx, row in enumerate(data):
        try:
            # SAP fields mapping (realistic SAP export format)
            # Typical SAP export has German headers in some configs
            material = row.get('Material') or row.get('Materialnr') or row.get('MATNR', '')
            plant = row.get('Plant') or row.get('Werks') or row.get('WERKS', '')
            quantity = row.get('Quantity') or row.get('Menge') or row.get('QTY', 0)
            unit = row.get('Unit') or row.get('Einheit') or row.get('MEINS', 'KG')
            date_str = row.get('Date') or row.get('Datum') or row.get('BUDAT', '')
            document = row.get('Document') or row.get('BELNR', '')

            # Normalize date
            period_start = normalize_date(date_str) or datetime.now().date()
            period_end = period_start

            # Determine category based on material type
            if any(x in str(material).lower() for x in ['fuel', 'diesel', 'gas', 'oil', 'brennstoff']):
                category = mobile_cat if 'vehicle' in str(material).lower() else stationary_cat
                activity_unit = 'l'  # liters for fuel
            else:
                category = procurement_cat
                activity_unit = unit.lower() if unit else 'kg'

            activity_value = normalize_decimal(quantity)
            if not activity_value:
                raise ValueError(f'Invalid quantity: {quantity}')

            # Convert to normalized unit
            normalized_activity = activity_value * normalize_unit(activity_unit, 'mass')

            # Create record
            record = EmissionRecord.objects.create(
                tenant=tenant,
                source=source,
                category=category,
                source_record_id=f'{document}_{idx}',
                raw_data=row,
                activity_value=normalized_activity,
                activity_unit_id=1,  # kg as base
                period_start=period_start,
                period_end=period_end,
                import_status='completed',
                import_batch_id=str(batch.id),
                imported_by=user,
                status='pending'
            )

            # Check for suspicious values
            flag_reason = detect_suspicious_record(
                {'activity_value': normalized_activity},
                category.category_type
            )
            if flag_reason:
                record.status = 'suspicious'
                record.flagged_reason = flag_reason
                record.save()

            success_count += 1

        except Exception as e:
            error_rows.append({
                'row': idx,
                'data': row,
                'error': str(e)
            })

    batch.success_rows = success_count
    batch.failed_rows = len(error_rows)
    batch.status = 'completed' if success_count > 0 else 'failed'
    batch.errors = error_rows
    batch.save()

    return {
        'batch_id': batch.id,
        'total_rows': len(data),
        'success_count': success_count,
        'failed_count': len(error_rows),
        'errors': error_rows[:10]  # Return first 10 errors
    }


@transaction.atomic
def ingest_utility_data(tenant_id, source_id, data, user):
    """Ingest utility electricity data"""
    tenant = Tenant.objects.get(id=tenant_id)
    source = DataSource.objects.get(id=source_id)

    # Get electricity category
    electricity_cat, _ = EmissionCategory.objects.get_or_create(
        scope=2,
        category_type='purchased_electricity',
        defaults={'description': 'Purchased electricity from utility portals'}
    )

    batch = ImportBatch.objects.create(
        tenant=tenant,
        source=source,
        file_name='utility_import',
        file_hash='',
        total_rows=len(data),
        imported_by=user
    )

    success_count = 0
    error_rows = []

    for idx, row in enumerate(data):
        try:
            # Typical utility portal CSV format
            account = row.get('account_number') or row.get('Account') or row.get('ACCT', '')
            meter = row.get('meter_number') or row.get('Meter', '')
            start_date = row.get('billing_period_start') or row.get('StartDate') or row.get('period_start', '')
            end_date = row.get('billing_period_end') or row.get('EndDate') or row.get('period_end', '')
            kwh = row.get('kwh') or row.get('consumption') or row.get('Usage', 0)
            tariff = row.get('tariff') or row.get('Rate', '')

            period_start = normalize_date(start_date) or datetime.now().date()
            period_end = normalize_date(end_date) or period_start

            activity_value = normalize_decimal(kwh)
            if not activity_value:
                raise ValueError(f'Invalid kWh: {kwh}')

            record = EmissionRecord.objects.create(
                tenant=tenant,
                source=source,
                category=electricity_cat,
                source_record_id=f'{account}_{meter}_{idx}',
                raw_data=row,
                activity_value=activity_value,
                activity_unit_id=2,  # kWh
                period_start=period_start,
                period_end=period_end,
                import_status='completed',
                import_batch_id=str(batch.id),
                imported_by=user,
                status='pending'
            )

            # Check for suspicious values
            flag_reason = detect_suspicious_record(
                {'activity_value': activity_value},
                'purchased_electricity'
            )
            if flag_reason:
                record.status = 'suspicious'
                record.flagged_reason = flag_reason
                record.save()

            success_count += 1

        except Exception as e:
            error_rows.append({
                'row': idx,
                'data': row,
                'error': str(e)
            })

    batch.success_rows = success_count
    batch.failed_rows = len(error_rows)
    batch.status = 'completed' if success_count > 0 else 'failed'
    batch.errors = error_rows
    batch.save()

    return {
        'batch_id': batch.id,
        'total_rows': len(data),
        'success_count': success_count,
        'failed_count': len(error_rows),
        'errors': error_rows[:10]
    }


@transaction.atomic
def ingest_travel_data(tenant_id, source_id, data, user):
    """Ingest corporate travel data"""
    tenant = Tenant.objects.get(id=tenant_id)
    source = DataSource.objects.get(id=source_id)

    # Get travel category
    travel_cat, _ = EmissionCategory.objects.get_or_create(
        scope=3,
        category_type='business_travel',
        defaults={'description': 'Business travel from corporate travel platform'}
    )

    batch = ImportBatch.objects.create(
        tenant=tenant,
        source=source,
        file_name='travel_import',
        file_hash='',
        total_rows=len(data),
        imported_by=user
    )

    success_count = 0
    error_rows = []

    for idx, row in enumerate(data):
        try:
            # Typical Concur/Navan API format
            trip_id = row.get('trip_id') or row.get('TripID') or row.get('TripId', '')
            traveler = row.get('traveler') or row.get('Employee') or row.get('Traveler', '')
            trip_type = row.get('trip_type') or row.get('Type') or row.get('Category', 'flight')
            date_str = row.get('date') or row.get('TripDate') or row.get('Date', '')
            origin = row.get('origin') or row.get('From') or row.get('Origin', '')
            destination = row.get('destination') or row.get('To') or row.get('Destination', '')
            distance = row.get('distance') or row.get('Distance', 0)

            period_start = normalize_date(date_str) or datetime.now().date()
            period_end = period_start

            activity_value = normalize_decimal(distance) or Decimal('0')

            # For flights, use great circle distance calculation
            # In real scenario, would calculate based on airport codes
            if not activity_value and origin and destination:
                # Placeholder - would use airport code lookup
                activity_value = Decimal('500')  # Default assumption

            if not activity_value:
                raise ValueError(f'No distance available for trip: {trip_id}')

            record = EmissionRecord.objects.create(
                tenant=tenant,
                source=source,
                category=travel_cat,
                source_record_id=f'{trip_id}_{idx}',
                raw_data=row,
                activity_value=activity_value,
                activity_unit_id=3,  # km
                period_start=period_start,
                period_end=period_end,
                import_status='completed',
                import_batch_id=str(batch.id),
                imported_by=user,
                status='pending'
            )

            # Check for suspicious values
            flag_reason = detect_suspicious_record(
                {'activity_value': activity_value},
                'business_travel'
            )
            if flag_reason:
                record.status = 'suspicious'
                record.flagged_reason = flag_reason
                record.save()

            success_count += 1

        except Exception as e:
            error_rows.append({
                'row': idx,
                'data': row,
                'error': str(e)
            })

    batch.success_rows = success_count
    batch.failed_rows = len(error_rows)
    batch.status = 'completed' if success_count > 0 else 'failed'
    batch.errors = error_rows
    batch.save()

    return {
        'batch_id': batch.id,
        'total_rows': len(data),
        'success_count': success_count,
        'failed_count': len(error_rows),
        'errors': error_rows[:10]
    }