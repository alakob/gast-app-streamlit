# AMR Prediction & Genome Annotation Streamlit UI

This is a Streamlit interface for the AMR Prediction and Bakta Genome Annotation tools. The application provides an easy-to-use web interface for analyzing bacterial sequences, predicting antimicrobial resistance, and performing genome annotation. 

## Features

- **Sequence Input**: Upload FASTA files or directly input sequence data
- **AMR Prediction**: Predict antimicrobial resistance genes and mutations
- **Bakta Annotation**: Optional bacterial genome annotation
- **Results Visualization**: View and download analysis results
- **Job Management**: Track and manage analysis jobs

## Installation

1. Make sure you have Python 3.8+ installed

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables for API access:
   ```bash
   export AMR_API_URL="http://localhost:8000"  # Replace with actual AMR API URL
   export AMR_API_KEY="your_amr_api_key"       # Replace with your API key
   export BAKTA_API_URL="https://api.bakta.computational.bio"  # Replace with actual Bakta API URL
   export BAKTA_API_KEY="your_bakta_api_key"   # Replace with your API key
   ```

## Running the App

Start the Streamlit app by running:

```bash
cd streamlit
streamlit run app.py
```

The app will be available at http://localhost:8501 in your web browser.

## Usage Guide

### Annotation Settings Tab

1. Enable or disable Bakta genome annotation
2. Configure Bakta annotation parameters when enabled:
   - Organism information (genus, species, strain)
   - Genome settings (complete genome, translation table)
   - Locus settings for gene naming

### Sequence Input Tab

1. Input your sequence using one of two methods:
   - Text entry (paste sequence directly)
   - File upload (FASTA or text file)
2. Sequence validation is performed automatically
3. View sequence statistics (length, GC content)
4. Click "Submit for Analysis" to process the sequence

### Results Tab

1. View real-time status updates for submitted jobs
2. Access AMR prediction results when available
3. Access Bakta annotation results when enabled and available
4. Toggle between different view formats (Table, JSON, Files)
5. Download results in various formats

### Job Management Tab

1. View all submitted jobs and their status
2. Select jobs to view results, refresh status, or delete

## Troubleshooting

- If the application fails to connect to the APIs, check your environment variables and network connectivity
- Large sequences may take longer to process; be patient with Bakta annotation jobs
- If a job fails, check the error messages in the Results tab for more information

## License

This project is part of the AMR Prediction tool suite.
