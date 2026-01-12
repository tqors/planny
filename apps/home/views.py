"""
Copyright (c) 2019 - present AppSeed.us
"""
from datetime import timedelta
from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import loader, TemplateDoesNotExist
from django.urls import reverse
from django.shortcuts import render, redirect
from django.db import connection
from datetime import datetime, time
from django.views.decorators.http import require_http_methods
import json
import math
from django.core.mail import send_mail
from apps.home.profile_form import ProfileForm
import requests
import urllib.parse

# ...existing code...

@login_required(login_url="/login/")
def profile(request):
    user = request.user
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=user)
    return render(request, 'home/profile.html', {'form': form, 'user': user, 'segment': 'profile'})
# ProjectForm was used previously but client selection was removed from the UI


# AI-based task generation system
PROJECT_TYPE_TASKS = {
    'Web Development': [
        'Setup Database & Server Architecture',
        'Create API Endpoints',
        'Build Frontend UI Components',
        'Implement Authentication & Authorization',
        'Integrate Frontend with Backend',
        'Testing & Quality Assurance',
        'Deployment & Monitoring'
    ],
    'Mobile App': [
        'Define App Requirements & Wireframes',
        'Setup Development Environment',
        'Create User Interface (UI)',
        'Implement Core Features',
        'Add Payment/Authentication System',
        'Testing on Devices',
        'App Store Submission'
    ],
    'Desktop Software': [
        'Define Software Architecture',
        'Setup Development Framework',
        'Create User Interface',
        'Implement Core Functionality',
        'Add Database Integration',
        'Testing & Debugging',
        'Build Installer & Documentation'
    ],
    'AI/Machine Learning': [
        'Data Collection & Preparation',
        'Exploratory Data Analysis (EDA)',
        'Feature Engineering',
        'Model Selection & Training',
        'Model Evaluation & Tuning',
        'Deployment Pipeline Setup',
        'Monitoring & Maintenance'
    ],
    'Other': [
        'Project Planning & Requirements',
        'Development & Implementation',
        'Testing & Quality Assurance',
        'Review & Refinement',
        'Documentation',
        'Deployment',
        'Maintenance & Support'
    ]
}

def generate_tasks_for_project(project_type, project_id, start_date, end_date, num_sprints_input=None):
    """
    AI function to automatically generate tasks based on project type.
    Agile Update: Distributes tasks into Sprints (approx 2 weeks) with parallel execution.
    """
    # Get task templates for the project type
    task_templates = PROJECT_TYPE_TASKS.get(project_type, PROJECT_TYPE_TASKS['Other'])
    num_tasks = len(task_templates)
    
    # Calculate total duration
    total_days = (end_date - start_date).days
    if total_days < 1: total_days = 1
    
    if num_sprints_input and num_sprints_input > 0:
        num_sprints = num_sprints_input
        sprint_days = total_days // num_sprints
        if sprint_days < 1: sprint_days = 1
    else:
        # Agile Strategy: Target 2-week Sprints (14 days)
        target_sprint_days = 14
        
        # Calculate how many sprints fit in the timeline
        num_sprints = math.ceil(total_days / target_sprint_days)
        
        # Adjust if project is short or very long
        if num_sprints < 1:
            num_sprints = 1
            sprint_days = total_days
        else:
            # If we have more sprints than tasks, cap sprints to task count
            if num_sprints > num_tasks:
                num_sprints = num_tasks
            sprint_days = total_days // num_sprints

    # Determine tasks per sprint (round up to ensure all tasks are covered)
    tasks_per_sprint = math.ceil(num_tasks / num_sprints)
    
    current_sprint_start = start_date
    task_idx = 0
    
    with connection.cursor() as cursor:
        for sprint_i in range(num_sprints):
            # Calculate Sprint End Date
            if sprint_i == num_sprints - 1:
                current_sprint_end = end_date
            else:
                current_sprint_end = current_sprint_start + timedelta(days=sprint_days - 1)
            
            # Get tasks for this sprint
            sprint_tasks = task_templates[task_idx : task_idx + tasks_per_sprint]
            task_idx += tasks_per_sprint

            for task_title in sprint_tasks:
                cursor.execute("""
                    INSERT INTO task 
                    (projectID, taskTitle, taskDescription, statusID, startDate, dueDate)
                    VALUES (%s, %s, %s, 1, %s, %s)
                """, [
                project_id,
                task_title,
                f"Sprint {sprint_i + 1} Task - {project_type}",
                current_sprint_start,
                current_sprint_end
            ])
            
            # Next sprint starts the day after this one ends
            current_sprint_start = current_sprint_end + timedelta(days=1)
            
            if task_idx >= num_tasks:
                break
        
        connection.commit()


