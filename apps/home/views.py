# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader, TemplateDoesNotExist
from django.urls import reverse
from django.shortcuts import render, redirect
from django.db import connection
from datetime import datetime, time
# ProjectForm was used previously but client selection was removed from the UI


@login_required(login_url="/login/")
def index(request):
    context = {'segment': 'index'}
    return render(request, 'home/index.html', context)


@login_required(login_url="/login/")
def kanban(request):
    # direct view for the kanban page
    return render(request, 'home/kanban.html')


@login_required(login_url="/login/")
def projects(request):
    """
    Projects page view
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT clientID, companyName FROM client")
            clients = cursor.fetchall()
            
            # Fetch all projects with client and status info
            cursor.execute("""
                SELECT p.projectID, p.projectName, p.startDate, p.endDate, p.projectProgress, 
                       c.companyName, s.statusDesc
                FROM project p
                LEFT JOIN client c ON p.clientID = c.clientID
                LEFT JOIN status s ON p.statusID = s.statusID
                ORDER BY p.projectID DESC
            """)
            projects_data = cursor.fetchall()
            
        projects_list = []
        for proj in projects_data:
            projects_list.append({
                'projectID': proj[0],
                'projectName': proj[1],
                'startDate': proj[2],
                'endDate': proj[3],
                'projectProgress': proj[4] if proj[4] else 0,
                'clientName': proj[5] if proj[5] else 'No Client',
                'statusDesc': proj[6] if proj[6] else 'No Status'
            })
        
        context = {
            'segment': 'projects',
            'clients': [{'clientID': c[0], 'companyName': c[1]} for c in clients],
            'projects': projects_list
        }
    except Exception as e:
        context = {
            'segment': 'projects',
            'clients': [],
            'projects': [],
            'error': str(e)
        }
    return render(request, 'home/projects.html', context)


@login_required(login_url="/login/")
def create_project(request):
    """
    Create a new project
    """
    if request.method == 'POST':
        # Read POST fields directly (client selection removed)
        projectName = request.POST.get('projectName', '').strip()
        deadline_str = request.POST.get('deadline', '').strip()
        # Try to map the Django auth user to the custom `user` table (if present)
        createdBy = None
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT userID FROM user WHERE username = %s LIMIT 1", [request.user.username])
                row = cursor.fetchone()
                if row:
                    createdBy = row[0]
        except Exception:
            createdBy = None

        # Basic validation - require project name and deadline
        if not projectName or not deadline_str:
            # Return to projects page with a simple error message (could be improved)
            context = {'segment': 'projects', 'error': 'Project name and deadline are required.'}
            return render(request, 'home/projects.html', context)

        try:
            # Parse date (expecting YYYY-MM-DD)
            deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        except Exception:
            context = {'segment': 'projects', 'error': 'Invalid deadline date format.'}
            return render(request, 'home/projects.html', context)

        # Set deadline time to 11:59:59 (we'll store date portion in the endDate column)
        deadline_datetime = datetime.combine(deadline_date, time(23, 59, 59))

        try:
            now_date = datetime.now().date()
            with connection.cursor() as cursor:
                # Insert new project. Use NULL for statusID and clientID since client was removed.
                cursor.execute("""
                    INSERT INTO project (projectName, statusID, startDate, endDate, projectProgress, createdBy, clientID)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [projectName, None, now_date, deadline_datetime.date(), 0, createdBy, None])

            # Redirect back to projects so the page reloads and shows the new project
            return redirect('projects')
        except Exception as e:
            context = {'segment': 'projects', 'error': f'Error creating project: {str(e)}'}
            return render(request, 'home/projects.html', context)

    return redirect('projects')


@login_required(login_url="/login/")
def pages(request):
    """
    Generic page loader (keeps backward compatibility with original project).
    Request URL should end with the template name, e.g. /pages/about.html
    """
    try:
        load_template = request.path.split('/')[-1]
        if load_template in ('', 'index.html', 'index'):
            return redirect('index')
        if load_template == 'admin':
            return redirect('/admin/')

        template_path = f'home/{load_template}'
        return render(request, template_path)
    except TemplateDoesNotExist:
        return render(request, 'home/page-404.html')
    except Exception:
        return render(request, 'home/page-500.html')
