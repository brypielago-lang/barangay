import csv
from io import BytesIO

import qrcode

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.db.models import Count
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils import timezone

from .forms import RequestForm, ResidentForm, SignUpForm
from .models import (
    ActivityLog,
    BarangayProfile,
    CertificateRequest,
    CertificateTemplate,
    Notification,
    Resident,
)


# =========================================================
# STAFF ACCESS
# =========================================================

def staff_required(view):
    return user_passes_test(
        lambda u: u.is_staff
    )(view)


# =========================================================
# ACTIVITY LOG
# =========================================================

def log(user, action, detail=''):
    ActivityLog.objects.create(
        user=user,
        action=action,
        detail=detail
    )


# =========================================================
# WEBSITE NOTIFICATION + EMAIL
# =========================================================

def notify_request(request_obj, title, message):

    resident = request_obj.resident

    user = resident.user

    print("======================================")
    print("NOTIFICATION SYSTEM")
    print("Request:", request_obj.reference_no)
    print("Resident:", resident.full_name)
    print("User:", user)
    print(
        "Email:",
        user.email if user else "NO USER"
    )
    print("======================================")

    # -----------------------------------------------------
    # CHECK USER
    # -----------------------------------------------------

    if not user:

        print(
            "NOTIFICATION ERROR: "
            "Resident has no connected user account."
        )

        return

    # =====================================================
    # 1. WEBSITE NOTIFICATION
    # =====================================================

    try:

        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            url=f'/requests/{request_obj.pk}/'
        )

        print(
            "WEBSITE NOTIFICATION CREATED:",
            notification.id
        )

    except Exception as e:

        print(
            "WEBSITE NOTIFICATION ERROR:",
            repr(e)
        )

    # =====================================================
    # 2. EMAIL NOTIFICATION
    # =====================================================

    if user.email:

        try:

            send_mail(
                subject=title,
                message=message,
                from_email=None,
                recipient_list=[
                    user.email
                ],
                fail_silently=False
            )

            print(
                "EMAIL SENT SUCCESSFULLY TO:",
                user.email
            )

        except Exception as e:

            print(
                "EMAIL ERROR:",
                repr(e)
            )

    else:

        print(
            "EMAIL NOT SENT: "
            "User account has no email address."
        )


# =========================================================
# SIGN UP
# =========================================================

def signup(request):

    if request.method == 'POST':

        form = SignUpForm(
            request.POST
        )

        if form.is_valid():

            user = form.save()

            login(
                request,
                user
            )

            messages.info(
                request,
                'Your account is ready. Please complete your resident profile.'
            )

            return redirect(
                'profile'
            )

    else:

        form = SignUpForm()

    return render(
        request,
        'registration/signup.html',
        {
            'form': form
        }
    )


# =========================================================
# DASHBOARD
# =========================================================

@login_required
def dashboard(request):

    profile = getattr(
        request.user,
        'resident_profile',
        None
    )

    # =====================================================
    # ADMIN DASHBOARD
    # =====================================================

    if request.user.is_staff:

        context = {

            'total_residents':
                Resident.objects.filter(
                    is_active=True
                ).count(),

            'pending':
                CertificateRequest.objects.filter(
                    status='pending'
                ).count(),

            'approved':
                CertificateRequest.objects.filter(
                    status='approved'
                ).count(),

            'recent':
                CertificateRequest.objects
                .select_related('resident')
                .order_by('-requested_at')[:8],
        }

        return render(
            request,
            'core/staff_dashboard.html',
            context
        )

    # =====================================================
    # USER DASHBOARD
    # =====================================================

    recent = []

    if profile:

        recent = (
            profile.requests
            .all()
            .order_by('-requested_at')[:5]
        )

    return render(
        request,
        'core/dashboard.html',
        {
            'profile': profile,
            'recent': recent
        }
    )


# =========================================================
# RESIDENT PROFILE
# =========================================================

@login_required
def profile(request):

    resident = getattr(
        request.user,
        'resident_profile',
        None
    )

    if request.method == 'POST':

        form = ResidentForm(
            request.POST,
            request.FILES,
            instance=resident
        )

        if form.is_valid():

            obj = form.save(
                commit=False
            )

            obj.user = request.user

            obj.save()

            log(
                request.user,
                'Updated resident profile',
                obj.full_name
            )

            messages.success(
                request,
                'Profile saved.'
            )

            return redirect(
                'dashboard'
            )

    else:

        form = ResidentForm(
            instance=resident
        )

    return render(
        request,
        'core/profile.html',
        {
            'form': form
        }
    )


# =========================================================
# CREATE CERTIFICATE REQUEST
# =========================================================

