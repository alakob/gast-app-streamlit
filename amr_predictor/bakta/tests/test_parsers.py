"""
Tests for the parsers module.

This module contains tests for the parsers that handle various Bakta result formats:
- GFF3 (General Feature Format version 3)
- TSV (Tab-Separated Values)
- JSON (JavaScript Object Notation)
- EMBL (European Molecular Biology Laboratory format)
- GenBank (GenBank format)
- FASTA (FASTA format)
"""

import io
import os
import json
import tempfile
import pytest
from pathlib import Path

from amr_predictor.bakta.parsers import (
    BaktaParser,
    GFF3Parser,
    TSVParser,
    JSONParser,
    EMBLParser,
    GenBankParser,
    FASTAParser,
    get_parser_for_file,
    parse_file
)
from amr_predictor.bakta.exceptions import BaktaParserError


# Sample data for testing
SAMPLE_GFF3 = """##gff-version 3
##sequence-region contig1 1 1000
contig1\tBakta\tgene\t100\t300\t.\t+\t0\tID=gene1;Name=test_gene
contig1\tBakta\tCDS\t100\t300\t.\t+\t0\tID=cds1;Parent=gene1;product=hypothetical protein
##FASTA
>contig1
ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC
"""

SAMPLE_TSV = """Locus Tag\tType\tStart\tEnd\tStrand\tProduct
test_1\tgene\t100\t300\t+\tHypothetical protein
test_2\tCDS\t400\t600\t-\tPutative transporter
test_3\ttRNA\t700\t780\t+\tTransfer RNA-Ala
"""

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
      "strand": "+"
    },
    {
      "id": "cds1",
      "type": "CDS",
      "start": 100,
      "end": 300,
      "strand": "+",
      "product": "hypothetical protein"
    }
  ]
}"""

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

SAMPLE_FASTA = """>contig1 Escherichia coli test contig
ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC
ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC
>contig2 Escherichia coli test contig 2
GTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC
GTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC
"""


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample files for testing."""
    # Create the files
    files = {}
    
    # GFF3
    gff_file = temp_dir / "sample.gff3"
    with open(gff_file, 'w') as f:
        f.write(SAMPLE_GFF3)
    files['gff3'] = gff_file
    
    # TSV
    tsv_file = temp_dir / "sample.tsv"
    with open(tsv_file, 'w') as f:
        f.write(SAMPLE_TSV)
    files['tsv'] = tsv_file
    
    # JSON
    json_file = temp_dir / "sample.json"
    with open(json_file, 'w') as f:
        f.write(SAMPLE_JSON)
    files['json'] = json_file
    
    # EMBL
    embl_file = temp_dir / "sample.embl"
    with open(embl_file, 'w') as f:
        f.write(SAMPLE_EMBL)
    files['embl'] = embl_file
    
    # GenBank
    gb_file = temp_dir / "sample.gbff"
    with open(gb_file, 'w') as f:
        f.write(SAMPLE_GENBANK)
    files['genbank'] = gb_file
    
    # FASTA
    fasta_file = temp_dir / "sample.fasta"
    with open(fasta_file, 'w') as f:
        f.write(SAMPLE_FASTA)
    files['fasta'] = fasta_file
    
    return files


class TestBaseParser:
    """Tests for the base BaktaParser class."""
    
    def test_parser_requires_input(self):
        """Test that the parser requires either a file path or content."""
        # Create a concrete subclass of BaktaParser for testing
        class TestParser(BaktaParser):
            def parse(self):
                return {"test": "data"}
        
        with pytest.raises(BaktaParserError):
            parser = TestParser()
    
    def test_abstract_parse_method(self):
        """Test that the abstract parse method raises NotImplementedError."""
        class TestParser(BaktaParser):
            pass
        
        with pytest.raises(TypeError):
            parser = TestParser(content="test")


class TestGFF3Parser:
    """Tests for the GFF3Parser."""
    
    def test_parse_gff3_from_file(self, sample_files):
        """Test parsing a GFF3 file from disk."""
        parser = GFF3Parser(file_path=sample_files['gff3'])
        data = parser.parse()
        
        # Check format
        assert data['format'] == 'gff3'
        
        # Check metadata
        assert data['metadata']['version'] == '3'
        
        # Check sequences
        assert 'contig1' in data['sequences']
        assert data['sequences']['contig1']['start'] == 1
        assert data['sequences']['contig1']['end'] == 1000
        
        # Check features
        assert len(data['features']) == 2
        
        # Check first feature
        feature = data['features'][0]
        assert feature['seqid'] == 'contig1'
        assert feature['source'] == 'Bakta'
        assert feature['type'] == 'gene'
        assert feature['start'] == 100
        assert feature['end'] == 300
        assert feature['strand'] == '+'
        assert feature['attributes']['ID'] == 'gene1'
        assert feature['attributes']['Name'] == 'test_gene'
    
    def test_parse_gff3_from_content(self):
        """Test parsing GFF3 from a string."""
        parser = GFF3Parser(content=SAMPLE_GFF3)
        data = parser.parse()
        
        # Check format
        assert data['format'] == 'gff3'
        
        # Check features
        assert len(data['features']) == 2
        
        # Check second feature
        feature = data['features'][1]
        assert feature['type'] == 'CDS'
        assert feature['attributes']['ID'] == 'cds1'
        assert feature['attributes']['Parent'] == 'gene1'
        assert feature['attributes']['product'] == 'hypothetical protein'


