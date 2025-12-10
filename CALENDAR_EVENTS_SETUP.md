# Server-Side Calendar Events Implementation

## Overview
Added persistent server-side storage for user calendar events. Users can now create, read, update, and delete calendar events that are stored in the database and persist across sessions.

## Database Changes

### New Table: `userCalendarEvent`
```sql
CREATE TABLE userCalendarEvent (
    eventID INT AUTO_INCREMENT PRIMARY KEY,
    userID INT NOT NULL,
    taskID INT,
    eventTitle VARCHAR(255) NOT NULL,
    eventDescription LONGTEXT,
    startDate DATE,
    endDate DATE,
    isTaskBased BOOLEAN DEFAULT 0,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (userID) REFERENCES user(userID) ON DELETE CASCADE,
    FOREIGN KEY (taskID) REFERENCES task(taskID) ON DELETE SET NULL,
    INDEX (userID),
    INDEX (taskID)
);
```

**Migration file**: `apps/home/migrations/0002_add_user_calendar_events.py`

Run migrations to create the table:
```bash
python manage.py migrate
```

## API Endpoints

### 1. List User Calendar Events
**Endpoint**: `GET /api/user-calendar-events/`

**Authentication**: Required (login_required)

**Response**:
```json
{
  "events": [
    {
      "eventID": 1,
      "taskID": null,
      "summary": "Team Meeting",
      "description": "Q4 planning meeting",
      "start": {"date": "2025-12-10"},
      "end": {"date": "2025-12-11"},
      "isTaskBased": false,
      "createdAt": "2025-12-07T10:30:00"
    }
  ]
}
```

### 2. Create Calendar Event
**Endpoint**: `POST /api/user-calendar-events/`

**Authentication**: Required

**Request Body**:
```json
{
  "eventTitle": "Team Meeting",
  "eventDescription": "Q4 planning meeting",
  "startDate": "2025-12-10",
  "endDate": "2025-12-11",
  "taskID": null
}
```

**Response**:
```json
{
  "success": true,
  "eventID": 1,
  "message": "Calendar event created successfully"
}
```

### 3. Update Calendar Event
**Endpoint**: `PATCH /api/user-calendar-events/<event_id>/`

**Authentication**: Required

**Request Body** (partial update):
```json
{
  "eventTitle": "Updated Meeting Title",
  "startDate": "2025-12-12"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Event updated successfully"
}
```

### 4. Delete Calendar Event
**Endpoint**: `DELETE /api/user-calendar-events/<event_id>/`

**Authentication**: Required

**Response**:
```json
{
  "success": true,
  "message": "Event deleted successfully"
}
```

## Updated Components

### Backend (`apps/home/views.py`)
- **`user_calendar_events_api(request)`**: GET/POST handler for user calendar events
- **`user_calendar_event_detail_api(request, event_id)`**: PATCH/DELETE handler for individual events

### Frontend (`apps/templates/home/calender.html`)
- Updated `loadCalendar()` to fetch both:
  - User-persisted calendar events via `/api/user-calendar-events/`
  - Auto-generated task events via `/api/calendar-events/`
- Merges and displays all events in the calendar event list

### URLs (`apps/home/urls.py`)
Added two new routes:
```python
path('api/user-calendar-events/', views.user_calendar_events_api, name='user_calendar_events_api'),
path('api/user-calendar-events/<int:event_id>/', views.user_calendar_event_detail_api, name='user_calendar_event_detail_api'),
```

## Features

✅ **User-Specific Events**: Each user's calendar events are isolated and private
✅ **Linked to Tasks**: Calendar events can optionally reference tasks (for future task-to-event linking)
✅ **Timestamps**: Creation and update timestamps for audit trails
✅ **Full CRUD**: Create, Read, Update, Delete calendar events
✅ **Date Validation**: Automatic date parsing and validation
✅ **Authorization**: Users can only access/modify their own events
✅ **Cascade Delete**: When a user is deleted, their calendar events are removed

## Usage Example

### Creating a calendar event via JavaScript:
```javascript
const event = {
  eventTitle: "Project Review",
  eventDescription: "Review Q4 progress",
  startDate: "2025-12-15",
  endDate: "2025-12-15",
  taskID: null
};

fetch('/api/user-calendar-events/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(event)
})
.then(r => r.json())
.then(data => console.log('Event created:', data.eventID));
```

### Updating a calendar event:
```javascript
fetch('/api/user-calendar-events/1/', {
  method: 'PATCH',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    eventTitle: "Updated Title",
    startDate: "2025-12-20"
  })
})
.then(r => r.json())
.then(data => console.log('Event updated:', data));
```

### Deleting a calendar event:
```javascript
fetch('/api/user-calendar-events/1/', {
  method: 'DELETE'
})
.then(r => r.json())
.then(data => console.log('Event deleted:', data));
```

## Migration Steps

1. **Backup your database** (recommended)
2. **Run migrations**:
   ```bash
   cd /path/to/interface
   python manage.py migrate home
   ```
3. **Verify the table was created**:
   ```sql
   DESCRIBE userCalendarEvent;
   ```
4. **Test the new endpoints** via the calendar page

## Notes

- Calendar events are now displayed alongside auto-generated task events
- Events persist server-side and survive browser cache clears
- The `isTaskBased` flag is reserved for future task-event linking
- All timestamps use MySQL server time (CURRENT_TIMESTAMP)
- The `taskID` field can link events to specific tasks (currently optional)
