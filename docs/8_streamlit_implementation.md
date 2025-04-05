
# AMR App Streamlit UI Implementation Action Plan

Thank you for providing the requirements for the AMR app's Streamlit interface. Here's a detailed action plan for implementing the UI according to your specifications:

## 1. Project Setup and Structure
- **Create a main Streamlit app file (`app.py`)**
- **Create supporting modules:**
  - `config.py` - For configuration settings
  - `api_client.py` - For handling API requests to AMR and Bakta services
  - `ui_components.py` - For reusable UI components
  - `utils.py` - For utility functions (sequence validation, file parsing, etc.)

## 2. Left Panel Implementation
- Create a sidebar using `st.sidebar` containing:
  - App title and description
  - Parameter settings organized in logical sections:
    - **AMR Prediction Parameters** (from predict endpoint)
    - **Sequence Processing Parameters** (from sequence endpoint)
  - Status indicators

## 3. Tab Structure Implementation
Create the main tab structure using `st.tabs()` with the following tabs:

### Tab 1: Annotation Settings
- Add a checkbox to enable Bakta annotation
- Create collapsible sections for Bakta API parameters (read from `bakta.md`)
- Include tooltips explaining each parameter
- Implement validation for parameter inputs

### Tab 2: Sequence Input
- Create two input methods:
  - Text area for direct sequence input
  - File uploader for FASTA/text files
- Implement sequence validation to ensure only DNA nucleotides are accepted
- Add visual feedback for invalid inputs
- Include a sample sequence button
- Show sequence statistics (length, GC content)
- Run/Submit button


### Tab 3: Results
- Design a results display area with:
  - Status indicators
  - JSON/table toggle view
  - Download options for results
  - Visualization components for AMR predictions
  - Collapsible sections for detailed results
- Add error handling and user-friendly messages

### Tab 4: Job Management
- Create a job listing interface showing:
  - Job ID
  - Status
  - Submission time
  - Type of analysis
- Implement job controls (cancel, resubmit, download)
- Add job filtering and sorting options
- Include job details expansion panel

## 4. State Management
- Implement session state for maintaining user inputs across interactions
- Create caching mechanisms for API responses
- Design a workflow state manager to track app state

## 5. API Integration

### AMR API Integration
- Import and interface with AMR API endpoints:
  ```python
  from amr_predictor.api_client import AMRApiClient
  
  def create_amr_client():
      return AMRApiClient(
          base_url=config.AMR_API_URL,
          api_key=config.AMR_API_KEY
      )
  ```
- Implement request handling for:
  - Submitting sequences for AMR prediction
  - Retrieving prediction results
  - Managing job status
- Add error handling and retry logic for API calls
- Implement queuing mechanism for multiple job submissions

### Bakta API Integration
- Utilize the Bakta unified interface for genome annotation:
  ```python
  from amr_predictor.bakta import (
      get_interface, 
      BaktaException,
      BaktaApiError
  )
  
  def create_bakta_interface():
      # Configuration is read from environment variables by default
      # Can be overridden with specific parameters if needed
      return get_interface()
  ```
- Implement conditional Bakta processing when the checkbox is enabled
- Create helper functions based on the example workflow in `amr_predictor/bakta/examples/run_bakta_job.py`:
  ```python
  def submit_bakta_job(fasta_data, bakta_config):
      interface = create_bakta_interface()
      
      # Submit job with configuration from the UI
      job = interface.submit_job(
          fasta_path=fasta_data,
          job_name=f"streamlit_job_{datetime.now().strftime('%Y%m%d%H%M%S')}",
          config=bakta_config
      )
      
      return job.job_id
  ```
- Add monitoring for job status:
  ```python
  def check_bakta_job_status(job_id):
      interface = create_bakta_interface()
      return interface.get_job_status(job_id)
  ```
- Create results retrieval:
  ```python
  def get_bakta_results(job_id):
      interface = create_bakta_interface()
      if interface.get_job_status(job_id) == "SUCCESSFUL":
          return interface.get_job_results(job_id)
      return None
  ```

### Integration with Streamlit UI
- Implement asynchronous processing for long-running operations using threading:
  ```python
  import threading
  
  def run_bakta_job_async(fasta_data, bakta_config, callback):
      def _run():
          try:
              job_id = submit_bakta_job(fasta_data, bakta_config)
              st.session_state.bakta_job_id = job_id
              callback(job_id)
          except Exception as e:
              st.error(f"Error submitting Bakta job: {str(e)}")
      
      thread = threading.Thread(target=_run)
      thread.start()
  ```
- Add progress indicators and status updates in the UI
- Implement intelligent polling with backoff for job status checks
- Create unified error handling for both API services

## 6. UI Enhancements
- Apply consistent styling to match the stride-gpt app
- Add progress indicators for API calls
- Implement responsive design elements
- Add helpful tooltips and documentation links

## 7. Testing Plan
- Create test cases for sequence validation
- Test parameter validation logic
- Test API integration with mock responses
- Conduct usability testing

This plan provides a comprehensive roadmap for implementing the AMR app's Streamlit interface. Once you approve this plan, we can proceed with the implementation phase.

Would you like me to elaborate on any specific section of this plan before we move forward?

---

Feedback submitted
Generating
```

Let me know if you need any adjustments!