@login_required(login_url="/login/")
def index(request):
    # Set segment to 'kanban' so the sidebar highlights the Dashboard link
    context = {'segment': 'kanban'}
    return render(request, 'home/kanban.html', context)

@login_required(login_url="/login/")
def kanban(request):
    return index(request)

def calculate_daysleft(end_date):
    """
    Calculate the number of days left until the project's end date.
    If the end date has passed, return 0.
    """
    today = datetime.now().date()
    if end_date and end_date >= today:
        delta = end_date - today
        return delta.days
    return 0

def calculate_project_progress(project_id):
    """
    Calculates project completion based on weighted task status.
    - Completed (ID 3): 100% value (1.0)
    - In Progress (ID 2): 50% value (0.5)
    - Pending/Cancelled (ID 1/4): 0% value (0.0)
    """
    with connection.cursor() as cursor:
        # Fetch just the statusID for all tasks in this project
        cursor.execute("SELECT statusID FROM task WHERE projectID = %s", [project_id])
        tasks = cursor.fetchall()

    if not tasks:
        return 0

    total_tasks = len(tasks)
    weighted_score = 0.0

    for task in tasks:
        status_id = task[0]
        
        if status_id == 3:      # Completed
            weighted_score += 1.0
        elif status_id == 2:    # In Progress
            weighted_score += 0.5
        # status 1 (Pending) and 4 (Cancelled) add 0.0

    # Calculate percentage: (Score / Total Count) * 100
    progress_percent = int((weighted_score / total_tasks) * 100)
    
    return progress_percent
# apps/home/views.py

@login_required(login_url="/login/")
def projects(request):
    """
    Projects page view - Updated to fetch Developers and Clients for the form
    """
    try:
        with connection.cursor() as cursor:
            # 1. Fetch Clients
            cursor.execute("SELECT clientID, companyName FROM client")
            clients = cursor.fetchall()
            
            # 2. Fetch Developers (Users linked to Developer table)
            cursor.execute("""
                SELECT u.userID, u.username, u.firstName, u.lastName 
                FROM user u 
                JOIN developer d ON u.userID = d.developerID
            """)
            developers = cursor.fetchall()

            # 3. Fetch Projects
            cursor.execute("""
                SELECT p.projectID, p.projectName, p.startDate, p.endDate, 
                       p.projectProgress, c.companyName, s.statusDesc
                FROM project p
                LEFT JOIN client c ON p.clientID = c.clientID
                LEFT JOIN status s ON p.statusID = s.statusID
                ORDER BY p.projectID DESC
            """)
            projects_data = cursor.fetchall()

        projects_list = []
        for proj in projects_data:
            # Using the dynamic calculation method we added previously
            dynamic_progress = calculate_project_progress(proj[0]) 

            # Calculate Est. Sprints (Agile: ~14 days per sprint)
            sprints_count = 1
            if proj[2] and proj[3]:
                days = (proj[3] - proj[2]).days
                if days > 0:
                    sprints_count = math.ceil(days / 14)
            
            projects_list.append({
                    'projectID': proj[0],
                    'projectName': proj[1],
                    'startDate': proj[2],
                    'endDate': proj[3],
                    'projectProgress': dynamic_progress, 
                    'clientName': proj[5] if proj[5] else 'No Client',
                    'statusDesc': proj[6] if proj[6] else 'No Status',
                    'sprintsCount': sprints_count
                })

        context = {
            'segment': 'projects',
            'clients': [{'clientID': c[0], 'companyName': c[1]} for c in clients],
            'developers': [{'id': d[0], 'name': f"{d[2]} {d[3]} ({d[1]})"} for d in developers],
            'projects': projects_list
        }
    except Exception as e:
        context = {'segment': 'projects', 'error': str(e), 'projects': []}
        
    return render(request, 'home/projects.html', context)


