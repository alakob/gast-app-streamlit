# Bakta Annotation Integration: Action Plan

## Phase 1: Bakta API Integration & Job Submission

1. **API Client Setup**
   - Implement/leverage existing Bakta API client in `amr_predictor/bakta/`
   - Create connection handlers with appropriate error handling
   - Implement authentication mechanisms for external Bakta API

2. **Job Submission Flow**
   - Create a submission handler in the Streamlit app to trigger Bakta jobs
   - Add validation for input sequence files
   - Generate unique job IDs and track submission metadata
   - Implement progress indicators during submission

3. **Database Schema Updates**
   - Define schema for Bakta job tracking in PostgreSQL
   - Create tables for:
     - Bakta job metadata (job_id, status, timestamps, etc.)
     - Annotation results (features, sequences, etc.)
     - Relationship to submitted sequence data

## Phase 2: Job Status Monitoring

1. **Status Polling System**
   - Implement an asynchronous polling mechanism to check Bakta job status
   - Create status update handlers with appropriate refresh rates
   - Implement timeout and retry logic for resilience

2. **Status UI Components**
   - Add status indicators in the Annotation tab
   - Create progress bars/spinners for running jobs
   - Implement error handling and user-friendly error messages
   - Add estimated time remaining where possible

3. **Session State Management**
   - Store job status in Streamlit session state
   - Implement persistence across page refreshes
   - Create mechanisms to link Bakta jobs with AMR prediction jobs

## Phase 3: Results Processing & Storage

1. **Results Retrieval**
   - Implement handlers to fetch completed annotation results
   - Create parsers for Bakta result formats (JSON, TSV, etc.)
   - Handle large result sets efficiently

2. **Database Storage**
   - Implement DAO layer for Bakta results
   - Create efficient storage patterns for potentially large annotation datasets
   - Implement data validation before storage

3. **Result Processing**
   - Create utility functions to process and transform raw Bakta data
   - Generate derived data for visualization
   - Implement caching for frequently accessed results

## Phase 4: UI Implementation for Annotation Tab

1. **Tab Structure**
   - Create a nested tab structure within the Annotation tab:
     - **Overview**: Summary statistics and key findings
     - **Genomic Features**: Detailed list of annotated features
     - **Sequence Viewer**: Interactive view of annotated sequences
     - **Functional Analysis**: Pathway and functional annotations
     - **Raw Data**: Access to raw annotation files

2. **Interactive Components**
   - Create filterable tables for genomic features
   - Implement sorting and searching capabilities
   - Add expandable sections for detailed feature information
   - Create feature type toggles (CDS, rRNA, tRNA, etc.)

3. **Visualization Components**
   - Implement genome map visualization
   - Create gene distribution charts
   - Add functional category breakdown visualizations
   - Implement sequence detail viewer with feature highlighting

4. **Data Export**
   - Add download buttons for raw data files
   - Create export options for processed results
   - Implement report generation capabilities

## Phase 5: Integration & Testing

1. **Cross-Feature Integration**
   - Connect annotation data with AMR prediction results
   - Create unified views showing both annotation and resistance data
   - Implement correlation analysis between annotations and resistance

2. **Performance Optimization**
   - Optimize database queries for large result sets
   - Implement data pagination and lazy loading
   - Add caching for frequently accessed data

3. **Comprehensive Testing**
   - Create unit tests for all components
   - Implement integration tests for API flows
   - Perform UI testing for all interactive components
   - Test with real-world data volumes and edge cases

## Technical Considerations

1. **Docker Volume Management**
   - Ensure proper file sharing between containers
   - Maintain consistent path references

2. **Security**
   - Implement proper API authentication
   - Sanitize all user inputs
   - Validate sequence data before submission

3. **Error Handling**
   - Create comprehensive error handling for API failures
   - Implement user-friendly error messages
   - Add logging for debugging and monitoring

4. **Performance**
   - Consider pagination for large result sets
   - Implement efficient database access patterns
   - Use asynchronous processing where appropriate

This phased approach will allow for iterative development and testing, ensuring that each component works correctly before moving to the next phase.