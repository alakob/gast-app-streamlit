#!/usr/bin/env python3
"""
Data processing utilities for Bakta annotation results.

This module provides functions for processing, transforming, and analyzing
Bakta annotation data. It includes utilities for deriving summary statistics,
generating visualization data, and performing feature analysis.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import Counter, defaultdict
from datetime import datetime

from amr_predictor.bakta.models import BaktaAnnotation, BaktaJob, BaktaSequence

# Configure logging
logger = logging.getLogger("bakta-data-processing")

def extract_feature_statistics(annotations: List[BaktaAnnotation]) -> Dict[str, Any]:
    """
    Extract statistical summaries from a list of annotations.
    
    Args:
        annotations: List of BaktaAnnotation objects
        
    Returns:
        Dictionary containing feature statistics
    """
    if not annotations:
        return {
            "total_features": 0,
            "feature_types": {},
            "avg_feature_length": 0,
            "contig_distribution": {},
            "strand_distribution": {"forward": 0, "reverse": 0},
            "length_distribution": {
                "< 500 bp": 0,
                "500-1000 bp": 0,
                "1000-2000 bp": 0, 
                "2000-5000 bp": 0,
                "> 5000 bp": 0
            }
        }
    
    # Count feature types
    feature_types = Counter([ann.feature_type for ann in annotations])
    
    # Count features by contig
    contig_counts = Counter([ann.contig for ann in annotations])
    
    # Count features by strand
    strand_counts = {"forward": 0, "reverse": 0}
    for ann in annotations:
        if ann.strand == "+":
            strand_counts["forward"] += 1
        elif ann.strand == "-":
            strand_counts["reverse"] += 1
    
    # Calculate length statistics
    lengths = [ann.end - ann.start + 1 for ann in annotations]
    avg_length = sum(lengths) / len(lengths) if lengths else 0
    
    # Length distribution bins
    length_distribution = {
        "< 500 bp": 0,
        "500-1000 bp": 0,
        "1000-2000 bp": 0, 
        "2000-5000 bp": 0,
        "> 5000 bp": 0
    }
    
    for length in lengths:
        if length < 500:
            length_distribution["< 500 bp"] += 1
        elif length < 1000:
            length_distribution["500-1000 bp"] += 1
        elif length < 2000:
            length_distribution["1000-2000 bp"] += 1
        elif length < 5000:
            length_distribution["2000-5000 bp"] += 1
        else:
            length_distribution["> 5000 bp"] += 1
    
    return {
        "total_features": len(annotations),
        "feature_types": dict(feature_types),
        "avg_feature_length": round(avg_length, 2),
        "contig_distribution": dict(contig_counts),
        "strand_distribution": strand_counts,
        "length_distribution": length_distribution
    }

def extract_gene_functions(annotations: List[BaktaAnnotation]) -> Dict[str, Any]:
    """
    Extract gene function statistics from annotations.
    
    Args:
        annotations: List of BaktaAnnotation objects
        
    Returns:
        Dictionary containing gene function statistics
    """
    # Filter for CDS features
    cds_features = [ann for ann in annotations if ann.feature_type == "CDS"]
    
    if not cds_features:
        return {
            "total_genes": 0,
            "hypothetical_genes": 0,
            "characterized_genes": 0,
            "top_functions": [],
            "functional_categories": {}
        }
    
    # Count genes with/without function
    has_product = 0
    no_product = 0
    products = []
    
    for feature in cds_features:
        product = feature.attributes.get("product", "").strip()
        if product and product.lower() != "hypothetical protein":
            has_product += 1
            products.append(product)
        else:
            no_product += 1
    
    # Get top 10 most common products
    top_products = Counter(products).most_common(10)
    
    # Create basic functional categories
    functional_categories = {
        "metabolism": 0,
        "transport": 0,
        "regulation": 0,
        "virulence": 0,
        "mobile_elements": 0,
        "hypothetical": no_product,
        "other": 0
    }
    
    # Categorize by keyword matching (simplified)
    for product in products:
        product_lower = product.lower()
        
        if any(keyword in product_lower for keyword in ["metabol", "synthase", "synthetase", "reductase", "dehydrogenase"]):
            functional_categories["metabolism"] += 1
        elif any(keyword in product_lower for keyword in ["transport", "permease", "channel", "porin", "exporter", "importer"]):
            functional_categories["transport"] += 1
        elif any(keyword in product_lower for keyword in ["regulator", "transcription", "repressor", "activator"]):
            functional_categories["regulation"] += 1
        elif any(keyword in product_lower for keyword in ["toxin", "virulence", "adhesin", "invasion", "pathogen"]):
            functional_categories["virulence"] += 1
        elif any(keyword in product_lower for keyword in ["transposase", "integrase", "recombinase", "plasmid", "phage"]):
            functional_categories["mobile_elements"] += 1
        else:
            functional_categories["other"] += 1
    
    return {
        "total_genes": len(cds_features),
        "hypothetical_genes": no_product,
        "characterized_genes": has_product,
        "top_functions": top_products,
        "functional_categories": functional_categories
    }

def create_visualization_data(annotations: List[BaktaAnnotation]) -> Dict[str, Any]:
    """
    Create data structures optimized for visualization.
    
    Args:
        annotations: List of BaktaAnnotation objects
        
    Returns:
        Dictionary with visualization-ready data structures
    """
    if not annotations:
        return {
            "feature_type_data": [],
            "contig_data": [],
            "strand_data": [],
            "length_histogram_data": [],
            "function_data": []
        }
    
    # Extract statistics
    stats = extract_feature_statistics(annotations)
    gene_stats = extract_gene_functions(annotations)
    
    # Create feature type data for pie chart
    feature_type_data = [
        {"type": k, "count": v} 
        for k, v in stats["feature_types"].items()
    ]
    
    # Create contig data for bar chart
    contig_data = [
        {"contig": k, "count": v} 
        for k, v in stats["contig_distribution"].items()
    ]
    
    # Create strand data for pie chart
    strand_data = [
        {"strand": k, "count": v} 
        for k, v in stats["strand_distribution"].items()
    ]
    
    # Create length histogram data
    length_histogram_data = [
        {"range": k, "count": v} 
        for k, v in stats["length_distribution"].items()
    ]
    
    # Create functional category data
    function_data = [
        {"category": k, "count": v} 
        for k, v in gene_stats["functional_categories"].items()
    ]
    
    return {
        "feature_type_data": feature_type_data,
        "contig_data": contig_data,
        "strand_data": strand_data,
        "length_histogram_data": length_histogram_data,
        "function_data": function_data
    }

def create_feature_dataframe(annotations: List[BaktaAnnotation]) -> pd.DataFrame:
    """
    Convert annotation list to a pandas DataFrame for analysis and display.
    
    Args:
        annotations: List of BaktaAnnotation objects
        
    Returns:
        Pandas DataFrame with annotation data
    """
    if not annotations:
        return pd.DataFrame()
    
    # Extract relevant fields from annotations
    data = []
    for ann in annotations:
        row = {
            "id": ann.id,
            "feature_id": ann.feature_id,
            "feature_type": ann.feature_type,
            "contig": ann.contig,
            "start": ann.start,
            "end": ann.end,
            "strand": ann.strand,
            "length": ann.end - ann.start + 1
        }
        
        # Add key attributes
        for key, value in ann.attributes.items():
            # Include all attributes to allow for comprehensive filtering
            row[key] = value
        
        data.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Add helpful derived columns
    if "product" in df.columns:
        df["has_function"] = ~(df["product"].isna() | (df["product"] == "") | 
                             (df["product"].str.lower() == "hypothetical protein"))
    
    # Calculate GC content for CDS features
    if "translation" in df.columns:
        def calculate_gc(seq):
            if not isinstance(seq, str):
                return None
            g_count = seq.upper().count('G')
            c_count = seq.upper().count('C')
            total = len(seq)
            return round((g_count + c_count) / total * 100, 2) if total > 0 else 0
        
        df["gc_content"] = df["translation"].apply(calculate_gc)
    
    # Categorize features by function (for CDS)
    if "product" in df.columns and "feature_type" in df.columns:
        def categorize_function(row):
            if row["feature_type"] != "CDS" or pd.isna(row["product"]):
                return "other"
                
            product_lower = str(row["product"]).lower()
            
            if "hypothetical protein" in product_lower or not product_lower:
                return "hypothetical"
            elif any(kw in product_lower for kw in ["metabol", "synthase", "synthetase", "reductase", "dehydrogenase"]):
                return "metabolism"
            elif any(kw in product_lower for kw in ["transport", "permease", "channel", "porin", "exporter", "importer"]):
                return "transport"
            elif any(kw in product_lower for kw in ["regulator", "transcription", "repressor", "activator"]):
                return "regulation"
            elif any(kw in product_lower for kw in ["toxin", "virulence", "adhesin", "invasion", "pathogen", "resistance"]):
                return "virulence_resistance"
            elif any(kw in product_lower for kw in ["transposase", "integrase", "recombinase", "plasmid", "phage", "mobile"]):
                return "mobile_elements"
            else:
                return "other"
        
        df["functional_category"] = df.apply(categorize_function, axis=1)
    
    return df

def create_interactive_charts(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Create interactive Plotly charts for Bakta annotation data visualization.
    
    Args:
        df: DataFrame with annotation data from create_feature_dataframe()
        
    Returns:
        Dictionary containing Plotly figure objects for various visualizations
    """
    if df.empty:
        return {}
    
    charts = {}
    
    # 1. Feature type distribution chart
    feature_counts = df['feature_type'].value_counts().reset_index()
    feature_counts.columns = ['Feature Type', 'Count']
    
    charts['feature_type_chart'] = {
        'data': feature_counts.to_dict('records'),
        'layout': {
            'title': 'Distribution of Feature Types',
            'xaxis_title': 'Feature Type',
            'yaxis_title': 'Count'
        }
    }
    
    # 2. Contig distribution chart
    if 'contig' in df.columns and len(df['contig'].unique()) > 1:
        contig_counts = df['contig'].value_counts().reset_index()
        contig_counts.columns = ['Contig', 'Count']
        
        charts['contig_chart'] = {
            'data': contig_counts.to_dict('records'),
            'layout': {
                'title': 'Features per Contig',
                'xaxis_title': 'Contig',
                'yaxis_title': 'Count'
            }
        }
    
    # 3. Feature length distribution histogram data
    if 'length' in df.columns:
        length_data = df[['feature_id', 'feature_type', 'length']].copy()
        
        charts['length_histogram'] = {
            'data': length_data.to_dict('records'),
            'layout': {
                'title': 'Feature Length Distribution',
                'xaxis_title': 'Length (bp)',
                'yaxis_title': 'Count'
            }
        }
    
    # 4. Functional category breakdown (for CDS features)
    if 'functional_category' in df.columns:
        func_counts = df['functional_category'].value_counts().reset_index()
        func_counts.columns = ['Category', 'Count']
        
        charts['functional_category_chart'] = {
            'data': func_counts.to_dict('records'),
            'layout': {
                'title': 'Functional Categories',
                'xaxis_title': 'Category',
                'yaxis_title': 'Count'
            }
        }
    
    # 5. Strand distribution
    if 'strand' in df.columns:
        strand_counts = df['strand'].value_counts().reset_index()
        strand_counts.columns = ['Strand', 'Count']
        
        charts['strand_chart'] = {
            'data': strand_counts.to_dict('records'),
            'layout': {
                'title': 'Strand Distribution',
                'labels': {'Strand': '+': 'Forward', '-': 'Reverse'}
            }
        }
    
    return charts

