# GAST - Genomic Antimicrobial Susceptibility Testing

Advanced machine learning platform for predicting antimicrobial resistance from bacterial genome sequences.

## Core Functionality

### Sequence Analysis
- **Sequence Input**: Upload FASTA files for analysis or use sample data
- **Annotation Settings**: Configure sequence segmentation and processing parameters

### AMR Prediction
- **ML Models**: Utilizes state-of-the-art models (DraGNOME-50m, DraGNOME-2.5b)
- **Resistance Prediction**: Predicts resistance/susceptibility for multiple antimicrobials
- **Sequence Aggregation**: Consolidates predictions across sequence segments

### Results & Visualization
- **Current Analysis**: View real-time AMR predictions with interactive tables
- **Results History**: Browse historical predictions with filtering and pagination
- **Summary Statistics**: View aggregated resistance statistics across sequences

### Job Management
- **Status Monitoring**: Track job progress in real-time
- **API Integration**: Seamless communication with AMR prediction API
- **Docker-based**: Containerized for consistent execution environments

## Technical Architecture

- **Frontend**: Streamlit-based interactive UI
- **Backend**: FastAPI for high-performance prediction API
- **Database**: PostgreSQL for job and result persistence
- **Docker**: Multi-container deployment with shared volumes

## Development

See [Docker Development Guide](docs/10_docker_development.md) for setup and contribution instructions.