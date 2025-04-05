### Prompt for Technical Documentation

You are tasked with creating detailed technical documentation for our Python-based antimicrobial sequence prediction application. This documentation will guide frontend developers in building an intuitive web-based UI that supports concurrent use by multiple users. The application includes a backend service with the following functionality: it loads a transformer model, processes user-provided sequences, fetches annotations for those sequences via an external API, and stores the annotations in an SQLite database for later retrieval. The existing codebase also provides command-line interfaces (CLIs) for prediction, annotation API calls, and database storage.

Your documentation should follow best practices, providing a comprehensive yet accessible reference for frontend developers to integrate with the backend seamlessly. Include the following sections and details:

1. **Overview**  
   - Provide a concise summary of the application’s purpose: predicting antimicrobial properties of sequences and annotating them with external data.  
   - Outline the main components: transformer model, sequence processing, external API integration, SQLite database, and the transition from CLI to API-based access.

2. **Setup and Installation**  
   - List all steps to install dependencies (e.g., Python packages, libraries for the transformer model, database drivers).  
   - Describe how to set up the environment (e.g., virtual environment setup, configuration files).  
   - Explain how to launch the backend service, including loading the transformer model and initializing the SQLite database.

3. **API Endpoints**  
   - Document the RESTful API endpoints that expose the backend functionality (replacing or complementing the existing CLIs). Focus on:  
     - **POST /analyze**  
       - **Purpose**: Processes a sequence to predict its antimicrobial properties and fetches its annotations.  
       - **Request**: JSON body, e.g., `{"sequence": "ACGT..."}`, with validation rules (e.g., valid characters: A, C, G, T).  
       - **Response**: JSON, e.g., `{"prediction": "antimicrobial", "annotations": {...}}`, including success and error cases.  
       - **Notes**: Combines prediction and annotation fetching for a streamlined UI experience.  
     - Optionally, include separate endpoints (e.g., `POST /predict`, `GET /annotations/<sequence>`) if modularity is preferred, with similar request/response details.  
   - Specify HTTP methods, URL paths, parameters, and expected data formats.

4. **Data Formats**  
   - Define the structure of API responses:  
     - Prediction: e.g., a string ("antimicrobial") or a probability score (float).  
     - Annotations: e.g., a JSON object with fields from the external API.  
   - Include example requests and responses, e.g.:  
     - Request: `POST /analyze` with `{"sequence": "ACGT"}`  
     - Response: `{"prediction": "antimicrobial", "annotations": {"property": "value"}}`

5. **Database Schema**  
   - Describe the SQLite database structure:  
     - Table(s) for storing annotations (e.g., columns: `sequence_hash` (TEXT), `sequence` (TEXT), `annotations` (JSON/TEXT), `timestamp` (DATETIME)).  
     - Explain sequence identification (e.g., using a hash like SHA-256 for efficiency).  
   - Note how the backend manages DB interactions (e.g., caching annotations to avoid redundant API calls).

6. **External API Integration**  
   - Summarize how the backend calls the external annotation API (e.g., endpoint URL, parameters, authentication if applicable).  
   - Highlight considerations like rate limits or error handling, noting these are abstracted from the frontend.

7. **Concurrency and Performance**  
   - Explain how the backend handles multiple concurrent users:  
     - Use of an async framework (e.g., FastAPI) for request handling.  
     - Transformer model sharing across requests (loaded once at startup).  
     - SQLite concurrency limitations (e.g., single-writer constraint) and mitigation strategies (e.g., transaction management, connection pooling).  
   - Discuss optimization, such as parallel execution of prediction and annotation fetching.

8. **Error Handling**  
   - List common error scenarios and responses:  
     - `400 Bad Request`: Invalid sequence input.  
     - `500 Internal Server Error`: Model failure or external API downtime.  
   - Provide example error responses, e.g., `{"error": "Invalid sequence", "details": "Only ACGT allowed"}`.

9. **Security Considerations**  
   - Detail security measures:  
     - Input validation to prevent injection attacks (e.g., sanitizing sequence strings).  
     - Lack of authentication (if applicable) or recommendations for adding it if needed for multi-user access.  

10. **Testing**  
    - Include instructions for running any existing unit or integration tests to validate backend functionality (e.g., CLI tests or API endpoint tests).

### Additional Notes  
- Ensure the documentation is concise yet detailed, avoiding unnecessary backend implementation specifics unless relevant to frontend integration.  
- Map the existing CLI commands (predict, annotation API call, DB storage) to API equivalents where applicable, but prioritize API usage for the UI context.  
- Use markdown for readability, with code blocks for examples and tables for schemas or endpoint summaries.  
- Assume the frontend developers need clear API interaction guidance without deep Python or ML knowledge.
