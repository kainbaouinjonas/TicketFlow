from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(
        required=True,
        label="Numéro de téléphone (avec indicatif pays, ex: +225...)",
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: +2250707070707',
        })
    )
    role = forms.ChoiceField(choices=[('USER', 'Acheteur'), ('ORGANIZER', 'Organisateur')])

    INPUT_CLASSES = (
        "w-full px-4 py-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 "
        "rounded-xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-brand-500 transition "
        "text-slate-900 dark:text-slate-100"
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['password1', 'password2']:
            self.fields[field_name].widget.attrs.update({'class': self.INPUT_CLASSES})

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not phone:
            raise forms.ValidationError("Le numéro de téléphone est obligatoire.")
        
        # Doit commencer par '+'
        if not phone.startswith('+'):
            raise forms.ValidationError("Le numéro de téléphone doit inclure l'indicatif pays commençant par '+' (ex: +225 pour la Côte d'Ivoire).")
        
        # Le reste doit contenir uniquement des chiffres (pas de lettres)
        digits_part = phone[1:]
        if not digits_part.isdigit():
            raise forms.ValidationError("Le numéro de téléphone ne doit contenir que des chiffres après le '+'. Les lettres sont interdites.")
        
        # Longueur minimum
        if len(phone) < 10:
            raise forms.ValidationError("Le numéro de téléphone est trop court. Veuillez entrer le numéro complet avec indicatif.")
            
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.role = self.cleaned_data['role']
        if user.role == 'ORGANIZER':
            user.is_active = False  # En attente d'approbation administrative
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    INPUT_CLASSES = (
        "w-full px-4 py-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 "
        "rounded-xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-brand-500 transition "
        "text-slate-900 dark:text-slate-100"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': self.INPUT_CLASSES,
            'placeholder': 'Votre nom d\'utilisateur'
        })
        self.fields['password'].widget.attrs.update({
            'class': self.INPUT_CLASSES,
            'placeholder': '••••••••'
        })
