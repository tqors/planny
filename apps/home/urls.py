# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path, re_path
from apps.home import views

urlpatterns = [

    # The home page
    path('', views.index, name='home'),
    
    # Kanban page
    path('kanban/', views.kanban, name='kanban'),
    
    # Projects page
    path('projects/', views.projects, name='projects'),
    
    # Create project
    path('project/create/', views.create_project, name='create_project'),

    # Kanban API endpoints
    path('api/kanban-tasks/', views.kanban_tasks_api, name='kanban_tasks_api'),
    path('api/kanban-tasks/<int:task_id>/', views.kanban_task_detail_api, name='kanban_task_detail_api'),
    path('api/projects/', views.projects_api, name='projects_api'),
    path('api/developers/', views.developers_api, name='developers_api'),
    path('api/calendar-event/', views.calendar_event_api, name='calendar_event_api'),

    path('project/<int:project_id>/timeline/', views.project_timeline, name='project_timeline'),
    path('project/<int:project_id>/edit/', views.edit_project, name='edit_project'),

    # Matches any html file
    re_path(r'^.*\.*', views.pages, name='pages'),

]
