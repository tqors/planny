# Generated migration to add userCalendarEvent table

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE TABLE IF NOT EXISTS userCalendarEvent (
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            reverse_sql="DROP TABLE IF EXISTS userCalendarEvent;"
        ),
    ]
