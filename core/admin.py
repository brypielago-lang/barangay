from django.contrib import admin
from .models import (
    ActivityLog,
    BarangayProfile,
    CertificateRequest,
    CertificateTemplate,
    IDTemplate,
    Notification,
    Resident,
)


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = (
        'resident_no',
        'last_name',
        'first_name',
        'purok',
        'is_active',
    )
    list_filter = ('sex', 'is_active', 'purok')
    search_fields = (
        'resident_no',
        'first_name',
        'last_name',
    )


@admin.register(CertificateRequest)
class RequestAdmin(admin.ModelAdmin):
    list_display = (
        'reference_no',
        'resident',
        'certificate_type',
        'status',
        'requested_at',
    )
    list_filter = ('status', 'certificate_type')
    search_fields = (
        'reference_no',
        'resident__last_name',
    )


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'certificate_type',
        'updated_at',
    )

    list_filter = ('certificate_type',)

    search_fields = (
        'title',
        'body',
        'footer',
    )

    fieldsets = (
        (
            'Certificate Information',
            {
                'fields': (
                    'certificate_type',
                    'title',
                )
            },
        ),
        (
            'Certificate Body',
            {
                'description': (
                    'You can use the following placeholders: '
                    '{{ resident.full_name }}, '
                    '{{ resident.address }}, '
                    '{{ resident.resident_no }}, '
                    '{{ request.purpose }}, '
                    '{{ barangay.name }}, '
                    '{{ barangay.municipality }}, '
                    '{{ barangay.province }}, '
                    '{{ barangay.captain_name }}.'
                ),
                'fields': (
                    'body',
                    'footer',
                ),
            },
        ),
    )

    readonly_fields = ('updated_at',)


@admin.register(BarangayProfile)
class BarangayProfileAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'municipality',
        'province',
        'captain_name',
    )


@admin.register(IDTemplate)
class IDTemplateAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'is_active',
        'updated_at',
    )
    list_filter = ('is_active',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'title',
        'is_read',
        'created_at',
    )
    list_filter = ('is_read',)
    search_fields = (
        'title',
        'message',
        'user__username',
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        'action',
        'user',
        'created_at',
    )
    search_fields = (
        'action',
        'detail',
        'user__username',
    )
