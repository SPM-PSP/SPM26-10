import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.backend.api.endpoints import router as api_router, initialize_global_resources
from src.backend.database import init_db  # 数据库初始化函数

# 后端接口根目录：http://localhost:8000/api

app = FastAPI(
    title="智教魔方",
    description="基于 Qwen3_0_6B 的智能教学与学习助手",
    version="1.0.0",
)

# --- 配置 CORS (跨域资源共享) ---
origins = [
    "http://localhost",
    "http://localhost:3200",
    "http://localhost:8080",
    "http://10.135.40.15:3200",
    "http://172.20.10.3:3200",
    "http://10.135.40.65:3200"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Session-ID"]
)

# --- 注册 API 路由 ---
app.include_router(api_router, prefix="/api")

# --- 应用生命周期事件：启动时初始化资源 ---
@app.on_event("startup")
async def startup_event():
    print("FastAPI 应用正在启动...")
    # 1. 初始化数据库
    await init_db()
    # 2. 初始化 LLM 和向量数据库
    initialize_global_resources()  # 这个函数负责加载LLM和向量库
    print("FastAPI 应用启动完成。")

# --- 定义根路径（可选）---
@app.get("/")
async def root():
    return {"message": "欢迎使用“智教魔方”后端服务！"}

if __name__ == "__main__":
    # 禁用 Uvicorn 默认日志配置，避免 isatty() 错误
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_config=None  # 关键修改：禁用默认日志配置
    )