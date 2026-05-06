# 智教魔方后端服务文档

## 一、项目概述
基于 FastAPI 和 Qwen3_0_6B 大语言模型的智能教学助手后端服务，提供智能问答、知识检索等功能。

## 二、项目结构
```
backend/
├── src/                # 源代码目录
│   ├── api/            # API接口定义
│   ├── database/       # 数据库操作
│   ├── models/         # 模型相关
│   └── utils/          # 工具函数
├── main.py             # 应用入口
├── requirements.txt    # 依赖列表
└── models_download.txt # 模型下载说明
```

## 三、环境准备
### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 下载模型
根据 `models_download.txt` 中的百度网盘链接，下载所需的模型文件，并将其放置在项目指定目录（如 `src/models/`）。

## 四、配置说明
### 1. 修改服务器IP
打开 `main.py` 文件，将 `host` 参数修改为您的实际IP地址：
```python
# main.py
if __name__ == "__main__":
    uvicorn.run(app, host="您的实际IP", port=8000)
```

### 2. 配置跨域访问
在 `main.py` 中，将您前端应用的实际IP添加到 `origins` 列表：
```python
# main.py
origins = [
    "http://localhost",
    "http://localhost:3200",  # 本地前端开发环境
    "http://您的前端IP:端口号",  # 添加您的前端实际IP和端口
]
```

## 五、运行服务
```bash
python main.py
```
服务启动后，您可以通过以下地址访问API文档：
```
http://您的IP:8000/docs
```

## 六、常见问题
1. **模型加载失败**：
   - 检查模型文件路径是否正确
   - 确认模型文件完整性（根据 `models_download.txt` 中的MD5值校验）

2. **跨域请求失败**：
   - 确保 `origins` 列表中已添加前端应用的IP和端口
   - 检查防火墙是否开放了8000端口

3. **依赖安装问题**：
   ```bash
   # 使用国内镜像加速安装
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

## 七、联系方式
如有任何问题，请联系：
- 邮箱：1072455364@qq.com
