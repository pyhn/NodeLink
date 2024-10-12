from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class':'form-control', 'placeholder':'Email'})
    )
    first_name = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'First Name'})
    )
    last_name = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Last Name'})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class':'form-control', 'placeholder':'Description'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'description', 'password1', 'password2')

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class':'form-control', 'placeholder':'Password'})
    )

    class Meta:
        model = User
        fields = ('username', 'password')