@login_required
def request_create(request):

    resident = getattr(
        request.user,
        'resident_profile',
        None
    )

    if not resident:

        messages.warning(
            request,
            'Complete your resident profile first.'
        )

        return redirect(
            'profile'
        )

    if request.method == 'POST':

        form = RequestForm(
            request.POST
        )

        if form.is_valid():

            obj = form.save(
                commit=False
            )

            obj.resident = resident

            obj.save()

            log(
                request.user,
                'Submitted certificate request',
                obj.reference_no
            )

            messages.success(
                request,
                f'Request {obj.reference_no} submitted.'
            )

            return redirect(
                'request_detail',
                pk=obj.pk
            )

    else:

        form = RequestForm(
            initial={
                'certificate_type':
                    request.GET.get(
                        'type',
                        ''
                    )
            }
        )

    return render(
        request,
        'core/request_form.html',
        {
            'form': form
        }
    )


# =========================================================
# REQUEST DETAIL
# =========================================================

@login_required
def request_detail(request, pk):

    obj = get_object_or_404(
        CertificateRequest.objects
        .select_related(
            'resident__user'
        ),
        pk=pk
    )

    # Resident can only see own request
    if (
        not request.user.is_staff
        and obj.resident.user_id != request.user.id
    ):
        raise Http404

    return render(
        request,
        'core/request_detail.html',
        {
            'item': obj
        }
    )


# =========================================================
# STAFF REQUESTS
# =========================================================

@staff_required
def staff_requests(request):

    status = request.GET.get(
        'status',
        ''
    )

    if status:

        items = (
            CertificateRequest.objects
            .select_related('resident')
            .filter(status=status)
            .order_by('-requested_at')
        )

    else:

        items = (
            CertificateRequest.objects
            .select_related('resident')
            .order_by('-requested_at')
        )

    return render(
        request,
        'core/staff_requests.html',
        {
            'items': items,
            'active_status': status
        }
    )


# =========================================================
# UPDATE REQUEST
# =========================================================

@staff_required
def update_request(request, pk):

    obj = get_object_or_404(
        CertificateRequest.objects
        .select_related(
            'resident__user'
        ),
        pk=pk
    )

    if request.method != 'POST':

        return redirect(
            'request_detail',
            pk=pk
        )

    # -----------------------------------------------------
    # GET STATUS FROM ADMIN FORM
    # -----------------------------------------------------

    status = request.POST.get(
        'status'
    )

    valid_statuses = dict(
        CertificateRequest.STATUS
    )

    if status not in valid_statuses:

        messages.error(
            request,
            'Invalid request status.'
        )

        return redirect(
            'request_detail',
            pk=pk
        )

    # -----------------------------------------------------
    # UPDATE REQUEST
    # -----------------------------------------------------

    obj.status = status

    obj.remarks = request.POST.get(
        'remarks',
        ''
    )

    obj.reviewed_by = request.user

    # Approved / rejected date
    if status in (
        'approved',
        'rejected'
    ):

        obj.reviewed_at = timezone.now()

    # Released date
    if status == 'released':

        obj.released_at = timezone.now()

    obj.save()

    # =====================================================
    # SEND NOTIFICATION TO USER
    # =====================================================

    certificate_name = (
        obj.get_certificate_type_display()
    )

    status_text = (
        obj.get_status_display()
    )

    notification_title = (
        f'Certificate Request {status_text}'
    )

    notification_message = (
        f'Your {certificate_name} request '
        f'({obj.reference_no}) '
        f'is now {status_text.lower()}.'
    )

    if obj.remarks:

        notification_message += (
            f'\n\nRemarks: {obj.remarks}'
        )

    # -----------------------------------------------------
    # CALL NOTIFICATION SYSTEM
    # -----------------------------------------------------

    notify_request(
        obj,
        notification_title,
        notification_message
    )

    # =====================================================
    # ACTIVITY LOG
    # =====================================================

    log(
        request.user,
        f'Changed request to {status}',
        obj.reference_no
    )

    messages.success(
        request,
        f'Request {obj.reference_no} '
        f'updated to {status_text}.'
    )

    return redirect(
        'request_detail',
        pk=pk
    )


# =========================================================
# CERTIFICATE / DOCUMENT
# =========================================================

