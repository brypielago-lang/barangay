from django.contrib import admin
from .models import (
    BarangayProfile,
    Resident,
    CertificateTemplate,
    IDTemplate,
    CertificateRequest,
    Notification,
    ActivityLog,
)


@admin.register(BarangayProfile)
class BarangayProfileAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'municipality',
        'province',
        'captain_name',
    )


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = (
        'certificate_type',
        'title',
        'updated_at',
    )

    list_filter = (
        'certificate_type',
    )

    search_fields = (
        'title',
        'body',
    )

    fieldsets = (
        (
            'Certificate Information',
            {
                'fields': (
                    'certificate_type',
                    'title',
                )
            }
        ),
        (
            'Certificate Content',
            {
                'fields': (
                    'body',
                    'footer',
                ),
                'description': (
                    'Available variables: '
                    '{{ resident.full_name }}, '
                    '{{ request.purpose }}, '
                    '{{ request.business_name }}, '
                    '{{ request.business_address }}, '
                    '{{ barangay.name }}, '
                    '{{ barangay.municipality }}, '
                    '{{ barangay.province }}, '
                    '{{ barangay.captain_name }}'
                ),
            }
        ),
    )


@admin.register(IDTemplate)
class IDTemplateAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'is_active',
        'updated_at',
    )


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = (
        'resident_no',
        'full_name',
        'sex',
        'civil_status',
        'address',
        'is_active',
    )

    search_fields = (
        'resident_no',
        'first_name',
        'middle_name',
        'last_name',
    )

    list_filter = (
        'sex',
        'civil_status',
        'is_active',
    )


@admin.register(CertificateRequest)
class CertificateRequestAdmin(admin.ModelAdmin):
    list_display = (
        'reference_no',
        'resident',
        'certificate_type',
        'status',
        'requested_at',
    )

    list_filter = (
        'certificate_type',
        'status',
    )

    search_fields = (
        'reference_no',
        'resident__first_name',
        'resident__last_name',
        'business_name',
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'user',
        'is_read',
        'created_at',
    )

    list_filter = (
        'is_read',
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        'action',
        'user',
        'created_at',
    )

    list_filter = (
        'action',
    )
