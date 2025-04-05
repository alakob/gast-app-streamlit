I'll analyze the Bakta API documentation to understand the integration requirements for your UI.

First, let me understand how Bakta API works according to the documentation:

Search files...
Let me look at how the data is stored in the database:

Search files...
Let me also check the database manager to see how jobs are stored and retrieved:

Search files...
Let me check the current UI structure to understand how we can integrate Bakta job management:

Search files...
I need to look at the result display to understand the current implementation:

Search files...
Let me see what actual job result files exist and how they're handled:

Search files...
Let me check the Bakta result visualization part:

Search files...
I need to check the actual app.py current version to see if there's any result viewing functionality:

Read file: streamlit_app/app.py
Let's search specifically for the bakta results section in app.py:

Ran tool
Let's see what happens in the results tab:

Read file: streamlit_app/app.py
Let's look at what happens further down in the results display section:

Read file: streamlit_app/app.py
Let's see the rendering of actual results:

Read file: streamlit_app/app.py
Based on my analysis of the codebase and documentation, here's my comprehensive plan for improving the Bakta job management and results visualization UI:

# Bakta Integration UI Improvement Plan

## 1. Analysis of Bakta API Integration

The codebase implements Bakta API integration in accordance with the documentation. Key observations:

- The workflow follows the documented process: Init -> Put Data -> Start -> List -> Query Results
- Job metadata is stored both in files (`bakta_job_{job_id}.json`) and a SQLite database
- Results are downloaded and stored in a dedicated directory (`bakta_results_{job_id}`)
- The system handles API-specific error cases and implements proper retry logic

The implementation is generally conformant with the API documentation, with appropriate error handling and backup storage mechanisms.

## 2. Data Storage Architecture

The system uses a hybrid approach for storing Bakta job data:

**Database Storage:**
- SQLite database (`bakta_jobs.db`) with tables for jobs, results, and status history
- Job data includes ID, secret, status, submission time, completion time, etc.
- Result files are tracked with paths, file types, and sizes
- Status history table tracks job status changes over time

**Filesystem Storage:**
- Job metadata in JSON files (`bakta_job_{job_id}.json`)
- Result files in dedicated directories (`bakta_results_{job_id}/`)
- Result metadata in JSON files (`result_info.json`)

The dual storage provides redundancy, with the database being the primary source and filesystem as fallback.

## 3. UI Improvements for Bakta Job Management

### Left Panel - Active Jobs Overview

**Proposal:** Create a dedicated sidebar section for active Bakta jobs.

```
- "Active Bakta Jobs" panel in the sidebar
  - Real-time status indicators with color coding
  - Progress indicators for running jobs
  - Status counts (Running: 3, Queued: 2, Error: 1)
  - Quick access links to job details
  - Notification badge for newly completed jobs
```

**Implementation Details:**
1. Add a collapsible section in the sidebar that shows only active jobs
2. Use eye-catching status icons and colors (green for success, blue for running, orange for queued, red for errors)
3. Include a mini progress bar for running jobs
4. Show estimated completion time based on job size and elapsed time
5. Add a notification system that alerts users when jobs complete

### Main UI - Job Management Interface

**Proposal:** Enhance the existing job management UI with better organization and filtering.

```
- Job Dashboard with:
  - Filterable, sortable table view with key metrics
  - Visual timeline of jobs (submitted → running → completed)
  - Batch actions (refresh multiple jobs, delete multiple jobs)
  - Job search by name, ID, status, date range
  - Detailed job cards with expandable sections
```

**Implementation Details:**
1. Implement tabs for different job states: "All Jobs", "Running", "Completed", "Failed"
2. Add rich filtering options (by date, name, status, etc.)
3. Create a visual timeline showing job progress across pipeline stages
4. Add batch operations for managing multiple jobs simultaneously
5. Improve the job cards with more detailed information and action buttons
6. Implement pagination for handling large numbers of jobs

## 4. Results Visualization Interface

**Proposal:** Create a comprehensive, interactive results visualization interface.

```
- Results Explorer with:
  - Multi-tab interface for different result file types
  - Interactive genome plot with feature highlighting
  - Feature counts visualization (bar/pie charts)
  - Feature search and filtering
  - Genome statistics dashboard
  - Export options for different formats
```

**Implementation Details:**
1. Create a dedicated results page with multiple visualization tabs:
   - **Overview Tab**: Summary statistics, genome size, GC content, feature counts
   - **Genome Plot Tab**: Interactive circular plot with clickable features
   - **Features Tab**: Searchable, filterable table of all features
   - **Sequences Tab**: Access to sequence data with search capability
   - **Files Tab**: Access to all result files for download

2. For feature visualization:
   - Interactive genome browser for navigating genes and features
   - Feature highlighting by type (CDS, tRNA, rRNA, etc.)
   - Detailed popup information on feature hover/click
   - Zoom in/out and pan capabilities
   - Option to toggle feature layers

3. For statistics visualization:
   - Dashboard with key genome metrics
   - Bar charts for feature type distribution
   - Pie charts for functional categories
   - GC content distribution across genome
   - Contig length distribution for draft genomes

## 5. Running Jobs Status Display

**Proposal:** Implement a real-time status monitor for running Bakta jobs.

```
- Live Status Monitor with:
  - Auto-refreshing status cards
  - Detailed progress information
  - Log viewer for running jobs
  - Estimated time remaining
  - Resource usage indicators
  - Ability to cancel running jobs
```

**Implementation Details:**
1. Implement a WebSocket-based or polling mechanism for real-time updates
2. Show detailed progress information parsed from Bakta logs
3. Add a log viewer for monitoring job execution in real time
4. Calculate and display estimated completion time based on progress
5. Add options to pause, resume, or cancel jobs
6. Implement status change notifications

## Implementation Plan

### Phase 1: Core UI Framework (2 weeks)
1. Design and implement the left panel active jobs component
2. Enhance the job management table with filtering and sorting
3. Improve job cards with detailed information and status indicators
4. Implement real-time status updating mechanism

### Phase 2: Results Visualization (3 weeks)
1. Develop the multi-tab results interface
2. Implement the genome statistics dashboard
3. Create the interactive circular genome plot
4. Build the feature browser with search capabilities
5. Develop the sequence viewer component

### Phase 3: Advanced Features (2 weeks)
1. Implement batch job management operations
2. Add export functionality for different file formats
3. Create the detailed log viewer
4. Implement job timeline visualization
5. Add notification system for job status changes

### Phase 4: Testing and Optimization (1 week)
1. Test with various job types and result sizes
2. Optimize performance for large result sets
3. Improve error handling and recovery
4. Enhance mobile responsiveness
5. Add user preferences and customization options

## Technical Considerations

1. **Performance**: Implement lazy loading for large result files and pagination for feature tables
2. **Caching**: Cache processed results to avoid repeated parsing of large files
3. **Responsive Design**: Ensure UI works well on different screen sizes
4. **Error Recovery**: Improve handling of missing or corrupted result files
5. **Background Processing**: Move heavy processing to background threads to keep UI responsive

By implementing these improvements, the Bakta integration will provide users with a more intuitive, informative, and efficient workflow for genome annotation tasks.
