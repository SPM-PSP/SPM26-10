import os
import torch
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document  # 导入 Document 类型

# --- 配置常量 ---
# 确保与 build_knowledge_base.py 中的路径和模型一致
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
CHROMA_PERSIST_DIR = os.path.join(PROJECT_ROOT, "data", "chroma_db")
EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"  # 确保和构建时一致

# 检查设备
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- 存储向量数据库和嵌入模型的全局变量 ---
_vectorstore = None
_embeddings_model = None


# 初始化并加载 ChromaDB 向量数据库和嵌入模型（单例）
def initialize_vector_store():
    global _vectorstore, _embeddings_model

    if _vectorstore is None or _embeddings_model is None:
        print(f"正在加载嵌入模型: {EMBEDDING_MODEL_NAME}，设备: {DEVICE}...")
        try:
            _embeddings_model = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL_NAME,
                model_kwargs={'device': DEVICE}
            )
            print("嵌入模型加载成功。")
        except Exception as e:
            print(f"加载嵌入模型失败: {e}")
            raise RuntimeError(f"嵌入模型加载失败，请检查网络或模型名称。错误: {e}")

        print(f"正在从 '{CHROMA_PERSIST_DIR}' 加载 ChromaDB 向量数据库...")
        if not os.path.exists(CHROMA_PERSIST_DIR):
            raise RuntimeError(f"ChromaDB 路径 '{CHROMA_PERSIST_DIR}' 不存在。请先运行知识库构建脚本！")
        try:
            _vectorstore = Chroma(persist_directory=CHROMA_PERSIST_DIR, embedding_function=_embeddings_model)
            print("ChromaDB 向量数据库加载成功。")
        except Exception as e:
            print(f"加载 ChromaDB 失败: {e}")
            raise RuntimeError(f"ChromaDB 加载失败，请检查数据库文件完整性。错误: {e}")

    return _vectorstore, _embeddings_model


# 获取向量数据库的检索器
def get_retriever(k: int = 5):

    vectorstore, _ = initialize_vector_store()
    return vectorstore.as_retriever(search_kwargs={"k": k})


# --- 测试的示例 ---
if __name__ == "__main__":
    print("--- 启动 Vector Store Manager 测试 ---")
    try:
        vec_store, embed_model = initialize_vector_store()
        print("向量数据库和嵌入模型测试加载成功！")

        # 尝试检索
        retriever = get_retriever(k=2)
        test_query = "什么是Linux内核模块？"
        docs = retriever.invoke(test_query)

        # 添加调试打印，确认 docs 的类型和值
        print(f"DEBUG: Type of 'docs' before len(): {type(docs)}")
        print(f"DEBUG: Value of 'docs' before len(): {docs}")

        print(f"\n测试查询: '{test_query}'，检索到 {len(docs)} 个文档:")
        for i, doc in enumerate(docs):
            print(f"--- 文档 {i + 1} ---")
            print(doc.page_content[:200] + "...")  # 打印前200字符
            print(f"来源: {doc.metadata.get('source', '未知')}")

    except Exception as e:
        print(f"Vector Store Manager 测试失败: {e}")