@login_required(login_url="/login/")
def tables_view(request):
    print("DEBUG: tables_view() called!")  # Check if view is being called
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT clientID, companyName FROM client")
            clients = cursor.fetchall()

            cursor.execute("""
                SELECT p.projectID, p.projectName, p.startDate, p.endDate, 
                       p.projectProgress, c.companyName, s.statusDesc
                FROM project p
                LEFT JOIN client c ON p.clientID = c.clientID
                LEFT JOIN status s ON p.statusID = s.statusID
                ORDER BY p.projectID DESC
            """)
            projects_data = cursor.fetchall()
            
            print(f"DEBUG: Retrieved {len(projects_data)} projects")  # Debug line

            # Fetch developers for assignment dropdown
            try:
                cursor.execute("""
                    SELECT u.userID, u.username, u.firstName, u.lastName 
                    FROM user u 
                    JOIN developer d ON u.userID = d.developerID
                """)
                developers = cursor.fetchall()
            except Exception:
                developers = []

        projects_list = []
        for proj in projects_data:
            print(f"DEBUG: Processing project {proj[0]}: {proj[1]}")  # Debug line
            dynamic_progress = calculate_project_progress(proj[0])
            projects_list.append({
                'projectID': proj[0],
                'projectName': proj[1],
                'startDate': proj[2],
                'endDate': proj[3],
                'daysLeft': calculate_daysleft(proj[3]),
                'projectProgress': dynamic_progress,
                'clientName': proj[5] if proj[5] else 'No Client',
                'statusDesc': proj[6] if proj[6] else 'No Status'
            })

        print(f"DEBUG: Final projects_list has {len(projects_list)} items")  # Debug line
        
        context = {
            'segment': 'tables',
            'clients': [{'clientID': c[0], 'companyName': c[1]} for c in clients],
            'developers': [{'id': d[0], 'name': f"{d[2]} {d[3]} ({d[1]})"} for d in developers],
            'projects': projects_list
        }
    except Exception as e:
        print(f"ERROR in tables_view: {e}")  # Debug line
        import traceback
        traceback.print_exc()
        context = {'segment': 'tables', 'projects': [], 'error': str(e)}

    return render(request, 'home/tables.html', context)


@login_required(login_url="/login/")
def delete_project(request, project_id):
    """
    Delete a project and all its associated data (tasks, assignments)
    """
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                # Delete all tasks associated with this project
                cursor.execute("DELETE FROM task WHERE projectID = %s", [project_id])
                
                # Delete all project assignments
                cursor.execute("DELETE FROM projectAssignment WHERE projectID = %s", [project_id])
                
                # Delete the project itself
                cursor.execute("DELETE FROM project WHERE projectID = %s", [project_id])
                
                connection.commit()
            
            return redirect('tables')
        except Exception as e:
            print(f"Error deleting project: {e}")
            import traceback
            traceback.print_exc()
            return redirect('tables')
    
    return redirect('tables')


