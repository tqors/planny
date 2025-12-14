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
from apps.home.profile_form import ProfileForm

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
    return render(request, 'home/profile.html', {'form': form, 'user': user})
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

def generate_tasks_for_project(project_type, project_id, start_date, end_date):
    """
    AI function to automatically generate tasks based on project type.
    Distributes tasks evenly across the project timeline.
    """
    # Get task templates for the project type
    task_templates = PROJECT_TYPE_TASKS.get(project_type, PROJECT_TYPE_TASKS['Other'])
    
    # Calculate days per task
    total_days = (end_date - start_date).days
    if total_days < 1:
        total_days = 1
    
    days_per_task = total_days // len(task_templates)
    if days_per_task < 1:
        days_per_task = 1
    
    current_task_start = start_date
    
    with connection.cursor() as cursor:
        for i, task_title in enumerate(task_templates):
            # Calculate end date for this task
            if i == len(task_templates) - 1:
                current_task_end = end_date
            else:
                current_task_end = current_task_start + timedelta(days=days_per_task)
            
            # Insert task into database
            cursor.execute("""
                INSERT INTO task 
                (projectID, taskTitle, taskDescription, statusID, startDate, dueDate)
                VALUES (%s, %s, %s, 1, %s, %s)
            """, [
                project_id,
                task_title,
                f"Auto-generated task for {project_type} project",
                current_task_start,
                current_task_end
            ])
            
            # Set next task to start the day after this one ends
            current_task_start = current_task_end + timedelta(days=1)
        
        connection.commit()


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
            
            projects_list.append({
                    'projectID': proj[0],
                    'projectName': proj[1],
                    'startDate': proj[2],
                    'endDate': proj[3],
                    'projectProgress': dynamic_progress, 
                    'clientName': proj[5] if proj[5] else 'No Client',
                    'statusDesc': proj[6] if proj[6] else 'No Status'
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
    """
    Render the projects table with project data from the database.
    This ensures `tables.html` receives the `projects` context expected by the template.
    """
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
            return redirect('tables') # In production, send an error message

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

                connection.commit()

            # 4. AUTO-TIMELINE GENERATION USING AI
            # Always generate tasks based on project type
            generate_tasks_for_project(project_type, new_project_id, start_date, end_date)
            
            # Also support custom features if provided
            try:
                with connection.cursor() as cursor:
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

                                # Ensure dates are properly formatted
                                cursor.execute("""
                                    INSERT INTO task 
                                    (projectID, taskTitle, taskDescription, statusID, startDate, dueDate)
                                    VALUES (%s, %s, %s, 1, %s, %s)
                                """, [
                                    new_project_id, 
                                    feature, 
                                    "Auto-generated from Project Requirements", 
                                    current_task_start,  # DATE object
                                    current_task_end      # DATE object
                                ])
                                
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
                    SET taskTitle = %s, taskDescription = %s, statusID = %s, dueDate = %s, assignedTo = %s, projectID = %s
                    WHERE taskID = %s
                """, [task_title, task_description, status_id, due_date_obj, assigned_to, project_id, task_id])
            
            return JsonResponse({'success': True, 'taskID': task_id, 'message': 'Task updated successfully'})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
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


def create_calendar_event(task_id, task_title, task_description, start_date, due_date, project_name, assigned_to_email=None):
    """
    Helper function to create a calendar event for a task.
    Uses Google Calendar Data API format to generate an event object.
    The event is stored as JSON in localStorage on the client side.
    
    Returns a dict representing the calendar event.
    """
    # Prefer start_date if provided; otherwise fall back to due_date
    event_start = start_date if start_date else due_date
    event_end = due_date if due_date else (start_date or None)

    if not event_start:
        return None

    event = {
        'taskID': task_id,
        'summary': task_title,
        'description': f"{task_description or ''}\nProject: {project_name}",
        'start': {
            'date': event_start.isoformat() if hasattr(event_start, 'isoformat') else str(event_start)
        },
        'end': {
            'date': ((event_end + timedelta(days=1)).isoformat() if hasattr(event_end, 'isoformat') else str(event_end)) if event_end else None
        }
    }
    
    if assigned_to_email:
        event['attendees'] = [{'email': assigned_to_email, 'responseStatus': 'needsAction'}]
    
    return event


@login_required(login_url="/login/")
def calendar_event_api(request):
    """
    POST: Create a calendar event from a task
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_id = data.get('taskID')
            
            if not task_id:
                return JsonResponse({'error': 'Task ID is required'}, status=400)
            
            # Fetch task details from database
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT t.taskTitle, t.taskDescription, t.startDate, t.dueDate, p.projectName, u.email
                    FROM task t
                    LEFT JOIN project p ON t.projectID = p.projectID
                    LEFT JOIN developer d ON t.assignedTo = d.developerID
                    LEFT JOIN user u ON d.developerID = u.userID
                    WHERE t.taskID = %s
                """, [task_id])
                result = cursor.fetchone()
            
            if not result:
                return JsonResponse({'error': 'Task not found'}, status=404)
            
            task_title, task_desc, start_date, due_date, project_name, email = result

            # Create calendar event (prefer start_date when available)
            event = create_calendar_event(
                task_id=task_id,
                task_title=task_title,
                task_description=task_desc,
                start_date=start_date,
                due_date=due_date,
                project_name=project_name or 'Unknown Project',
                assigned_to_email=email
            )
            
            return JsonResponse({'event': event, 'message': 'Calendar event created'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url="/login/")
def calendar_events_api(request):
    """
    GET: Return calendar events for all tasks that have a dueDate
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT t.taskID, t.taskTitle, t.taskDescription, t.startDate, t.dueDate, p.projectName, u.email
                FROM task t
                LEFT JOIN project p ON t.projectID = p.projectID
                LEFT JOIN developer d ON t.assignedTo = d.developerID
                LEFT JOIN user u ON d.developerID = u.userID
                WHERE t.dueDate IS NOT NULL OR t.startDate IS NOT NULL
                ORDER BY COALESCE(t.startDate, t.dueDate) ASC
            """)
            rows = cursor.fetchall()

        events = []
        for r in rows:
            task_id, title, desc, start_date, due_date, project_name, email = r
            event = create_calendar_event(task_id, title, desc, start_date, due_date, project_name or 'Unknown Project', email)
            if event:
                events.append(event)

        return JsonResponse({'events': events})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==================== USER CALENDAR EVENT ENDPOINTS ====================

@login_required(login_url="/login/")
def user_calendar_events_api(request):
    """
    GET: Retrieve all calendar events for the logged-in user (both task-based and custom)
    POST: Create a new calendar event for the user
    """
    try:
        # Get user ID from Django auth
        user_id = request.user.id
        
        with connection.cursor() as cursor:
            # First, fetch the planny userID from the custom user table
            cursor.execute("SELECT userID FROM user WHERE username = %s", [request.user.username])
            user_row = cursor.fetchone()
            if not user_row:
                return JsonResponse({'error': 'User not found in database'}, status=404)
            planny_user_id = user_row[0]
        
        if request.method == 'GET':
            # Fetch all events for this user from userCalendarEvent table
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT eventID, taskID, eventTitle, eventDescription, startDate, endDate, isTaskBased, createdAt
                    FROM userCalendarEvent
                    WHERE userID = %s
                    ORDER BY startDate ASC
                """, [planny_user_id])
                rows = cursor.fetchall()
            
            events = []
            for r in rows:
                event_id, task_id, title, desc, start_date, end_date, is_task_based, created_at = r
                events.append({
                    'eventID': event_id,
                    'taskID': task_id,
                    'summary': title,
                    'description': desc,
                    'start': {'date': start_date.isoformat() if start_date else None},
                    'end': {'date': end_date.isoformat() if end_date else None},
                    'isTaskBased': bool(is_task_based),
                    'createdAt': created_at.isoformat() if created_at else None
                })
            
            return JsonResponse({'events': events})
        
        elif request.method == 'POST':
            data = json.loads(request.body)
            event_title = data.get('eventTitle', '').strip()
            event_desc = data.get('eventDescription', '').strip()
            start_date_str = data.get('startDate')
            end_date_str = data.get('endDate')
            task_id = data.get('taskID')
            
            if not event_title:
                return JsonResponse({'error': 'Event title is required'}, status=400)
            
            # Parse dates
            start_date = None
            end_date = None
            try:
                if start_date_str:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                if end_date_str:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'error': 'Invalid date format'}, status=400)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO userCalendarEvent (userID, taskID, eventTitle, eventDescription, startDate, endDate, isTaskBased)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [planny_user_id, task_id or None, event_title, event_desc, start_date, end_date, 0])
                
                cursor.execute("SELECT LAST_INSERT_ID()")
                event_id = cursor.fetchone()[0]
            
            return JsonResponse({
                'success': True,
                'eventID': event_id,
                'message': 'Calendar event created successfully'
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url="/login/")
def user_calendar_event_detail_api(request, event_id):
    """
    PATCH: Update a user calendar event
    DELETE: Delete a user calendar event
    """
    try:
        user_id = request.user.id
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT userID FROM user WHERE username = %s", [request.user.username])
            user_row = cursor.fetchone()
            if not user_row:
                return JsonResponse({'error': 'User not found'}, status=404)
            planny_user_id = user_row[0]
            
            # Verify event belongs to this user
            cursor.execute("SELECT userID FROM userCalendarEvent WHERE eventID = %s", [event_id])
            event_row = cursor.fetchone()
            if not event_row or event_row[0] != planny_user_id:
                return JsonResponse({'error': 'Event not found or unauthorized'}, status=404)
        
        if request.method == 'PATCH':
            data = json.loads(request.body)
            event_title = data.get('eventTitle')
            event_desc = data.get('eventDescription')
            start_date_str = data.get('startDate')
            end_date_str = data.get('endDate')
            
            # Parse dates
            start_date = None
            end_date = None
            try:
                if start_date_str:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                if end_date_str:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'error': 'Invalid date format'}, status=400)
            
            with connection.cursor() as cursor:
                updates = []
                params = []
                
                if event_title is not None:
                    updates.append("eventTitle = %s")
                    params.append(event_title)
                if event_desc is not None:
                    updates.append("eventDescription = %s")
                    params.append(event_desc)
                if start_date_str:
                    updates.append("startDate = %s")
                    params.append(start_date)
                if end_date_str:
                    updates.append("endDate = %s")
                    params.append(end_date)
                
                if updates:
                    updates.append("updatedAt = CURRENT_TIMESTAMP")
                    params.append(event_id)
                    
                    update_sql = f"UPDATE userCalendarEvent SET {', '.join(updates)} WHERE eventID = %s"
                    cursor.execute(update_sql, params)
            
            return JsonResponse({'success': True, 'message': 'Event updated successfully'})
        
        elif request.method == 'DELETE':
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM userCalendarEvent WHERE eventID = %s", [event_id])
            
            return JsonResponse({'success': True, 'message': 'Event deleted successfully'})
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



