#!/usr/bin/env python3
"""
Tests for the Bakta data transformers.
"""

import pytest
from pathlib import Path
import tempfile
import json

from amr_predictor.bakta.parsers import (
    GFF3Parser,
    TSVParser,
    JSONParser,
    EMBLParser,
    GenBankParser,
    FASTAParser
)

from amr_predictor.bakta.transformers import (
    BaseTransformer,
    SequenceTransformer,
    GFF3Transformer,
    TSVTransformer,
    JSONTransformer,
    GenBankTransformer,
    EMBLTransformer,
    get_transformer_for_format
)

from amr_predictor.bakta.models import (
    BaktaAnnotation,
    BaktaSequence
)

from amr_predictor.bakta.exceptions import BaktaParserError

# Sample data for testing
SAMPLE_JOB_ID = "test-job-123"

# Sample GFF3 data
SAMPLE_GFF3 = """##gff-version 3
##sequence-region contig1 1 1000
contig1\tBakta\tgene\t100\t300\t.\t+\t.\tID=gene1;Name=test_gene;locus_tag=TEST_0001
contig1\tBakta\tCDS\t100\t300\t.\t+\t0\tID=cds1;Parent=gene1;product=hypothetical protein
"""

# Sample TSV data
SAMPLE_TSV = """Locus Tag\tType\tStart\tEnd\tStrand\tProduct
TEST_0001\tgene\t100\t300\t+\thypothetical protein
TEST_0002\tCDS\t400\t600\t-\tpredicted protein
"""

# Sample JSON data
SAMPLE_JSON = """{
  "metadata": {
    "organism": "Escherichia coli",
    "strain": "test strain",
    "contigs": 1,
    "genes": 2
  },
  "features": [
    {
      "id": "gene1",
      "type": "gene",
      "start": 100,
      "end": 300,
      "strand": "+",
      "contig": "contig1"
    },
    {
      "id": "cds1",
      "type": "CDS",
      "start": 100,
      "end": 300,
      "strand": "+",
      "contig": "contig1",
      "product": "hypothetical protein"
    }
  ]
}"""

# Sample EMBL data
SAMPLE_EMBL = """ID   CONTIG1; SV 1; linear; DNA; STD; PRO; 1000 BP.
AC   TEST1234;
DE   Escherichia coli test contig
KW   test; genome.
OS   Escherichia coli
OC   Bacteria; Proteobacteria; Gammaproteobacteria; Enterobacterales; 
OC   Enterobacteriaceae; Escherichia.
FH   Key             Location/Qualifiers
FH
FT   source          1..1000
FT                   /organism="Escherichia coli"
FT                   /strain="test strain"
FT   gene            100..300
FT                   /locus_tag="test_1"
FT   CDS             100..300
FT                   /locus_tag="test_1"
FT                   /product="hypothetical protein"
SQ   Sequence 1000 BP; 250 A; 250 C; 250 G; 250 T; 0 other;
     atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc        60
     atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc       120
//"""

# Sample GenBank data
SAMPLE_GENBANK = """LOCUS       CONTIG1                 1000 bp    DNA     linear   BCT 01-JAN-2023
DEFINITION  Escherichia coli test contig.
ACCESSION   TEST1234
VERSION     TEST1234.1
KEYWORDS    test; genome.
SOURCE      Escherichia coli
  ORGANISM  Escherichia coli
            Bacteria; Proteobacteria; Gammaproteobacteria; Enterobacterales;
            Enterobacteriaceae; Escherichia.
FEATURES             Location/Qualifiers
     source          1..1000
                     /organism="Escherichia coli"
                     /strain="test strain"
     gene            100..300
                     /locus_tag="test_1"
     CDS             100..300
                     /locus_tag="test_1"
                     /product="hypothetical protein"
ORIGIN
        1 atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc
       61 atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc
//"""

# Sample FASTA data
SAMPLE_FASTA = """>contig1 Escherichia coli test contig
ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC
ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC
>contig2 Escherichia coli test contig 2
GTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC
GTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC
"""


class TestBaseTransformer:
    """Tests for the BaseTransformer class."""
    
    def test_transform_not_implemented(self):
        """Test that the transform method raises NotImplementedError."""
        transformer = BaseTransformer(SAMPLE_JOB_ID)
        with pytest.raises(NotImplementedError):
            transformer.transform({})