class TestTSVParser:
    """Tests for the TSVParser."""
    
    def test_parse_tsv_from_file(self, sample_files):
        """Test parsing a TSV file from disk."""
        parser = TSVParser(file_path=sample_files['tsv'])
        data = parser.parse()
        
        # Check format
        assert data['format'] == 'tsv'
        
        # Check headers
        expected_headers = ['Locus Tag', 'Type', 'Start', 'End', 'Strand', 'Product']
        assert data['headers'] == expected_headers
        
        # Check rows
        assert len(data['rows']) == 3
        
        # Check first row
        row = data['rows'][0]
        assert row['Locus Tag'] == 'test_1'
        assert row['Type'] == 'gene'
        assert row['Start'] == '100'
        assert row['End'] == '300'
        assert row['Strand'] == '+'
        assert row['Product'] == 'Hypothetical protein'
    
    def test_parse_tsv_from_content(self):
        """Test parsing TSV from a string."""
        parser = TSVParser(content=SAMPLE_TSV)
        data = parser.parse()
        
        # Check rows
        assert len(data['rows']) == 3
        
        # Check second row
        row = data['rows'][1]
        assert row['Locus Tag'] == 'test_2'
        assert row['Type'] == 'CDS'
        assert row['Product'] == 'Putative transporter'
    
    def test_parse_tsv_empty_file(self):
        """Test parsing an empty TSV file."""
        with pytest.raises(BaktaParserError):
            parser = TSVParser(content="")
            data = parser.parse()


class TestJSONParser:
    """Tests for the JSONParser."""
    
    def test_parse_json_from_file(self, sample_files):
        """Test parsing a JSON file from disk."""
        parser = JSONParser(file_path=sample_files['json'])
        data = parser.parse()
        
        # Check format
        assert data['format'] == 'json'
        
        # Check metadata
        assert data['metadata']['organism'] == 'Escherichia coli'
        assert data['metadata']['strain'] == 'test strain'
        assert data['metadata']['contigs'] == 1
        assert data['metadata']['genes'] == 2
        
        # Check features
        assert len(data['features']) == 2
        
        # Check first feature
        feature = data['features'][0]
        assert feature['id'] == 'gene1'
        assert feature['type'] == 'gene'
        assert feature['start'] == 100
        assert feature['end'] == 300
        assert feature['strand'] == '+'
    
    def test_parse_json_from_content(self):
        """Test parsing JSON from a string."""
        parser = JSONParser(content=SAMPLE_JSON)
        data = parser.parse()
        
        # Check features
        assert len(data['features']) == 2
        
        # Check second feature
        feature = data['features'][1]
        assert feature['id'] == 'cds1'
        assert feature['type'] == 'CDS'
        assert feature['product'] == 'hypothetical protein'
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        with pytest.raises(BaktaParserError):
            parser = JSONParser(content="{invalid json")
            data = parser.parse()


class TestEMBLParser:
    """Tests for the EMBLParser."""
    
    def test_parse_embl_from_file(self, sample_files):
        """Test parsing an EMBL file from disk."""
        parser = EMBLParser(file_path=sample_files['embl'])
        data = parser.parse()
        
        # Check format
        assert data['format'] == 'embl'
        
        # Check metadata
        assert data['metadata']['id'] == 'CONTIG1'
        assert data['metadata']['accession'] == 'TEST1234'
        assert 'Escherichia coli' in data['metadata']['organism']
        
        # Check features
        assert len(data['features']) == 3
        
        # Check source feature
        feature = data['features'][0]
        assert feature['type'] == 'source'
        assert feature['location'] == '1..1000'
        assert feature['qualifiers']['organism'] == 'Escherichia coli'
        assert feature['qualifiers']['strain'] == 'test strain'
    
    def test_parse_embl_from_content(self):
        """Test parsing EMBL from a string."""
        parser = EMBLParser(content=SAMPLE_EMBL)
        data = parser.parse()
        
        # Check features
        assert len(data['features']) == 3
        
        # Check gene feature
        feature = data['features'][1]
        assert feature['type'] == 'gene'
        assert feature['location'] == '100..300'
        assert feature['qualifiers']['locus_tag'] == 'test_1'
        
        # Check CDS feature
        feature = data['features'][2]
        assert feature['type'] == 'CDS'
        assert feature['qualifiers']['product'] == 'hypothetical protein'
    
    def test_parse_embl_sequence(self):
        """Test parsing the sequence from an EMBL file."""
        parser = EMBLParser(content=SAMPLE_EMBL)
        data = parser.parse()
        
        # Check sequence
        assert data['sequence'].startswith('ATGCATGCAT')
        assert len(data['sequence']) > 0