def analyze_feature_clusters(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Identify and analyze feature clusters in the genome.
    
    Args:
        df: Feature DataFrame from create_feature_dataframe()
        
    Returns:
        Dictionary with cluster analysis results
    """
    if df.empty or 'contig' not in df.columns or 'start' not in df.columns:
        return {}
    
    results = {}
    
    # Group features by contig
    for contig, contig_df in df.groupby('contig'):
        # Sort features by position
        sorted_features = contig_df.sort_values('start')
        
        # Find feature density regions (Simple approach: sliding window)
        window_size = 10000  # 10kb window
        step_size = 5000    # 5kb step
        
        windows = []
        contig_length = sorted_features['end'].max()
        
        for window_start in range(0, int(contig_length), step_size):
            window_end = window_start + window_size
            features_in_window = sorted_features[
                ((sorted_features['start'] >= window_start) & (sorted_features['start'] <= window_end)) |
                ((sorted_features['end'] >= window_start) & (sorted_features['end'] <= window_end)) |
                ((sorted_features['start'] <= window_start) & (sorted_features['end'] >= window_end))
            ]
            
            if len(features_in_window) > 0:
                density = len(features_in_window) / (window_size / 1000)  # Features per kb
                feature_types = features_in_window['feature_type'].value_counts().to_dict()
                
                windows.append({
                    'window_start': window_start,
                    'window_end': window_end,
                    'feature_count': len(features_in_window),
                    'density': round(density, 2),
                    'feature_types': feature_types
                })
        
        # Identify high-density regions (hotspots)
        if windows:
            avg_density = sum(w['density'] for w in windows) / len(windows)
            density_std = np.std([w['density'] for w in windows])
            
            hotspots = [w for w in windows if w['density'] > avg_density + 1.5 * density_std]
            
            results[contig] = {
                'total_windows': len(windows),
                'avg_density': round(avg_density, 2),
                'max_density': round(max(w['density'] for w in windows), 2) if windows else 0,
                'hotspots': hotspots
            }
    
    return results

def find_genomic_islands(df: pd.DataFrame, gc_threshold: float = 2.0) -> List[Dict[str, Any]]:
    """
    Identify potential genomic islands based on feature characteristics.
    
    Args:
        df: Feature DataFrame from create_feature_dataframe()
        gc_threshold: Standard deviation threshold for GC content deviation
        
    Returns:
        List of potential genomic islands
    """
    if df.empty or 'contig' not in df.columns or 'gc_content' not in df.columns:
        return []
    
    islands = []
    
    # Group by contig for analysis
    for contig, contig_df in df.groupby('contig'):
        if len(contig_df) < 10:  # Skip if too few features
            continue
            
        # Sort by position
        sorted_df = contig_df.sort_values('start')
        
        # Calculate baseline GC content (genome average)
        avg_gc = sorted_df['gc_content'].mean()
        gc_std = sorted_df['gc_content'].std()
        
        # Find regions with aberrant GC content
        window_size = 10  # Number of genes to check in a sliding window
        
        for i in range(len(sorted_df) - window_size):
            window = sorted_df.iloc[i:i+window_size]
            window_gc = window['gc_content'].mean()
            
            # Check if window GC content deviates significantly
            if abs(window_gc - avg_gc) > gc_threshold * gc_std:
                # Check for mobile elements or certain function categories
                has_mobile = any(window['feature_type'].str.contains('mobile|transposase|integrase|plasmid|phage', case=False))
                
                # Collect region characteristics
                region = {
                    'contig': contig,
                    'start': int(window['start'].min()),
                    'end': int(window['end'].max()),
                    'size': int(window['end'].max() - window['start'].min()),
                    'feature_count': len(window),
                    'gc_content': round(window_gc, 2),
                    'gc_deviation': round(window_gc - avg_gc, 2),
                    'has_mobile_elements': has_mobile,
                    'features': window['feature_id'].tolist()
                }
                
                islands.append(region)
    
    # Remove overlapping islands (simplified approach)
    islands.sort(key=lambda x: (x['contig'], x['start']))
    filtered_islands = []
    
    for island in islands:
        # Check if this island overlaps with any already included island
        overlaps = False
        for included in filtered_islands:
            if (island['contig'] == included['contig'] and 
                island['start'] <= included['end'] and 
                island['end'] >= included['start']):
                overlaps = True
                break
        
        if not overlaps:
            filtered_islands.append(island)
    
    return filtered_islands

def extract_genome_statistics(annotations: List[BaktaAnnotation], sequences: List[BaktaSequence]) -> Dict[str, Any]:
    """
    Extract genome-level statistics from annotations and sequences.
    
    Args:
        annotations: List of BaktaAnnotation objects
        sequences: List of BaktaSequence objects
        
    Returns:
        Dictionary containing genome statistics
    """
    if not sequences:
        return {
            "genome_size": 0,
            "num_contigs": 0,
            "gc_content": 0,
            "n50": 0,
            "longest_contig": 0,
            "shortest_contig": 0,
            "avg_contig_length": 0,
            "coding_density": 0
        }
    
    # Calculate basic genome stats
    contig_lengths = [seq.length for seq in sequences]
    genome_size = sum(contig_lengths)
    num_contigs = len(sequences)
    
    # Calculate N50
    sorted_lengths = sorted(contig_lengths, reverse=True)
    cumsum = 0
    n50 = 0
    for length in sorted_lengths:
        cumsum += length
        if cumsum >= genome_size / 2:
            n50 = length
            break
    
    # Calculate feature statistics
    if annotations:
        # Total length of coding sequences
        coding_length = 0
        for ann in annotations:
            if ann.feature_type == "CDS":
                coding_length += (ann.end - ann.start + 1)
        
        coding_density = (coding_length / genome_size) * 100 if genome_size > 0 else 0
    else:
        coding_density = 0
    
    # Calculate GC content
    gc_bases = 0
    total_bases = 0
    for seq in sequences:
        if seq.sequence:  # Ensure sequence is available
            gc_bases += seq.sequence.upper().count('G') + seq.sequence.upper().count('C')
            total_bases += len(seq.sequence)
    
    gc_content = (gc_bases / total_bases) * 100 if total_bases > 0 else 0
    
    return {
        "genome_size": genome_size,
        "num_contigs": num_contigs,
        "gc_content": round(gc_content, 2),
        "n50": n50,
        "longest_contig": max(contig_lengths) if contig_lengths else 0,
        "shortest_contig": min(contig_lengths) if contig_lengths else 0,
        "avg_contig_length": sum(contig_lengths) / num_contigs if num_contigs > 0 else 0,
        "coding_density": round(coding_density, 2)
    }

def generate_sequence_map(annotations: List[BaktaAnnotation], max_features: int = 500) -> Dict[str, Any]:
    """
    Generate data for a linear genome map visualization.
    
    Args:
        annotations: List of BaktaAnnotation objects
        max_features: Maximum number of features to include
        
    Returns:
        Dictionary with data for sequence map visualization
    """
    if not annotations:
        return {"contigs": []}
    
    # Group annotations by contig
    contig_annotations = defaultdict(list)
    for ann in annotations:
        contig_annotations[ann.contig].append(ann)
    
    # Prepare contig data
    contigs = []
    
    for contig_id, features in contig_annotations.items():
        # Get contig length
        if features:
            contig_length = max(f.end for f in features)
        else:
            contig_length = 0
            
        # Limit number of features per contig if needed
        if len(features) > max_features:
            # Prioritize important features
            important_types = ["CDS", "rRNA", "tRNA"]
            important_features = [f for f in features if f.feature_type in important_types]
            important_features = sorted(important_features, 
                                       key=lambda x: (0 if x.feature_type == "CDS" else 
                                                    (1 if x.feature_type == "rRNA" else 2)))
            
            features = important_features[:max_features]
        
        # Prepare feature data
        feature_data = []
        for f in features:
            feature_info = {
                "id": f.feature_id,
                "start": f.start,
                "end": f.end,
                "strand": f.strand,
                "type": f.feature_type,
                "name": f.attributes.get("gene", f.attributes.get("locus_tag", "")),
                "product": f.attributes.get("product", "")
            }
            feature_data.append(feature_info)
        
        contigs.append({
            "id": contig_id,
            "length": contig_length,
            "features": feature_data
        })
    
    return {"contigs": contigs}

def cache_key(job_id: str, feature_type: Optional[str] = None) -> str:
    """
    Generate a consistent cache key for annotation data.
    
    Args:
        job_id: Bakta job ID
        feature_type: Optional feature type filter
        
    Returns:
        Cache key string
    """
    if feature_type:
        return f"bakta_data_{job_id}_{feature_type}"
    return f"bakta_data_{job_id}_all"

def generate_results_summary(job: BaktaJob, annotations: List[BaktaAnnotation], 
                           sequences: List[BaktaSequence]) -> Dict[str, Any]:
    """
    Generate a comprehensive summary of annotation results.
    
    Args:
        job: BaktaJob object
        annotations: List of BaktaAnnotation objects
        sequences: List of BaktaSequence objects
        
    Returns:
        Dictionary containing complete results summary
    """
    # Get basic job information
    summary = {
        "job_id": job.id,
        "job_name": job.name,
        "created_at": job.created_at,
        "completed_at": job.updated_at,
        "status": job.status,
        "config": job.config
    }
    
    # Add feature statistics
    summary["feature_stats"] = extract_feature_statistics(annotations)
    
    # Add gene function statistics
    summary["gene_stats"] = extract_gene_functions(annotations)
    
    # Add genome statistics
    summary["genome_stats"] = extract_genome_statistics(annotations, sequences)
    
    # Add visualization data
    summary["visualization_data"] = create_visualization_data(annotations)
    
    return summary
