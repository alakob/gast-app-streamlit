# Architecture Component Explanations

This document provides details on the components shown in the architecture diagram in the main README.

1.  **User Interaction:**
    *   `User`: The end-user interacting with the application through their web browser.

2.  **Frontend (Streamlit):**
    *   `Streamlit UI (app.py)`: The main web interface built with Streamlit. Handles user input (sequence entry, file uploads, setting parameters), displays information (validation, statistics, job status, results), and orchestrates calls to the backend API.
    *   `Streamlit Utils (utils.py)`: Contains helper functions used by the main UI, such as sequence validation, statistics calculation, dataframe filtering, and potentially formatting.
    *   `Session State`: Streamlit's mechanism for maintaining user-specific data across interactions within a single session (e.g., input sequence, job IDs, selected parameters, current tab).

3.  **Backend (FastAPI):**
    *   `AMR FastAPI`: The core backend API built with FastAPI. It exposes endpoints for job submission, status checking, and retrieving results. It handles business logic, coordinates with other backend components, and interacts with the database.
    *   `AMR Prediction Model`: The internal machine learning model or logic responsible for performing the actual AMR prediction based on the input sequence. This is called by the API.
    *   `Bakta Client/Executor`: A component within the API responsible for communicating with the external Bakta service. It handles submitting annotation jobs, checking their status, and retrieving results, likely using the Bakta job `secret`.
    *   `Database Client (SQLAlchemy, asyncpg)`: Handles all communication with the PostgreSQL database using SQLAlchemy ORM and asyncpg for asynchronous operations. Responsible for CRUD operations on job, result, user, and other tables.
    *   `Auth (Potential)`: Represents potential authentication/authorization mechanisms (e.g., user logins, API keys) that might secure the API endpoints.

4.  **Database (PostgreSQL):**
    *   `PostgreSQL Database`: The relational database storing persistent data, including job details (AMR & Bakta), job parameters, job status history, sequences, annotation results, potentially user information, and AMR antibiotic reference data.
    *   `Schema Init Scripts`: SQL files (like `02a-create-bakta-schema.sql`, `02-init-amr-schema.sql`) located in `docker/postgres/init/` that define and create the necessary tables and indexes when the database container starts.

5.  **External Services:**
    *   `Bakta Service/API`: An external service (or potentially a separate container/process managed by the system) responsible for performing genome annotation using Bakta. The FastAPI backend interacts with it via the `Bakta Client`.

6.  **Infrastructure & Deployment (Docker):**
    *   `build_container.sh`: A shell script used by developers to automate the build process. It stops/removes old containers/volumes, rebuilds images, starts containers in the correct order (DB first), verifies the DB schema, and tails logs.
    *   `Docker Environment`: The set of containers managed by Docker Compose (Streamlit, API, DB, pgAdmin).
    *   `Docker Volumes`: Persistent storage managed by Docker, used for the PostgreSQL data, and potentially for storing large result files.

7.  **Logging & Monitoring:**
    *   `Logging (Python Logger)`: Standard Python logging used within both the Streamlit and FastAPI applications to record events, errors, and debug information. Logs might be output to the console or configured for other destinations. 