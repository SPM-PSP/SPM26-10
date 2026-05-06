import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import os

# --- 配置模型ID和缓存路径 ---
# 使用 Qwen/Qwen3-0.6B 的 Hugging Face 模型ID
MODEL_ID = "Qwen/Qwen3-0.6B"

# 模型缓存目录
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

MODEL_CACHE_DIR = os.path.join(PROJECT_ROOT, "models", "Qwen3_0_6B")
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)  # 确保缓存目录存在


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

quantization_config = None

QUANTIZATION_MODE = os.environ.get("QUANTIZATION_MODE", "bf16").lower()

quantization_config = None # 初始化为 None

if DEVICE == "cuda":
    if QUANTIZATION_MODE == "4bit":
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",  # NormalFloat4 量化类型
            bnb_4bit_compute_dtype=torch.bfloat16,  # 计算数据类型，RTX 4050支持bfloat16
            bnb_4bit_use_double_quant=True,  # 启用双重量化
        )
        print("CUDA GPU 检测到。将尝试使用 4-bit 量化加载模型以节省显存。")
    elif QUANTIZATION_MODE == "8bit":
        quantization_config = BitsAndBytesConfig(
            load_in_8bit=True, # 启用8位量化
            # 8位量化通常不需要4位量化的那些额外参数
        )
        print("CUDA GPU 检测到。将尝试使用 8-bit 量化加载模型。")
    elif QUANTIZATION_MODE == "bf16":
        # BF16模式下，quantization_config 保持为 None，并在 from_pretrained 中直接指定 torch_dtype
        print("CUDA GPU 检测到。将尝试以 BF16 精度加载模型。")
    else:
        # 如果 QUANTIZATION_MODE 是一个无效值，则回退到 BF16
        print(f"警告：无效的量化模式 '{QUANTIZATION_MODE}'。将尝试以 BF16 精度加载模型。")
        QUANTIZATION_MODE = "bf16" # 确保模式回退到 bf16
else: # CPU 模式下，不进行 bitsandbytes 量化
    print("未检测到 CUDA GPU，模型将在 CPU 上运行。")
    # CPU 上通常使用 float32，不进行 bnb 量化

# 存储模型和分词器的全局变量
_model = None
_tokenizer = None

# Qwen3-0.6B 的最大上下文窗口（官方文档：32768 序列长度）
MODEL_MAX_CONTEXT_TOKENS = 32768


