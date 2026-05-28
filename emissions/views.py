from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Sum, Q
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
import hashlib
import json

from .models import (
    Tenant, DataSource, Unit, EmissionCategory, EmissionFactor,
    PlantCode, EmissionRecord, AuditTrail, ImportBatch
)
from .serializers import (
    TenantSerializer, DataSourceSerializer, UnitSerializer,
    EmissionCategorySerializer, EmissionFactorSerializer,
    PlantCodeSerializer, EmissionRecordSerializer,
    EmissionRecordCreateSerializer, EmissionRecordStatusUpdateSerializer,
    ImportBatchSerializer, DashboardStatsSerializer
)


class TenantViewSet(viewsets.ModelViewSet):
    """Tenant management"""
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']


class DataSourceViewSet(viewsets.ModelViewSet):
    """Data source management"""
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant_id = self.request.query_params.get('tenant')
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        return queryset


class UnitViewSet(viewsets.ModelViewSet):
    """Unit management"""
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'symbol']
    ordering_fields = ['name', 'unit_type']


class EmissionCategoryViewSet(viewsets.ModelViewSet):
    """Emission category management"""
    queryset = EmissionCategory.objects.all()
    serializer_class = EmissionCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['scope', 'category_type']


class EmissionFactorViewSet(viewsets.ModelViewSet):
    """Emission factor management"""
    queryset = EmissionFactor.objects.all()
    serializer_class = EmissionFactorSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['source_reference']
    ordering_fields = ['-year', 'category']

    def get_queryset(self):
        queryset = super().get_queryset()
        scope = self.request.query_params.get('scope')
        if scope:
            queryset = queryset.filter(category__scope=scope)
        return queryset


class PlantCodeViewSet(viewsets.ModelViewSet):
    """Plant code lookup"""
    queryset = PlantCode.objects.all()
    serializer_class = PlantCodeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['plant_code', 'name']
    ordering_fields = ['plant_code']

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant_id = self.request.query_params.get('tenant')
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        return queryset


