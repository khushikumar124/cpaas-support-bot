"""Factory for DataSource implementations (CSV vs Google Sheets)."""

from __future__ import annotations

import logging

from config import (
    DATA_SOURCE,
    GOOGLE_SERVICE_ACCOUNT_JSON,
    GOOGLE_SPREADSHEET_ID,
)

from datasources.base import DataSource
from datasources.csv_source import CSVDataSource
from datasources.google_sheets_source import GoogleSheetsDataSource

logger = logging.getLogger(__name__)


def create_data_source() -> DataSource:
    """Instantiate the configured data source backend."""

    if DATA_SOURCE == "google_sheets":
        logger.info("DataSource backend: GoogleSheetsDataSource")

        return GoogleSheetsDataSource(
            credentials_path=GOOGLE_SERVICE_ACCOUNT_JSON,
            spreadsheet_id=GOOGLE_SPREADSHEET_ID,
        )

    logger.info("DataSource backend: CSVDataSource")
    return CSVDataSource()