# 加载 Qwen3-0.6B 模型和分词器
def load_qwen3_model():
    global _model, _tokenizer
    if _model is None or _tokenizer is None:
        print(f"正在尝试从本地缓存加载模型和分词器: '{MODEL_ID}' 到本地目录: '{MODEL_CACHE_DIR}'")
        try:
            # Qwen 模型通常要求 trust_remote_code=True
            _tokenizer = AutoTokenizer.from_pretrained(
                MODEL_ID,
                trust_remote_code=True,
                cache_dir=MODEL_CACHE_DIR,
                # local_files_only=True # 首次加载需下载，后续可启用
                padding_side='left'  # Qwen 官方推荐 left padding for text generation
            )
            # 设置pad_token_id以避免警告
            if _tokenizer.pad_token is None:
                _tokenizer.pad_token = _tokenizer.eos_token  # 或者根据模型文档选择合适的pad token

            # --- 核心修改部分：根据 QUANTIZATION_MODE 加载模型 ---
            if DEVICE == "cuda":
                if QUANTIZATION_MODE in ["4bit", "8bit"]:
                    # 量化模式下，使用 quantization_config
                    _model = AutoModelForCausalLM.from_pretrained(
                        MODEL_ID,
                        # bnb 量化通常会设置自己的 compute_dtype，但为了兼容性，仍可指定
                        torch_dtype=torch.bfloat16, # 计算数据类型，RTX 4050支持bfloat16
                        quantization_config=quantization_config,
                        device_map="auto", # 智能分配到可用GPU
                        trust_remote_code=True,
                        cache_dir=MODEL_CACHE_DIR,
                    )
                elif QUANTIZATION_MODE == "bf16":
                    # BF16模式下，直接指定 torch_dtype
                    _model = AutoModelForCausalLM.from_pretrained(
                        MODEL_ID,
                        torch_dtype=torch.bfloat16, # 显式设置为BF16
                        device_map="auto",
                        trust_remote_code=True,
                        cache_dir=MODEL_CACHE_DIR,
                    )
                else: # 兼容无效 QUANTIZATION_MODE 的情况，回退到 BF16
                    _model = AutoModelForCausalLM.from_pretrained(
                        MODEL_ID,
                        torch_dtype=torch.bfloat16,
                        device_map="auto",
                        trust_remote_code=True,
                        cache_dir=MODEL_CACHE_DIR,
                    )
            else: # CPU 模式
                _model = AutoModelForCausalLM.from_pretrained(
                    MODEL_ID,
                    torch_dtype=torch.float32, # CPU 上通常使用 float32
                    device_map=None, # CPU 不用 device_map
                    trust_remote_code=True,
                    cache_dir=MODEL_CACHE_DIR,
                )
            # --- 修改结束 ---

            _model.eval()  # 将模型设置为评估模式，关闭 dropout 等训练特性

            print(f"{MODEL_ID} 模型和分词器加载成功！")
            if DEVICE == "cuda":
                # 打印显存占用，确保模型已加载到GPU
                print(f"模型已加载到 {DEVICE}。显存占用：{torch.cuda.memory_allocated() / 1024 ** 3:.2f} GB (估算)")

        except Exception as e:
            print(f"加载 {MODEL_ID} 模型失败: {e}")
            _model = None
            _tokenizer = None
            raise e  # 重新抛出异常以便上层捕获

    return _model, _tokenizer