@login_required(login_url="/login/")
def create_project(request):
    if request.method == 'POST':
        # 1. Get Form Data
        project_name = request.POST.get('projectName', '').strip()
        project_type = request.POST.get('projectType', '').strip()
        start_date_str = request.POST.get('startDate', '')
        end_date_str = request.POST.get('deadline', '')
        num_sprints_str = request.POST.get('numSprints', '')
        client_id = request.POST.get('client')
        developer_ids = request.POST.getlist('developers') # Get list of selected IDs
        features_text = request.POST.get('mainFeatures', '').strip()
        
        # Admin ID (Creator)
        created_by = None
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT userID FROM user WHERE username = %s", [request.user.username])
                row = cursor.fetchone()
                if row: created_by = row[0]
        except: pass

        # Basic Validation
        if not (project_name and start_date_str and end_date_str):
            return redirect('tables') # In production, send an error message

        # Date Parsing
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        num_sprints_input = None
        if num_sprints_str and num_sprints_str.strip():
            try:
                num_sprints_input = int(num_sprints_str)
            except ValueError:
                pass

        try:
            with connection.cursor() as cursor:
                # 2. Insert Project
                cursor.execute("""
                    INSERT INTO project 
                    (projectName, projectType, statusID, startDate, endDate, projectProgress, createdBy, clientID)
                    VALUES (%s, %s, 1, %s, %s, 0, %s, %s)
                """, [project_name, project_type, start_date, end_date, created_by, client_id])
                
                # Get the new Project ID
                cursor.execute("SELECT LAST_INSERT_ID()")
                new_project_id = cursor.fetchone()[0]

                # 3. Assign Developers (Insert into projectAssignment)
                for dev_id in developer_ids:
                    cursor.execute("""
                        INSERT INTO projectAssignment (projectID, developerID, roleInProject)
                        VALUES (%s, %s, 'Developer')
                    """, [new_project_id, dev_id])

                connection.commit()

            # 4. AUTO-TIMELINE GENERATION USING AI
            # Always generate tasks based on project type
            generate_tasks_for_project(project_type, new_project_id, start_date, end_date, num_sprints_input)
            
            # Also support custom features if provided
            try:
                with connection.cursor() as cursor:
                    if features_text:
                        # Split features by new line
                        features = [f.strip() for f in features_text.split('\n') if f.strip()]
                        
                        if features:
                            # AGILE CALCULATION FOR CUSTOM FEATURES
                            # Distribute features into Sprints (approx 2 weeks)
                            
                            total_days = (end_date - start_date).days
                            if total_days < 1: total_days = 1
                            
                            if num_sprints_input and num_sprints_input > 0:
                                num_sprints = num_sprints_input
                                sprint_days = total_days // num_sprints
                                if sprint_days < 1: sprint_days = 1
                            else:
                                target_sprint_days = 14
                                num_sprints = math.ceil(total_days / target_sprint_days)
                                
                                # If we have more sprints than features, cap sprints to feature count to avoid empty sprints
                                if num_sprints > len(features):
                                    num_sprints = len(features)
                                if num_sprints < 1: num_sprints = 1
                                    
                                sprint_days = total_days // num_sprints
                                if sprint_days < 1: sprint_days = 1
                            
                            tasks_per_sprint = math.ceil(len(features) / num_sprints)
                            
                            current_task_start = start_date
                            feature_idx = 0
                            
                            for sprint_i in range(num_sprints):
                                if sprint_i == num_sprints - 1:
                                    current_sprint_end = end_date
                                else:
                                    current_sprint_end = current_task_start + timedelta(days=sprint_days - 1)

                                sprint_features = features[feature_idx : feature_idx + tasks_per_sprint]
                                feature_idx += tasks_per_sprint

                                for feature in sprint_features:
                                    cursor.execute("""
                                        INSERT INTO task 
                                        (projectID, taskTitle, taskDescription, statusID, startDate, dueDate)
                                        VALUES (%s, %s, %s, 1, %s, %s)
                                    """, [new_project_id, feature, f"Sprint {sprint_i + 1} - Custom Feature", current_task_start, current_sprint_end])
                                
                                # Set next task to start the day after this one ends
                                current_task_start = current_task_end + timedelta(days=1)
                    
                    # Explicitly commit after all inserts
                    connection.commit()

            except Exception as e:
                print(f"Error creating custom features tasks: {e}")
                import traceback
                traceback.print_exc()

            return redirect('tables')
            
        except Exception as e:
            print(f"Error creating project: {e}")
            import traceback
            traceback.print_exc()
            return redirect('tables')

    return redirect('tables')

