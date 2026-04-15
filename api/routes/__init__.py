from api.routes.consent import router as consent_router
from api.routes.fiduciary import router as fiduciary_router
from api.routes.audit import router as audit_router
from api.routes.grievance import router as grievance_router
from api.routes.guardian import router as guardian_router
from api.routes.deletion import router as deletion_router
from api.routes.public import router as public_router
from api.routes.dpo import router as dpo_router
from api.routes.children import router as children_router

__all__ = [
    "consent_router",
    "fiduciary_router",
    "audit_router",
    "grievance_router",
    "guardian_router",
    "deletion_router",
    "public_router",
    "dpo_router",
    "children_router",
]
