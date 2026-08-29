from fastapi import APIRouter

from .chat import router as chat_router
from .product import router as products_router
from .search import router as search_router
from .sessions import router as sessions_router
from .recommendations import router as recommendations_router
from .feedback import router as feedback_router
from .evaluation import router as evaluation_router
from .wishlist import router as wishlist_router


router = APIRouter()

router.include_router(chat_router)
router.include_router(products_router)
router.include_router(search_router)
router.include_router(sessions_router)
router.include_router(recommendations_router)
router.include_router(feedback_router)
router.include_router(evaluation_router)
router.include_router(wishlist_router)
