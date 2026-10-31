# RESQ Shared Contracts & Schemas

This package defines common enumerations, Pydantic schemas, and event contracts shared across:
1. `backend/`: FastAPI validation and ORM bridging.
2. `agents/`: LangGraph inputs, outputs, and HTTP client requests.
3. `simulation/`: Kerala flood test generation and assertions.

Neither developer should introduce private divergent enums when shared definitions exist here.
