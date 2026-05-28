"""
Management command to seed initial reference data for ESG system.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from emissions.models import (
    Tenant, DataSource, Unit, EmissionCategory, EmissionFactor, PlantCode
)
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seed initial reference data for the ESG system'

    def handle(self, *args, **options):
        self.stdout.write('Seeding reference data...')

        # Create units
        units_data = [
            ('kilogram', 'kg', 'mass', '1', 'kg'),
            ('kilogram', 'kg', 'mass', '1', 'kg'),
            ('tonne', 't', 'mass', '1000', 'kg'),
            ('pound', 'lb', 'mass', '0.453592', 'kg'),
            ('kilowatt hour', 'kWh', 'energy', '1', 'kWh'),
            ('megawatt hour', 'MWh', 'energy', '1000', 'kWh'),
            ('gigawatt hour', 'GWh', 'energy', '1000000', 'kWh'),
            ('liter', 'L', 'volume', '1', 'L'),
            ('gallon', 'gal', 'volume', '3.78541', 'L'),
            ('kilometer', 'km', 'distance', '1', 'km'),
            ('mile', 'mi', 'distance', '1.60934', 'km'),
        ]

        units = {}
        for name, symbol, unit_type, factor, base in units_data:
            unit, created = Unit.objects.get_or_create(
                name=name,
                defaults={
                    'symbol': symbol,
                    'unit_type': unit_type,
                    'conversion_factor_to_base': Decimal(factor),
                    'base_unit_name': base
                }
            )
            units[name] = unit

        self.stdout.write(f'Created {len(Unit.objects.all())} units')

        # Create emission categories
        categories_data = [
            (1, 'stationary_combustion', 'Stationary Combustion', units['kilogram']),
            (1, 'mobile_combustion', 'Mobile Combustion', units['liter']),
            (1, 'fugitive_emissions', 'Fugitive Emissions', units['kilogram']),
            (2, 'purchased_electricity', 'Purchased Electricity', units['kilowatt hour']),
            (2, 'purchased_steam', 'Purchased Steam', units['kilowatt hour']),
            (3, 'business_travel', 'Business Travel', units['kilometer']),
            (3, 'employee_commuting', 'Employee Commuting', units['kilometer']),
            (3, 'waste_generated', 'Waste Generated', units['kilogram']),
            (3, 'procurement', 'Procurement & Supply Chain', units['kilogram']),
        ]

        for scope, cat_type, desc, default_unit in categories_data:
            EmissionCategory.objects.get_or_create(
                scope=scope,
                category_type=cat_type,
                defaults={
                    'description': desc,
                    'default_unit': default_unit
                }
            )

        self.stdout.write(f'Created {len(EmissionCategory.objects.all())} categories')

        # Create demo tenant
        tenant, created = Tenant.objects.get_or_create(
            name='Acme Corporation',
            defaults={'name': 'Acme Corporation'}
        )
        if created:
            self.stdout.write(f'Created tenant: {tenant.name}')

        # Create data sources
        sources = [
            ('SAP System', 'sap', 'SAP fuel and procurement exports'),
            ('Utility Portal', 'utility', 'Electricity data from utility portal'),
            ('Concur Travel', 'travel', 'Corporate travel platform'),
        ]

        for name, source_type, desc in sources:
            DataSource.objects.get_or_create(
                tenant=tenant,
                name=name,
                defaults={
                    'source_type': source_type,
                    'description': desc
                }
            )

        self.stdout.write(f'Created {len(DataSource.objects.all())} data sources')

        # Create demo user if none exists
        if not User.objects.exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            self.stdout.write(self.style.SUCCESS('Created admin user (admin/admin123)'))
        else:
            self.stdout.write('Users already exist, skipping')

        # Create sample plant codes
        plant_codes = [
            ('US01', 'New York HQ', 'USA', 'Northeast'),
            ('US02', 'Los Angeles Plant', 'USA', 'West'),
            ('DE01', 'Munich Office', 'Germany', 'Bavaria'),
            ('UK01', 'London Branch', 'UK', 'England'),
        ]

        for code, name, country, region in plant_codes:
            PlantCode.objects.get_or_create(
                tenant=tenant,
                plant_code=code,
                defaults={
                    'name': name,
                    'country': country,
                    'region': region
                }
            )

        self.stdout.write(f'Created {len(PlantCode.objects.all())} plant codes')

        self.stdout.write(self.style.SUCCESS('Seed data created successfully!'))