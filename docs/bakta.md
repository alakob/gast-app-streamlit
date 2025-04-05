Bakta API
Bakta provides a open-access REST-API that can be used to annotate own genomes programmatically.

The API and the corresponding OpenAPI 3.1 documentation can be found here:

https://api.bakta.computational.bio

swagger

The API provides the following endpoints:

Init Job - Initializes a new annotation job
Start Job - Start a previously initialized job
Delete Job - Deleting an existing job
Procedure
The overall procedure for jobs should look like this:

Init -> Put Data -> Start -> List (wait till job succeeeds) -> Query Results

Bugs and Issues
If you find any bugs, issues please report them here:

Bakta Web backend: https://github.com/ag-computational-bio/bakta-web-backend

Init Job
Initialize a new bakta annotation job.

Method: POST

Request Body:

{
  "name": "string",
  "repliconTableType": "CSV"
}
The body contains a user-defined name and the type of the replicon table (either TSV or CSV).

Response Body:

{
  "job": {
    "jobID": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "secret": "string"
  },
  "uploadLinkFasta": "string",
  "uploadLinkProdigal": "string",
  "uploadLinkReplicons": "string"
}
The job section of the response contains a UUIDv4 (jobID) and a corresponding secret, this must be stored and provided by all subsequent requests that are associated to this job.

The response also contains three pre-authenticated S3 Urls:

uploadLinkFasta should be used to upload the (fasta) sequence data for annotation. uploadLinkProdigal (optional) can be used to upload an additional prodigal training file uploadLinkReplicons (optional) should be used to upload a replicon table in tsv format that describes the provided replicons in the fasta input file

By issuing a PUT request with the associated data as body you can upload the necessary data needed for the initialization.

NOTE: Previous API versions required the upload of all three files (FASTA, prodigal.tf and replicons.tsv) even if they were not used, this is no longer necessary as long these are not used in the subsequent start request.

Full Example (cURL)
Init request:

curl -X 'POST' \
  'https://api.bakta.computational.bio/api/v1/job/init' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "test",
  "repliconTableType": "TSV"
}'
Put sequence data (required):

curl -X 'PUT' \
  '<uploadLinkFasta>' \
  --data-binary "@path/to/file.fasta"
Put prodigal training file (optional):

curl -X 'PUT' \
  '<uploadLinkProdigal>' \
  --data-binary "@path/to/file.tf"
Put replicon table (optional):

curl -X 'PUT' \
  '<uploadLinkReplicons>' \
  --data-binary "@path/to/file.tsv"


Start Job
Start a job that has been initialized before. Please make sure that all files have been successfully uploaded before issuing this request.

Method: POST

Request Body:

{
  "config": {
    "completeGenome": true, // Complete genome
    "compliant": true, // INDSC compliant
    "dermType": null, // (optional) Either empty or one of "UNKNOWN", "MONODERM", "DIDERM"
    "genus": "string", // Genus name
    "hasReplicons": true, // If true a PUT to uploadLinkReplicons must have been issued beforehand
    "keepContigHeaders": true, // Keep the contig header names
    "locus": "string", // Add locus name
    "locusTag": "string", // Add locus tag
    "minContigLength": 9007199254740991, // Minimal contig length
    "plasmid": "string", // --plasmid option
    "prodigalTrainingFile": "string", // If any string is provided a PUT to uploadLinkProdigal must have been issued before
    "species": "string", // Species name
    "strain": "string", // Strain
    "translationTable": 4 // Either 4 or 11
  },
  "job": {
    "jobID": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "secret": "string"
  }
}
For a more detailed description of all the config options please visit the corresponding CLI docs.

Response Body:

This request has no response body, a successfull request will be indicated by a 200 statuscode.

Full Example (cURL)

