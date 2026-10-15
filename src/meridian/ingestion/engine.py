from pathlib import Path
from typing import List, Tuple
from meridian.config import DATA_DIR
from meridian.ingestion.directory_loader import Directory, load_directory
from meridian.ingestion.claude_ingest import ingest_claude_data
from meridian.ingestion.gemini_ingest import ingest_gemini_data
from meridian.models.unified import UnifiedUsageRecord

class IngestionEngine:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.directory: Directory = load_directory(data_dir)
        self.records: List[UnifiedUsageRecord] = []

    def run_ingestion(self) -> Tuple[Directory, List[UnifiedUsageRecord]]:
        claude_records = ingest_claude_data(self.data_dir, self.directory)
        gemini_records = ingest_gemini_data(self.data_dir, self.directory)
        self.records = claude_records + gemini_records
        return self.directory, self.records
