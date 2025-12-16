const statusMap = {
  '1': 'To-Do',
  '2': 'In Progress',
  '3': 'Bug Report',
  '4': 'Testing',
  '5': 'Complete'
};

const statusClasses = {
  '1': 'status-todo',
  '2': 'status-in-progress',
  '3': 'status-bug-report',
  '4': 'status-testing',
  '5': 'status-complete'
};

// Initialize the kanban board
document.addEventListener('DOMContentLoaded', function() {
  loadKanbanData();
  loadProjects();
  loadDevelopers();
  
  // Add event listener for project filter
  document.getElementById('projectFilter').addEventListener('change', filterKanbanByProject);
});

// Load kanban data from the server
function loadKanbanData() {
  fetch('/api/kanban-tasks/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    }
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Failed to load tasks');
    }
    return response.json();
  })
  .then(data => {
    // Store all tasks globally for filtering
    window.allTasks = data.tasks;
    renderKanban(data.tasks);
  })
  .catch(error => {
    console.error('Error loading kanban data:', error);
    showErrorMessage('Failed to load tasks. Please refresh the page.');
  });
}

// Filter kanban by selected project
function filterKanbanByProject() {
  const selectedProjectId = document.getElementById('projectFilter').value;
  
  if (selectedProjectId === '') {
    // Show all tasks
    renderKanban(window.allTasks);
  } else {
    // Filter tasks by project
    const filteredTasks = window.allTasks.filter(task => 
      task.projectID === parseInt(selectedProjectId)
    );
    renderKanban(filteredTasks);
  }
}

// Render the kanban board
function renderKanban(tasks) {
  const container = document.getElementById('kanbanContainer');
  container.innerHTML = '';

  const statusOrder = ['1', '2', '3', '4', '5'];

  statusOrder.forEach(statusId => {
    const statusTasks = tasks.filter(task => task.statusID === parseInt(statusId));
    
    const column = document.createElement('div');
    column.className = 'kanban-column';
    column.innerHTML = `
      <div class="kanban-column-header">
        <span>${statusMap[statusId]}</span>
        <span class="badge">${statusTasks.length}</span>
      </div>
      <div class="kanban-cards" id="column-${statusId}">
        ${statusTasks.map(task => `
          <div class="kanban-card ${statusClasses[statusId]}" draggable="true" data-task-id="${task.taskID}" ondragstart="dragStart(event)" ondragend="dragEnd(event)">
            <div class="kanban-card-title">${escapeHtml(task.taskTitle)}</div>
            <div class="kanban-card-description">${escapeHtml(task.taskDescription || 'No description')}</div>
            <div class="kanban-card-meta">
              <div class="kanban-card-meta-item">
                <span class="kanban-card-label">Project:</span>
                <span class="kanban-card-value">${escapeHtml(task.projectName)}</span>
              </div>
              <div class="kanban-card-meta-item">
                <span class="kanban-card-label">Priority:</span>
                <span class="kanban-card-value">${task.priority ? `<span class="badge badge-dot"><i class="${getPriorityColorClass(task.priority)}"></i> ${escapeHtml(task.priority)}</span>` : 'None'}</span>
              </div>
              <div class="kanban-card-meta-item">
                <span class="kanban-card-label">Due:</span>
                <span class="kanban-card-value">${task.dueDate || 'No date'}</span>
              </div>
              <div class="kanban-card-meta-item">
                <span class="kanban-card-label">Assigned:</span>
                <span class="kanban-card-value">${task.assignedToName || 'Unassigned'}</span>
              </div>
            </div>
            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; display: flex; justify-content: flex-end;">
              <div class="dropdown" style="position: relative; display: inline-block;">
                <button class="btn btn-sm btn-icon-only text-muted" style="background: none; border: none; cursor: pointer; padding: 4px;" onclick="toggleDropdown(event)">
                  <i class="fas fa-ellipsis-v"></i>
                </button>
                <div class="dropdown-menu" style="position: absolute; right: 0; background: white; border: 1px solid #ddd; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); min-width: 120px; z-index: 1000; display: none;">
                  <a class="dropdown-item" href="#" onclick="openEditTaskModal(${task.taskID}, '${escapeHtml(task.taskTitle).replace(/'/g, "\\'")}', '${escapeHtml((task.taskDescription || '').replace(/'/g, "\\'"))}', ${task.statusID}, '${task.dueDate || ''}', ${task.assignedTo || 'null'}, ${task.projectID}, '${task.priority || ''}'); return false;" style="display: block; padding: 10px 15px; color: #333; text-decoration: none; cursor: pointer; border-bottom: 1px solid #eee;">Edit</a>
                  <a class="dropdown-item" href="#" onclick="deleteTask(${task.taskID}, '${escapeHtml(task.taskTitle).replace(/'/g, "\\'")}'); return false;" style="display: block; padding: 10px 15px; color: #dc3545; text-decoration: none; cursor: pointer;">Delete</a>
                </div>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    // Add drag-over listeners
    const cardsContainer = column.querySelector(`#column-${statusId}`);
    cardsContainer.addEventListener('dragover', dragOver);
    cardsContainer.addEventListener('drop', drop);

    container.appendChild(column);
  });
}