class ImportBatchViewSet(viewsets.ModelViewSet):
    """Import batch tracking"""
    queryset = ImportBatch.objects.all()
    serializer_class = ImportBatchSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['-imported_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant_id = self.request.query_params.get('tenant')
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        source_id = self.request.query_params.get('source')
        if source_id:
            queryset = queryset.filter(source_id=source_id)
        return queryset


class EmissionRecordViewSet(viewsets.ModelViewSet):
    """Main emission record management with review workflow"""
    queryset = EmissionRecord.objects.all()
    serializer_class = EmissionRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['source_record_id', 'import_batch_id', 'analyst_notes']
    ordering_fields = ['period_start', 'imported_at', 'status']

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant_id = self.request.query_params.get('tenant')
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        source_id = self.request.query_params.get('source')
        if source_id:
            queryset = queryset.filter(source_id=source_id)

        scope = self.request.query_params.get('scope')
        if scope:
            queryset = queryset.filter(category__scope=scope)

        period_start = self.request.query_params.get('period_start')
        if period_start:
            queryset = queryset.filter(period_start__gte=period_start)

        period_end = self.request.query_params.get('period_end')
        if period_end:
            queryset = queryset.filter(period_end__lte=period_end)

        suspicious_only = self.request.query_params.get('suspicious')
        if suspicious_only:
            queryset = queryset.filter(
                Q(flagged_reason__isnull=False) & ~Q(flagged_reason='')
            )

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = EmissionRecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        record = serializer.save()
        if record.emission_factor:
            record.emission_value = record.activity_value * record.emission_factor.factor_value
            record.save()

        AuditTrail.objects.create(
            record=record,
            action='create',
            changed_by=request.user,
            new_value=serializer.data
        )

        return Response(
            EmissionRecordSerializer(record).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update record status (approve, reject, flag)"""
        record = self.get_object()
        serializer = EmissionRecordStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = record.status
        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')

        record.status = new_status
        if notes:
            record.analyst_notes = notes

        if new_status == 'suspicious' and notes:
            record.flagged_reason = notes

        record.last_modified_by = request.user
        record.save()

        action_map = {
            'approved': 'approve',
            'rejected': 'reject',
            'suspicious': 'flag',
            'pending': 'unflag'
        }
        action_type = action_map.get(new_status, 'update')

        AuditTrail.objects.create(
            record=record,
            action=action_type,
            changed_by=request.user,
            previous_value={'status': old_status},
            new_value={'status': new_status, 'notes': notes}
        )

        return Response(EmissionRecordSerializer(record).data)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics"""
        tenant_id = request.query_params.get('tenant')
        if not tenant_id:
            return Response({'error': 'tenant parameter required'}, status=400)

        queryset = EmissionRecord.objects.filter(tenant_id=tenant_id)

        total_records = queryset.count()
        pending_review = queryset.filter(status='pending').count()
        approved = queryset.filter(status='approved').count()
        rejected = queryset.filter(status='rejected').count()
        suspicious = queryset.filter(status='suspicious').count()

        by_source = {}
        for source in DataSource.objects.filter(tenant_id=tenant_id):
            count = queryset.filter(source=source).count()
            if count > 0:
                by_source[source.name] = count

        by_category = {}
        for category in EmissionCategory.objects.all():
            count = queryset.filter(category=category).count()
            if count > 0:
                by_category[category.get_category_type_display()] = count

        data = {
            'total_records': total_records,
            'pending_review': pending_review,
            'approved': approved,
            'rejected': rejected,
            'suspicious': suspicious,
            'by_source': by_source,
            'by_category': by_category
        }

        return Response(DashboardStatsSerializer(data).data)

    @action(detail=False, methods=['post'])
    def bulk_approve(self, request):
        """Bulk approve multiple records"""
        record_ids = request.data.get('record_ids', [])
        if not record_ids:
            return Response({'error': 'record_ids required'}, status=400)

        records = EmissionRecord.objects.filter(
            id__in=record_ids,
            status__in=['pending', 'suspicious']
        )

        count = 0
        for record in records:
            old_status = record.status
            record.status = 'approved'
            record.last_modified_by = request.user
            record.save()

            AuditTrail.objects.create(
                record=record,
                action='approve',
                changed_by=request.user,
                previous_value={'status': old_status},
                new_value={'status': 'approved'}
            )
            count += 1

        return Response({'approved_count': count})

    @action(detail=False, methods=['post'])
    def bulk_reject(self, request):
        """Bulk reject multiple records"""
        record_ids = request.data.get('record_ids', [])
        notes = request.data.get('notes', '')
        if not record_ids:
            return Response({'error': 'record_ids required'}, status=400)

        records = EmissionRecord.objects.filter(
            id__in=record_ids,
            status__in=['pending', 'suspicious', 'approved']
        )

        count = 0
        for record in records:
            old_status = record.status
            record.status = 'rejected'
            record.last_modified_by = request.user
            if notes:
                record.analyst_notes = notes
            record.save()

            AuditTrail.objects.create(
                record=record,
                action='reject',
                changed_by=request.user,
                previous_value={'status': old_status},
                new_value={'status': 'rejected', 'notes': notes}
            )
            count += 1

        return Response({'rejected_count': count})


class DataIngestionViewSet(viewsets.ViewSet):
    """API endpoints for data ingestion from different sources"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def ingest_sap(self, request):
        """Ingest SAP fuel and procurement data"""
        from .ingestion import ingest_sap_data

        tenant_id = request.data.get('tenant_id')
        source_id = request.data.get('source_id')
        data = request.data.get('data', [])

        if not all([tenant_id, source_id, data]):
            return Response(
                {'error': 'tenant_id, source_id, and data required'},
                status=400
            )

        result = ingest_sap_data(tenant_id, source_id, data, request.user)
        return Response(result)

    @action(detail=False, methods=['post'])
    def ingest_utility(self, request):
        """Ingest utility electricity data"""
        from .ingestion import ingest_utility_data

        tenant_id = request.data.get('tenant_id')
        source_id = request.data.get('source_id')
        data = request.data.get('data', [])

        if not all([tenant_id, source_id, data]):
            return Response(
                {'error': 'tenant_id, source_id, and data required'},
                status=400
            )

        result = ingest_utility_data(tenant_id, source_id, data, request.user)
        return Response(result)

    @action(detail=False, methods=['post'])
    def ingest_travel(self, request):
        """Ingest corporate travel data"""
        from .ingestion import ingest_travel_data

        tenant_id = request.data.get('tenant_id')
        source_id = request.data.get('source_id')
        data = request.data.get('data', [])

        if not all([tenant_id, source_id, data]):
            return Response(
                {'error': 'tenant_id, source_id, and data required'},
                status=400
            )

        result = ingest_travel_data(tenant_id, source_id, data, request.user)
        return Response(result)


class AuthViewSet(viewsets.ViewSet):
    """Simple auth endpoints"""
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register a new user"""
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')

        if not all([username, password, email]):
            return Response(
                {'error': 'username, password, and email required'},
                status=400
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'username already exists'},
                status=400
            )

        user = User.objects.create_user(username, email, password)
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email
        }, status=201)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """Login and get user info"""
        from django.contrib.auth import authenticate
        from rest_framework.authtoken.models import Token

        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            })

        return Response(
            {'error': 'invalid credentials'},
            status=401
        )