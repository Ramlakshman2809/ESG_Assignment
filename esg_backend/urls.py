from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from emissions.views import (
    TenantViewSet, DataSourceViewSet, UnitViewSet,
    EmissionCategoryViewSet, EmissionFactorViewSet,
    PlantCodeViewSet, EmissionRecordViewSet,
    ImportBatchViewSet, DataIngestionViewSet, AuthViewSet
)

router = DefaultRouter()
router.register(r'tenants', TenantViewSet)
router.register(r'data-sources', DataSourceViewSet)
router.register(r'units', UnitViewSet)
router.register(r'emission-categories', EmissionCategoryViewSet)
router.register(r'emission-factors', EmissionFactorViewSet)
router.register(r'plant-codes', PlantCodeViewSet)
router.register(r'emission-records', EmissionRecordViewSet)
router.register(r'import-batches', ImportBatchViewSet)
router.register(r'ingestion', DataIngestionViewSet, basename='ingestion')
router.register(r'auth', AuthViewSet, basename='auth')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]