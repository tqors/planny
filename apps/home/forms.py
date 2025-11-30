# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django import forms
from django.db import connection


class ProjectForm(forms.Form):
    projectName = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter project name'
        })
    )
    deadline = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    clientId = forms.IntegerField(
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        # Populate clientId choices from database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT clientID, companyName FROM client")
                clients = cursor.fetchall()
                self.fields['clientId'].widget.choices = [('', '-- Select a Client --')] + [(c[0], c[1]) for c in clients]
        except Exception:
            self.fields['clientId'].widget.choices = [('', '-- Select a Client --')]