@login_required
def certificate_pdf(request, pk):

    obj = get_object_or_404(
        CertificateRequest.objects
        .select_related(
            'resident__user'
        ),
        pk=pk
    )

    # -----------------------------------------------------
    # ACCESS CONTROL
    # -----------------------------------------------------

    if (
        not request.user.is_staff
        and obj.resident.user_id != request.user.id
    ):
        raise Http404

    # -----------------------------------------------------
    # APPROVAL CHECK
    # -----------------------------------------------------

    if obj.status not in (
        'approved',
        'released'
    ):

        messages.error(
            request,
            'This document is not yet approved.'
        )

        return redirect(
            'request_detail',
            pk=pk
        )

    # =====================================================
    # CERTIFICATE TEMPLATES
    # =====================================================

    certificate_templates = {

        'indigency':
            'core/indigency.html',

        'clearance':
            'core/clearance.html',

        'residency':
            'core/residency.html',

        'business':
            'core/business.html',

        'good_moral':
            'core/good_moral.html',
    }

    template_name = certificate_templates.get(
        obj.certificate_type,
        'core/default.html'
    )

    # =====================================================
    # BARANGAY PROFILE
    # =====================================================

    barangay = (
        BarangayProfile.objects
        .first()
    )

    if barangay is None:

        barangay = BarangayProfile()

    # =====================================================
    # ADMIN CERTIFICATE TEMPLATE
    # =====================================================

    certificate_template = (
        CertificateTemplate.objects
        .filter(
            certificate_type=obj.certificate_type
        )
        .first()
    )

    if certificate_template:

        title = (
            certificate_template.title
        )

        footer = (
            certificate_template.footer
            or ''
        )

    else:

        title = (
            obj.get_certificate_type_display()
        )

        footer = ''

    # =====================================================
    # CERTIFICATE BODY
    # =====================================================

    body = ''

    if (
        certificate_template
        and certificate_template.body
    ):

        try:

            body = Template(
                certificate_template.body
            ).render(
                Context({
                    'resident':
                        obj.resident,

                    'request':
                        obj,

                    'barangay':
                        barangay,
                })
            )

        except Exception as e:

            print(
                'CERTIFICATE BODY ERROR:',
                repr(e)
            )

            body = (
                certificate_template.body
            )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        'item':
            obj,

        'resident':
            obj.resident,

        'request':
            obj,

        'barangay':
            barangay,

        'title':
            title,

        'body':
            body,

        'footer':
            footer,
    }

    # =====================================================
    # DOWNLOAD PDF
    # =====================================================

    if request.GET.get(
        'download'
    ) == 'pdf':

        try:

            from weasyprint import HTML

            html = render_to_string(
                template_name,
                context,
                request=request
            )

            pdf = HTML(
                string=html,
                base_url=request.build_absolute_uri('/')
            ).write_pdf()

            response = HttpResponse(
                pdf,
                content_type='application/pdf'
            )

            response[
                'Content-Disposition'
            ] = (
                f'attachment; '
                f'filename="{obj.reference_no}.pdf"'
            )

            return response

        except Exception as e:

            print(
                'PDF ERROR:',
                repr(e)
            )

            messages.error(
                request,
                'PDF download failed. Please use Print Document.'
            )

            return redirect(
                'request_detail',
                pk=obj.pk
            )

    # =====================================================
    # PRINT DOCUMENT
    # =====================================================

    return render(
        request,
        template_name,
        context
    )


# =========================================================
# VERIFY CERTIFICATE
# =========================================================

def verify(request, token):

    obj = get_object_or_404(
        CertificateRequest,
        verification_token=token
    )

    return render(
        request,
        'core/verify.html',
        {
            'item': obj
        }
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

@login_required
def notifications(request):

    notes = (
        Notification.objects
        .filter(
            user=request.user
        )
        .order_by(
            '-created_at'
        )
    )

    # -----------------------------------------------------
    # Mark notifications as read
    # -----------------------------------------------------

    notes.filter(
        is_read=False
    ).update(
        is_read=True
    )

    return render(
        request,
        'core/notifications.html',
        {
            'notes': notes
        }
    )


# =========================================================
# REPORTS
# =========================================================

@staff_required
def reports(request):

    by_type = (
        CertificateRequest.objects
        .values(
            'certificate_type'
        )
        .annotate(
            total=Count('id')
        )
        .order_by(
            '-total'
        )
    )

    recent_logs = (
        ActivityLog.objects
        .select_related(
            'user'
        )[:15]
    )

    return render(
        request,
        'core/reports.html',
        {
            'by_type': by_type,
            'recent_logs': recent_logs
        }
    )


# =========================================================
# CSV REPORT
# =========================================================

@staff_required
def report_csv(request):

    response = HttpResponse(
        content_type='text/csv'
    )

    response[
        'Content-Disposition'
    ] = (
        'attachment; '
        'filename="certificate_requests.csv"'
    )

    writer = csv.writer(
        response
    )

    writer.writerow([
        'Reference',
        'Resident',
        'Type',
        'Status',
        'Requested'
    ])

    requests = (
        CertificateRequest.objects
        .select_related(
            'resident'
        )
    )

    for obj in requests:

        writer.writerow([

            obj.reference_no,

            obj.resident.full_name,

            obj.get_certificate_type_display(),

            obj.get_status_display(),

            obj.requested_at.strftime(
                '%Y-%m-%d'
            )
        ])

    return response


# =========================================================
# QR CODE
# =========================================================

def qr_code(request, token):

    verification_url = (
        request.build_absolute_uri(
            f'/verify/{token}/'
        )
    )

    image = qrcode.make(
        verification_url
    )

    stream = BytesIO()

    image.save(
        stream,
        'PNG'
    )

    return HttpResponse(
        stream.getvalue(),
        content_type='image/png'
    )
