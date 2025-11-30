# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from . import models

User = get_user_model()

for name, model in vars(models).items():
    if not (isinstance(model, type) and hasattr(model, "_meta")):
        continue
    # skip models not defined in this app (e.g. imported AbstractUser)
    if model.__module__ != models.__name__:
        continue
    # skip abstract models
    if getattr(model._meta, "abstract", False):
        continue

    # register the project's User with Django's UserAdmin for proper admin handling
    if model is User:
        try:
            admin.site.register(model, DjangoUserAdmin)
        except admin.sites.AlreadyRegistered:
            pass
        continue

    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass
