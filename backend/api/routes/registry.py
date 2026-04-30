from fastapi import APIRouter
from backend.registry import available

router = APIRouter(prefix="/registry", tags=["registry"])


@router.get("/")
def get_registry():
    """Return all registered component types and their implementations."""
    return available()


@router.get("/{component_type}")
def get_component_type(component_type: str):
    return available(component_type)
