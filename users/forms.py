# Formularios de usuario (registro).

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class RegisterForm(UserCreationForm):
    """Formulario de registro con email obligatorio."""

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este email.')
        return email


class ProfileForm(forms.ModelForm):
    """Edición de los datos de perfil del usuario."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'bio', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'avatar': forms.ClearableFileInput(attrs={
                'accept': 'image/png,image/jpeg,image/webp',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ya existe una cuenta con este email.')
        return email
