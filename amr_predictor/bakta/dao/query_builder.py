#!/usr/bin/env python3
"""
Query builder for Bakta annotations.

This module provides classes for building and executing
queries against Bakta annotations.
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union, Callable

class FilterOperator(str, Enum):
    """Filter operators for query conditions."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    CONTAINS = "contains"
    STARTS_WITH = "startswith"
    ENDS_WITH = "endswith"
    IN = "in"
    NOT_IN = "not_in"

class LogicalOperator(str, Enum):
    """Logical operators for combining conditions."""
    AND = "and"
    OR = "or"

class QueryCondition:
    """
    Condition for filtering annotations.
    
    Attributes:
        field: Field to filter on
        operator: Comparison operator
        value: Value to compare against
        is_attribute: Whether the field is an attribute field
    """
    
    def __init__(
        self,
        field: str,
        operator: FilterOperator,
        value: Any,
        is_attribute: bool = False
    ):
        """
        Initialize a query condition.
        
        Args:
            field: Field to filter on
            operator: Comparison operator
            value: Value to compare against
            is_attribute: Whether the field is an attribute field
        """
        self.field = field
        self.operator = operator
        self.value = value
        self.is_attribute = is_attribute
    
    def __str__(self) -> str:
        """
        Convert the condition to a string.
        
        Returns:
            String representation of the condition
        """
        prefix = "attributes." if self.is_attribute else ""
        return f"{prefix}{self.field} {self.operator.value} {repr(self.value)}"

class QueryBuilder:
    """
    Builder for constructing complex queries.
    
    This class provides methods for building queries with
    multiple conditions and logical operations.
    """
    
    def __init__(self, logical_operator: LogicalOperator = LogicalOperator.AND):
        """
        Initialize a query builder.
        
        Args:
            logical_operator: Logical operator for combining conditions
        """
        self.logical_operator = logical_operator
        self.conditions: List[QueryCondition] = []
    
    def add_condition(
        self,
        field: str,
        operator: FilterOperator,
        value: Any
    ) -> 'QueryBuilder':
        """
        Add a condition to the query.
        
        Args:
            field: Field to filter on
            operator: Comparison operator
            value: Value to compare against
        
        Returns:
            Self, for method chaining
        """
        is_attribute = field.startswith("attributes.")
        if is_attribute:
            field = field[11:]  # Remove "attributes." prefix
        
        condition = QueryCondition(field, operator, value, is_attribute)
        self.conditions.append(condition)
        return self
    
    def build(self) -> List[QueryCondition]:
        """
        Build the query.
        
        Returns:
            List of query conditions
        """
        return self.conditions 