curl -X 'POST' \
  'https://api.bakta.computational.bio/api/v1/job/start' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "config": {
    "completeGenome": true,
    "compliant": true,
    "dermType": null,
    "genus": "string",
    "hasReplicons": true,
    "keepContigHeaders": true,
    "locus": "string",
    "locusTag": "string",
    "minContigLength": 9007199254740991,
    "plasmid": "string",
    "prodigalTrainingFile": "string",
    "species": "string",
    "strain": "string",
    "translationTable": 1073741824
  },
  "job": {
    "jobID": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "secret": "string"
  }
}'


List
List the status of all jobs provided.

Method: POST

Request Body:

{
  "jobs": [
    {
      "jobID": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "secret": "secret-job-1"
    },
    {
      "jobID": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "secret": "secret-job-2"
    }
  ]
}
The request contains a list for all jobs you want to have a status update (potentially all), including their secrets.

Response Body:


{
  "jobs": [
    {
      "jobID": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "jobStatus": "SUCCESSFUL",
      "started": "2025-01-07T17:01:14Z",
      "updated": "2025-01-07T17:09:22Z",
      "name": "result_1_.fna"
    }
  ],
  "failedJobs": []
}
The response contains two sections: jobs a list with all jobs including the following fields:

jobID: Job UUID
jobStatus: Status of the job
INIT: Job has not started yet, either not started or queued due to high demand
RUNNING: Job is currently running
SUCCESSFUL: Job has successfully annotated the sequence
ERROR: Either malformed inputs/sequences or an internal server error, query logs for deeper information
started: Started timestamp
updated: Updated timestamp
name: Provided name of the job
The failedJobs section contains jobs that could not be returned. This can have two reasons: A wrong secret UNAUTHORIZED or a wrong id / deleted job NOT_FOUND

Full Example (cURL)
curl -X 'POST' \
  'https://api.bakta.computational.bio/api/v1/job/list' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "jobs": [
    {
      "jobID": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "secret": "string"
    }
  ]
}'

Logs
Start a job that has been initialized before. Please make sure that all files have been successfully uploaded before issuing this request.

Method: GET

Request:

This Request has no body, but requires the user to provide a specific job via query parameters jobId and secret.

Response Body:

The response contains the stdout/stderr output of the specified job.

Example responses:

If an internal server occurs that is not associated with wrong or malformed user-input the following message will be returned:

Internal server error, please contact the administrator or try again later.
A regular Bakta stdout output, it will always start with a print of the issued command.

Bakta Command: bakta --tmp-dir /cache --threads 8 --prefix result -o /results --db /db/db --replicons /data/replicons.tsv --gram ? /data/fastadata.fasta --force
Parse genome sequences...
    imported: 86
    filtered & revised: 86
    contigs: 86

Start annotation...
predict tRNAs...
    found: 78
predict tmRNAs...
    found: 1
predict rRNAs...
    found: 3
predict ncRNAs...
    found: 221
predict ncRNA regions...
    found: 54
predict CRISPR arrays...
    found: 2
predict & annotate CDSs...
    predicted: 4586 
    discarded spurious: 6
    revised translational exceptions: 3
    detected IPSs: 4412
    found PSCs: 137
    found PSCCs: 11
    lookup annotations...
    conduct expert systems...
        amrfinder: 16
        protein sequences: 690
    combine annotations and mark hypotheticals...
    detect pseudogenes...
        candidates: 26
        verified: 15
    analyze hypothetical proteins: 72
        detected Pfam hits: 1 
        calculated proteins statistics
    revise special cases...
detect & annotate sORF...
    detected: 59639
    discarded due to overlaps: 47954
    discarded spurious: 9
    detected IPSs: 92
    found PSCs: 11
    lookup annotations...
    filter and combine annotations...
    filtered sORFs: 88
detect gaps...
    found: 0
detect oriCs/oriVs...
    found: 5
detect oriTs...
    found: 0
apply feature overlap filters...
select features and create locus tags...
    selected: 5014
improve annotations...
    revised gene symbols: 43