class TestSequenceTransformer:
    """Tests for the SequenceTransformer class."""
    
    def test_transform_fasta_data(self):
        """Test transforming FASTA data into BaktaSequence objects."""
        # Parse FASTA data
        parser = FASTAParser(content=SAMPLE_FASTA)
        parsed_data = parser.parse()
        
        # Transform the data
        transformer = SequenceTransformer(SAMPLE_JOB_ID)
        sequences = transformer.transform(parsed_data)
        
        # Check results
        assert len(sequences) == 2
        assert all(isinstance(seq, BaktaSequence) for seq in sequences)
        
        # Check first sequence
        assert sequences[0].job_id == SAMPLE_JOB_ID
        assert sequences[0].header == "contig1 Escherichia coli test contig"
        assert "ATGCATGCAT" in sequences[0].sequence
        assert sequences[0].length > 0
        
        # Check second sequence
        assert sequences[1].job_id == SAMPLE_JOB_ID
        assert sequences[1].header == "contig2 Escherichia coli test contig 2"
        assert "GTACGTACGT" in sequences[1].sequence
        assert sequences[1].length > 0
    
    def test_transform_invalid_data(self):
        """Test that transforming invalid data raises an error."""
        transformer = SequenceTransformer(SAMPLE_JOB_ID)
        with pytest.raises(BaktaParserError):
            transformer.transform({"format": "unknown"})


class TestGFF3Transformer:
    """Tests for the GFF3Transformer class."""
    
    def test_transform_gff3_data(self):
        """Test transforming GFF3 data into BaktaAnnotation objects."""
        # Parse GFF3 data
        parser = GFF3Parser(content=SAMPLE_GFF3)
        parsed_data = parser.parse()
        
        # Transform the data
        transformer = GFF3Transformer(SAMPLE_JOB_ID)
        annotations = transformer.transform(parsed_data)
        
        # Check results
        assert len(annotations) == 2
        assert all(isinstance(ann, BaktaAnnotation) for ann in annotations)
        
        # Check first annotation (gene)
        assert annotations[0].job_id == SAMPLE_JOB_ID
        assert annotations[0].feature_id == "gene1"
        assert annotations[0].feature_type == "gene"
        assert annotations[0].contig == "contig1"
        assert annotations[0].start == 100
        assert annotations[0].end == 300
        assert annotations[0].strand == "+"
        assert "Name" in annotations[0].attributes
        assert annotations[0].attributes["Name"] == "test_gene"
        
        # Check second annotation (CDS)
        assert annotations[1].job_id == SAMPLE_JOB_ID
        assert annotations[1].feature_id == "cds1"
        assert annotations[1].feature_type == "CDS"
        assert annotations[1].contig == "contig1"
        assert annotations[1].start == 100
        assert annotations[1].end == 300
        assert annotations[1].strand == "+"
        assert "Parent" in annotations[1].attributes
        assert annotations[1].attributes["Parent"] == "gene1"


class TestTSVTransformer:
    """Tests for the TSVTransformer class."""
    
    def test_transform_tsv_data(self):
        """Test transforming TSV data into BaktaAnnotation objects."""
        # Parse TSV data
        parser = TSVParser(content=SAMPLE_TSV)
        parsed_data = parser.parse()
        
        # Transform the data
        transformer = TSVTransformer(SAMPLE_JOB_ID)
        annotations = transformer.transform(parsed_data)
        
        # Check results
        assert len(annotations) == 2
        assert all(isinstance(ann, BaktaAnnotation) for ann in annotations)
        
        # Check first annotation (gene)
        assert annotations[0].job_id == SAMPLE_JOB_ID
        assert annotations[0].feature_id == "TEST_0001"
        assert annotations[0].feature_type == "gene"
        assert annotations[0].start == 100
        assert annotations[0].end == 300
        assert annotations[0].strand == "+"
        assert "Product" in annotations[0].attributes
        assert annotations[0].attributes["Product"] == "hypothetical protein"
        
        # Check second annotation (CDS)
        assert annotations[1].job_id == SAMPLE_JOB_ID
        assert annotations[1].feature_id == "TEST_0002"
        assert annotations[1].feature_type == "CDS"
        assert annotations[1].start == 400
        assert annotations[1].end == 600
        assert annotations[1].strand == "-"
        assert "Product" in annotations[1].attributes
        assert annotations[1].attributes["Product"] == "predicted protein"


class TestJSONTransformer:
    """Tests for the JSONTransformer class."""
    
    def test_transform_json_data(self):
        """Test transforming JSON data into BaktaAnnotation objects."""
        # Parse JSON data
        parser = JSONParser(content=SAMPLE_JSON)
        parsed_data = parser.parse()
        
        # Transform the data
        transformer = JSONTransformer(SAMPLE_JOB_ID)
        annotations = transformer.transform(parsed_data)
        
        # Check results
        assert len(annotations) == 2
        assert all(isinstance(ann, BaktaAnnotation) for ann in annotations)
        
        # Check first annotation (gene)
        assert annotations[0].job_id == SAMPLE_JOB_ID
        assert annotations[0].feature_id == "gene1"
        assert annotations[0].feature_type == "gene"
        assert annotations[0].contig == "contig1"
        assert annotations[0].start == 100
        assert annotations[0].end == 300
        assert annotations[0].strand == "+"
        
        # Check second annotation (CDS)
        assert annotations[1].job_id == SAMPLE_JOB_ID
        assert annotations[1].feature_id == "cds1"
        assert annotations[1].feature_type == "CDS"
        assert annotations[1].contig == "contig1"
        assert annotations[1].start == 100
        assert annotations[1].end == 300
        assert annotations[1].strand == "+"
        assert "product" in annotations[1].attributes
        assert annotations[1].attributes["product"] == "hypothetical protein"


