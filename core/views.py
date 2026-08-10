import csv
import os
from io import BytesIO
from urllib.parse import urlencode
from urllib.request import Request as URLRequest
from urllib.request import urlopen
from base64 import b64encode

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
# PHONE NUMBER FORMAT
# =========================================================

def format_philippine_number(number):
    """
    Converts common Philippine mobile formats:

    09171234567
    9171234567
    +639171234567

    into:

    +639171234567
    """

    if not number:
        return None

    number = str(number).strip()

    # Remove spaces, dash and parentheses
    number = (
        number
        .replace(' ', '')
        .replace('-', '')
        .replace('(', '')
        .replace(')', '')
    )

    if number.startswith('+63'):
        return number

    if number.startswith('63'):
        return '+' + number

    if number.startswith('09'):
        return '+63' + number[1:]

    if number.startswith('9') and len(number) == 10:
        return '+63' + number

    return number


# =========================================================
# SEND SMS USING TWILIO
# =========================================================

def send_sms(phone_number, message):
    """
    Sends SMS using Twilio REST API.

    Required environment variables:

    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_PHONE_NUMBER
    """

    account_sid = os.environ.get(
        'TWILIO_ACCOUNT_SID'
    )

    auth_token = os.environ.get(
        'TWILIO_AUTH_TOKEN'
    )

    twilio_phone = os.environ.get(
        'TWILIO_PHONE_NUMBER'
    )

    if not account_sid:
        print(
            'SMS NOT SENT: TWILIO_ACCOUNT_SID is missing.'
        )
        return False

    if not auth_token:
        print(
            'SMS NOT SENT: TWILIO_AUTH_TOKEN is missing.'
        )
        return False

    if not twilio_phone:
        print(
            'SMS NOT SENT: TWILIO_PHONE_NUMBER is missing.'
        )
        return False

    formatted_number = format_philippine_number(
        phone_number
    )

    if not formatted_number:
        print(
            'SMS NOT SENT: Resident has no contact number.'
        )
        return False

    url = (
        f'https://api.twilio.com/2010-04-01/'
        f'Accounts/{account_sid}/Messages.json'
    )

    data = urlencode({
        'From': twilio_phone,
        'To': formatted_number,
        'Body': message,
    }).encode('utf-8')

    credentials = (
        f'{account_sid}:{auth_token}'
    ).encode('utf-8')

    authorization = (
        'Basic '
        + b64encode(credentials).decode('ascii')
    )

    request = URLRequest(
        url,
        data=data,
        method='POST',
        headers={
            'Authorization': authorization,
            'Content-Type':
                'application/x-www-form-urlencoded',
        }
    )

    try:

        with urlopen(
            request,
            timeout=20
        ) as response:

            response.read()

        print(
            f'SMS SENT TO: {formatted_number}'
        )

        return True

    except Exception as e:

        print(
            f'SMS ERROR: {repr(e)}'
        )

        return False


# =========================================================
# NOTIFICATION + EMAIL + SMS
# =========================================================

