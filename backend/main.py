from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.auth import verify_password, create_token
from backend.database import init_db
from backend.routes import conversations, chat, images, videos
from backend.schemas import LoginRequest, LoginResponse


# ---- 生命周期 ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


# ---- 创建应用 ----
app = FastAPI(title="LLM Chat", lifespan=lifespan)

# CORS（开发时前端在不同端口）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- 注册路由 ----
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(images.router)  # 图片生成 + 从 DB 读取
app.include_router(videos.router)  # 视频生成 + 从文件读取


# ---- 登录 ----
@app.post("/api/login", response_model=LoginResponse)
def login(body: LoginRequest):
    if not verify_password(body.password):
        raise HTTPException(401, "密码错误")
    return LoginResponse(token=create_token())


# ---- 生产环境：挂载前端静态文件 ----
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