# 使用 Qwen3 模型生成文本（智能上下文管理）
def generate_text_with_qwen3(system_instruction: str, user_question: str, retrieved_documents_content: list[str],
                             final_instruction: str, max_new_tokens: int = 512, temperature: float = 0.7,
                             top_p: float = 0.8, presence_penalty: float = 1.5,
                             enable_thinking_mode: bool = True) -> str:
    '''
    :param system_instruction: 大模型扮演的角色和通用指令
    :param user_question: 用户提出的原始问题
    :param retrieved_documents_content: 从知识库检索到的相关文档内容列表
    :param final_instruction: 给模型的最终指令，如“请给出你的回答：”
    :param max_new_tokens: 模型生成新闻本的最大token数量
    :param temperature: 采样温度，越高输出越随机
    :param top_p: Top-p 采样，选择概率累积和达到 P 的 token
    :param presence_penalty: 存在惩罚，用于减少重复 (Qwen推荐)
    :param enable_thinking_mode: 是否启用Qwen3的思考模式 (True为默认)
    :return: str: 模型生成的文本回答
    '''

    model, tokenizer = load_qwen3_model()
    if model is None or tokenizer is None:
        return "模型未加载，无法生成内容。"

    # 1. 定义 Prompt 结构组件 (Qwen3 推荐使用 chat template)
    # 这里我们将 Prompt 的 RAG 部分整合到 user 消息中
    # 或者可以将知识库内容放在 system 消息之后，user 消息之前。
    # 为了简化，我们把 RAG 内容也放到用户问题中
    # Qwen3 的 chat template 处理消息列表，而不是单个字符串
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})

    # 构建知识库内容字符串
    context_text_for_llm = []
    # 估算 Prompt 模板和用户问题本身占据的token长度
    # rough_base_prompt_tokens = len(tokenizer.encode(system_instruction + user_question + final_instruction))
    # 对于 chat template，更准确的做法是先编码一个不含文档的骨架来估算
    # 为了简化且避免重复编码，我们可以预留一个固定的安全边际，并基于 total_tokens 倒推
    # 这里我们直接利用 MODEL_MAX_CONTEXT_TOKENS 和 max_new_tokens 来决定文档长度

    # 预留空间给模型生成和系统/用户指令本身
    # 假设系统指令+用户问题+最终指令+少量分隔符占用约 256 tokens (保守估计)
    # Qwen3 的上下文是 32768
    SAFETY_MARGIN_FOR_PROMPT_STRUCTURE = 256 + max_new_tokens + 50  # 额外给 Prompt 结构本身和安全边际

    # 计算可用于知识库内容的 token 空间
    available_context_tokens_for_docs = MODEL_MAX_CONTEXT_TOKENS - SAFETY_MARGIN_FOR_PROMPT_STRUCTURE

    current_docs_tokens = 0
    selected_docs = []

    for doc_content in retrieved_documents_content:
        # 注意：这里简单的 len(tokenizer.encode(doc_content)) 会导致重复编码，效率较低。
        # 但在Python中，为了精确控制token数量，这是常用方法。
        doc_tokens = len(tokenizer.encode(doc_content))
        if current_docs_tokens + doc_tokens <= available_context_tokens_for_docs:
            selected_docs.append(doc_content)
            current_docs_tokens += doc_tokens
        else:
            break

    # 构建用户消息
    user_message_content = ""
    if not selected_docs and retrieved_documents_content:
        print("警告：有检索结果，但因上下文限制未能将任何知识库内容加入到Prompt中。")
        user_message_content += f"当前知识库中没有足够空间提供直接相关的信息。\n\n"
        user_message_content += f"{user_question}\n\n请尝试根据你的一般知识回答，或说明你无法根据当前知识库回答。"
    elif not retrieved_documents_content:
        user_message_content += f"当前知识库中没有直接相关的信息。\n\n"
        user_message_content += f"{user_question}\n\n请尝试根据你的一般知识回答，或说明你无法回答。"
    else:
        user_message_content += "知识库内容：\n---\n"
        user_message_content += "\n--PHRASE_SEP\n".join(selected_docs)  # 使用特殊分隔符，或简单换行
        user_message_content += "\n---\n\n"
        user_message_content += f"用户问题：{user_question}\n\n"

    user_message_content += final_instruction

    messages.append({"role": "user", "content": user_message_content})

    # 应用 Qwen3 的 chat 模板
    # enable_thinking=True 会让模型在生成前“思考”，有助于复杂问题和代码生成
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=enable_thinking_mode  # 控制思考模式
    )

    print(f"最终Prompt (部分): {text[:500]}...")  # 打印部分Prompt方便调试
    final_prompt_tokens = len(tokenizer.encode(text))
    print(f"最终Prompt token长度: {final_prompt_tokens}")

    # 6.调用 Qwen3-0.6B 进行生成
    try:
        input_ids = tokenizer.encode(text, return_tensors="pt").to(model.device)

        # 检查是否超出模型最大上下文
        if final_prompt_tokens + max_new_tokens > MODEL_MAX_CONTEXT_TOKENS:
            print(f"警告：最终Prompt和期望生成内容总长度 ({final_prompt_tokens + max_new_tokens}) "
                  f"超出模型最大上下文限制 ({MODEL_MAX_CONTEXT_TOKENS})。模型可能会截断或报错。")

        # 官方建议的采样参数：
        # 思考模式: Temperature=0.6, TopP=0.95, TopK=20, MinP=0
        # 非思考模式: Temperature=0.7, TopP=0.8, TopK=20, MinP=0
        # 我们使用传入的参数，如果未指定则使用默认值
        generation_kwargs = {
            "max_new_tokens": max_new_tokens,
            "do_sample": True,
            "temperature": temperature,
            "top_p": top_p,
            "pad_token_id": tokenizer.pad_token_id,
            "eos_token_id": tokenizer.eos_token_id,
            "repetition_penalty": 1.0  # 保持默认，presence_penalty 通常更有效
        }
        # 如果模型支持并需要，可以添加 top_k 和 min_p
        # if enable_thinking_mode:
        #     generation_kwargs["top_k"] = 20
        #     generation_kwargs["min_p"] = 0.0
        # else:
        #     generation_kwargs["top_k"] = 20
        #     generation_kwargs["min_p"] = 0.0

        generated_output = model.generate(
            input_ids,
            **generation_kwargs
        )

        # 提取新生成的token序列
        output_ids_tensor = generated_output[0]  # Qwen generate usually returns tuple(sequences)
        generated_sequence_ids = output_ids_tensor[len(input_ids[0]):].tolist()

        # 解析思考内容和最终内容
        # Qwen3 在 thinking 模式下会生成 <think>...</think> 块
        # tokenizer.apply_chat_template 默认会处理这些
        # 但是 generate 返回的原始ID流需要手动解析
        # 根据Qwen3的文档，</think> 的 token_id 是 151668
        # 我们需要找到这个 token，然后将其前面的内容作为思考内容。
        thinking_content = ""
        final_response_content = ""

        if enable_thinking_mode:
            try:
                # 寻找 </think> token_id (151668)
                # Qwen 模型的特殊 token ID 可以在 tokenizer.json 中找到
                # Tokenizer 应该已经处理好这些特殊 token 的 ID
                # 这里假设 Qwen3 的 </think> token id 是 151668, 如果不是请根据 tokenizer.convert_tokens_to_ids("</think>") 调整
                end_think_token_id = tokenizer.convert_tokens_to_ids("</think>")

                # 从生成的序列中寻找 </think> 的位置
                # 注意：generated_sequence_ids 是一个列表
                if end_think_token_id in generated_sequence_ids:
                    # 找到最后一个 </think> 的位置
                    # 考虑到可能会有多个 <think>...</think> 块，我们应该关注最后一个
                    end_think_index = len(generated_sequence_ids) - generated_sequence_ids[::-1].index(
                        end_think_token_id)

                    thinking_content_ids = generated_sequence_ids[:end_think_index]
                    # 排除 </think> 自身
                    actual_response_ids = generated_sequence_ids[end_think_index + 1:]  # +1 跳过 </think>

                    thinking_content = tokenizer.decode(thinking_content_ids, skip_special_tokens=True).strip()
                    final_response_content = tokenizer.decode(actual_response_ids, skip_special_tokens=True).strip()
                else:
                    # 如果没有 </think> 标记，则全部视为最终响应
                    final_response_content = tokenizer.decode(generated_sequence_ids, skip_special_tokens=True).strip()
                    print("警告：在思考模式下未检测到 </think> token。全部输出作为最终响应。")

            except ValueError:
                # 如果没有 </think> token，则整个输出都是最终响应
                final_response_content = tokenizer.decode(generated_sequence_ids, skip_special_tokens=True).strip()
                print("警告：在思考模式下未检测到 </think> token。全部输出作为最终响应。")
            except Exception as e:
                print(f"解析思考内容时出错: {e}。将全部输出作为最终响应。")
                final_response_content = tokenizer.decode(generated_sequence_ids, skip_special_tokens=True).strip()
        else:
            # 非思考模式，直接解码全部内容
            final_response_content = tokenizer.decode(generated_sequence_ids, skip_special_tokens=True).strip()

        # 打印思考内容（如果存在）
        if thinking_content:
            print(f"\n--- 模型的思考过程 ---\n{thinking_content}\n--------------------\n")

        return final_response_content
    except Exception as e:
        print(f"模型生成失败: {e}")
        # 捕获CUDA OOM错误并给出提示
        if "CUDA out of memory" in str(e):
            print("错误：显存不足！尝试减小 max_new_tokens 或将 global_use_4bit_quantization 设置为 True。")
        return "生成内容时发生错误。"


