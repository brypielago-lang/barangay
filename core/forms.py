from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import CertificateRequest, Resident


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=80)
    last_name = forms.CharField(max_length=80)

    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'password1',
            'password2',
        )


class ResidentForm(forms.ModelForm):

    email = forms.EmailField(
        required=True,
        label='Email address'
    )

    class Meta:
        model = Resident

        exclude = (
            'user',
            'resident_no',
            'is_active',
            'created_at',
        )

        widgets = {
            'birth_date': forms.DateInput(
                attrs={'type': 'date'}
            ),

            'address': forms.Textarea(
                attrs={'rows': 2}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Kunin ang email mula sa Django User
        if self.instance and self.instance.user:
            self.fields['email'].initial = (
                self.instance.user.email
            )

    def save(self, commit=True):
        resident = super().save(commit=False)

        # I-save ang email sa linked Django User
        if resident.user:
            resident.user.email = self.cleaned_data['email']
            resident.user.save(
                update_fields=['email']
            )

        if commit:
            resident.save()

        return resident


class RequestForm(forms.ModelForm):

    class Meta:
        model = CertificateRequest

        fields = (
            'certificate_type',
            'purpose',
            'business_name',
            'business_address',
        )

        widgets = {
            'purpose': forms.Textarea(
                attrs={'rows': 3}
            ),

            'business_address': forms.Textarea(
                attrs={'rows': 2}
            ),
        }
