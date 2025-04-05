"""Tests for core sequence module."""

import pytest
import numpy as np
from typing import Dict, List

from amr_predictor.core.sequence import (
    Sequence,
    SequenceSet,
    SequenceProcessor,
    SequenceTokenizer
)

def test_sequence_creation(test_sequences: Dict[str, str]):
    """Test Sequence creation."""
    for name, seq in test_sequences.items():
        sequence = Sequence(name, seq)
        assert sequence.name == name
        assert sequence.sequence == seq
        assert len(sequence) == len(seq)

def test_sequence_validation():
    """Test Sequence validation."""
    # Valid sequence
    valid_seq = Sequence("seq1", "ATCGATCG")
    assert valid_seq.is_valid()
    
    # Invalid sequence with non-DNA characters
    invalid_seq = Sequence("seq2", "ATCGX")
    assert not invalid_seq.is_valid()

def test_sequence_set_creation(test_sequence_set: SequenceSet):
    """Test SequenceSet creation."""
    assert len(test_sequence_set) == 3
    assert all(isinstance(seq, Sequence) for seq in test_sequence_set.values())
    assert all(seq.is_valid() for seq in test_sequence_set.values())

def test_sequence_set_operations(test_sequence_set: SequenceSet):
    """Test SequenceSet operations."""
    # Add sequence
    new_seq = Sequence("seq4", "GCTAGCTA")
    test_sequence_set.add(new_seq)
    assert len(test_sequence_set) == 4
    assert "seq4" in test_sequence_set
    
    # Remove sequence
    test_sequence_set.remove("seq4")
    assert len(test_sequence_set) == 3
    assert "seq4" not in test_sequence_set
    
    # Get sequence
    seq = test_sequence_set.get("seq1")
    assert seq is not None
    assert seq.name == "seq1"

def test_sequence_processor_initialization():
    """Test SequenceProcessor initialization."""
    processor = SequenceProcessor()
    assert processor.max_length == 512
    assert processor.pad_token == "[PAD]"
    assert processor.unk_token == "[UNK]"

def test_sequence_processor_preprocessing(test_sequence_set: SequenceSet):
    """Test SequenceProcessor preprocessing."""
    processor = SequenceProcessor()
    
    # Process single sequence
    seq = test_sequence_set.get("seq1")
    processed = processor.preprocess(seq)
    assert isinstance(processed, str)
    assert len(processed) <= processor.max_length
    
    # Process sequence set
    processed_set = processor.preprocess_set(test_sequence_set)
    assert len(processed_set) == len(test_sequence_set)
    assert all(len(seq) <= processor.max_length for seq in processed_set.values())

def test_sequence_tokenizer_initialization():
    """Test SequenceTokenizer initialization."""
    tokenizer = SequenceTokenizer()
    assert tokenizer.vocab_size > 0
    assert tokenizer.pad_token_id is not None
    assert tokenizer.unk_token_id is not None

def test_sequence_tokenizer_tokenization(test_sequence_set: SequenceSet):
    """Test SequenceTokenizer tokenization."""
    tokenizer = SequenceTokenizer()
    
    # Tokenize single sequence
    seq = test_sequence_set.get("seq1")
    tokens = tokenizer.tokenize(seq.sequence)
    assert isinstance(tokens, list)
    assert all(isinstance(t, int) for t in tokens)
    
    # Tokenize sequence set
    tokenized_set = tokenizer.tokenize_set(test_sequence_set)
    assert len(tokenized_set) == len(test_sequence_set)
    assert all(isinstance(tokens, list) for tokens in tokenized_set.values())

def test_sequence_tokenizer_padding(test_sequence_set: SequenceSet):
    """Test SequenceTokenizer padding."""
    tokenizer = SequenceTokenizer()
    max_length = 100
    
    # Pad single sequence
    seq = test_sequence_set.get("seq1")
    tokens = tokenizer.tokenize(seq.sequence)
    padded = tokenizer.pad(tokens, max_length)
    assert len(padded) == max_length
    assert all(t == tokenizer.pad_token_id for t in padded[len(tokens):])
    
    # Pad sequence set
    tokenized_set = tokenizer.tokenize_set(test_sequence_set)
    padded_set = tokenizer.pad_set(tokenized_set, max_length)
    assert all(len(tokens) == max_length for tokens in padded_set.values())

def test_sequence_tokenizer_batch_creation(test_sequence_set: SequenceSet):
    """Test SequenceTokenizer batch creation."""
    tokenizer = SequenceTokenizer()
    batch_size = 2
    
    # Create batches
    batches = tokenizer.create_batches(test_sequence_set, batch_size)
    assert len(batches) == (len(test_sequence_set) + batch_size - 1) // batch_size
    
    # Check batch contents
    for batch in batches:
        assert len(batch) <= batch_size
        assert all(isinstance(tokens, list) for tokens in batch)
        assert all(isinstance(t, int) for t in batch[0])

def test_sequence_tokenizer_special_tokens():
    """Test SequenceTokenizer special tokens."""
    tokenizer = SequenceTokenizer()
    
    # Check special token IDs
    assert tokenizer.get_token_id("[PAD]") == tokenizer.pad_token_id
    assert tokenizer.get_token_id("[UNK]") == tokenizer.unk_token_id
    
    # Check unknown token handling
    unknown_token = "X"
    assert tokenizer.get_token_id(unknown_token) == tokenizer.unk_token_id

def test_sequence_tokenizer_vocabulary():
    """Test SequenceTokenizer vocabulary."""
    tokenizer = SequenceTokenizer()
    
    # Check vocabulary size
    assert tokenizer.vocab_size > 0
    
    # Check token existence
    dna_tokens = ["A", "T", "C", "G"]
    for token in dna_tokens:
        assert tokenizer.get_token_id(token) != tokenizer.unk_token_id
    
    # Check token to ID mapping
    for token, token_id in tokenizer.token_to_id.items():
        assert isinstance(token, str)
        assert isinstance(token_id, int)
        assert token_id >= 0
        assert token_id < tokenizer.vocab_size 