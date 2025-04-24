from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    """Schema for chat message request."""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = "anonymous"

class ChatResponse(BaseModel):
    """Schema for chat API response."""
    message: str
    data: Optional[Dict[str, Any]] = None
    follow_up_suggestions: Optional[List[str]] = []
    visualization_data: Optional[Any] = None
    visualization_type: Optional[str] = None

class ProteinStructure(BaseModel):
    """Schema for protein structure data."""
    pdb_id: Optional[str] = None
    alphafold_id: Optional[str] = None
    resolution: Optional[float] = None
    method: Optional[str] = None
    chain_count: Optional[int] = None
    release_date: Optional[str] = None

class ProteinInteraction(BaseModel):
    """Schema for protein interaction data."""
    protein_id: str
    protein_name: str
    score: float
    description: Optional[str] = None

class Disease(BaseModel):
    """Schema for disease data."""
    disease_id: str
    name: str
    description: Optional[str] = None
    evidence: Optional[str] = None

class Drug(BaseModel):
    """Schema for drug data."""
    drug_id: str
    name: str
    description: Optional[str] = None
    mechanism: Optional[str] = None

class Variant(BaseModel):
    """Schema for protein variant data."""
    variant_id: str
    name: str
    type: str
    location: Optional[int] = None
    original_residue: Optional[str] = None
    variant_residue: Optional[str] = None
    effect: Optional[str] = None
    clinical_significance: Optional[str] = None

class ProteinResponse(BaseModel):
    """Schema for protein data response."""
    id: str
    name: str
    full_name: Optional[str] = None
    function: Optional[str] = None
    description: Optional[str] = None
    sequence: Optional[str] = None
    structure: Optional[ProteinStructure] = None
    interactions: Optional[List[ProteinInteraction]] = None
    diseases: Optional[List[Disease]] = None
    drugs: Optional[List[Drug]] = None
    variants: Optional[List[Variant]] = None