class TestGenBankParser:
    """Tests for the GenBankParser."""
    
    def test_parse_genbank_from_file(self, sample_files):
        """Test parsing a GenBank file from disk."""
        parser = GenBankParser(file_path=sample_files['genbank'])
        data = parser.parse()
        
        # Check format
        assert data['format'] == 'genbank'
        
        # Check metadata
        assert data['metadata']['locus'] == 'CONTIG1'
        assert data['metadata']['accession'] == 'TEST1234'
        assert 'Escherichia coli test contig' in data['metadata']['definition']
        
        # Check features
        assert len(data['features']) == 3
        
        # Check source feature
        feature = data['features'][0]
        assert feature['type'] == 'source'
        assert feature['location'] == '1..1000'
        assert feature['qualifiers']['organism'] == 'Escherichia coli'
        assert feature['qualifiers']['strain'] == 'test strain'
    
    def test_parse_genbank_from_content(self):
        """Test parsing GenBank from a string."""
        parser = GenBankParser(content=SAMPLE_GENBANK)
        data = parser.parse()
        
        # Check features
        assert len(data['features']) == 3
        
        # Check gene feature
        feature = data['features'][1]
        assert feature['type'] == 'gene'
        assert feature['location'] == '100..300'
        assert feature['qualifiers']['locus_tag'] == 'test_1'
        
        # Check CDS feature
        feature = data['features'][2]
        assert feature['type'] == 'CDS'
        assert feature['qualifiers']['product'] == 'hypothetical protein'
    
    def test_parse_genbank_sequence(self):
        """Test parsing the sequence from a GenBank file."""
        parser = GenBankParser(content=SAMPLE_GENBANK)
        data = parser.parse()
        
        # Check sequence
        assert data['sequence'].startswith('ATGCATGCAT')
        assert len(data['sequence']) > 0


class TestFASTAParser:
    """Tests for the FASTAParser."""
    
    def test_parse_fasta_from_file(self, sample_files):
        """Test parsing a FASTA file from disk."""
        parser = FASTAParser(file_path=sample_files['fasta'])
        data = parser.parse()
        
        # Check format
        assert data['format'] == 'fasta'
        
        # Check sequences
        assert len(data['sequences']) == 2
        
        # Check first sequence
        seq = data['sequences'][0]
        assert seq['header'] == 'contig1 Escherichia coli test contig'
        assert 'ATGCATGCAT' in seq['sequence']
        assert len(seq['sequence']) > 0
    
    def test_parse_fasta_from_content(self):
        """Test parsing FASTA from a string."""
        parser = FASTAParser(content=SAMPLE_FASTA)
        data = parser.parse()
        
        # Check sequences
        assert len(data['sequences']) == 2
        
        # Check second sequence
        seq = data['sequences'][1]
        assert seq['header'] == 'contig2 Escherichia coli test contig 2'
        assert 'GTACGTACGT' in seq['sequence']
        assert len(seq['sequence']) > 0


class TestParserUtilities:
    """Tests for the parser utility functions."""
    
    def test_get_parser_for_file(self, sample_files):
        """Test getting the appropriate parser for a file."""
        # GFF3
        parser = get_parser_for_file(sample_files['gff3'])
        assert isinstance(parser, GFF3Parser)
        
        # TSV
        parser = get_parser_for_file(sample_files['tsv'])
        assert isinstance(parser, TSVParser)
        
        # JSON
        parser = get_parser_for_file(sample_files['json'])
        assert isinstance(parser, JSONParser)
        
        # EMBL
        parser = get_parser_for_file(sample_files['embl'])
        assert isinstance(parser, EMBLParser)
        
        # GenBank
        parser = get_parser_for_file(sample_files['genbank'])
        assert isinstance(parser, GenBankParser)
        
        # FASTA
        parser = get_parser_for_file(sample_files['fasta'])
        assert isinstance(parser, FASTAParser)
    
    def test_get_parser_for_unsupported_extension(self, temp_dir):
        """Test getting a parser for an unsupported file extension."""
        unsupported_file = temp_dir / "sample.xyz"
        with open(unsupported_file, 'w') as f:
            f.write("test content")
        
        with pytest.raises(BaktaParserError):
            parser = get_parser_for_file(unsupported_file)
    
    def test_parse_file(self, sample_files):
        """Test parsing a file with the parse_file function."""
        # GFF3
        data = parse_file(sample_files['gff3'])
        assert data['format'] == 'gff3'
        
        # TSV
        data = parse_file(sample_files['tsv'])
        assert data['format'] == 'tsv'
        
        # JSON
        data = parse_file(sample_files['json'])
        assert data['format'] == 'json'
        
        # EMBL
        data = parse_file(sample_files['embl'])
        assert data['format'] == 'embl'
        
        # GenBank
        data = parse_file(sample_files['genbank'])
        assert data['format'] == 'genbank'
        
        # FASTA
        data = parse_file(sample_files['fasta'])
        assert data['format'] == 'fasta' 