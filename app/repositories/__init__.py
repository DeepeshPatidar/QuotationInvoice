"""Persistence repositories."""

from .customer_repository import CustomerRepository
from .invoice_repository import InvoiceRepository

__all__ = ["CustomerRepository", "InvoiceRepository"]