@login_required(login_url="/login/")
def project_timeline(request, project_id):
    """
    Displays the Gantt Chart Timeline for a specific project
    """
    try:
        with connection.cursor() as cursor:
            # 1. Fetch Project Details
            cursor.execute("""
                SELECT projectID, projectName, startDate, endDate, projectProgress 
                FROM project 
                WHERE projectID = %s
            """, [project_id])
            project = cursor.fetchone()

            if not project:
                return redirect('projects')

            # 2. Fetch Tasks for this Project
            # We calculate 'Percent Complete' based on status: 
            # Completed(3)=100, In Progress(2)=50, Others=0
            cursor.execute("""
                SELECT 
                    taskID, 
                    taskTitle, 
                    startDate, 
                    dueDate,
                    CASE 
                        WHEN statusID = 3 THEN 100
                        WHEN statusID = 2 THEN 50
                        ELSE 0 
                    END as completion
                FROM task 
                WHERE projectID = %s
                ORDER BY startDate ASC
            """, [project_id])
            tasks_db = cursor.fetchall()

        # 3. Format Data for Google Charts
        gantt_data = []
        
        # --- NEW: Calculate Sprint Stats for Progress ---
        sprint_stats = {}
        if project[2]: # If project has start date
            for t in tasks_db:
                if t[2]: # Task start date
                    days_from_start = (t[2] - project[2]).days
                    sprint_num = (days_from_start // 14) + 1
                    if sprint_num < 1: sprint_num = 1
                    
                    if sprint_num not in sprint_stats:
                        sprint_stats[sprint_num] = {'total': 0, 'sum_progress': 0}
                    
                    sprint_stats[sprint_num]['total'] += 1
                    sprint_stats[sprint_num]['sum_progress'] += t[4]

        # --- NEW: Add Sprint Overview Rows ---
        if project[2] and project[3]:
            total_days = (project[3] - project[2]).days
            if total_days < 1: total_days = 1
            num_sprints = math.ceil(total_days / 14)
            if num_sprints < 1: num_sprints = 1
            
            for i in range(num_sprints):
                sprint_num = i + 1
                s_start = project[2] + timedelta(days=i*14)
                s_end = s_start + timedelta(days=14)
                if s_end > project[3]:
                    s_end = project[3]
                
                avg_progress = 0
                if sprint_num in sprint_stats:
                    stats = sprint_stats[sprint_num]
                    if stats['total'] > 0:
                        avg_progress = stats['sum_progress'] / stats['total']

                gantt_data.append([
                    f"Sprint_{sprint_num}",
                    f"Sprint {sprint_num} (Overview)",
                    f"Sprint {sprint_num}",
                    s_start.strftime('%Y-%m-%d'),
                    s_end.strftime('%Y-%m-%d'),
                    None,
                    avg_progress,
                    None
                ])

        # --- Add Task Rows ---
        for t in tasks_db:
            start_str = t[2].strftime('%Y-%m-%d') if t[2] else ''
            end_str = t[3].strftime('%Y-%m-%d') if t[3] else ''
            
            resource_name = 'General'
            if t[2] and project[2]:
                days_from_start = (t[2] - project[2]).days
                sprint_num = (days_from_start // 14) + 1
                if sprint_num < 1: sprint_num = 1
                resource_name = f"Sprint {sprint_num}"

            if start_str and end_str:
                gantt_data.append([
                    str(t[0]),      # Task ID
                    t[1],           # Task Name
                    resource_name,  # Resource
                    start_str,      # Start Date
                    end_str,        # End Date
                    None,           # Duration
                    t[4],           # Percent Complete
                    None            # Dependencies
                ])
        
        # Sort by start date
        gantt_data.sort(key=lambda x: x[3])

        context = {
            'segment': 'projects',
            'project': {
                'id': project[0],
                'name': project[1],
                'start': project[2],
                'end': project[3],
                'progress': project[4],
                'days_left': calculate_daysleft(project[3])
            },
            'gantt_data': json.dumps(gantt_data) # Pass as JSON to template
        }
        return render(request, 'home/project_timeline.html', context)

    except Exception:
        return redirect('projects')

@login_required(login_url="/login/")
def edit_project(request, project_id):
    """
    Edit project details (GET shows form, POST updates)
    """
    try:
        with connection.cursor() as cursor:
            # Fetch project
            cursor.execute("""
                SELECT projectID, projectName, projectType, statusID, startDate, endDate, projectProgress, createdBy, clientID
                FROM project
                WHERE projectID = %s
            """, [project_id])
            proj = cursor.fetchone()

            if not proj:
                return redirect('projects')

            # Fetch clients and developers for selects
            cursor.execute("SELECT clientID, companyName FROM client ORDER BY companyName")
            clients = cursor.fetchall()

            cursor.execute("SELECT d.developerID, u.firstName, u.lastName FROM developer d LEFT JOIN user u ON d.developerID = u.userID ORDER BY u.firstName, u.lastName")
            developers = cursor.fetchall()

            # Fetch assigned developers for this project
            cursor.execute("SELECT developerID FROM projectAssignment WHERE projectID = %s", [project_id])
            assigned_rows = cursor.fetchall()
            assigned_ids = [r[0] for r in assigned_rows]

        # Prepare context
        context = {
            'segment': 'projects',
            'project': {
                'projectID': proj[0],
                'projectName': proj[1],
                'projectType': proj[2] if len(proj) > 2 else '',
                'statusID': proj[3],
                'startDate': proj[4],
                'endDate': proj[5],
                'projectProgress': proj[6]
            },
            'clients': [{'clientID': c[0], 'companyName': c[1]} for c in clients],
            'developers': [{'developerID': d[0], 'firstName': d[1] or '', 'lastName': d[2] or ''} for d in developers],
            'assigned_ids': assigned_ids
        }

        if request.method == 'POST':
            # Read form fields
            project_name = request.POST.get('projectName', '').strip()
            project_type = request.POST.get('projectType', '').strip()
            client_id = request.POST.get('client') or None
            start_date_str = request.POST.get('startDate')
            end_date_str = request.POST.get('deadline')
            developer_ids = request.POST.getlist('developers')
            main_features = request.POST.get('mainFeatures', '').strip()

            # Basic validation
            if not project_name or not start_date_str or not end_date_str:
                context['error'] = 'Project name and dates are required.'
                return render(request, 'home/project_edit.html', context)

            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except Exception:
                context['error'] = 'Invalid date format.'
                return render(request, 'home/project_edit.html', context)

            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE project SET projectName=%s, projectType=%s, startDate=%s, endDate=%s, clientID=%s
                        WHERE projectID = %s
                    """, [project_name, project_type, start_date, end_date, client_id, project_id])

                    # Update project assignments: remove existing and add new
                    cursor.execute("DELETE FROM projectAssignment WHERE projectID = %s", [project_id])
                    for dev_id in developer_ids:
                        try:
                            cursor.execute("INSERT INTO projectAssignment (projectID, developerID, roleInProject) VALUES (%s, %s, %s)", [project_id, dev_id, 'Developer'])
                        except Exception:
                            # ignore individual insert errors
                            pass

                return redirect('projects')
            except Exception as e:
                context['error'] = str(e)
                return render(request, 'home/project_edit.html', context)

        return render(request, 'home/project_edit.html', context)
    except Exception:
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
            return redirect('home')
        if load_template == 'admin':
            return redirect('/admin/')

        template_path = f'home/{load_template}'
        return render(request, template_path)
    except TemplateDoesNotExist:
        return render(request, 'home/page-404.html')
    except Exception:
        return render(request, 'home/page-500.html')


@login_required(login_url="/login/")
def create_calendar_event(request):
    """
    Proxy view to trigger Google Apps Script for Calendar Event Creation
    """
    if request.method == 'POST':
        try:
            # Parse JSON data from the request body
            data = json.loads(request.body)
            
            # Extract fields expected by the Google Apps Script
            event_title = data.get('title')
            start_time = data.get('start')
            end_time = data.get('end')
            calendar_id = data.get('calendarId', 'primary')

            # If the calendar_id provided is a URL (from the saved embed link), extract the actual ID
            if 'src=' in calendar_id:
                try:
                    parsed_url = urllib.parse.urlparse(calendar_id)
                    query_params = urllib.parse.parse_qs(parsed_url.query)
                    if 'src' in query_params:
                        calendar_id = query_params['src'][0]
                except Exception:
                    pass # Fallback to using the string as-is if parsing fails

            # Your Google Apps Script Web App URL
            # Replace with the actual URL from your Google Script deployment
            gas_url = "https://script.google.com/macros/s/AKfycbxSsqctRAjksqA2oKixnFnqiwMsodEfNu8ytMlw70X3l1of0OpOLmRMvSNbiIgzdfXp/exec"

            # Payload for Google Apps Script
            payload = {
                "action": "calendar",
                "event": event_title,
                "startTime": start_time,
                "endTime": end_time,
                "calendarId": calendar_id
            }

            # Send POST request to Google Apps Script
            response = requests.post(gas_url, json=payload)

            # Return the response from GAS to the frontend
            return HttpResponse(response.text, content_type='text/plain')

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required(login_url="/login/")
def send_invitation(request):
    """
    Proxy view to trigger Google Apps Script for Email Invitations
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            role = data.get('role', 'User')
            
            # Determine registration page based on role
            reg_page = 'registerclient.html' if str(role).lower() == 'client' else 'registerdev.html'
            invite_link = request.build_absolute_uri(f'/{reg_page}')
            
            # The GAS script uses 'event' for the email body: "You are invited to " + data.event
            message_context = f"Join Planny as a {role}. Register here: {invite_link}"

            gas_url = "https://script.google.com/macros/s/AKfycbxSsqctRAjksqA2oKixnFnqiwMsodEfNu8ytMlw70X3l1of0OpOLmRMvSNbiIgzdfXp/exec"

            payload = {
                "action": "email",
                "email": email,
                "event": message_context 
            }

            response = requests.post(gas_url, json=payload)
            
            # Return JSON as expected by the profile.html JS
            return JsonResponse({'success': True, 'message': response.text})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def public_registration(request, template_name):
    return render(request, f'home/{template_name}')


@login_required(login_url="/login/")
def calendar_view(request):
    context = {'segment': 'calendar'}
    return render(request, 'home/calender.html', context)


# ==================== KANBAN API ENDPOINTS ====================

@login_required(login_url="/login/")
@require_http_methods(["GET", "POST"])
def kanban_tasks_api(request):
    """
    GET: Retrieve all tasks for kanban board
    POST: Create a new task
    """
    if request.method == 'GET':
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        t.taskID, 
                        t.taskTitle, 
                        t.taskDescription, 
                        t.statusID, 
                        t.dueDate, 
                        t.projectID,
                        p.projectName,
                        t.assignedTo,
                        u.firstName,
                        u.lastName,
                        t.priority
                    FROM task t
                    LEFT JOIN project p ON t.projectID = p.projectID
                    LEFT JOIN developer d ON t.assignedTo = d.developerID
                    LEFT JOIN user u ON d.developerID = u.userID
                    ORDER BY t.projectID, t.statusID, t.taskID
                """)
                tasks = cursor.fetchall()
                
            task_list = []
            for task in tasks:
                task_list.append({
                    'taskID': task[0],
                    'taskTitle': task[1],
                    'taskDescription': task[2],
                    'statusID': task[3],
                    'dueDate': task[4].strftime('%Y-%m-%d') if task[4] else None,
                    'projectID': task[5],
                    'projectName': task[6],
                    'assignedTo': task[7],
                    'assignedToName': f"{task[8]} {task[9]}" if task[8] and task[9] else None,
                    'priority': task[10]
                })
            
            return JsonResponse({'tasks': task_list})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            task_title = data.get('taskTitle', '').strip()
            task_description = data.get('taskDescription', '').strip()
            status_id = data.get('statusID')
            due_date = data.get('dueDate')
            assigned_to = data.get('assignedTo')
            project_id = data.get('projectID')
            priority = data.get('priority')
            
            # Validation
            if not task_title:
                return JsonResponse({'error': 'Task title is required'}, status=400)
            
            if not status_id:
                return JsonResponse({'error': 'Status is required'}, status=400)
            
            if not project_id:
                return JsonResponse({'error': 'Project is required'}, status=400)
            
            # Parse due date if provided
            due_date_obj = None
            if due_date:
                try:
                    due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'error': 'Invalid date format'}, status=400)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO task 
                    (taskTitle, taskDescription, statusID, dueDate, assignedTo, projectID, priority)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [task_title, task_description, status_id, due_date_obj, assigned_to, project_id, priority])
                
                # Get the last inserted task ID
                cursor.execute("SELECT LAST_INSERT_ID()")
                last_id = cursor.fetchone()[0]
            
            return JsonResponse({'success': True, 'taskID': last_id, 'message': 'Task created successfully'})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url="/login/")
@require_http_methods(["PATCH", "PUT", "DELETE"])
def kanban_task_detail_api(request, task_id):
    """
    PATCH: Update task status (for drag-drop)
    PUT: Update full task details (for edit modal)
    DELETE: Delete a task
    """
    if request.method == 'PATCH':
        try:
            data = json.loads(request.body)
            status_id = data.get('statusID')
            
            if not status_id:
                return JsonResponse({'error': 'Status is required'}, status=400)
            
            with connection.cursor() as cursor:
                # 1. Update the Task
                cursor.execute("UPDATE task SET statusID = %s WHERE taskID = %s", [status_id, task_id])
                
                # 2. Find the project ID for this task
                cursor.execute("SELECT projectID FROM task WHERE taskID = %s", [task_id])
                row = cursor.fetchone()
                if row:
                    project_id = row[0]
                    
                    # 3. LOGIC: If task is 'In Progress' (2), set Project to 'In Progress' (2)
                    # You can make this more complex (e.g., check if ALL are done)
                    if int(status_id) == 2:
                        cursor.execute("UPDATE project SET statusID = 2 WHERE projectID = %s", [project_id])
                    
                    # 4. LOGIC: If task is 'Completed' (3), check if ALL tasks are completed
                    elif int(status_id) == 3:
                        cursor.execute("SELECT count(*) FROM task WHERE projectID = %s AND statusID != 3", [project_id])
                        remaining = cursor.fetchone()[0]
                        if remaining == 0:
                            cursor.execute("UPDATE project SET statusID = 3 WHERE projectID = %s", [project_id])

            return JsonResponse({'success': True, 'message': 'Task updated successfully'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            task_title = data.get('taskTitle', '').strip()
            task_description = data.get('taskDescription', '').strip()
            status_id = data.get('statusID')
            due_date = data.get('dueDate')
            assigned_to = data.get('assignedTo')
            project_id = data.get('projectID')
            priority = data.get('priority')
            
            # Validation
            if not task_title:
                return JsonResponse({'error': 'Task title is required'}, status=400)
            
            if not status_id:
                return JsonResponse({'error': 'Status is required'}, status=400)
            
            if not project_id:
                return JsonResponse({'error': 'Project is required'}, status=400)
            
            # Parse due date if provided
            due_date_obj = None
            if due_date:
                try:
                    due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'error': 'Invalid date format'}, status=400)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE task 
                    SET taskTitle = %s, taskDescription = %s, statusID = %s, dueDate = %s, assignedTo = %s, projectID = %s, priority = %s
                    WHERE taskID = %s
                """, [task_title, task_description, status_id, due_date_obj, assigned_to, project_id, priority, task_id])
            
            return JsonResponse({'success': True, 'taskID': task_id, 'message': 'Task updated successfully'})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    elif request.method == 'DELETE':
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM task WHERE taskID = %s", [task_id])
            
            return JsonResponse({'success': True, 'message': 'Task deleted successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url="/login/")
def projects_api(request):
    """
    GET: Retrieve all projects
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT projectID, projectName 
                FROM project 
                ORDER BY projectName
            """)
            projects = cursor.fetchall()
        
        projects_list = [{'projectID': p[0], 'projectName': p[1]} for p in projects]
        return JsonResponse({'projects': projects_list})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url="/login/")
def developers_api(request):
    """
    GET: Retrieve all developers
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT d.developerID, u.firstName, u.lastName, u.email
                FROM developer d
                LEFT JOIN user u ON d.developerID = u.userID
                ORDER BY u.firstName, u.lastName
            """)
            developers = cursor.fetchall()
        
        developers_list = [
            {
                'developerID': d[0], 
                'firstName': d[1] if d[1] else '',
                'lastName': d[2] if d[2] else '',
                'email': d[3] if d[3] else ''
            } for d in developers
        ]
        return JsonResponse({'developers': developers_list})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
