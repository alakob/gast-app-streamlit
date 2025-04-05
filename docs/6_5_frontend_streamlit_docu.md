# AMR Predictor - Frontend Documentation (Streamlit Implementation)

## 1. Overview

This document outlines the implementation of the AMR Predictor frontend using Streamlit. The frontend will provide an intuitive interface for users to interact with the AMR prediction and annotation services while maintaining scalability and performance.

### Key Features
- Sequence submission and analysis
- Real-time job status monitoring
- Batch processing capabilities
- Interactive visualization of results
- Responsive design for various screen sizes

## 2. Setup and Installation

### Dependencies
```bash
pip install streamlit
pip install streamlit-websockets-client
pip install plotly
pip install pandas
pip install requests
pip install python-dotenv
```

### Environment Configuration
Create a `.env` file in the frontend directory:
```bash
BACKEND_API_URL=http://localhost:8000
WEBSOCKET_URL=ws://localhost:8000
```

## 3. Implementation Phases

### Phase 1: Basic Setup and Single Sequence Analysis
#### Components to Implement:
1. Main page layout and navigation
2. Sequence input form
   - Text area for sequence input
   - Model selection dropdown
   - Submit button
3. Results display section
   - Prediction results card
   - Confidence score visualization
   - Annotation details expandable section

#### Implementation Example:
```python
import streamlit as st
import requests
import json

def main():
    st.title("AMR Predictor")
    
    # Sequence Input
    sequence = st.text_area("Enter DNA Sequence", height=150)
    model_id = st.selectbox("Select Model", ["amr_default"])
    
    if st.button("Analyze"):
        if validate_sequence(sequence):
            with st.spinner("Analyzing sequence..."):
                results = submit_sequence(sequence, model_id)
                display_results(results)

def validate_sequence(sequence):
    if not sequence:
        st.error("Please enter a sequence")
        return False
    if not all(c in "ACGT" for c in sequence.upper()):
        st.error("Invalid sequence. Only A, C, G, T allowed.")
        return False
    return True

def display_results(results):
    if results["status"] == "completed":
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Prediction", 
                     "Antimicrobial" if results["results"]["prediction"]["is_antimicrobial"] else "Non-antimicrobial")
        with col2:
            st.metric("Confidence", f"{results['results']['prediction']['confidence']*100:.1f}%")
```

#### Testing Checkpoints:
- [ ] Verify sequence input validation
- [ ] Confirm API connection and error handling
- [ ] Test results display formatting
- [ ] Validate model selection functionality

### Phase 2: Real-time Updates and WebSocket Integration
#### Components to Implement:
1. WebSocket connection manager
2. Progress indicator
3. Real-time status updates
4. Auto-refresh functionality

#### Implementation Example:
```python
import streamlit as st
from streamlit_websocket_client import WebSocketClient
import asyncio

class JobMonitor:
    def __init__(self, job_id):
        self.job_id = job_id
        self.ws_url = f"{os.getenv('WEBSOCKET_URL')}/ws/jobs/{job_id}"
        
    async def monitor_job(self):
        async with WebSocketClient(self.ws_url) as client:
            while True:
                message = await client.receive()
                data = json.loads(message)
                if data["type"] == "status_update":
                    st.session_state.job_status = data["data"]
                    st.experimental_rerun()
                elif data["type"] == "completed":
                    st.session_state.results = data["data"]["results"]
                    break
```

#### Testing Checkpoints:
- [ ] Verify WebSocket connection establishment
- [ ] Test real-time updates display
- [ ] Validate progress indicator accuracy
- [ ] Confirm proper connection closure

### Phase 3: Batch Processing Implementation
#### Components to Implement:
1. Batch upload interface
   - File upload support
   - Multiple sequence input
2. Batch progress tracking
3. Results summary table
4. Export functionality

