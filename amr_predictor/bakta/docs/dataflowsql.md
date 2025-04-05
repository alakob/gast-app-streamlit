

Data Flow Between Bakta and SQLite Database
Based on the code analysis, here's a clear explanation of how data flows between the Bakta annotation system and its SQLite database:

Architecture Layers
The Bakta module uses a well-structured, layered architecture for database interactions:

Interface Layer (BaktaUnifiedInterface)
Top-level API for applications
Provides user-friendly methods for all Bakta operations
Coordinates across other layers
Job Management Layer (BaktaJobManager)
Coordinates job submission, status tracking, and result retrieval
Connects the API client with local data storage
Repository Layer (BaktaRepository)
Provides higher-level database operations
Handles complex queries and data transformations
Data Access Object (DAO) Layer
BaseDAO: Abstract class defining common database operations
Specific DAOs (e.g., AnnotationDAO, ResultFileDAO, SequenceDAO)
Implements entity-specific database operations
Database Layer (DatabaseManager)
Core interaction with SQLite
Handles connection management, SQL execution, error handling
Implements CRUD operations for all entities
Data Flow for Common Operations
1. Job Submission Flow
CopyInsert
BaktaUnifiedInterface.submit_job()
  → BaktaJobManager
    → DatabaseManager.save_job()
      → SQLite Database (bakta_jobs table)
2. Annotation Storage Flow
CopyInsert
BaktaUnifiedInterface.import_results()
  → BaktaRepository.import_results()
    → AnnotationDAO
      → DatabaseManager.save_annotations()
        → SQLite Database (bakta_annotations table)
3. Status Updates Flow
CopyInsert
BaktaUnifiedInterface.update_job_status()
  → DatabaseManager.update_job_status()
    → DatabaseManager.save_job_status_history()
      → SQLite Database (bakta_jobs and bakta_job_status_history tables)
4. Annotation Query Flow
CopyInsert
BaktaUnifiedInterface.get_annotations()
  → BaktaRepository.query_annotations()
    → DatabaseManager.get_annotations()
      → SQLite Database (bakta_annotations table)
        → Results transformed into BaktaAnnotation objects
Database Schema
The SQLite database consists of several tables:

bakta_jobs - Stores job metadata, configuration, and status
bakta_sequences - Stores sequences submitted for annotation
bakta_result_files - Stores paths to downloaded result files
bakta_annotations - Stores actual annotation data extracted from results
bakta_job_status_history - Tracks historical status changes for jobs
Error Handling
Each layer implements consistent error handling:

Database errors (sqlite3.Error) are caught and wrapped in BaktaDatabaseError
DAO errors are caught and wrapped in DAOError
Application-level exceptions are wrapped in BaktaException
All operations include proper transaction management
This multi-layered architecture provides clean separation of concerns and follows database best practices.