function getPriorityColorClass(priority) {
  if (priority === 'High') return 'bg-danger';
  if (priority === 'Medium') return 'bg-warning';
  if (priority === 'Low') return 'bg-info';
  return 'bg-secondary';
}

// Drag and drop handlers
let draggedElement = null;

function dragStart(event) {
  draggedElement = event.target.closest('.kanban-card');
  event.dataTransfer.effectAllowed = 'move';
}

function dragEnd(event) {
  draggedElement = null;
}

function dragOver(event) {
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
}

function drop(event) {
  event.preventDefault();
  if (!draggedElement) return;

  const targetColumn = event.currentTarget;
  const statusId = targetColumn.id.split('-')[1];
  const taskId = draggedElement.dataset.taskId;

  // Update task status on the server
  updateTaskStatus(taskId, statusId);

  // Move the card to the new column
  targetColumn.appendChild(draggedElement);
  
  // Update column badge counts
  updateColumnBadges();
}

// Update task status via API
function updateTaskStatus(taskId, newStatusId) {
  fetch(`/api/kanban-tasks/${taskId}/`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({ statusID: parseInt(newStatusId) })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Failed to update task status');
    }
    return response.json();
  })
  .then(data => {
    console.log('Task updated:', data);
    // Reload the kanban board
    loadKanbanData();
  })
  .catch(error => {
    console.error('Error updating task status:', error);
    // Reload to revert the UI change
    loadKanbanData();
  });
}

// Update column badge counts
function updateColumnBadges() {
  document.querySelectorAll('.kanban-cards').forEach(column => {
    const cards = column.querySelectorAll('.kanban-card').length;
    const badge = column.parentElement.querySelector('.badge');
    if (badge) {
      badge.textContent = cards;
    }
  });
}

// Load projects for the dropdown
function loadProjects() {
  fetch('/api/projects/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    }
  })
  .then(response => response.json())
  .then(data => {
    const projectSelect = document.getElementById('taskProject');
    const editProjectSelect = document.getElementById('editTaskProject');
    const projectFilter = document.getElementById('projectFilter');
    
    data.projects.forEach(project => {
      // Add to task creation dropdown
      const option = document.createElement('option');
      option.value = project.projectID;
      option.textContent = project.projectName;
      projectSelect.appendChild(option);
      
      // Add to edit task dropdown
      const editOption = document.createElement('option');
      editOption.value = project.projectID;
      editOption.textContent = project.projectName;
      editProjectSelect.appendChild(editOption);
      
      // Add to project filter dropdown
      const filterOption = document.createElement('option');
      filterOption.value = project.projectID;
      filterOption.textContent = project.projectName;
      projectFilter.appendChild(filterOption);
    });
  })
  .catch(error => {
    console.error('Error loading projects:', error);
  });
}

// Load developers for the dropdown
function loadDevelopers() {
  fetch('/api/developers/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    }
  })
  .then(response => response.json())
  .then(data => {
    const developerSelect = document.getElementById('taskAssignedTo');
    const editDeveloperSelect = document.getElementById('editTaskAssignedTo');
    data.developers.forEach(developer => {
      const option = document.createElement('option');
      option.value = developer.developerID;
      option.textContent = developer.firstName + ' ' + developer.lastName;
      developerSelect.appendChild(option);
      
      // Add to edit task dropdown
      const editOption = document.createElement('option');
      editOption.value = developer.developerID;
      editOption.textContent = developer.firstName + ' ' + developer.lastName;
      editDeveloperSelect.appendChild(editOption);
    });
  })
  .catch(error => {
    console.error('Error loading developers:', error);
  });
}

