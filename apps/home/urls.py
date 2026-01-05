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
    path('tables/', views.tables_view, name='tables'),
    
    # Create project
    path('project/create/', views.create_project, name='create_project'),
    path('project/<int:project_id>/delete/', views.delete_project, name='delete_project'),

    # Profile page
    path('profile/', views.profile, name='profile'),

    # Kanban API endpoints
    path('api/kanban-tasks/', views.kanban_tasks_api, name='kanban_tasks_api'),
    path('api/kanban-tasks/<int:task_id>/', views.kanban_task_detail_api, name='kanban_task_detail_api'),
    path('api/projects/', views.projects_api, name='projects_api'),
    path('api/developers/', views.developers_api, name='developers_api'),
    path('api/create-calendar-event/', views.create_calendar_event, name='create_calendar_event'),
    path('api/send-invitation/', views.send_invitation, name='send_invitation'),
    path('registerclient.html', views.public_registration, {'template_name': 'registerclient.html'}, name='register_client'),
    path('registerdev.html', views.public_registration, {'template_name': 'registerdev.html'}, name='register_dev'),
    path('calendar/', views.calendar_view, name='calendar'),
  


    path('project/<int:project_id>/timeline/', views.project_timeline, name='project_timeline'),
    path('project/<int:project_id>/edit/', views.edit_project, name='edit_project'),

    # Matches any html file (MUST be last to avoid catching other routes)
    # Only match files that are NOT already handled by other routes
    re_path(r'^(?!api/|project/|tables/|projects/|kanban/|profile/)[\w/]*\.html$', views.pages, name='pages'),

]
