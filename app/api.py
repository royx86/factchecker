"""
api.py
------
FastAPI application for the Instagram Fact-Checker.

Endpoints:
  - GET/POST /api/fact-check?url=...&version=v1|v2
  - POST /api/fact-check with JSON body
"""

import json
from typing import Optional, Literal
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
import scraper
import preprocessor
import fact_checker
import fact_checker_v2


# ============================================================
# PYDANTIC MODELS
# ============================================================
class FactCheckRequest(BaseModel):
    """Request body for fact-checking."""
    url: str = Field(..., description="Instagram post URL")
    version: Literal["v1", "v2"] = Field("v1", description="Fact-checker version (v1 or v2)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://www.instagram.com/p/DUDmwcmjFX-/?img_index=1",
                "version": "v1"
            }
        }
    )


class ClaimDetail(BaseModel):
    """Per-claim analysis (v2 only)."""
    claim: str
    verdict: str
    evidence: Optional[str] = None


class FactCheckResponse(BaseModel):
    """Response from fact-checker."""
    post_url: str
    owner: str
    verdict: Literal["REAL", "FAKE", "MISLEADING", "NOT ENOUGH INFO"]
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    explanation: str
    key_sources: list[str] = []
    extracted_claims: Optional[list[str]] = None
    claim_details: Optional[list[ClaimDetail]] = None
    engine: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "post_url": "https://www.instagram.com/p/DUDmwcmjFX-/",
                "owner": "aiwith.akash",
                "verdict": "MISLEADING",
                "confidence": "MEDIUM",
                "explanation": "The claim is partially supported by evidence...",
                "key_sources": ["https://reuters.com", "https://bbc.com"],
                "extracted_claims": ["Everyone has access to AI now"],
                "engine": "v1-pipeline"
            }
        }
    )


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(
    title="Instagram Fact-Checker API",
    description="Verify Instagram posts using AI vision, web search, and reasoning",
    version="1.0.0",
)


# ============================================================
# ROUTES
# ============================================================

@app.get("/")
async def root():
    """Health check / API info."""
    return {
        "status": "ok",
        "message": "Instagram Fact-Checker API",
        "docs": "/docs",
        "endpoints": {
            "fact_check_query": "GET /api/fact-check?url=...&version=v1",
            "fact_check_body": "POST /api/fact-check"
        }
    }


@app.get("/api/fact-check", response_model=FactCheckResponse, tags=["Fact-Checking"])
async def fact_check_get(
    url: str = Query(..., description="Instagram post URL"),
    version: Literal["v1", "v2"] = Query("v1", description="Fact-checker version")
):
    """
    Fact-check an Instagram post using query parameters.
    
    Example:
      GET /api/fact-check?url=https://www.instagram.com/p/DUDmwcmjFX-/&version=v1
    """
    request = FactCheckRequest(url=url, version=version)
    return await _process_fact_check(request)


@app.post("/api/fact-check", response_model=FactCheckResponse, tags=["Fact-Checking"])
async def fact_check_post(request: FactCheckRequest):
    """
    Fact-check an Instagram post using request body.
    
    Example:
      POST /api/fact-check
      {
        "url": "https://www.instagram.com/p/DUDmwcmjFX-/",
        "version": "v1"
      }
    """
    return await _process_fact_check(request)


# ============================================================
# HELPER FUNCTION
# ============================================================

async def _process_fact_check(request: FactCheckRequest) -> FactCheckResponse:
    """
    Main fact-checking logic.
    
    Flow:
      1. Scrape Instagram post
      2. Preprocess (download images)
      3. Run fact-checker (v1 or v2)
      4. Return structured response
    """
    url = request.url.strip()
    version = request.version

    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    # ── Step 1: Scrape ──────────────────────────────────────
    try:
        post_data = scraper.scrape(url)
    except scraper.VideoPostError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scraping failed: {str(e)}"
        )

    # ── Step 2: Preprocess ──────────────────────────────────
    try:
        preprocessed = preprocessor.preprocess(post_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Preprocessing failed: {str(e)}"
        )

    # ── Step 3: Fact-check ──────────────────────────────────
    try:
        if version == "v2":
            result = fact_checker_v2.run(preprocessed)
        else:
            result = fact_checker.run(preprocessed)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fact-checking failed: {str(e)}"
        )

    # ── Step 4: Build response ──────────────────────────────
    claim_details = None
    if version == "v2" and "claim_details" in result:
        claim_details = [
            ClaimDetail(**cd) if isinstance(cd, dict) else cd
            for cd in result.get("claim_details", [])
        ]

    response = FactCheckResponse(
        post_url=result.get("post_url", ""),
        owner=result.get("owner", "unknown"),
        verdict=result.get("verdict", "NOT ENOUGH INFO"),
        confidence=result.get("confidence", "LOW"),
        explanation=result.get("explanation", ""),
        key_sources=result.get("key_sources", []),
        extracted_claims=result.get("extracted_claims"),
        claim_details=claim_details,
        engine=result.get("engine", f"v{version[-1]}-pipeline")
    )

    return response


# ============================================================
# EXCEPTION HANDLERS
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP {exc.status_code}",
            "detail": exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Catch-all exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
