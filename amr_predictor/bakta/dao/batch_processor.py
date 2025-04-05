#!/usr/bin/env python3
"""
Batch processor for handling large datasets in Bakta operations.

This module provides tools for efficiently processing large datasets
by breaking them into manageable batches to optimize memory usage
and improve performance.
"""

import logging
import time
from typing import List, Callable, TypeVar, Generic, Iterator, Optional, Any, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import asyncio
from functools import partial

logger = logging.getLogger("bakta-batch-processor")

T = TypeVar('T')
R = TypeVar('R')

@dataclass
class BatchResult(Generic[T, R]):
    """Result of a batch operation."""
    batch: List[T]
    result: R
    success: bool
    error: Optional[Exception] = None
    processing_time: float = 0.0


class BatchProcessor(Generic[T, R]):
    """
    Processor for handling large datasets in batches.
    
    This class provides methods for processing large collections of items
    in smaller batches to optimize memory usage and performance.
    """
    
    def __init__(self, batch_size: int = 100, max_workers: int = 4):
        """
        Initialize the batch processor.
        
        Args:
            batch_size: Number of items to process in each batch
            max_workers: Maximum number of concurrent workers for parallel processing
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        logger.info(f"Initialized batch processor with batch size: {batch_size}, max workers: {max_workers}")
    
    def process(
        self,
        items: List[T],
        processor_fn: Callable[[List[T]], R],
        parallel: bool = False
    ) -> List[BatchResult[T, R]]:
        """
        Process items in batches.
        
        Args:
            items: List of items to process
            processor_fn: Function to process each batch
            parallel: Whether to process batches in parallel
            
        Returns:
            List of batch results
        """
        if not items:
            return []
        
        # Split into batches
        batches = self._split_batches(items)
        logger.info(f"Processing {len(items)} items in {len(batches)} batches")
        
        if parallel and len(batches) > 1:
            return self._process_parallel(batches, processor_fn)
        else:
            return self._process_sequential(batches, processor_fn)
    
    def _split_batches(self, items: List[T]) -> List[List[T]]:
        """Split items into batches of specified size."""
        return [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
    
    def _process_sequential(
        self,
        batches: List[List[T]],
        processor_fn: Callable[[List[T]], R]
    ) -> List[BatchResult[T, R]]:
        """Process batches sequentially."""
        results = []
        
        for i, batch in enumerate(batches):
            start_time = time.time()
            try:
                logger.debug(f"Processing batch {i+1}/{len(batches)} with {len(batch)} items")
                result = processor_fn(batch)
                processing_time = time.time() - start_time
                results.append(BatchResult(
                    batch=batch,
                    result=result,
                    success=True,
                    processing_time=processing_time
                ))
                logger.debug(f"Completed batch {i+1}/{len(batches)} in {processing_time:.2f}s")
            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"Error processing batch {i+1}/{len(batches)}: {str(e)}")
                results.append(BatchResult(
                    batch=batch,
                    result=None,
                    success=False,
                    error=e,
                    processing_time=processing_time
                ))
        
        return results
    
    def _process_parallel(
        self,
        batches: List[List[T]],
        processor_fn: Callable[[List[T]], R]
    ) -> List[BatchResult[T, R]]:
        """Process batches in parallel using ThreadPoolExecutor."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batches to the executor
            future_to_batch = {
                executor.submit(self._process_batch, batch, processor_fn, i+1, len(batches)): batch
                for i, batch in enumerate(batches)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Unexpected error in batch processing: {str(e)}")
                    results.append(BatchResult(
                        batch=batch,
                        result=None,
                        success=False,
                        error=e,
                        processing_time=0.0
                    ))
        
        return results
    
    def _process_batch(
        self,
        batch: List[T],
        processor_fn: Callable[[List[T]], R],
        batch_num: int,
        total_batches: int
    ) -> BatchResult[T, R]:
        """Process a single batch and return the result."""
        start_time = time.time()
        try:
            logger.debug(f"Processing batch {batch_num}/{total_batches} with {len(batch)} items")
            result = processor_fn(batch)
            processing_time = time.time() - start_time
            logger.debug(f"Completed batch {batch_num}/{total_batches} in {processing_time:.2f}s")
            return BatchResult(
                batch=batch,
                result=result,
                success=True,
                processing_time=processing_time
            )
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error processing batch {batch_num}/{total_batches}: {str(e)}")
            return BatchResult(
                batch=batch,
                result=None,
                success=False,
                error=e,
                processing_time=processing_time
            )


class AsyncBatchProcessor(Generic[T, R]):
    """
    Asynchronous processor for handling large datasets in batches.
    
    This class provides asynchronous methods for processing large collections
    of items in smaller batches to optimize memory usage and performance.
    """
    
    def __init__(self, batch_size: int = 100, max_concurrency: int = 4):
        """
        Initialize the async batch processor.
        
        Args:
            batch_size: Number of items to process in each batch
            max_concurrency: Maximum number of concurrent tasks
        """
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency
        self.semaphore = None  # Will be initialized during processing
        logger.info(f"Initialized async batch processor with batch size: {batch_size}, max concurrency: {max_concurrency}")
    
    async def process(
        self,
        items: List[T],
        processor_fn: Callable[[List[T]], R]
    ) -> List[BatchResult[T, R]]:
        """
        Process items in batches asynchronously.
        
        Args:
            items: List of items to process
            processor_fn: Async function to process each batch
            
        Returns:
            List of batch results
        """
        if not items:
            return []
        
        # Create semaphore for limiting concurrency
        self.semaphore = asyncio.Semaphore(self.max_concurrency)
        
        # Split into batches
        batches = self._split_batches(items)
        logger.info(f"Processing {len(items)} items in {len(batches)} batches asynchronously")
        
        # Process all batches concurrently but with limited concurrency
        tasks = []
        for i, batch in enumerate(batches):
            task = asyncio.create_task(
                self._process_batch(batch, processor_fn, i+1, len(batches))
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error in batch {i+1}: {str(result)}")
                processed_results.append(BatchResult(
                    batch=batches[i],
                    result=None,
                    success=False,
                    error=result,
                    processing_time=0.0
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _split_batches(self, items: List[T]) -> List[List[T]]:
        """Split items into batches of specified size."""
        return [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
    
    async def _process_batch(
        self,
        batch: List[T],
        processor_fn: Callable[[List[T]], R],
        batch_num: int,
        total_batches: int
    ) -> BatchResult[T, R]:
        """Process a single batch asynchronously and return the result."""
        async with self.semaphore:
            start_time = time.time()
            try:
                logger.debug(f"Processing batch {batch_num}/{total_batches} with {len(batch)} items")
                
                # If the processor function is a coroutine function, await it
                if asyncio.iscoroutinefunction(processor_fn):
                    result = await processor_fn(batch)
                else:
                    # If it's a regular function, run it in the executor
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, processor_fn, batch)
                
                processing_time = time.time() - start_time
                logger.debug(f"Completed batch {batch_num}/{total_batches} in {processing_time:.2f}s")
                return BatchResult(
                    batch=batch,
                    result=result,
                    success=True,
                    processing_time=processing_time
                )
            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"Error processing batch {batch_num}/{total_batches}: {str(e)}")
                return BatchResult(
                    batch=batch,
                    result=None,
                    success=False,
                    error=e,
                    processing_time=processing_time
                )


def batch_generator(items: List[T], batch_size: int) -> Iterator[List[T]]:
    """
    Generate batches from a list of items.
    
    Args:
        items: List of items to divide into batches
        batch_size: Size of each batch
        
    Returns:
        Iterator of batches
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def process_in_batches(
    items: List[T],
    processor_fn: Callable[[List[T]], Any],
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Simple utility function to process items in batches.
    
    Args:
        items: Items to process
        processor_fn: Function to process each batch
        batch_size: Size of each batch
        
    Returns:
        Dictionary with processing statistics
    """
    if not items:
        return {"processed": 0, "batches": 0, "success": True, "time": 0}
    
    start_time = time.time()
    total_batches = (len(items) + batch_size - 1) // batch_size
    processed = 0
    errors = []
    
    logger.info(f"Processing {len(items)} items in batches of {batch_size}")
    
    for i, batch in enumerate(batch_generator(items, batch_size)):
        try:
            logger.debug(f"Processing batch {i+1}/{total_batches} with {len(batch)} items")
            processor_fn(batch)
            processed += len(batch)
        except Exception as e:
            logger.error(f"Error processing batch {i+1}/{total_batches}: {str(e)}")
            errors.append(str(e))
    
    total_time = time.time() - start_time
    logger.info(f"Completed processing {processed}/{len(items)} items in {total_time:.2f}s")
    
    return {
        "processed": processed,
        "total": len(items),
        "batches": total_batches,
        "success": len(errors) == 0,
        "errors": errors,
        "time": total_time
    } 