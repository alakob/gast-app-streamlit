# gAST Predictor Frontend

This is the frontend application for the gAST Predictor platform, which provides an interface for predicting antimicrobial properties of genetic sequences.

## Overview

The gAST (genomic Antimicrobial Susceptibility Testing) Predictor frontend is built using React with TypeScript and interfaces with the backend API to provide users with a seamless experience for:

- Submitting genetic sequences for analysis
- Displaying prediction and annotation results
- Supporting batch processing of multiple sequences
- Providing real-time updates during job processing
- Visualizing results with intuitive data representations

## Technologies

- React 18 with TypeScript
- React Router for navigation
- React Query for server state management
- Formik and Yup for form validation
- React Toastify for notifications
- Recharts for data visualization
- Tailwind CSS for styling

## Getting Started

### Prerequisites

- Node.js 16.x or higher
- npm 8.x or higher

### Installation

1. Clone the repository
2. Navigate to the frontend directory:

```bash
cd app/frontend
```

3. Install dependencies:

```bash
npm install
```

4. Start the development server:

```bash
npm start
```

The application will be available at [http://localhost:3000](http://localhost:3000).

### Environment Variables

Create a `.env` file in the `app/frontend` directory with the following variables:

```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

## Available Scripts

- `npm start`: Start the development server
- `npm test`: Run tests
- `npm run build`: Build the application for production
- `npm run eject`: Eject from Create React App (irreversible)

## Project Structure

```
app/frontend/
├── public/                  # Static files
├── src/
│   ├── api/                 # API service layer
│   ├── components/          # Reusable UI components
│   │   ├── common/          # Generic UI components
│   │   ├── layout/          # Layout components
│   │   ├── sequence/        # Sequence-specific components
│   │   ├── results/         # Results visualization components
│   │   └── jobs/            # Job management components
│   ├── hooks/               # Custom React hooks
│   ├── pages/               # Page components
│   ├── utils/               # Utility functions
│   └── context/             # React context providers
├── .env                     # Environment variables
└── package.json             # Dependencies and scripts
```

## Features

- Predict antimicrobial resistance from genomic sequences
- Process and aggregate prediction results
- Visualize resistance predictions in genome browser format (WIG)
- Support for segmented sequence analysis
- Comprehensive logging and progress tracking

## Installation

```bash
pip install -e .
```

## Usage

### 1. Predict AMR

```bash
python -m amr_predictor predict \
    --input <input_file> \
    --output <output_dir> \
    --model <model_name> \
    --verbose
```

### 2. Process Sequence Predictions

```bash
python -m amr_predictor sequence \
    --input <prediction_file> \
    --output <output_dir> \
    --threshold 0.5 \
    --verbose
```

This command processes sequence-level predictions and applies aggregation methods:
- Any Resistance: Marks a sequence as resistant if any segment shows resistance
- Majority Voting: Classifies based on majority of segments
- Probability Averaging: Uses average probabilities across segments

### 3. Aggregate Results

```bash
python -m amr_predictor aggregate \
    --input-files <prediction_files> \
    --output <output_dir> \
    --model-suffix "_amr_predictions" \
    --verbose
```

Aggregates results from multiple prediction files, providing:
- Overall resistance statistics
- Method agreement analysis
- Detailed per-sequence metrics

### 4. Visualize Results

```bash
python -m amr_predictor visualize \
    --input <prediction_file> \
    --output <output_file.wig> \
    --step-size 1200 \
    --processed <processed_file.csv> \
    --verbose
```

Creates a WIG file for genome browser visualization with:
- Resistance probability tracks
- Support for segmented sequences
- Configurable step size (default: 1200bp)

## Input File Formats

### Prediction File (CSV/TSV)
Required columns:
- `Sequence_ID`: Unique identifier for each sequence
- `Resistant`: Probability of resistance
- `Susceptible`: Probability of susceptibility

Optional columns:
- `Start`: Starting position (if not in Sequence_ID)
- `End`: Ending position (if not in Sequence_ID)
- `Length`: Sequence length

### Sequence ID Format
The tool supports two sequence ID formats:

1. Segmented sequences:
```
<original_id>_segment_<segment_number>_<start>_<end>
```
Example: `OXA-264:27215228mrsa_S13_L001_R1_001_(paired)_contig_1_segment_1_300`

2. Non-segmented sequences:
```
<contig_id>_<start>_<end>
```
Example: `contig_1_1_300`

## Output Files

### Prediction Results
- CSV file with sequence-level predictions
- Includes probabilities and classifications

### Processed Results
- CSV file with extracted sequence information
- Contains contig, start, end positions
- Includes aggregated metrics

### WIG File
- Genome browser compatible format
- Fixed-step format with configurable step size
- Resistance probability tracks

## Development

### Project Structure
```
amr_predictor/
├── cli/                 # Command-line interface
├── core/               # Core functionality
├── models/             # AMR prediction models
├── processing/         # Data processing modules
└── utils/             # Utility functions
```

### Running Tests
```bash
pytest tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 