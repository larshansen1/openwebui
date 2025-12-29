"""
File system watcher for vault changes
Uses watchdog to monitor file system events and invalidate cache
"""
import logging
from pathlib import Path
from typing import Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent, FileMovedEvent

logger = logging.getLogger(__name__)


class VaultEventHandler(FileSystemEventHandler):
    """Handle file system events in vault"""

    def __init__(self, vault_path: Path, on_change_callback: Callable[[str], None]):
        """
        Initialize event handler

        Args:
            vault_path: Path to vault root
            on_change_callback: Callback function to call on changes
        """
        super().__init__()
        self.vault_path = vault_path
        self.on_change = on_change_callback

    def _get_relative_path(self, event: FileSystemEvent) -> Optional[str]:
        """Get relative path from event"""
        try:
            path = Path(event.src_path)
            if path.suffix == '.md':
                return str(path.relative_to(self.vault_path))
        except (ValueError, AttributeError):
            pass
        return None

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification"""
        if event.is_directory:
            return

        rel_path = self._get_relative_path(event)
        if rel_path:
            logger.debug(f"File modified: {rel_path}")
            self.on_change(rel_path)

    def on_created(self, event: FileSystemEvent):
        """Handle file creation"""
        if event.is_directory:
            return

        rel_path = self._get_relative_path(event)
        if rel_path:
            logger.debug(f"File created: {rel_path}")
            self.on_change(rel_path)

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion"""
        if event.is_directory:
            return

        rel_path = self._get_relative_path(event)
        if rel_path:
            logger.debug(f"File deleted: {rel_path}")
            self.on_change(rel_path)

    def on_moved(self, event: FileMovedEvent):
        """Handle file move/rename"""
        if event.is_directory:
            return

        # Invalidate both old and new paths
        try:
            old_path = Path(event.src_path)
            new_path = Path(event.dest_path)

            if old_path.suffix == '.md':
                old_rel = str(old_path.relative_to(self.vault_path))
                logger.debug(f"File moved from: {old_rel}")
                self.on_change(old_rel)

            if new_path.suffix == '.md':
                new_rel = str(new_path.relative_to(self.vault_path))
                logger.debug(f"File moved to: {new_rel}")
                self.on_change(new_rel)
        except (ValueError, AttributeError):
            pass


class FileWatcher:
    """File system watcher for vault"""

    def __init__(self, vault_path: Path, on_change_callback: Callable[[str], None]):
        """
        Initialize file watcher

        Args:
            vault_path: Path to vault root
            on_change_callback: Callback to call on file changes
        """
        self.vault_path = vault_path
        self.on_change = on_change_callback
        self.observer: Optional[Observer] = None
        self._running = False

    def start(self):
        """Start watching for file changes"""
        if self._running:
            logger.warning("File watcher already running")
            return

        self.observer = Observer()
        event_handler = VaultEventHandler(self.vault_path, self.on_change)
        self.observer.schedule(event_handler, str(self.vault_path), recursive=True)
        self.observer.start()
        self._running = True
        logger.info(f"File watcher started for: {self.vault_path}")

    def stop(self):
        """Stop watching for file changes"""
        if not self._running or not self.observer:
            return

        self.observer.stop()
        self.observer.join(timeout=5)
        self._running = False
        logger.info("File watcher stopped")

    def is_running(self) -> bool:
        """Check if watcher is running"""
        return self._running