# --- 用于测试的示例 ---
if __name__ == "__main__":
    print("--- 启动 LLM Manager 测试 ---")

    # 1. 预加载模型，以确保在 Flask/FastAPI 启动时模型已准备好
    print(f"正在测试 {MODEL_ID} 模型加载...")
    try:
        model, tokenizer = load_qwen3_model()
        print("模型加载测试通过！")
    except Exception as e:
        print(f"模型加载测试失败: {e}")
        exit(1)  # 如果加载失败，就退出

    # 2. 准备测试数据（模拟 RAG 检索结果）
    test_system_instruction = "你是一位经验丰富的《嵌入式Linux开发实践教程》老师。"
    test_user_question = "Linux 内核模块的初始化函数和退出函数分别是什么，它们有什么作用？请包含一个简单的 hello world 示例代码。"
    test_retrieved_docs = [
        "Linux内核模块编程中，模块的初始化函数通常命名为`module_init()`，它在模块被加载到内核时执行一次。这个函数负责为模块分配资源、注册设备驱动、初始化数据结构等。",
        "模块的退出函数通常命名为`module_exit()`，它在模块被卸载时执行。这个函数负责释放初始化函数中分配的资源，注销已注册的驱动等，以确保系统清理干净。",
        "一个简单的内核模块示例代码通常会包含`module_init`和`module_exit`宏，将自定义的初始化和退出函数与内核钩子关联起来。",
        "除了初始化和退出函数，内核模块还可以包含其他函数，用于实现具体的功能，比如文件操作、网络通信等。这些函数在模块加载后可以被其他内核部分或用户空间程序调用。",
        "模块加载命令通常是`insmod`，卸载命令是`rmmod`。使用`lsmod`可以查看当前已加载的模块。"
    ]
    test_final_instruction = "请给出你的回答，并包含示例代码。"

    # 3. 进行文本生成测试 (模拟 RAG 问答)
    print("\n--- 进行 RAG 文本生成测试 (思考模式) ---")
    print(f"用户问题: {test_user_question}")
    print(f"检索到的文档数量: {len(test_retrieved_docs)}")

    rag_response = generate_text_with_qwen3(
        system_instruction=test_system_instruction,
        user_question=test_user_question,
        retrieved_documents_content=test_retrieved_docs,
        final_instruction=test_final_instruction,
        max_new_tokens=600,  # 允许生成更多内容，包含示例代码
        enable_thinking_mode=True
    )
    print(f"\n生成的 RAG 响应:\n{rag_response}")

    # 4. 进行简单生成测试 (不带知识库，模拟备课或出题，非思考模式)
    print("\n--- 进行不带知识库的生成测试（备课模拟，非思考模式）---")
    lesson_prompt_system = "你是一位资深的嵌入式Linux课程设计师。"
    lesson_outline_question = "请根据以下主题，为大学三年级学生设计一份关于'Linux文件系统'的课程大纲和主要知识点，并包含至少一个实践任务建议。"
    lesson_retrieved_docs = []  # 这里是空的，表示不使用知识库
    lesson_final_instruction = "请给出详细的课程设计。"

    lesson_plan_response = generate_text_with_qwen3(
        system_instruction=lesson_prompt_system,
        user_question=lesson_outline_question,
        retrieved_documents_content=lesson_retrieved_docs,
        final_instruction=lesson_final_instruction,
        max_new_tokens=800,  # 允许生成更多内容
        enable_thinking_mode=False  # 禁用思考模式
    )
    print(f"\n生成的课程计划:\n{lesson_plan_response}")

    # 5. 测试一个长 Prompt 的情况，可能触发显存边界
    # print("\n--- 进行长 Prompt 和长生成测试 (测试显存边界) ---")
    # long_user_question = "请详细阐述大型语言模型（LLM）的Transformer架构、注意力机制（Self-Attention、Multi-Head Attention）、Encoder-Decoder结构、以及预训练和微调（Fine-tuning）的原理和最新发展，并探讨其在自然语言处理中的应用前景和局限性。请写一篇至少1000字的综述。"
    # try:
    #     long_response = generate_text_with_qwen3(
    #         system_instruction="你是一位专业的AI研究员。",
    #         user_question=long_user_question,
    #         retrieved_documents_content=[],
    #         final_instruction="请给出你的详细综述。",
    #         max_new_tokens=1000,
    #         enable_thinking_mode=True
    #     )
    #     print(f"\n生成的长响应:\n{long_response[:1000]}...")
    # except Exception as e:
    #     print(f"长文本生成测试失败: {e}")