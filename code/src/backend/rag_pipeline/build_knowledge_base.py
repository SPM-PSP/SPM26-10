#主入口：构建知识库

import os

import torch
from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# 1.配置常量和路径
# DOCS_DIR= "/data/docs"  #原始教学文档存放路径
# CHROMA_PERSIST_DIR= "../../../data/chroma_db"  #向量数据库存放
# EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5" # 用于生成文本嵌入的预训练模型名称
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DOCS_DIR = os.path.join(PROJECT_ROOT, "data", "docs")  # 原始教学文档存放路径
CHROMA_PERSIST_DIR = os.path.join(PROJECT_ROOT, "data", "chroma_db")  # 向量数据库存放
EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5" # 用于生成文本嵌入的预训练模型名称
SUPPORTED_TEXT_SUFFIXES = (".txt", ".md")
LOCAL_EMBEDDING_SNAPSHOT = os.path.expanduser(
    "~/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5/snapshots/7999e1d3359715c523056ef9478215996d62a620"
)

DEVICE = "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") is not None or \
                    (hasattr(os, 'is_available') and torch.cuda.is_available()) else "cpu"

#加载指定目录下的所有支持的文档文件（递归支持 PDF、DOCX、DOC、TXT、MD）
def load_documents(directory:str)->list:
    documents=[]
    print(f"开始加载{directory}中的文档")
    for root, _, files in os.walk(directory):
        for filename in sorted(files):
            filepath=os.path.join(root,filename)
            relative_path = os.path.relpath(filepath, directory)
            loader=None
            lower_filename = filename.lower()
            if lower_filename.endswith(".pdf"):
                loader = PyPDFLoader(filepath)
                print(f"  - 加载 PDF: {relative_path}")
            elif lower_filename.endswith((".docx", ".doc")):
                loader = UnstructuredWordDocumentLoader(filepath)
                print(f"  - 加载 DOCX/DOC: {relative_path}")
            elif lower_filename.endswith(SUPPORTED_TEXT_SUFFIXES):
                loader = TextLoader(filepath, encoding="utf-8")
                print(f"  - 加载文本: {relative_path}")
            else:
                print(f"  - 跳过不支持的文件类型: {relative_path}")
                continue

            if loader:
                try:
                    documents.extend(loader.load())
                except Exception as e:
                    print(f"  -错误：无法加载文件{relative_path}:{e}")

    print(f"共加载了{len(documents)}个文档对象")
    return documents

#将文档分割成小块chunks
def split_documents(documents:list)->list:

    # RecursiveCharacterTextSplitter按分隔符(\n\n,\n等)递归地分割文本
    # 尽可能地保留语义完整的块，例如先按段落，再按句子，最后按单词
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,  # 每个文本块的最大字符数
        chunk_overlap=50, # 块与块之间的重叠字符数，有助于保留上下文
        length_function=len, # 使用 Python 的 len() 函数计算长度
        add_start_index=True # 在元数据中添加块的起始位置
    )
    chunks=text_splitter.split_documents(documents)
    print(f"共生成了{len(chunks)}个文本块")
    return chunks

#初始化并返回用于生成嵌入的HuggingFaceEmbeddings模型
def get_embeddings_model(model_name: str, device: str):
    model_path = LOCAL_EMBEDDING_SNAPSHOT if os.path.exists(LOCAL_EMBEDDING_SNAPSHOT) else model_name
    print(f"加载嵌入模型: {model_path}，设备: {device}...")
    # HuggingFaceEmbeddings 封装了 sentence-transformers 库
    embeddings = HuggingFaceEmbeddings(
        model_name=model_path,
        model_kwargs={'device': device} # 指定模型运行在 CPU 还是 GPU；若存在本地快照则直接加载快照路径
    )
    print("嵌入模型加载成功。")
    return embeddings

#将文本块及其嵌入存储到 ChromaDB 向量数据库
def build_vector_store(chunks: list,
                       embeddings_model,
                       persist_directory: str):
    print(f"开始构建/更新 ChromaDB 向量数据库到: {persist_directory}...")

    # from_documents 会负责将 chunks 转换为嵌入，并存储到 ChromaDB
    # 如果 persist_directory 已经存在，它会尝试加载现有的数据库并添加新的数据
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings_model,
        persist_directory=persist_directory
    )

    # 确保存储到磁盘
    # vectorstore.persist()
    print("ChromaDB 向量数据库构建/更新完成并已持久化。")
    return vectorstore

#主函数，执行知识库的完整构建流程
def main():
    # 1. 确保文档目录存在
    if not os.path.exists(DOCS_DIR):
        print(f"错误：文档目录 '{DOCS_DIR}' 不存在。请确保将教学资料放入此目录。")
        return

    # 2. 加载原始文档
    raw_documents = load_documents(DOCS_DIR)
    if not raw_documents:
        print("没有加载到任何文档，请检查 'data/docs' 目录。")
        return

    # 3. 分割文档为文本块
    processed_chunks = split_documents(raw_documents)
    if not processed_chunks:
        print("文档分割后没有生成任何文本块，请检查文档内容或分割参数。")
        return

    # 4. 获取嵌入模型
    embeddings = get_embeddings_model(EMBEDDING_MODEL_NAME, DEVICE)

    # 5. 构建或更新向量数据库
    vector_db = build_vector_store(processed_chunks, embeddings, CHROMA_PERSIST_DIR)

    print("\n知识库构建流程已全部完成！")
    print(f"现在你可以通过加载 '{CHROMA_PERSIST_DIR}' 中的向量数据库来检索知识。")

if __name__ == "__main__":
    main()
