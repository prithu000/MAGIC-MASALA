"""apps/accounts/forms.py"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Address, CustomerProfile

User = get_user_model()


class CustomerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=60, required=True)
    last_name = forms.CharField(max_length=60, required=True)
    phone = forms.CharField(max_length=15, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists. Please log in.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            phone = self.cleaned_data.get("phone")
            if phone:
                user.profile.phone = phone
                user.profile.save()
        return user


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ("user",)
        widgets = {
            "address_type": forms.RadioSelect,
        }


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)

    class Meta:
        model = CustomerProfile
        fields = ("phone", "alternate_phone", "avatar")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.user.first_name
        self.fields["last_name"].initial = self.user.last_name

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and hasattr(avatar, "size"):
            from apps.core.validators import validate_image_size, validate_image_type
            validate_image_size(avatar)
            validate_image_type(avatar)
        return avatar

    def save(self, commit=True):
        profile = super().save(commit=commit)
        self.user.first_name = self.cleaned_data["first_name"]
        self.user.last_name = self.cleaned_data["last_name"]
        self.user.save()
        return profile
