import csv
from io import BytesIO
import qrcode
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.template import Context, Template
from django.utils import timezone
from .forms import RequestForm, ResidentForm, SignUpForm
from .models import ActivityLog, BarangayProfile, CertificateRequest, CertificateTemplate, Notification, Resident

def staff_required(view): return user_passes_test(lambda u: u.is_staff)(view)
def log(user, action, detail=''): ActivityLog.objects.create(user=user, action=action, detail=detail)
def notify_request(request, title, message):
    if request.resident.user: Notification.objects.create(user=request.resident.user, title=title, message=message, url=f'/requests/{request.pk}/')

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(); login(request, user)
            messages.info(request, 'Your account is ready. Please complete your resident profile.')
            return redirect('profile')
    else: form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def dashboard(request):
    profile = getattr(request.user, 'resident_profile', None)
    if request.user.is_staff:
        context = {'total_residents': Resident.objects.filter(is_active=True).count(), 'pending': CertificateRequest.objects.filter(status='pending').count(),
                   'approved': CertificateRequest.objects.filter(status='approved').count(), 'recent': CertificateRequest.objects.select_related('resident')[:8]}
        return render(request, 'core/staff_dashboard.html', context)
    return render(request, 'core/dashboard.html', {'profile': profile, 'recent': profile.requests.all()[:5] if profile else []})

@login_required
def profile(request):
    resident = getattr(request.user, 'resident_profile', None)
    if request.method == 'POST':
        form = ResidentForm(request.POST, request.FILES, instance=resident)
        if form.is_valid():
            obj = form.save(commit=False); obj.user = request.user; obj.save(); log(request.user, 'Updated resident profile', obj.full_name)
            messages.success(request, 'Profile saved.'); return redirect('dashboard')
    else: form = ResidentForm(instance=resident)
    return render(request, 'core/profile.html', {'form': form})

@login_required
def request_create(request):
    resident = getattr(request.user, 'resident_profile', None)
    if not resident: messages.warning(request, 'Complete your resident profile first.'); return redirect('profile')
    if request.method == 'POST':
        form = RequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False); obj.resident = resident; obj.save(); log(request.user, 'Submitted certificate request', obj.reference_no)
            messages.success(request, f'Request {obj.reference_no} submitted.'); return redirect('request_detail', pk=obj.pk)
    else: form = RequestForm(initial={'certificate_type': request.GET.get('type', '')})
    return render(request, 'core/request_form.html', {'form': form})

@login_required
def request_detail(request, pk):
    obj = get_object_or_404(CertificateRequest.objects.select_related('resident'), pk=pk)
    if not request.user.is_staff and obj.resident.user_id != request.user.id: raise Http404
    return render(request, 'core/request_detail.html', {'item': obj})

@staff_required
def staff_requests(request):
    status = request.GET.get('status', '')
    items = CertificateRequest.objects.select_related('resident').filter(status=status) if status else CertificateRequest.objects.select_related('resident')
    return render(request, 'core/staff_requests.html', {'items': items, 'active_status': status})

@staff_required
def update_request(request, pk):
    obj = get_object_or_404(CertificateRequest, pk=pk)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(CertificateRequest.STATUS):
            obj.status = status; obj.remarks = request.POST.get('remarks', '') ; obj.reviewed_by = request.user
            if status in ('approved', 'rejected'): obj.reviewed_at = timezone.now()
            if status == 'released': obj.released_at = timezone.now()
            obj.save(); notify_request(obj, f'Request {status.title()}', f'Your {obj.get_certificate_type_display()} request ({obj.reference_no}) is now {status}.')
            log(request.user, f'Changed request to {status}', obj.reference_no); messages.success(request, 'Request updated.')
    return redirect('request_detail', pk=pk)

def certificate_pdf(request, pk):
    obj = get_object_or_404(
        CertificateRequest.objects.select_related('resident'),
        pk=pk
    )

    if not request.user.is_staff and obj.resident.user_id != request.user.id:
        raise Http404

    if obj.status not in ('approved', 'released'):
        messages.error(
            request,
            'This document is not yet approved.'
        )
        return redirect('request_detail', pk=pk)

    template = CertificateTemplate.objects.filter(
        certificate_type=obj.certificate_type
    ).first()

    barangay = BarangayProfile.objects.first() or BarangayProfile()

    title = (
        template.title
        if template
        else obj.get_certificate_type_display()
    )

    default_body = """
    This is to certify that <strong>{{ resident.full_name }}</strong>,
    a bona fide resident of <strong>{{ barangay.name }}</strong>,
    {{ barangay.municipality }}, {{ barangay.province }},
    is known to this office and has no derogatory record on file.

    This certification is issued upon the request of the
    above-named person for <strong>{{ request.purpose }}</strong>.

    Issued for whatever legal purpose this may serve.
    """

    body_template = template.body if template else default_body

    body = Template(body_template).render(
        Context({
            'resident': obj.resident,
            'request': obj,
            'barangay': barangay,
        })
    )

    context = {
        'item': obj,
        'barangay': barangay,
        'title': title,
        'body': body,
        'footer': template.footer if template else '',
    }

    if request.GET.get('download') == 'pdf':
        try:
            from weasyprint import HTML

            html = render_to_string(
                'core/certificate_print.html',
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

            response['Content-Disposition'] = (
                f'attachment; filename="{obj.reference_no}.pdf"'
            )

            return response

        except (ImportError, OSError):
            messages.warning(
                request,
                'PDF support is unavailable; use browser print to save as PDF.'
            )

    return render(
        request,
        'core/certificate_print.html',
        context
    )

def verify(request, token):
    obj = get_object_or_404(CertificateRequest, verification_token=token)
    return render(request, 'core/verify.html', {'item': obj})

@login_required
def notifications(request):
    notes = request.user.notifications.all(); notes.filter(is_read=False).update(is_read=True)
    return render(request, 'core/notifications.html', {'notes': notes})

@staff_required
def reports(request):
    by_type = CertificateRequest.objects.values('certificate_type').annotate(total=Count('id')).order_by('-total')
    return render(request, 'core/reports.html', {'by_type': by_type, 'recent_logs': ActivityLog.objects.select_related('user')[:15]})

@staff_required
def report_csv(request):
    response = HttpResponse(content_type='text/csv'); response['Content-Disposition'] = 'attachment; filename="certificate_requests.csv"'
    writer = csv.writer(response); writer.writerow(['Reference', 'Resident', 'Type', 'Status', 'Requested'])
    for x in CertificateRequest.objects.select_related('resident'):
        writer.writerow([x.reference_no, x.resident.full_name, x.get_certificate_type_display(), x.status, x.requested_at.strftime('%Y-%m-%d')])
    return response

def qr_code(request, token):
    image = qrcode.make(request.build_absolute_uri(f'/verify/{token}/')); stream = BytesIO(); image.save(stream, 'PNG')
    return HttpResponse(stream.getvalue(), content_type='image/png')
