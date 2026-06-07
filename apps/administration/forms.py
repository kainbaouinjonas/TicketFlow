from django import forms
from events.models import Event
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

INPUT_CLASSES = (
    "w-full px-4 py-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 "
    "rounded-xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-brand-500 transition "
    "text-slate-900 dark:text-slate-100"
)

TEXTAREA_CLASSES = (
    "w-full px-4 py-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 "
    "rounded-xl text-sm font-light focus:outline-none focus:ring-2 focus:ring-brand-500 transition "
    "text-slate-900 dark:text-slate-100 resize-none"
)

SELECT_CLASSES = (
    "w-full px-4 py-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 "
    "rounded-xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-brand-500 transition "
    "text-slate-900 dark:text-slate-100"
)


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'category', 'description', 'banner', 'location', 'start_time', 'end_time', 'is_published', 'total_capacity', 'price']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Ex: Grand Concert Symphonique...',
            }),
            'category': forms.Select(attrs={
                'class': SELECT_CLASSES,
            }),
            'description': forms.Textarea(attrs={
                'class': TEXTAREA_CLASSES,
                'rows': 5,
                'placeholder': 'Décrivez l\'événement, le programme, les artistes...',
            }),
            'location': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Ex: Stade de France, Saint-Denis',
            }),
            'start_time': forms.DateTimeInput(attrs={
                'class': INPUT_CLASSES,
                'type': 'datetime-local',
            }),
            'end_time': forms.DateTimeInput(attrs={
                'class': INPUT_CLASSES,
                'type': 'datetime-local',
            }),
            'total_capacity': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Ex: 500',
                'min': '1',
                'max': '100000',
            }),
            'price': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Ex: 25.00',
                'min': '0',
                'step': '0.01',
            }),
            'is_published': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded border-slate-300 text-brand-600 focus:ring-brand-500 cursor-pointer',
            }),
            'banner': forms.FileInput(attrs={
                'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-brand-600 file:text-white hover:file:bg-brand-700 cursor-pointer',
                'accept': 'image/*',
            }),
        }


class ControllerCreateForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'controleur@example.com'})
    )
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': '+225 07 07 07 07 07'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'controleur_nom'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': INPUT_CLASSES})
        self.fields['password2'].widget.attrs.update({'class': INPUT_CLASSES})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.role = 'CONTROLLER'
        user.is_active = True
        if commit:
            user.save()
        return user
