from django.contrib import admin
from django.utils import timezone

from .models import (
    BarangayProfile,
    Resident,
    CertificateTemplate,
    IDTemplate,
    CertificateRequest,
    Notification,
    ActivityLog,
)


# =========================================================
# BARANGAY PROFILE
# =========================================================

@admin.register(BarangayProfile)
class BarangayProfileAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'municipality',
        'province',
        'captain_name',
        'contact_number',
        'email',
    )


# =========================================================
# RESIDENT
# =========================================================

@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):

    list_display = (
        'resident_no',
        'full_name',
        'sex',
        'civil_status',
        'contact_number',
        'user',
        'is_active',
    )

    search_fields = (
        'resident_no',
        'first_name',
        'middle_name',
        'last_name',
        'contact_number',
    )

    list_filter = (
        'sex',
        'civil_status',
        'is_active',
    )


# =========================================================
# CERTIFICATE TEMPLATE
# =========================================================

@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):

    list_display = (
        'certificate_type',
        'title',
        'updated_at',
    )

    search_fields = (
        'title',
        'body',
    )


# =========================================================
# ID TEMPLATE
# =========================================================

@admin.register(IDTemplate)
class IDTemplateAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'is_active',
        'show_qr',
        'updated_at',
    )


# =========================================================
# CERTIFICATE REQUEST
# =========================================================

@admin.register(CertificateRequest)
class CertificateRequestAdmin(admin.ModelAdmin):

    list_display = (
        'reference_no',
        'resident',
        'certificate_type',
        'status',
        'requested_at',
        'reviewed_at',
    )

    list_filter = (
        'status',
        'certificate_type',
    )

    search_fields = (
        'reference_no',
        'resident__first_name',
        'resident__last_name',
    )

    readonly_fields = (
        'reference_no',
        'requested_at',
        'reviewed_at',
        'released_at',
        'verification_token',
    )

    def save_model(self, request, obj, form, change):

        # =====================================================
        # GET OLD STATUS
        # =====================================================

        old_status = None

        if change and obj.pk:

            try:

                old_obj = CertificateRequest.objects.get(
                    pk=obj.pk
                )

                old_status = old_obj.status

            except CertificateRequest.DoesNotExist:

                old_status = None

        # =====================================================
        # REVIEWED BY
        # =====================================================

        if obj.status in (
            'approved',
            'rejected',
            'released',
        ):

            obj.reviewed_by = request.user

        # =====================================================
        # REVIEWED DATE
        # =====================================================

        if obj.status in (
            'approved',
            'rejected',
        ):

            if not obj.reviewed_at:

                obj.reviewed_at = timezone.now()

        # =====================================================
        # RELEASED DATE
        # =====================================================

        if obj.status == 'released':

            if not obj.released_at:

                obj.released_at = timezone.now()

        # =====================================================
        # SAVE REQUEST
        # =====================================================

        super().save_model(
            request,
            obj,
            form,
            change
        )

        # =====================================================
        # ONLY NOTIFY WHEN STATUS CHANGED
        # =====================================================

        if old_status == obj.status:

            return

        # =====================================================
        # GET RESIDENT
        # =====================================================

        resident = obj.resident

        if not resident:

            print(
                'NOTIFICATION ERROR: '
                'Request has no resident.'
            )

            return

        # =====================================================
        # GET USER
        # =====================================================

        user = resident.user

        if not user:

            print(
                'NOTIFICATION ERROR: '
                'Resident has no linked user.'
            )

            return

        # =====================================================
        # STATUS TEXT
        # =====================================================

        status_text = obj.get_status_display()

        certificate_name = (
            obj.get_certificate_type_display()
        )

        # =====================================================
        # NOTIFICATION TITLE
        # =====================================================

        title = (
            f'Certificate Request {status_text}'
        )

        # =====================================================
        # NOTIFICATION MESSAGE
        # =====================================================

        message = (
            f'Your {certificate_name} request '
            f'({obj.reference_no}) '
            f'is now {status_text.lower()}.'
        )

        if obj.remarks:

            message += (
                f'\n\nRemarks: {obj.remarks}'
            )

        # =====================================================
        # WEBSITE NOTIFICATION
        # =====================================================

        try:

            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                url=f'/requests/{obj.pk}/'
            )

            print(
                f'NOTIFICATION CREATED FOR USER: '
                f'{user.username}'
            )

        except Exception as e:

            print(
                f'NOTIFICATION ERROR: {repr(e)}'
            )

        # =====================================================
        # EMAIL
        # =====================================================
        #
        # IMPORTANT:
        # Email must NEVER stop the admin save.
        #
        # If email settings are missing or SMTP fails,
        # the notification above will still remain.
        #
        # =====================================================

        if not user.email:

            print(
                f'EMAIL NOT SENT: '
                f'{user.username} has no email.'
            )

            return

        try:

            print(
                f'SENDING EMAIL TO: '
                f'{user.email}'
            )

            send_mail(
                subject=title,
                message=message,
                from_email=getattr(
                    settings,
                    'DEFAULT_FROM_EMAIL',
                    None
                ),
                recipient_list=[
                    user.email
                ],
                fail_silently=True,
            )

            print(
                f'EMAIL PROCESS FINISHED FOR: '
                f'{user.email}'
            )

        except Exception as e:

            # =================================================
            # NEVER BREAK ADMIN IF EMAIL FAILS
            # =================================================

            print(
                f'EMAIL ERROR: {repr(e)}'
            )


# =========================================================
# NOTIFICATIONS
# =========================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'title',
        'is_read',
        'created_at',
    )

    list_filter = (
        'is_read',
        'created_at',
    )

    search_fields = (
        'user__username',
        'title',
        'message',
    )

    readonly_fields = (
        'created_at',
    )


# =========================================================
# ACTIVITY LOG
# =========================================================

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'action',
        'created_at',
    )

    list_filter = (
        'created_at',
    )

    search_fields = (
        'action',
        'detail',
        'user__username',
    )

    readonly_fields = (
        'created_at',
    )