#### Implementation Example:
```python
def batch_upload_section():
    st.header("Batch Analysis")
    
    uploaded_file = st.file_uploader("Upload FASTA file", type=["fasta", "txt"])
    if uploaded_file:
        sequences = parse_fasta_file(uploaded_file)
        st.write(f"Found {len(sequences)} sequences")
        
        if st.button("Start Batch Analysis"):
            batch_id = submit_batch(sequences)
            track_batch_progress(batch_id)

def track_batch_progress(batch_id):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    while True:
        batch_status = get_batch_status(batch_id)
        progress = batch_status["completed_jobs"] / batch_status["total_jobs"]
        progress_bar.progress(progress)
        status_text.text(f"Processed {batch_status['completed_jobs']} of {batch_status['total_jobs']} sequences")
        
        if batch_status["status"] == "completed":
            display_batch_results(batch_status["results"])
            break
```

#### Testing Checkpoints:
- [ ] Verify FASTA file parsing
- [ ] Test batch submission process
- [ ] Validate progress tracking
- [ ] Confirm results export functionality

### Phase 4: Data Visualization and Analysis
#### Components to Implement:
1. Interactive charts
   - Confidence score distribution
   - Class probability visualization
2. Annotation explorer
3. Results filtering and sorting
4. Data export options

#### Implementation Example:
```python
import plotly.express as px
import plotly.graph_objects as go

def create_visualization(results):
    # Confidence Score Distribution
    fig = px.histogram(
        results["class_probabilities"],
        title="Prediction Confidence Distribution"
    )
    st.plotly_chart(fig)
    
    # Annotation Explorer
    if "annotations" in results:
        with st.expander("Sequence Annotations"):
            display_annotations(results["annotations"])

def display_annotations(annotations):
    # Domain Visualization
    domains = annotations.get("domains", [])
    if domains:
        fig = go.Figure()
        for domain in domains:
            fig.add_shape(
                type="rect",
                x0=domain["start"],
                x1=domain["end"],
                y0=0,
                y1=1,
                name=domain["name"]
            )
        st.plotly_chart(fig)
```

#### Testing Checkpoints:
- [ ] Verify chart rendering
- [ ] Test interactive features
- [ ] Validate data export
- [ ] Confirm visualization responsiveness

## 4. Performance Optimization

### Caching Strategy
```python
@st.cache_data(ttl=3600)
def fetch_model_list():
    response = requests.get(f"{API_URL}/api/models")
    return response.json()

@st.cache_data(ttl=300)
def fetch_job_results(job_id):
    response = requests.get(f"{API_URL}/api/jobs/{job_id}")
    return response.json()
```

### Memory Management
- Implement session state cleanup
- Cache result visualizations
- Optimize large dataset handling

## 5. Error Handling and User Feedback

### Error Handling Implementation
```python
def handle_api_error(response):
    if response.status_code == 400:
        st.error("Invalid input. Please check your sequence.")
    elif response.status_code == 429:
        st.error("Too many requests. Please wait before trying again.")
    elif response.status_code >= 500:
        st.error("Server error. Please try again later.")
    else:
        st.error(f"Error: {response.json().get('error', {}).get('message', 'Unknown error')}")
```

### User Feedback
- Clear error messages
- Progress indicators
- Success notifications
- Help tooltips

## 6. Testing Guidelines

### Unit Tests
```python
import unittest
from unittest.mock import patch

class TestAMRPredictor(unittest.TestCase):
    def test_sequence_validation(self):
        valid_seq = "ACGTACGT"
        invalid_seq = "ACGTX"
        self.assertTrue(validate_sequence(valid_seq))
        self.assertFalse(validate_sequence(invalid_seq))

    @patch('requests.post')
    def test_sequence_submission(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"job_id": "test_id"}
        result = submit_sequence("ACGT", "amr_default")
        self.assertEqual(result["job_id"], "test_id")
```

### Integration Tests
- API connectivity
- WebSocket functionality
- Batch processing
- Data visualization

## 7. Deployment

### Production Configuration
```bash
# Production environment variables
BACKEND_API_URL=https://api.amrpredictor.example.com
WEBSOCKET_URL=wss://api.amrpredictor.example.com
```

### Deployment Command
```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

## 8. Maintenance and Monitoring

### Health Checks
- Regular API connectivity tests
- WebSocket connection monitoring
- Performance metrics tracking

### Logging
- User interaction events
- Error tracking
- Performance metrics

## Additional Resources
- Streamlit Documentation: https://docs.streamlit.io/
- Backend API Documentation: /docs or /redoc
- Support Contact: support@amrpredictor.example.com 