Genome statistics:
    Genome size: 4,879,557 bp
    Contigs/replicons: 86
    GC: 50.6 %
    N50: 146,704
    N90: 32,820
    N ratio: 0.0 %
    coding density: 88.6 %

annotation summary:
    tRNAs: 77
    tmRNAs: 1
    rRNAs: 3
    ncRNAs: 221
    ncRNA regions: 54
    CRISPR arrays: 2
    CDSs: 4574
        hypotheticals: 70
        pseudogenes: 15
    sORFs: 77
    gaps: 0
    oriCs/oriVs: 5
    oriTs: 0

Export annotation results to: /results
    human readable TSV...
    GFF3...
    INSDC GenBank & EMBL...
    genome sequences...
    feature nucleotide sequences...
    translated CDS sequences...
    feature inferences...
    circular genome plot...
    hypothetical TSV...
    translated hypothetical CDS sequences...
    machine readable JSON...
    Genome and annotation summary...

If you use these results please cite Bakta: https://doi.org/10.1099/mgen.0.000685
Annotation successfully finished in 7:26 [mm:ss].
Full Example (cURL)

curl -X 'POST' \
  'https://api.bakta.computational.bio/api/v1/job/start' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "config": {
    "completeGenome": true,
    "compliant": true,
    "dermType": null,
    "genus": "string",
    "hasReplicons": true,
    "keepContigHeaders": true,
    "locus": "string",
    "locusTag": "string",
    "minContigLength": 9007199254740991,
    "plasmid": "string",
    "prodigalTrainingFile": "string",
    "species": "string",
    "strain": "string",
    "translationTable": 1073741824
  },
  "job": {
    "jobID": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "secret": "string"
  }
}'

Result
The request to retrieve the results of an annotation workflow.

Method: POST

Request Body:

{
  "jobID": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "secret": "string"
}
Response Body:

{
  "ResultFiles": {
    "EMBL": "string",
    "FAA": "string",
    "FAAHypothetical": "string",
    "FFN": "string",
    "FNA": "string",
    "GBFF": "string",
    "GFF3": "string",
    "JSON": "string",
    "PNGCircularPlot": "string",
    "SVGCircularPlot": "string",
    "TSV": "string",
    "TSVHypothetical": "string",
    "TSVInference": "string",
    "TXTLogs": "string"
  },
  "jobID": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "string",
  "started": "2025-01-07T20:12:26.387Z",
  "updated": "2025-01-07T20:12:26.387Z"
}
The results response contains the usual job metadata (jobID, name, started and updated), as well as a ResultsFiles section, this section contains pre-authenticated URLs that can be used to retrieve the results of the job with a simple GET request.

Full Example (cURL)

curl -X 'POST' \
  'https://api.bakta.computational.bio/api/v1/job/result' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "jobID": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "secret": "string"
}'
Retrieve a result from ResultFiles:

curl '<ResultFilesUrl>'

Delete Job
Delete a job including all of its data.

NOTE: This is a destructive action that cannot be undone.

Method: DELETE

Request:

This Request has no body, but requires the user to provide a specific job via query parameters jobId and secret.

Response Body:

This request has no response body, a successfull request will be indicated by a 200 statuscode.

Full Example (cURL)

curl -X 'DELETE' \
  'https://api.staging.bakta.computational.bio/api/v1/job/delete?secret=test&jobID=957f4923-0b18-413d-b705-51b54015864d'

Version
Retrieve the versions of all backend components, including the Bakta CLI, Database and backend.

Method: GET

Request:

This Request has no body.

Response Body:

{
  "toolVersion": "1.10.3",
  "dbVersion": "5.1.0",
  "backendVersion": "0.6.4"
}
Versions of the bakta tool toolVersion, the bakta database dbVersion and the backend backendVersion.

Full Example (cURL)

curl -X 'GET' \
  'https://api.staging.bakta.computational.bio/api/v1/version' \
  -H 'accept: application/json'

