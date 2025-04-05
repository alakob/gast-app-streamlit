# AMR Predictor - Frontend Development Documentation

## Introduction

This document provides comprehensive guidelines for developing the React.js frontend for the AMR Predictor application. The frontend will interface with the existing backend API to provide users with a seamless experience for predicting antimicrobial properties of genetic sequences and viewing comprehensive annotations.

## System Overview

The AMR Predictor frontend will:
- Allow users to submit genetic sequences for analysis
- Display prediction and annotation results
- Support both single sequence and batch processing
- Provide real-time updates during job processing
- Implement intuitive data visualization for results

## Development Phases

### Phase 1: Project Setup and Core Architecture

#### 1.1. Environment Setup
- Initialize a new React application using Create React App or Next.js
- Configure project structure following React best practices
- Setup TypeScript for type safety
- Install and configure essential dependencies:
  ```bash
  npm install axios react-router-dom @tanstack/react-query formik yup react-toastify recharts
  npm install tailwindcss postcss autoprefixer --save-dev
  ```

#### 1.2. State Management & API Integration
- Implement API service layer using Axios
- Configure React Query for server state management
- Create custom hooks for backend API interactions
- Implement WebSocket connection utilities for real-time updates

#### 1.3. Authentication Foundation (if required)
- Setup authentication context
- Implement token management and secure storage
- Create login/register components if needed

#### Testing Checkpoint 1:
- Verify API connection and data fetching
- Ensure WebSocket connections can be established
- Validate proper rendering of core components
- Test responsive layouts across device sizes

### Phase 2: Sequence Submission and Job Management

#### 2.1. Sequence Input Interface
- Create an intuitive sequence input form with validation
- Implement file upload capability for FASTA files
- Add sequence validation based on backend rules (A, C, G, T characters)
- Provide model selection options

#### 2.2. Job Management Interface
- Develop job submission workflow
- Create job status dashboard
- Implement job history and results browsing
- Add batch job submission capabilities

#### 2.3. Real-time Status Updates
- Implement WebSocket integration for `/ws/jobs/{job_id}`
- Create progress indicators for long-running jobs
- Add notifications for job completion or errors

#### Testing Checkpoint 2:
- Verify sequence submission with various input methods
- Test batch submission functionality
- Ensure real-time updates are received and displayed correctly
- Confirm proper error handling and user feedback

### Phase 3: Results Visualization and Data Display

#### 3.1. Results Dashboard
- Create comprehensive results view
- Implement tabbed interface for different result sections
- Design responsive layouts for various screen sizes

#### 3.2. Prediction Visualization
- Develop charts and graphics for prediction confidence
- Create visual representations of class probabilities
- Implement summary cards for key prediction metrics

#### 3.3. Annotation Display
- Create expandable sections for annotation details
- Implement sequence visualization with domain highlighting
- Design intuitive navigation for complex annotation data

#### Testing Checkpoint 3:
- Verify correct rendering of all result components
- Test visualization components with various data sets
- Ensure proper handling of edge cases (missing data, large datasets)
- Validate accessibility of visualization components

### Phase 4: Advanced Features and Optimizations

#### 4.1. Caching and Performance
- Implement client-side caching strategies
- Optimize component rendering for large datasets
- Add virtualization for long lists

#### 4.2. Advanced User Features
- Create comparison view for multiple results
- Implement export functionality (PDF, CSV)
- Add sequence history with local storage
- Create custom visualization settings

#### 4.3. Error Handling and Fallbacks
- Implement comprehensive error boundaries
- Create fallback UI components
- Add offline capabilities where applicable
- Implement retry mechanisms for failed requests

#### Testing Checkpoint 4:
- Benchmark application performance
- Test error recovery scenarios
- Verify export functionality with various browsers
- Validate caching mechanisms work as expected

## Technical Implementation Details

### API Integration

#### Core API Services

Create a dedicated API service layer:

```javascript
// api/amrApi.js
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const amrApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Single sequence analysis
export const analyzeSequence = async (sequence, modelId = 'amr_default') => {
  return amrApi.post('/api/analyze', { sequence, model_id: modelId });
};

// Create async job
export const createJob = async (sequence, modelId = 'amr_default', includeAnnotations = true) => {
  return amrApi.post('/api/jobs', { 
    sequence, 
    model_id: modelId,
    include_annotations: includeAnnotations 
  });
};

// Get job status and results
export const getJobStatus = async (jobId) => {
  return amrApi.get(`/api/jobs/${jobId}`);
};

// Submit batch job
export const submitBatch = async (sequences, modelId = 'amr_default', includeAnnotations = true) => {
  return amrApi.post('/api/batch', {
    sequences,
    model_id: modelId,
    include_annotations: includeAnnotations
  });
};

// Get batch status
export const getBatchStatus = async (batchId) => {
  return amrApi.get(`/api/batch/${batchId}`);
};

// Get available models
export const getModels = async () => {
  return amrApi.get('/api/models');
};

export default amrApi;
```

