-- Add userCalendarEvent table for storing user-specific calendar events
-- This allows users to save and persist calendar events server-side

CREATE TABLE IF NOT EXISTS userCalendarEvent (
    eventID INT AUTO_INCREMENT PRIMARY KEY,
    userID INT NOT NULL,
    taskID INT,
    eventTitle VARCHAR(255) NOT NULL,
    eventDescription TEXT,
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
