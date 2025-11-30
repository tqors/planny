SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS admin;
DROP TABLE IF EXISTS complaint;
DROP TABLE IF EXISTS complaint_type;
DROP TABLE IF EXISTS fee;
DROP TABLE IF EXISTS fee_category;
DROP TABLE IF EXISTS guard;
DROP TABLE IF EXISTS report;
DROP TABLE IF EXISTS resident;
DROP TABLE IF EXISTS status;
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS visitor;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE user (
    userID INT AUTO_INCREMENT PRIMARY KEY,
    firstName VARCHAR(100),
    lastName VARCHAR(100),
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phoneNum VARCHAR(20)
);

CREATE TABLE status (
    statusID INT AUTO_INCREMENT PRIMARY KEY,
    statusDesc VARCHAR(255)
);

CREATE TABLE taskType (
    taskTypeID INT AUTO_INCREMENT PRIMARY KEY,
    taskTypeDesc VARCHAR(255)
);

CREATE TABLE admin (
    adminID INT PRIMARY KEY,
    adminLevel VARCHAR(50),
    FOREIGN KEY (adminID) REFERENCES user(userID)
);

CREATE TABLE developer (
    developerID INT PRIMARY KEY,
    programmingLanguage VARCHAR(255),
    FOREIGN KEY (developerID) REFERENCES user(userID)
);

CREATE TABLE client (
    clientID INT AUTO_INCREMENT PRIMARY KEY,
    companyName VARCHAR(255)
);

CREATE TABLE project (
    projectID INT AUTO_INCREMENT PRIMARY KEY,
    statusID INT,
    startDate DATE,
    endDate DATE,
    projectProgress INT,
    createdBy INT,
    clientID INT,
    FOREIGN KEY (statusID) REFERENCES status(statusID),
    FOREIGN KEY (createdBy) REFERENCES user(userID),
    FOREIGN KEY (clientID) REFERENCES client(clientID)
);

CREATE TABLE task (
    taskID INT AUTO_INCREMENT PRIMARY KEY,
    statusID INT,
    projectID INT,
    taskTypeID INT,
    assignedTo INT,
    taskTitle VARCHAR(255),
    taskDescription TEXT,
    dueDate DATE,
    taskComment VARCHAR(255),

    FOREIGN KEY (statusID) REFERENCES status(statusID),
    FOREIGN KEY (projectID) REFERENCES project(projectID),
    FOREIGN KEY (taskTypeID) REFERENCES taskType(taskTypeID),
    FOREIGN KEY (assignedTo) REFERENCES developer(developerID)
);

CREATE TABLE taskAssignment (
    taskID INT,
    developerID INT,
    PRIMARY KEY (taskID, developerID),
    FOREIGN KEY (taskID) REFERENCES task(taskID),
    FOREIGN KEY (developerID) REFERENCES developer(developerID)
);

CREATE TABLE projectAssignment (
    projectID INT,
    developerID INT,
    roleInProject VARCHAR(255),
    PRIMARY KEY (projectID, developerID),
    FOREIGN KEY (projectID) REFERENCES project(projectID),
    FOREIGN KEY (developerID) REFERENCES developer(developerID)
);

ALTER TABLE project
ADD COLUMN projectName VARCHAR(255) NOT NULL AFTER projectID;


