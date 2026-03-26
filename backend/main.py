"""
FastAPI main application entry point.
Initializes database, runs validation, and serves all API routes.
"""
import os
import sys

# Ensure the backend directory is in Python path
sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from db import init_db
from validator import get_validation_summary, print_validation_report
from logger import log_startup_summary
from routes.graph import router as graph_router
from routes.flows import router as flows_router
from routes.chat import router as chat_router
from routes.debug import router as debug_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # --- STARTUP ---
    print("\n🚀 Starting Context Graph API Server...")
    
    # Initialize database and load CSV data
    table_counts = init_db(force_reload=True)
    
    # Run validation
    print("\n🔍 Running data validation...")
    summary = get_validation_summary()
    print_validation_report(summary)
    
    # Log startup summary
    log_startup_summary(summary)
    
    # Store summary in app state for debug endpoints
    app.state.data_summary = summary
    
    print("✅ Server ready!\n")
    
    yield
    
    # --- SHUTDOWN ---
    print("\n👋 Shutting down Context Graph API Server...")


app = FastAPI(
    title="Context Graph API",
    description="LLM-powered supply chain context graph with natural language query interface",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(graph_router)
app.include_router(flows_router)
app.include_router(chat_router)
app.include_router(debug_router)


@app.get("/")
async def root():
    return {
        "name": "Context Graph API",
        "version": "1.0.0",
        "endpoints": [
            "GET  /api/graph",
            "GET  /api/node/{type}/{id}",
            "GET  /api/flow/{order_id}",
            "GET  /api/broken-flows",
            "POST /api/chat",
            "GET  /api/debug/logs",
            "GET  /api/debug/summary"
        ]
    }