class TestEMBLTransformer:
    """Tests for the EMBLTransformer class."""
    
    def test_transform_embl_data(self):
        """Test transforming EMBL data into BaktaAnnotation objects."""
        # Parse EMBL data
        parser = EMBLParser(content=SAMPLE_EMBL)
        parsed_data = parser.parse()
        
        # Transform the data
        transformer = EMBLTransformer(SAMPLE_JOB_ID)
        annotations = transformer.transform(parsed_data)
        
        # Check results
        assert len(annotations) == 3
        assert all(isinstance(ann, BaktaAnnotation) for ann in annotations)
        
        # Check source feature
        assert annotations[0].job_id == SAMPLE_JOB_ID
        assert annotations[0].feature_type == "source"
        assert annotations[0].contig == "CONTIG1"
        assert "organism" in annotations[0].attributes
        assert annotations[0].attributes["organism"] == "Escherichia coli"
        
        # Check gene feature
        assert annotations[1].job_id == SAMPLE_JOB_ID
        assert annotations[1].feature_id == "test_1"
        assert annotations[1].feature_type == "gene"
        assert annotations[1].contig == "CONTIG1"
        assert annotations[1].start == 100
        assert annotations[1].end == 300
        
        # Check CDS feature
        assert annotations[2].job_id == SAMPLE_JOB_ID
        assert annotations[2].feature_id == "test_1"
        assert annotations[2].feature_type == "CDS"
        assert annotations[2].contig == "CONTIG1"
        assert annotations[2].start == 100
        assert annotations[2].end == 300
        assert "product" in annotations[2].attributes
        assert annotations[2].attributes["product"] == "hypothetical protein"


class TestGenBankTransformer:
    """Tests for the GenBankTransformer class."""
    
    def test_transform_genbank_data(self):
        """Test transforming GenBank data into BaktaAnnotation objects."""
        # Parse GenBank data
        parser = GenBankParser(content=SAMPLE_GENBANK)
        parsed_data = parser.parse()
        
        # Transform the data
        transformer = GenBankTransformer(SAMPLE_JOB_ID)
        annotations = transformer.transform(parsed_data)
        
        # Check results
        assert len(annotations) == 3
        assert all(isinstance(ann, BaktaAnnotation) for ann in annotations)
        
        # Check source feature
        assert annotations[0].job_id == SAMPLE_JOB_ID
        assert annotations[0].feature_type == "source"
        assert annotations[0].contig == "CONTIG1"
        assert "organism" in annotations[0].attributes
        assert annotations[0].attributes["organism"] == "Escherichia coli"
        
        # Check gene feature
        assert annotations[1].job_id == SAMPLE_JOB_ID
        assert annotations[1].feature_id == "test_1"
        assert annotations[1].feature_type == "gene"
        assert annotations[1].contig == "CONTIG1"
        assert annotations[1].start == 100
        assert annotations[1].end == 300
        
        # Check CDS feature
        assert annotations[2].job_id == SAMPLE_JOB_ID
        assert annotations[2].feature_id == "test_1"
        assert annotations[2].feature_type == "CDS"
        assert annotations[2].contig == "CONTIG1"
        assert annotations[2].start == 100
        assert annotations[2].end == 300
        assert "product" in annotations[2].attributes
        assert annotations[2].attributes["product"] == "hypothetical protein"


class TestTransformerUtils:
    """Tests for transformer utility functions."""
    
    def test_get_transformer_for_format(self):
        """Test getting the appropriate transformer for a format."""
        # Test all format types
        assert isinstance(get_transformer_for_format("gff3", SAMPLE_JOB_ID), GFF3Transformer)
        assert isinstance(get_transformer_for_format("tsv", SAMPLE_JOB_ID), TSVTransformer)
        assert isinstance(get_transformer_for_format("json", SAMPLE_JOB_ID), JSONTransformer)
        assert isinstance(get_transformer_for_format("embl", SAMPLE_JOB_ID), EMBLTransformer)
        assert isinstance(get_transformer_for_format("genbank", SAMPLE_JOB_ID), GenBankTransformer)
        assert isinstance(get_transformer_for_format("gbff", SAMPLE_JOB_ID), GenBankTransformer)
        assert isinstance(get_transformer_for_format("fasta", SAMPLE_JOB_ID), SequenceTransformer)
        assert isinstance(get_transformer_for_format("faa", SAMPLE_JOB_ID), SequenceTransformer)
        
        # Test case insensitivity
        assert isinstance(get_transformer_for_format("GFF3", SAMPLE_JOB_ID), GFF3Transformer)
        
        # Test invalid format
        with pytest.raises(BaktaParserError):
            get_transformer_for_format("invalid", SAMPLE_JOB_ID) 