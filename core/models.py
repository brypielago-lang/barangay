import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

class BarangayProfile(models.Model):
    name = models.CharField(max_length=150, default='Barangay Mabuhay')
    municipality = models.CharField(max_length=150, blank=True)
    province = models.CharField(max_length=150, blank=True)
    logo = models.ImageField(upload_to='branding/', blank=True, null=True)
    captain_name = models.CharField(max_length=150, blank=True)
    secretary_name = models.CharField(max_length=150, blank=True)
    address = models.TextField(blank=True)
    contact_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    def __str__(self): return self.name

class Resident(models.Model):
    SEX = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    CIVIL = [('single', 'Single'), ('married', 'Married'), ('widowed', 'Widowed'), ('separated', 'Separated')]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resident_profile', null=True, blank=True)
    resident_no = models.CharField(max_length=24, unique=True, blank=True)
    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80)
    birth_date = models.DateField()
    sex = models.CharField(max_length=1, choices=SEX)
    civil_status = models.CharField(max_length=12, choices=CIVIL, default='single')
    address = models.TextField()
    purok = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=30, blank=True)
    occupation = models.CharField(max_length=120, blank=True)
    photo = models.ImageField(upload_to='residents/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    @property
    def full_name(self): return ' '.join(x for x in [self.first_name, self.middle_name, self.last_name] if x)
    def save(self, *args, **kwargs):
        if not self.resident_no: self.resident_no = f'RES-{timezone.now():%Y}-{uuid.uuid4().hex[:6].upper()}'
        super().save(*args, **kwargs)
    def __str__(self): return f'{self.resident_no} — {self.full_name}'

class CertificateTemplate(models.Model):
    TYPES = [('clearance','Barangay Clearance'), ('residency','Certificate of Residency'), ('indigency','Certificate of Indigency'), ('good_moral','Certificate of Good Moral'), ('business','Business Permit')]
    certificate_type = models.CharField(max_length=20, choices=TYPES, unique=True)
    title = models.CharField(max_length=150)
    body = models.TextField(help_text='Use {{ resident.full_name }}, {{ request.purpose }}, and {{ barangay.name }}.')
    footer = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return self.title

class IDTemplate(models.Model):
    name = models.CharField(max_length=100, default='Official Barangay ID')
    header_color = models.CharField(max_length=7, default='#0d6efd')
    accent_color = models.CharField(max_length=7, default='#ffc107')
    show_qr = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return self.name

class CertificateRequest(models.Model):
    TYPES = CertificateTemplate.TYPES
    STATUS = [('pending','Pending'), ('reviewing','Under review'), ('approved','Approved'), ('released','Released'), ('rejected','Rejected')]
    reference_no = models.CharField(max_length=30, unique=True, blank=True)
    resident = models.ForeignKey(Resident, on_delete=models.PROTECT, related_name='requests')
    certificate_type = models.CharField(max_length=20, choices=TYPES)
    purpose = models.TextField()
    business_name = models.CharField(max_length=150, blank=True)
    business_address = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default='pending')
    remarks = models.TextField(blank=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_requests')
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    def save(self, *args, **kwargs):
        if not self.reference_no: self.reference_no = f'BRGY-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:5].upper()}'
        super().save(*args, **kwargs)
    def __str__(self): return self.reference_no

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']

class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=150)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
    def __str__(self): return self.action