// Open task modal
function openTaskModal() {
  document.getElementById('taskOverlay').classList.add('active');
  document.getElementById('taskForm').reset();
  clearErrors();
}

// Close task modal
function closeTaskModal() {
  document.getElementById('taskOverlay').classList.remove('active');
  document.getElementById('taskForm').reset();
  clearErrors();
}

// Dropdown menu toggle
function toggleDropdown(event) {
  event.stopPropagation();
  const dropdown = event.currentTarget.parentElement.querySelector('.dropdown-menu');
  const isVisible = dropdown.style.display === 'block';
  
  // Close all open dropdowns
  document.querySelectorAll('.dropdown-menu').forEach(menu => {
    menu.style.display = 'none';
  });
  
  // Toggle current dropdown
  if (!isVisible) {
    dropdown.style.display = 'block';
  }
}

// Close dropdown when clicking outside
document.addEventListener('click', function() {
  document.querySelectorAll('.dropdown-menu').forEach(menu => {
    menu.style.display = 'none';
  });
});

// Delete task function
function deleteTask(taskId, taskName) {
  if (confirm(`Are you sure you want to delete the task "${taskName}"?\n\nThis action cannot be undone.`)) {
    fetch(`/api/kanban-tasks/${taskId}/`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      }
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(data => {
          throw new Error(data.error || 'Failed to delete task');
        });
      }
      return response.json();
    })
    .then(data => {
      loadKanbanData();
    })
    .catch(error => {
      console.error('Error deleting task:', error);
      alert('Error deleting task: ' + error.message);
    });
  }
}

// Open edit task modal
function openEditTaskModal(taskId, taskTitle, taskDescription, statusID, dueDate, assignedTo, projectID, priority) {
  document.getElementById('editTaskId').value = taskId;
  document.getElementById('editTaskTitle').value = taskTitle;
  document.getElementById('editTaskDescription').value = taskDescription;
  document.getElementById('editTaskStatus').value = statusID;
  document.getElementById('editTaskDueDate').value = dueDate;
  document.getElementById('editTaskAssignedTo').value = assignedTo || '';
  document.getElementById('editTaskProject').value = projectID;
  document.getElementById('editTaskPriority').value = priority || '';
  
  document.getElementById('editTaskOverlay').classList.add('active');
  clearEditErrors();
}

// Close edit task modal
function closeEditTaskModal() {
  document.getElementById('editTaskOverlay').classList.remove('active');
  document.getElementById('editTaskForm').reset();
  clearEditErrors();
}

// Clear edit error messages
function clearEditErrors() {
  document.querySelectorAll('#editTaskOverlay .error-message').forEach(el => {
    el.classList.remove('active');
    el.textContent = '';
  });
  document.getElementById('editSuccessMessage').classList.remove('active');
}

// Submit edit task form
document.getElementById('editTaskForm').addEventListener('submit', function(e) {
  e.preventDefault();
  clearEditErrors();

  const taskId = document.getElementById('editTaskId').value;
  const title = document.getElementById('editTaskTitle').value.trim();
  const description = document.getElementById('editTaskDescription').value.trim();
  const status = document.getElementById('editTaskStatus').value;
  const dueDate = document.getElementById('editTaskDueDate').value;
  const assignedTo = document.getElementById('editTaskAssignedTo').value;
  const project = document.getElementById('editTaskProject').value;
  const priority = document.getElementById('editTaskPriority').value;

  // Validation
  if (!title) {
    showEditError('editTitleError', 'Task title is required');
    return;
  }
  if (!status) {
    showEditError('editStatusError', 'Status is required');
    return;
  }
  if (!project) {
    showEditError('editProjectError', 'Project is required');
    return;
  }

  document.getElementById('editFormLoading').classList.add('active');

  // Submit form
  fetch(`/api/kanban-tasks/${taskId}/`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({
      taskTitle: title,
      taskDescription: description,
      statusID: parseInt(status),
      dueDate: dueDate || null,
      assignedTo: assignedTo ? parseInt(assignedTo) : null,
      projectID: parseInt(project),
      priority: priority || null
    })
  })
  .then(response => {
    document.getElementById('editFormLoading').classList.remove('active');
    if (!response.ok) {
      return response.json().then(data => {
        throw new Error(data.error || 'Failed to update task');
      });
    }
    return response.json();
  })
  .then(data => {
    document.getElementById('editSuccessMessage').classList.add('active');
    setTimeout(() => {
      closeEditTaskModal();
      loadKanbanData();
    }, 1500);
  })
  .catch(error => {
    document.getElementById('editFormLoading').classList.remove('active');
    console.error('Error updating task:', error);
    showEditError('editTitleError', error.message);
  });
});

