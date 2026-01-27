from typing import List, Dict, Optional
from pydantic import BaseModel

class MemberInfo(BaseModel):
    """Metadata for a method or property."""
    signature: str
    docstring: Optional[str] = None

class RankedTarget(BaseModel):
    """The final schema for a ranked target in the YAML file."""
    rank: int
    id: str
    name: str
    file_path: Optional[str] = None
    type: str # String representation of TargetType
    group: str # "Seed", "Dependency", "Orphan"
    usage_score: int
    docstring: Optional[str] = None
    signature: Optional[str] = None
    constructor_signature: Optional[str] = None
    
    methods: Optional[List[MemberInfo]] = None
    properties: Optional[List[MemberInfo]] = None
    
    inherited_methods: Optional[Dict[str, List[MemberInfo]]] = None
    inherited_properties: Optional[Dict[str, List[MemberInfo]]] = None
    
    omitted_inherited_members_from: Optional[List[str]] = None