def notify_request(
    request_obj,
    title,
    message
):

    resident = request_obj.resident

    user = resident.user

    # -----------------------------------------------------
    # CHECK USER ACCOUNT
    # -----------------------------------------------------

    if not user:

        print(
            'NOTIFICATION ERROR: '
            f'Resident {resident.full_name} '
            'has no linked user account.'
        )

        return


    # =====================================================
    # 1. WEBSITE NOTIFICATION
    # =====================================================

    try:

        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            url=f'/requests/{request_obj.pk}/'
        )

        print(
            f'NOTIFICATION CREATED FOR: '
            f'{user.username}'
        )

    except Exception as e:

        print(
            f'NOTIFICATION ERROR: {repr(e)}'
        )


    # =====================================================
    # 2. EMAIL
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
                fail_silently=False,
            )

            print(
                f'EMAIL SENT TO: {user.email}'
            )

        except Exception as e:

            print(
                f'EMAIL ERROR: {repr(e)}'
            )

    else:

        print(
            'EMAIL NOT SENT: '
            'User has no email address.'
        )


    # =====================================================
    # 3. SMS
    # =====================================================

    sms_message = (
        f'Barangay Maniwaya: {message}'
    )

    send_sms(
        resident.contact_number,
        sms_message
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
                'Your account is ready. '
                'Please complete your resident profile.'
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

    # -----------------------------------------------------
    # ADMIN DASHBOARD
    # -----------------------------------------------------

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
                [:8],
        }

        return render(
            request,
            'core/staff_dashboard.html',
            context
        )


    # -----------------------------------------------------
    # USER DASHBOARD
    # -----------------------------------------------------

    recent = []

    if profile:

        recent = (
            profile.requests
            .all()
            .order_by('-requested_at')
            [:5]
        )


    # -----------------------------------------------------
    # UNREAD NOTIFICATIONS
    # -----------------------------------------------------

    unread_notifications = (
        request.user.notifications
        .filter(
            is_read=False
        )
        .count()
    )


    # -----------------------------------------------------
    # RECENT NOTIFICATIONS
    # -----------------------------------------------------

    recent_notifications = (
        request.user.notifications
        .all()
        [:5]
    )


    return render(
        request,
        'core/dashboard.html',
        {
            'profile':
                profile,

            'recent':
                recent,

            'unread_notifications':
                unread_notifications,

            'recent_notifications':
                recent_notifications,
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
            .select_related(
                'resident'
            )
            .filter(
                status=status
            )
            .order_by(
                '-requested_at'
            )
        )

    else:

        items = (
            CertificateRequest.objects
            .select_related(
                'resident'
            )
            .order_by(
                '-requested_at'
            )
        )

    return render(
        request,
        'core/staff_requests.html',
        {
            'items':
                items,

            'active_status':
                status
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

    if request.method == 'POST':

        status = request.POST.get(
            'status'
        )

        valid_statuses = dict(
            CertificateRequest.STATUS
        )

        if status in valid_statuses:

            old_status = obj.status

            # -------------------------------------------------
            # PREVENT DUPLICATE NOTIFICATION
            # -------------------------------------------------

            if old_status == status:

                obj.remarks = request.POST.get(
                    'remarks',
                    ''
                )

                obj.reviewed_by = request.user

                obj.save(
                    update_fields=[
                        'remarks',
                        'reviewed_by'
                    ]
                )

                messages.info(
                    request,
                    f'Request is already '
                    f'{obj.get_status_display()}.'
                )

                return redirect(
                    'request_detail',
                    pk=pk
                )


            # -------------------------------------------------
            # UPDATE STATUS
            # -------------------------------------------------

            obj.status = status

            obj.remarks = request.POST.get(
                'remarks',
                ''
            )

            obj.reviewed_by = request.user


            # -------------------------------------------------
            # APPROVED / REJECTED
            # -------------------------------------------------

            if status in (
                'approved',
                'rejected'
            ):

                obj.reviewed_at = timezone.now()


            # -------------------------------------------------
            # RELEASED
            # -------------------------------------------------

            if status == 'released':

                obj.released_at = timezone.now()


            obj.save()


            # =================================================
            # NOTIFICATION MESSAGE
            # =================================================

            status_text = (
                obj.get_status_display()
            )

            certificate_name = (
                obj.get_certificate_type_display()
            )

            notification_title = (
                f'Certificate Request {status_text}'
            )

            notification_message = (
                f'Your {certificate_name} request '
                f'({obj.reference_no}) '
                f'is now {status_text.lower()}.'
            )


            # -------------------------------------------------
            # APPROVED MESSAGE
            # -------------------------------------------------

            if status == 'approved':

                notification_message = (
                    f'Your {certificate_name} request '
                    f'({obj.reference_no}) has been '
                    f'APPROVED. You may now print or '
                    f'download your certificate.'
                )


            # -------------------------------------------------
            # REJECTED MESSAGE
            # -------------------------------------------------

            elif status == 'rejected':

                notification_message = (
                    f'Your {certificate_name} request '
                    f'({obj.reference_no}) has been '
                    f'REJECTED.'
                )


            # -------------------------------------------------
            # RELEASED MESSAGE
            # -------------------------------------------------

            elif status == 'released':

                notification_message = (
                    f'Your {certificate_name} request '
                    f'({obj.reference_no}) has been '
                    f'RELEASED and is ready.'
                )


            # -------------------------------------------------
            # REMARKS
            # -------------------------------------------------

            if obj.remarks:

                notification_message += (
                    f'\n\nRemarks: {obj.remarks}'
                )


            # =================================================
            # SEND NOTIFICATION + EMAIL + SMS
            # =================================================

            notify_request(
                obj,
                notification_title,
                notification_message
            )


            # =================================================
            # ACTIVITY LOG
            # =================================================

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

        else:

            messages.error(
                request,
                'Invalid request status.'
            )

    return redirect(
        'request_detail',
        pk=pk
    )


# =========================================================
# CERTIFICATE DOCUMENT
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


    # -----------------------------------------------------
    # CERTIFICATE TEMPLATE
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # BARANGAY PROFILE
    # -----------------------------------------------------

    barangay = (
        BarangayProfile.objects
        .first()
    )


    if barangay is None:

        barangay = BarangayProfile()


    # -----------------------------------------------------
    # ADMIN CERTIFICATE TEMPLATE
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # CERTIFICATE BODY
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # CONTEXT
    # -----------------------------------------------------

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
                'PDF download failed. '
                'Please use Print Document.'
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
        request.user.notifications
        .all()
    )

    return render(
        request,
        'core/notifications.html',
        {
            'notes':
                notes
        }
    )


# =========================================================
# MARK NOTIFICATION AS READ
# =========================================================

@login_required
def mark_notification_read(
    request,
    pk
):

    notification = get_object_or_404(
        Notification,
        pk=pk,
        user=request.user
    )

    notification.is_read = True

    notification.save(
        update_fields=[
            'is_read'
        ]
    )

    if notification.url:

        return redirect(
            notification.url
        )

    return redirect(
        'notifications'
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
            'by_type':
                by_type,

            'recent_logs':
                recent_logs
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
