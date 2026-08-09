from django.contrib import admin
from .models import ActivityLog, BarangayProfile, CertificateRequest, CertificateTemplate, IDTemplate, Notification, Resident

@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ('resident_no', 'last_name', 'first_name', 'purok', 'is_active')
    search_fields = ('resident_no', 'first_name', 'last_name')
    list_filter = ('sex', 'is_active', 'purok')
@admin.register(CertificateRequest)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('reference_no', 'resident', 'certificate_type', 'status', 'requested_at')
    list_filter = ('status', 'certificate_type')
    search_fields = ('reference_no', 'resident__last_name')
admin.site.register([BarangayProfile, CertificateTemplate, IDTemplate, Notification, ActivityLog])