function showEditError(elementId, message) {
  const errorEl = document.getElementById(elementId);
  errorEl.textContent = message;
  errorEl.classList.add('active');
}

// Clear error messages
function clearErrors() {
  document.querySelectorAll('.error-message').forEach(el => {
    el.classList.remove('active');
    el.textContent = '';
  });
  document.getElementById('successMessage').classList.remove('active');
}

// Save calendar event to localStorage
function saveCalendarEvent(event) {
  const EVENTS_KEY = 'planny_calendar_events';
  let events = [];
  const stored = localStorage.getItem(EVENTS_KEY);
  if (stored) {
    try {
      events = JSON.parse(stored);
    } catch (e) {
      events = [];
    }
  }
  
  // Check if event already exists
  const exists = events.some(e => e.taskID === event.taskID);
  if (!exists) {
    events.push(event);
    localStorage.setItem(EVENTS_KEY, JSON.stringify(events));
    console.log('Calendar event saved:', event);
  }
}

// Create calendar event after task is created
function createCalendarEvent(taskId) {
  fetch('/api/calendar-event/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({ taskID: taskId })
  })
  .then(response => response.json())
  .then(data => {
    if (data.event) {
      saveCalendarEvent(data.event);
      console.log('Event added to calendar');
    }
  })
  .catch(error => {
    console.error('Error creating calendar event:', error);
    // Don't fail task creation if calendar event fails
  });
}

// Handle form submission
document.getElementById('taskForm').addEventListener('submit', function(event) {
  event.preventDefault();
  
  clearErrors();

  const title = document.getElementById('taskTitle').value.trim();
  const description = document.getElementById('taskDescription').value.trim();
  const status = document.getElementById('taskStatus').value;
  const dueDate = document.getElementById('taskDueDate').value;
  const assignedTo = document.getElementById('taskAssignedTo').value;
  const project = document.getElementById('taskProject').value;
  const priority = document.getElementById('taskPriority').value;

  // Validation
  if (!title) {
    showError('titleError', 'Task title is required');
    return;
  }

  if (!status) {
    showError('statusError', 'Please select a status');
    return;
  }

  if (!project) {
    showError('projectError', 'Please select a project');
    return;
  }

  // Show loading
  document.getElementById('formLoading').classList.add('active');

  // Submit form
  fetch('/api/kanban-tasks/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({
      taskTitle: title,
      taskDescription: description,
      statusID: parseInt(status),
      dueDate: dueDate || null,
      assignedTo: assignedTo ? parseInt(assignedTo) : null,
      projectID: parseInt(project),
      priority: priority || null
    })
  })
  .then(response => {
    document.getElementById('formLoading').classList.remove('active');
    if (!response.ok) {
      return response.json().then(data => {
        throw new Error(data.error || 'Failed to create task');
      });
    }
    return response.json();
  })
  .then(data => {
    document.getElementById('successMessage').classList.add('active');
    setTimeout(() => {
      // Get the created task ID from response if available, or fetch it
      createCalendarEvent(data.taskID || 'latest');
      closeTaskModal();
      loadKanbanData();
    }, 1500);
  })
  .catch(error => {
    document.getElementById('formLoading').classList.remove('active');
    console.error('Error creating task:', error);
    showError('titleError', error.message);
  });
});

// Helper functions
function showError(elementId, message) {
  const errorEl = document.getElementById(elementId);
  errorEl.textContent = message;
  errorEl.classList.add('active');
}

function showErrorMessage(message) {
  const errorEl = document.getElementById('titleError');
  errorEl.textContent = message;
  errorEl.classList.add('active');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Close modal when clicking outside
document.getElementById('taskOverlay').addEventListener('click', function(event) {
  if (event.target === this) {
    closeTaskModal();
  }
});

// Close edit modal when clicking outside
document.getElementById('editTaskOverlay').addEventListener('click', function(event) {
  if (event.target === this) {
    closeEditTaskModal();
  }
});