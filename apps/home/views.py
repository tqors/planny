# -*- encoding: utf-8 -*-
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
# ProjectForm was used previously but client selection was removed from the UI


@login_required(login_url="/login/")
def index(request):
    context = {'segment': 'index'}
    return render(request, 'home/index.html', context)


@login_required(login_url="/login/")
def kanban(request):
    # direct view for the kanban page
    return render(request, 'home/kanban.html')

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
                SELECT p.projectID, p.projectName, p.projectType, p.startDate, p.endDate, 
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
            # dynamic_progress = calculate_project_progress(proj[0]) 
            
            projects_list.append({
                'projectID': proj[0],
                'projectName': proj[1],
                'projectType': proj[2], # Added Project Type
                'startDate': proj[3],
                'endDate': proj[4],
                'projectProgress': proj[5], # Or use dynamic_progress
                'clientName': proj[6] if proj[6] else 'No Client',
                'statusDesc': proj[7] if proj[7] else 'No Status'
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
def create_project(request):
    """
    Create a new project with Auto-Timeline Generation
    """
    if request.method == 'POST':
        # 1. Get Form Data
        project_name = request.POST.get('projectName', '').strip()
        project_type = request.POST.get('projectType', '').strip()
        start_date_str = request.POST.get('startDate', '')
        end_date_str = request.POST.get('deadline', '')
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
            return redirect('projects') # In production, send an error message

        # Date Parsing
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
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

                # 4. AUTO-TIMELINE GENERATION (The "AI" Logic)
                if features_text:
                    # Split features by new line
                    features = [f.strip() for f in features_text.split('\n') if f.strip()]
                    
                    if features:
                        # Calculate how many days per feature
                        total_days = (end_date - start_date).days
                        if total_days < 1: total_days = 1
                        days_per_task = total_days // len(features)
                        
                        current_task_start = start_date
                        
                        for i, feature in enumerate(features):
                            # Calculate end date for this specific task
                            # The last task always ends on the project deadline to be safe
                            if i == len(features) - 1:
                                current_task_end = end_date
                            else:
                                current_task_end = current_task_start + timedelta(days=days_per_task)

                            # Insert the Auto-Generated Task
                            cursor.execute("""
                                INSERT INTO task 
                                (projectID, taskTitle, taskDescription, statusID, startDate, dueDate)
                                VALUES (%s, %s, %s, 1, %s, %s)
                            """, [
                                new_project_id, 
                                feature, 
                                "Auto-generated from Project Requirements", 
                                current_task_start, 
                                current_task_end
                            ])
                            
                            # Set next task to start the day after this one ends
                            current_task_start = current_task_end + timedelta(days=1)

            return redirect('projects')
            
        except Exception as e:
            print(f"Error: {e}")
            return redirect('projects')

    return redirect('projects')
# @login_required(login_url="/login/")
# def projects(request):
#     """
#     Projects page view
#     """
#     try:
#         with connection.cursor() as cursor:
#             cursor.execute("SELECT clientID, companyName FROM client")
#             clients = cursor.fetchall()
            
#             # Fetch basic project data (we ignore the stored 'projectProgress' column now)
#             cursor.execute("""
#                 SELECT p.projectID, p.projectName, p.startDate, p.endDate, 
#                        c.companyName, s.statusDesc
#                 FROM project p
#                 LEFT JOIN client c ON p.clientID = c.clientID
#                 LEFT JOIN status s ON p.statusID = s.statusID
#                 ORDER BY p.projectID DESC
#             """)
#             projects_data = cursor.fetchall()
            
#         projects_list = []
#         for proj in projects_data:
#             # ---------------------------------------------------------
#             # METHOD 2: Calculate weighted progress dynamically here
#             # ---------------------------------------------------------
#             current_project_id = proj[0]
#             dynamic_progress = calculate_project_progress(current_project_id)

#             projects_list.append({
#                 'projectID': proj[0],
#                 'projectName': proj[1],
#                 'startDate': proj[2],
#                 'endDate': proj[3],
#                 'projectProgress': dynamic_progress, # Use the calculated value!
#                 'clientName': proj[4] if proj[4] else 'No Client',
#                 'statusDesc': proj[5] if proj[5] else 'No Status'
#             })
        
#         context = {
#             'segment': 'projects',
#             'clients': [{'clientID': c[0], 'companyName': c[1]} for c in clients],
#             'projects': projects_list
#         }
#     except Exception as e:
#         context = {
#             'segment': 'projects',
#             'clients': [],
#             'projects': [],
#             'error': str(e)
#         }
#     return render(request, 'home/projects.html', context)

# @login_required(login_url="/login/")
# def create_project(request):
#     """
#     Create a new project
#     """
#     if request.method == 'POST':
#         # Read POST fields directly (client selection removed)
#         projectName = request.POST.get('projectName', '').strip()
#         deadline_str = request.POST.get('deadline', '').strip()
#         # Try to map the Django auth user to the custom `user` table (if present)
#         createdBy = None
#         try:
#             with connection.cursor() as cursor:
#                 cursor.execute("SELECT userID FROM user WHERE username = %s LIMIT 1", [request.user.username])
#                 row = cursor.fetchone()
#                 if row:
#                     createdBy = row[0]
#         except Exception:
#             createdBy = None

#         # Basic validation - require project name and deadline
#         if not projectName or not deadline_str:
#             # Return to projects page with a simple error message (could be improved)
#             context = {'segment': 'projects', 'error': 'Project name and deadline are required.'}
#             return render(request, 'home/projects.html', context)

#         try:
#             # Parse date (expecting YYYY-MM-DD)
#             deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
#         except Exception:
#             context = {'segment': 'projects', 'error': 'Invalid deadline date format.'}
#             return render(request, 'home/projects.html', context)

#         # Set deadline time to 11:59:59 (we'll store date portion in the endDate column)
#         deadline_datetime = datetime.combine(deadline_date, time(23, 59, 59))

#         try:
#             now_date = datetime.now().date()
#             with connection.cursor() as cursor:
#                 # Insert new project. Use NULL for statusID and clientID since client was removed.
#                 cursor.execute("""
#                     INSERT INTO project (projectName, statusID, startDate, endDate, projectProgress, createdBy, clientID)
#                     VALUES (%s, %s, %s, %s, %s, %s, %s)
#                 """, [projectName, None, now_date, deadline_datetime.date(), 0, createdBy, None])

#             # Redirect back to projects so the page reloads and shows the new project
#             return redirect('projects')
#         except Exception as e:
#             context = {'segment': 'projects', 'error': f'Error creating project: {str(e)}'}
#             return render(request, 'home/projects.html', context)

#     return redirect('projects')

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
        # Google Charts expects: [Task ID, Task Name, Resource(null), Start, End, Duration(null), % Complete, Dependencies(null)]
        gantt_data = []
        for t in tasks_db:
            # Javascript months are 0-indexed (0=Jan, 11=Dec), so we adjust if necessary in JS, 
            # but Google Charts usually takes string or Date objects. We'll pass YYYY-MM-DD strings.
            start_str = t[2].strftime('%Y-%m-%d') if t[2] else ''
            end_str = t[3].strftime('%Y-%m-%d') if t[3] else ''
            
            if start_str and end_str:
                gantt_data.append([
                    str(t[0]),      # Task ID
                    t[1],           # Task Name
                    'Task',         # Resource (Category)
                    start_str,      # Start Date
                    end_str,        # End Date
                    None,           # Duration (calculated auto)
                    t[4],           # Percent Complete
                    None            # Dependencies
                ])

        context = {
            'segment': 'projects',
            'project': {
                'id': project[0],
                'name': project[1],
                'start': project[2],
                'end': project[3],
                'progress': project[4]
            },
            'gantt_data': json.dumps(gantt_data) # Pass as JSON to template
        }
        return render(request, 'home/project_timeline.html', context)

    except Exception as e:
        print(f"Error: {e}")
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
                        u.lastName
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
                    'assignedToName': f"{task[8]} {task[9]}" if task[8] and task[9] else None
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
                    (taskTitle, taskDescription, statusID, dueDate, assignedTo, projectID)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [task_title, task_description, status_id, due_date_obj, assigned_to, project_id])
            
            return JsonResponse({'success': True, 'message': 'Task created successfully'})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url="/login/")
@require_http_methods(["PATCH", "DELETE"])
def kanban_task_detail_api(request, task_id):
    """
    PATCH: Update a task (specifically status)
    DELETE: Delete a task
    """
    if request.method == 'PATCH':
        try:
            data = json.loads(request.body)
            status_id = data.get('statusID')
            
            if not status_id:
                return JsonResponse({'error': 'Status is required'}, status=400)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE task 
                    SET statusID = %s 
                    WHERE taskID = %s
                """, [status_id, task_id])
            
            return JsonResponse({'success': True, 'message': 'Task updated successfully'})
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


