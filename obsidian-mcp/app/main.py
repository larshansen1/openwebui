"""
Obsidian MCP Server - Main Application
FastAPI wrapper with MCP server integration and health endpoints
"""
import logging
import sys
import secrets
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from mcp.server.stdio import stdio_server

from app.config import settings
from app.vault.manager import VaultManager
from app.vault.watcher import FileWatcher
from app.mcp.server import ObsidianMCPServer
from app.api import routes as api_routes

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Global instances (typed as Optional since they're initialized during lifespan)
vault_manager: Optional[VaultManager] = None
file_watcher: Optional[FileWatcher] = None
mcp_server: Optional[ObsidianMCPServer] = None


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify API key from Bearer token (constant-time comparison)"""
    if not secrets.compare_digest(credentials.credentials, settings.mcp_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global vault_manager, file_watcher, mcp_server

    logger.info("🚀 Starting Obsidian MCP Server")
    logger.info(f"📁 Vault path: {settings.vault_path}")
    logger.info(f"🔒 API key configured: {len(settings.mcp_api_key)} chars")

    # Initialize vault manager
    vault_manager = VaultManager()
    logger.info("✅ Vault manager initialized")

    # Set vault manager for API routes
    api_routes.vault_manager = vault_manager

    # Start file watcher
    file_watcher = FileWatcher(
        vault_path=settings.vault_path,
        on_change_callback=lambda path: vault_manager.invalidate_cache(path)
    )
    file_watcher.start()
    logger.info("✅ File watcher started")

    # Initialize MCP server
    mcp_server = ObsidianMCPServer(vault_manager)
    logger.info("✅ MCP server initialized")

    # Get initial stats
    stats = vault_manager.get_vault_stats()
    logger.info(f"📊 Vault stats: {stats['total_notes']} notes, {stats['total_size_mb']}MB")

    yield

    # Shutdown
    logger.info("🛑 Shutting down...")

    if file_watcher:
        file_watcher.stop()
        logger.info("✅ File watcher stopped")

    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Obsidian MCP Server",
    description="MCP server for Obsidian vault operations with wiki-link resolution and frontmatter support",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routes
app.include_router(api_routes.router)


@app.get("/health")
async def health():
    """
    Health check endpoint
    Returns vault statistics and server status
    """
    try:
        if vault_manager is None:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "error": "Vault manager not initialized"}
            )

        stats = vault_manager.get_vault_stats()

        return {
            "status": "healthy",
            "vault": {
                "path": str(stats['vault_path']),
                "total_notes": stats['total_notes'],
                "total_size_mb": stats['total_size_mb']
            },
            "cache": stats['cache_stats'],
            "watcher": {
                "running": file_watcher.is_running() if file_watcher else False
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": "Service unavailable"}
        )


@app.get("/vault/stats", dependencies=[Security(verify_api_key)])
async def get_vault_stats():
    """
    Get detailed vault statistics (requires authentication)
    """
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    return vault_manager.get_vault_stats()


@app.post("/cache/clear", dependencies=[Security(verify_api_key)])
async def clear_cache():
    """
    Clear vault cache (requires authentication)
    """
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    vault_manager.cache.clear()
    vault_manager.parser.invalidate_title_map()

    return {"status": "success", "message": "Cache cleared"}


# MCP Server stdio entry point (for running as MCP server)
async def run_mcp_server():
    """Run MCP server via stdio"""
    global vault_manager, file_watcher, mcp_server

    if vault_manager is None:
        # Initialize if not already done (when running via stdio directly)

        vault_manager = VaultManager()
        file_watcher = FileWatcher(
            vault_path=settings.vault_path,
            on_change_callback=lambda path: vault_manager.invalidate_cache(path)
        )
        file_watcher.start()
        mcp_server = ObsidianMCPServer(vault_manager)

    # Run MCP server on stdio
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.get_app().run(
            read_stream,
            write_stream,
            mcp_server.get_app().create_initialization_options()
        )


# Entry point
if __name__ == "__main__":
    import asyncio

    # Check if running as MCP server (stdio mode) or FastAPI server
    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        # Run as MCP server via stdio
        logger.info("Running in MCP stdio mode")
        asyncio.run(run_mcp_server())
    else:
        # Run as FastAPI server
        import uvicorn
        logger.info("Running in FastAPI mode")
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower()
        )