#### WebSocket Integration

Implement WebSocket connection for real-time updates:

```javascript
// utils/websocket.js
export class JobWebSocket {
  constructor(jobId, callbacks) {
    this.jobId = jobId;
    this.callbacks = callbacks;
    this.socket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    const wsUrl = `${process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}/ws/jobs/${this.jobId}`;
    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      if (this.callbacks.onOpen) this.callbacks.onOpen();
    };

    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (this.callbacks.onMessage) this.callbacks.onMessage(message);
        
        // Handle specific message types
        if (message.type === 'status_update' && this.callbacks.onStatusUpdate) {
          this.callbacks.onStatusUpdate(message.data);
        }
        
        if (message.type === 'completed' && this.callbacks.onCompleted) {
          this.callbacks.onCompleted(message.data);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.socket.onclose = (event) => {
      if (this.callbacks.onClose) this.callbacks.onClose(event);
      this.handleReconnect();
    };

    this.socket.onerror = (error) => {
      if (this.callbacks.onError) this.callbacks.onError(error);
    };
  }

  handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const timeout = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      setTimeout(() => this.connect(), timeout);
    }
  }

  disconnect() {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.close();
    }
  }
}
```

### Component Structure

The frontend will follow a modular component structure:

```
src/
├── api/
│   ├── amrApi.js
│   └── index.js
├── components/
│   ├── common/
│   │   ├── Button.jsx
│   │   ├── Card.jsx
│   │   ├── Input.jsx
│   │   └── ...
│   ├── layout/
│   │   ├── Header.jsx
│   │   ├── Footer.jsx
│   │   └── ...
│   ├── sequence/
│   │   ├── SequenceInput.jsx
│   │   ├── SequenceValidator.jsx
│   │   └── ...
│   ├── results/
│   │   ├── PredictionView.jsx
│   │   ├── AnnotationView.jsx
│   │   └── ...
│   └── jobs/
│       ├── JobsList.jsx
│       ├── JobStatus.jsx
│       └── ...
├── hooks/
│   ├── useJobStatus.js
│   ├── useWebSocket.js
│   └── ...
├── pages/
│   ├── Home.jsx
│   ├── AnalyzePage.jsx
│   ├── ResultsPage.jsx
│   ├── BatchPage.jsx
│   └── ...
├── utils/
│   ├── websocket.js
│   ├── formatters.js
│   └── ...
└── context/
    ├── AuthContext.jsx
    └── ...
```

## User Interface Guidelines

### Design System

- Implement a consistent color scheme that enhances data visualization
- Use clear visual hierarchies for complex result displays
- Ensure proper spacing and typography for readability of technical information
- Follow accessibility guidelines (WCAG 2.1 AA compliance)

### Key UI Components

1. **Sequence Input Area**
   - Multi-line text input with syntax highlighting for genetic sequences
   - File upload dropzone with preview
   - Input validation with clear error messages

2. **Job Management Dashboard**
   - Status cards with clear visual indicators
   - Progress bars for long-running jobs
   - Sortable and filterable job history table

3. **Results Visualization**
   - Interactive charts for prediction confidence
   - Sequence viewer with domain highlighting
   - Collapsible sections for detailed annotations
   - Export options for results

## Performance Considerations

- Implement code splitting for faster initial load times
- Use React.memo and useMemo for expensive computations
- Implement virtualization for long lists of results or sequences
- Optimize WebSocket connections to prevent memory leaks
- Use efficient state management to prevent unnecessary re-renders

## Error Handling Strategy

- Implement error boundaries to prevent UI crashes
- Create user-friendly error messages for common failure scenarios
- Add retry mechanisms for transient network failures
- Provide fallback UI for unavailable features
- Log errors for debugging and improvement

## Deployment Recommendations

- Configure CI/CD pipeline for automated testing and deployment
- Implement environment-specific configuration
- Setup monitoring and error tracking (Sentry, LogRocket)
- Configure proper caching headers for static assets
- Use a CDN for global distribution if applicable

## Testing Strategy

### Unit Testing
- Test individual components in isolation
- Use React Testing Library for component testing
- Mock API responses for predictable test outcomes

### Integration Testing
- Test component interactions
- Verify API integration with mock servers
- Test WebSocket functionality

### End-to-End Testing
- Use Cypress for full workflow testing
- Test complete user journeys

### Performance Testing
- Lighthouse audits for performance metrics
- Bundle size monitoring
- First contentful paint optimization

## Conclusion

This frontend development documentation provides a structured approach to building a React.js application that integrates with the AMR Predictor backend. By following the phased development process and adhering to the technical specifications outlined in this document, developers can create a robust, user-friendly interface that maximizes the utility of the underlying prediction and annotation capabilities.

Always refer to the backend API documentation for the most up-to-date endpoint specifications and data formats when implementing frontend integrations. 