from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from .forms import CustomUserCreationForm, CustomAuthenticationForm

class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        form = CustomUserCreationForm()
        return render(request, 'auth/register.html', {'form': form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.role == 'ORGANIZER':
                messages.success(request, "Inscription réussie ! Votre compte organisateur est en attente de validation par l'administrateur.")
            else:
                messages.success(request, "Inscription réussie !")
            return redirect('login')
        return render(request, 'auth/register.html', {'form': form})


class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        form = CustomAuthenticationForm(request)
        return render(request, 'auth/login.html', {'form': form})

    def post(self, request):
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f"Bonjour {user.username} !")
            return redirect('home')
        else:
            # Vérifier si l'utilisateur est inactif
            username = request.POST.get('username')
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(username=username)
                if not user.is_active:
                    messages.error(request, "Votre compte n'a pas encore été activé ou validé par un administrateur.")
                    return render(request, 'auth/login.html', {'form': form})
            except User.DoesNotExist:
                pass
            messages.error(request, "Identifiants incorrects")
        return render(request, 'auth/login.html', {'form': form})


class LogoutView(View):
    def get(self, request):
        auth_logout(request)
        messages.info(request, "Déconnecté")
        return redirect('home')


def check_two_factor_status(request):
    return JsonResponse({'has_2fa': False})
