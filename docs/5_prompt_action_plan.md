Task:
Using and strictly following the rules defined in @.cursorrules, create a detailed action plan for making API calls to Bakta with a FASTA sequence. The plan should systematically outline:

How to retrieve all annotation results from the Bakta API for a given FASTA sequence.

How to store the retrieved annotation data in a local SQLite database.

How to structure the implementation process into distinct, logically ordered phases.

How to verify correctness at each phase, by defining a clear test suite or validation guidelines before moving to the next phase.

Format:

Write the action plan as 5_bakta_integration.md in the @docs directory.

Do not write any code at this stage—focus purely on clear, step-by-step logical instructions.

Ensure the plan is comprehensive, including data validation and error handling considerations.

At the end of each phase, provide specific test guidelines to confirm that the implementation functions correctly before progressing to the next phase.

We have a proof of concept script @src/submit_bakta.py that queries the Bakta API successfully, you will use this as a guide and built from it

 <!-- ## PHASE 1 UNIT TEST
# Run all unit tests for the Bakta API client
pytest amr_predictor/bakta/tests/

# Run specific test files
pytest amr_predictor/bakta/tests/test_client.py
pytest amr_predictor/bakta/tests/test_validation.py
pytest amr_predictor/bakta/tests/test_config.py

# Run tests for the example scripts
pytest amr_predictor/bakta/tests/test_run_bakta_job.py

# Run integration tests (requires internet connection)
pytest amr_predictor/bakta/tests/ --run-integration --> -->
