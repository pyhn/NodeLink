from django.contrib import admin
from django import forms
from .models import Node
from django.contrib.auth.hashers import make_password
from datetime import datetime

class NodeAdminForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text='Leave blank to keep the current password.')

    class Meta:
        model = Node
        fields = ['url', 'username', 'password', 'is_active']

    def save(self, commit=True):
        node = super().save(commit=False)
        raw_password = self.cleaned_data.get('password')
        if raw_password:
            node.password = make_password(raw_password)
        else:
            if node.pk:
                # Keep the existing password if not changed
                node.password = Node.objects.get(pk=node.pk).password
        if commit:
            node.save()
        return node

@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    form = NodeAdminForm
    list_display = ('url', 'username', 'is_active', 'created_by', 'created_at', 'updated_at')
    readonly_fields = ('created_by', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
