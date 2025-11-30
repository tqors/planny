# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path, re_path
from apps.home import views

urlpatterns = [

    # The home page
    path('', views.index, name='home'),
    
    # Projects page
    path('projects/', views.projects, name='projects'),
    
    # Create project
    path('create-project/', views.create_project, name='create_project'),

    # Matches any html file
    re_path(r'^.*\.*', views.pages, name='pages'),

]
