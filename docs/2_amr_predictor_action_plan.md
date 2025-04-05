# AMR Predictor Consolidation Action Plan

## Project Overview

The current AMR Predictor system consists of four separate scripts:

1. **amr_predictor_pretty_performance.py** - Main prediction script that processes FASTA files and makes AMR predictions
2. **predictions_aggregation.py** - Aggregates AMR prediction results across multiple models and genomic files
3. **sequence_prediction.py** - Processes individual prediction files and applies aggregation methods on sequence segments
4. **prediction_to_wig.py** - Converts prediction results to WIG format for genome browser visualization

This action plan outlines the steps to consolidate these scripts into a single, modularized codebase suitable for integration into a web application.

## Objectives

- Create a unified, modular Python package that maintains all existing functionality
- Ensure all input parameters from original scripts are preserved
- Maintain all output file formats
- Remove performance metrics tracking code
- Implement progress tracking for UI integration
- Structure the code for easy importing and reuse

## Module Structure

The consolidated module will be organized as follows:

```
amr_predictor/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── models.py
│   ├── prediction.py
│   ├── sequence.py
│   └── utils.py
├── processing/
│   ├── __init__.py
│   ├── aggregation.py
│   ├── sequence_processing.py
│   └── visualization.py
├── cli/
│   ├── __init__.py
│   └── commands.py
└── web/
    ├── __init__.py
    └── api.py
```

## Component Breakdown

### 1. Core Module

#### models.py
- Functions for loading models and tokenizers
- Model configuration and management

#### prediction.py
- Core prediction functionality extracted from amr_predictor_pretty_performance.py
- Functions for running predictions on sequences

#### sequence.py 
- Sequence handling utilities
- Functions for sequence splitting, parsing, and management

#### utils.py
- Common utilities used across modules
- Progress tracking system for UI integration

### 2. Processing Module

#### aggregation.py
- Functions from predictions_aggregation.py
- Multi-model aggregation methods

#### sequence_processing.py
- Functionality from sequence_prediction.py
- Sequence ID parsing and segment processing

#### visualization.py
- WIG format conversion from prediction_to_wig.py
- Visualization data preparation functions

### 3. CLI Module

#### commands.py
- Command-line interface wrappers for all functionality
- Argument parsing and command execution

### 4. Web Module

#### api.py
- API endpoints for web application integration
- Progress reporting functionality

## Implementation Plan

### Phase 1: Code Analysis and Refactoring

1. **Identify Common Functionality**
   - Extract shared code across all scripts (logging, file handling, etc.)
   - Create shared utility functions

2. **Create Core Structure**
   - Set up the module directory structure
   - Implement basic imports and dependencies

3. **Extract Core Prediction Logic**
   - Refactor prediction logic from amr_predictor_pretty_performance.py
   - Remove performance metrics tracking
   - Restructure for modular use

### Phase 2: Processing Pipeline Implementation

1. **Sequence Processing**
   - Refactor sequence handling from sequence_prediction.py
   - Implement progress tracking for long-running operations

2. **Results Aggregation**
   - Extract aggregation methods from predictions_aggregation.py
   - Standardize interfaces for different aggregation types

3. **Visualization Generation**
   - Refactor WIG conversion code from prediction_to_wig.py
   - Ensure output format consistency

### Phase 3: Interface Development

1. **CLI Interface**
   - Implement command-line interface with all original parameters
   - Ensure backward compatibility with original script usage

2. **API Interface**
   - Create web API interface for integration
   - Implement progress reporting endpoints

### Phase 4: Testing and Validation

1. **Unit Testing**
   - Develop unit tests for each module
   - Ensure core functionality works as expected

2. **Integration Testing**
   - Test end-to-end workflows
   - Verify all output formats match original scripts

3. **Validation**
   - Compare output with original scripts
   - Ensure all features are preserved

## Progress Tracking Implementation

To enable progress tracking for the UI:

1. **Create Progress Tracker Class**
   - Implement a tracker with states, percentage complete, and descriptions
   - Add callback mechanism for UI updates

2. **Integrate Progress Tracking**
   - Add tracking points at key stages in the pipeline:
     - Model loading
     - Sequence processing
     - Prediction running
     - Results aggregation
     - Visualization generation

3. **Web API Status Endpoints**
   - Create endpoints to query current progress
   - Enable real-time updates through webhooks or polling

## Data Flow

The consolidated module will maintain the following data flow:

1. Input FASTA files → Sequence Processing → Prediction → Raw Results
2. Raw Results → Aggregation → Processed Results
3. Processed Results → Visualization → WIG Files

Each step will track progress independently, allowing the UI to show detailed status information.

## Considerations and Challenges

1. **Memory Management**
   - Ensure efficient memory usage when handling large genomic files
   - Implement proper cleanup for GPU resources

2. **Error Handling**
   - Implement comprehensive error handling and reporting
   - Ensure errors propagate appropriately to the UI

3. **Configuration Management**
   - Create a unified configuration system for all parameters
   - Support both file-based and programmatic configuration

4. **Backward Compatibility**
   - Ensure the CLI interface maintains compatibility with existing workflows
   - Preserve all output formats and file structures

## Future Enhancements

After initial consolidation, consider these enhancements:

1. **Async Processing**
   - Implement asynchronous processing for web application integration
   - Support background job handling

2. **Caching System**
   - Add result caching to improve performance
   - Implement model caching for faster loading

3. **Extended Visualization Options**
   - Support additional visualization formats beyond WIG
   - Add interactive visualization capabilities

## Conclusion

This consolidation will transform four separate scripts into a cohesive, modular system that can be easily integrated into a web application. The modular design will ensure maintainability while preserving all existing functionality and output formats. The progress tracking system will enable the UI to provide detailed feedback on processing status. 