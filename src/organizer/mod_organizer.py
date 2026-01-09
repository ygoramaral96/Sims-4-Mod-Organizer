import os
import shutil
import zipfile
import tempfile
import logging
from typing import Callable, Optional
from ..parser.dbpf import DBPFFile
from ..parser.cas_part import get_package_category

class ModOrganizer:
    def __init__(self, source_dir: str, dest_dir: str, keep_zip: bool = False, logger: Optional[logging.Logger] = None):
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.keep_zip = keep_zip
        self.logger = logger or logging.getLogger(__name__)
        self.stop_requested = False

    def organize(self, progress_callback: Callable[[str, float], None]):
        if not os.path.exists(self.source_dir):
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")
        
        if not os.path.exists(self.dest_dir):
            os.makedirs(self.dest_dir)

        # Find both ZIP files and standalone .package files (including subdirectories)
        zip_files = []
        package_files = []
        
        for root, dirs, files in os.walk(self.source_dir):
            for file in files:
                file_lower = file.lower()
                full_path = os.path.join(root, file)
                
                if file_lower.endswith('.zip'):
                    zip_files.append(full_path)
                elif file_lower.endswith('.package'):
                    package_files.append(full_path)
        
        total_files = len(zip_files) + len(package_files)
        
        if total_files == 0:
            progress_callback("No ZIP or .package files found.", 1.0)
            return

        processed = 0

        # Process ZIP files
        for zip_path in zip_files:
            if self.stop_requested:
                break

            zip_filename = os.path.basename(zip_path)
            progress_callback(f"Processing {zip_filename}...", processed / total_files)
            
            try:
                self._process_zip(zip_path)
            except Exception as e:
                self.logger.error(f"Error processing {zip_filename}: {str(e)}")
            
            processed += 1

        # Process standalone .package files
        for package_path in package_files:
            if self.stop_requested:
                break

            package_filename = os.path.basename(package_path)
            progress_callback(f"Processing {package_filename}...", processed / total_files)
            
            try:
                self._process_package(package_path)
            except Exception as e:
                self.logger.error(f"Error processing {package_filename}: {str(e)}")
            
            processed += 1

        progress_callback("Organization complete!", 1.0)

    def _process_zip(self, zip_path: str):
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
            except zipfile.BadZipFile:
                self.logger.error(f"Bad ZIP file: {zip_path}")
                return

            # Find and categorize all package files
            package_found = False
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith('.package'):
                        package_path = os.path.join(root, file)
                        self._process_package(package_path, os.path.basename(zip_path), file)
                        package_found = True

            # Clean up original ZIP if requested and verified
            if package_found and not self.keep_zip:
                try:
                    os.remove(zip_path)
                    self.logger.info(f"Deleted original ZIP: {zip_path}")
                except OSError as e:
                    self.logger.error(f"Failed to delete {zip_path}: {e}")

    def _process_package(self, package_path: str, zip_name: str = None, package_name: str = None):
        """Parse package file and organize it into appropriate category folder."""
        if package_name is None:
            package_name = os.path.basename(package_path)
            
        try:
            dbpf = DBPFFile(package_path)
            dbpf.read()
            category = get_package_category(dbpf)
            
            # Skip non-CAS items (when category is None)
            if category is None:
                self.logger.info(f"Skipping non-CAS file: {package_name}")
                return  # Don't move it, leave it in original location
            
            self.logger.info(f"Detected category '{category}' for {package_name}")
        except ValueError as e:
            # Specific parsing errors (e.g., compression issues)
            self.logger.warning(f"Parse error in {package_name}: {e}")
            category = "Uncategorized"
        except Exception as e:
            # Generic errors (corrupted files, unexpected formats)
            self.logger.warning(f"Error analyzing {package_name}: {type(e).__name__}: {e}")
            category = "Uncategorized"

        # Create category folder
        category_dir = os.path.join(self.dest_dir, category)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)
        
        # Handle duplicate names with numbered suffix
        base, ext = os.path.splitext(package_name)
        dest_path = os.path.join(category_dir, package_name)
        
        counter = 1
        while os.path.exists(dest_path):
            # Add numbered suffix: file (1).package, file (2).package, etc.
            dest_path = os.path.join(category_dir, f"{base} ({counter}){ext}")
            counter += 1

        shutil.move(package_path, dest_path)
        
        # Log with duplicate indicator if renamed
        if counter > 1:
            self.logger.info(f"Organized: {package_name} → {category} (renamed to avoid duplicate)")
        else:
            self.logger.info(f"Organized: {package_name} → {category}")

    def stop(self):
        self.stop_requested = True
