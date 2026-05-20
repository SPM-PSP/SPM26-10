import json
import os
from collections.abc import Iterator
import time
from urllib import error, request

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from src.backend.config import settings

# --- 配置模型ID和缓存路径 ---
MODEL_ID = "Qwen/Qwen3-0.6B"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_CACHE_DIR = os.path.join(PROJECT_ROOT, "models", "Qwen3_0_6B")
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
QUANTIZATION_MODE = os.environ.get("QUANTIZATION_MODE", "bf16").lower()

quantization_config = None
if DEVICE == "cuda":
    if QUANTIZATION_MODE == "4bit":
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True
        )
        print("CUDA GPU 检测到。将尝试使用 4-bit 量化加载模型以节省显存。")
    elif QUANTIZATION_MODE == "8bit":
        quantization_config = BitsAndBytesConfig(load_in_8bit=True)
        print("CUDA GPU 检测到。将尝试使用 8-bit 量化加载模型。")
    elif QUANTIZATION_MODE == "bf16":
        print("CUDA GPU 检测到。将尝试以 BF16 精度加载模型。")
    else:
        print(f"警告：无效的量化模式 '{QUANTIZATION_MODE}'。将尝试以 BF16 精度加载模型。")
        QUANTIZATION_MODE = "bf16"
else:
    print("未检测到 CUDA GPU，模型将在 CPU 上运行。")

_model = None
_tokenizer = None
MODEL_MAX_CONTEXT_TOKENS = 32768


def validate_llm_settings():
    if settings.LLM_MODE not in {"local", "api", "hybrid"}:
        raise RuntimeError(f"不支持的 LLM_MODE: {settings.LLM_MODE}")

    if settings.uses_remote_llm():
        if not settings.LLM_API_KEY:
            raise RuntimeError("当前启用了远程 LLM，但未配置 LLM_API_KEY。")
        if not settings.LLM_API_BASE_URL:
            raise RuntimeError("当前启用了远程 LLM，但未配置 LLM_API_BASE_URL。")
        if not settings.LLM_API_MODEL:
            raise RuntimeError("当前启用了远程 LLM，但未配置 LLM_API_MODEL。")


def _resolve_max_new_tokens(max_new_tokens: int | None, default: int = 512) -> int:
    return max_new_tokens if max_new_tokens is not None else default


def initialize_llm_runtime():
    validate_llm_settings()
    if settings.uses_local_llm():
        load_qwen3_model()
        print("LLM 本地模式已初始化。")
    else:
        print(
            f"LLM 远程模式已启用：provider={settings.LLM_PROVIDER}, "
            f"model={settings.LLM_API_MODEL}, base_url={settings.LLM_API_BASE_URL}"
        )


def load_qwen3_model():
    global _model, _tokenizer
    if _model is None or _tokenizer is None:
        print(f"正在尝试从本地缓存加载模型和分词器: '{MODEL_ID}' 到本地目录: '{MODEL_CACHE_DIR}'")
        try:
            _tokenizer = AutoTokenizer.from_pretrained(
                MODEL_ID,
                trust_remote_code=True,
                cache_dir=MODEL_CACHE_DIR,
                padding_side="left"
            )
            if _tokenizer.pad_token is None:
                _tokenizer.pad_token = _tokenizer.eos_token

            if DEVICE == "cuda":
                if QUANTIZATION_MODE in {"4bit", "8bit"}:
                    _model = AutoModelForCausalLM.from_pretrained(
                        MODEL_ID,
                        torch_dtype=torch.bfloat16,
                        quantization_config=quantization_config,
                        device_map="auto",
                        trust_remote_code=True,
                        cache_dir=MODEL_CACHE_DIR
                    )
                else:
                    _model = AutoModelForCausalLM.from_pretrained(
                        MODEL_ID,
                        torch_dtype=torch.bfloat16,
                        device_map="auto",
                        trust_remote_code=True,
                        cache_dir=MODEL_CACHE_DIR
                    )
            else:
                _model = AutoModelForCausalLM.from_pretrained(
                    MODEL_ID,
                    torch_dtype=torch.float32,
                    device_map=None,
                    trust_remote_code=True,
                    cache_dir=MODEL_CACHE_DIR
                )

            _model.eval()
            print(f"{MODEL_ID} 模型和分词器加载成功！")
            if DEVICE == "cuda":
                print(f"模型已加载到 {DEVICE}。显存占用：{torch.cuda.memory_allocated() / 1024 ** 3:.2f} GB (估算)")
        except Exception as exc:
            print(f"加载 {MODEL_ID} 模型失败: {exc}")
            _model = None
            _tokenizer = None
            raise

    return _model, _tokenizer


def _select_docs_for_local_prompt(tokenizer, retrieved_documents_content: list[str], max_new_tokens: int) -> list[str]:
    available_context_tokens_for_docs = MODEL_MAX_CONTEXT_TOKENS - (256 + max_new_tokens + 50)
    current_docs_tokens = 0
    selected_docs = []

    for doc_content in retrieved_documents_content:
        doc_tokens = len(tokenizer.encode(doc_content))
        if current_docs_tokens + doc_tokens <= available_context_tokens_for_docs:
            selected_docs.append(doc_content)
            current_docs_tokens += doc_tokens
        else:
            break

    return selected_docs


def _build_user_message(user_question: str, retrieved_documents_content: list[str], final_instruction: str) -> str:
    if retrieved_documents_content:
        context_block = "\n--PHRASE_SEP\n".join(retrieved_documents_content)
        return (
            "知识库内容：\n---\n"
            f"{context_block}\n"
            "---\n\n"
            f"用户问题：{user_question}\n\n"
            f"{final_instruction}"
        )

    return (
        "当前知识库中没有直接相关的信息。\n\n"
        f"{user_question}\n\n"
        "请尝试根据你的一般知识回答，或说明你无法回答。\n\n"
        f"{final_instruction}"
    )


def _build_chat_messages(
    system_instruction: str,
    user_question: str,
    retrieved_documents_content: list[str],
    final_instruction: str
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})

    messages.append(
        {
            "role": "user",
            "content": _build_user_message(user_question, retrieved_documents_content, final_instruction)
        }
    )
    return messages


def _call_remote_openai_compatible(
    system_instruction: str,
    user_question: str,
    retrieved_documents_content: list[str],
    final_instruction: str,
    max_new_tokens: int | None,
    temperature: float,
    top_p: float
) -> str:
    endpoint = f"{settings.LLM_API_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.LLM_API_MODEL,
        "messages": _build_chat_messages(
            system_instruction=system_instruction,
            user_question=user_question,
            retrieved_documents_content=retrieved_documents_content,
            final_instruction=final_instruction
        ),
        "temperature": temperature,
        "top_p": top_p,
        "stream": False
    }
    if max_new_tokens is not None:
        payload["max_tokens"] = max_new_tokens

    req = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.LLM_API_KEY}"
        },
        method="POST"
    )

    try:
        with request.urlopen(req, timeout=settings.LLM_API_TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8")
        data = json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"远程 LLM 调用失败 HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"远程 LLM 网络错误: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("远程 LLM 返回了无法解析的 JSON。") from exc

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"远程 LLM 返回格式异常: {data}")

    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()
    return str(content).strip()


def _stream_remote_openai_compatible(
    system_instruction: str,
    user_question: str,
    retrieved_documents_content: list[str],
    final_instruction: str,
    max_new_tokens: int | None,
    temperature: float,
    top_p: float
) -> Iterator[str]:
    endpoint = f"{settings.LLM_API_BASE_URL.rstrip('/')}/chat/completions"
    api_started_at = time.perf_counter()
    payload = {
        "model": settings.LLM_API_MODEL,
        "messages": _build_chat_messages(
            system_instruction=system_instruction,
            user_question=user_question,
            retrieved_documents_content=retrieved_documents_content,
            final_instruction=final_instruction
        ),
        "temperature": temperature,
        "top_p": top_p,
        "stream": True
    }
    if max_new_tokens is not None:
        payload["max_tokens"] = max_new_tokens

    req = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.LLM_API_KEY}"
        },
        method="POST"
    )

    try:
        with request.urlopen(req, timeout=settings.LLM_API_TIMEOUT_SECONDS) as resp:
            headers_received_at = time.perf_counter()
            print(
                f"Qwen API 流式请求已建立: headers_elapsed={headers_received_at - api_started_at:.2f}s, "
                f"model={settings.LLM_API_MODEL}, question_preview={user_question[:60]!r}"
            )
            first_chunk_logged = False
            chunk_count = 0
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="ignore").strip()
                if not line or not line.startswith("data:"):
                    continue

                payload_str = line[5:].strip()
                if payload_str == "[DONE]":
                    break

                try:
                    data = json.loads(payload_str)
                except json.JSONDecodeError:
                    continue

                choices = data.get("choices") or []
                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if content is None:
                    continue

                if isinstance(content, list):
                    chunk = "".join(part.get("text", "") for part in content if isinstance(part, dict))
                elif isinstance(content, str):
                    chunk = content
                else:
                    continue

                if chunk:
                    chunk_count += 1
                    if not first_chunk_logged:
                        first_chunk_logged = True
                        first_chunk_at = time.perf_counter()
                        print(
                            f"Qwen API 首 token 到达: ttft={first_chunk_at - api_started_at:.2f}s, "
                            f"headers_to_first_token={first_chunk_at - headers_received_at:.2f}s"
                        )
                    yield chunk
            finished_at = time.perf_counter()
            print(
                f"Qwen API 流式响应完成: total_elapsed={finished_at - api_started_at:.2f}s, "
                f"chunk_count={chunk_count}"
            )
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"远程 LLM 流式调用失败 HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"远程 LLM 流式网络错误: {exc}") from exc


def _generate_with_local_qwen(
    system_instruction: str,
    user_question: str,
    retrieved_documents_content: list[str],
    final_instruction: str,
    max_new_tokens: int | None,
    temperature: float,
    top_p: float,
    enable_thinking_mode: bool
) -> str:
    model, tokenizer = load_qwen3_model()
    if model is None or tokenizer is None:
        return "模型未加载，无法生成内容。"

    effective_max_new_tokens = _resolve_max_new_tokens(max_new_tokens)
    selected_docs = _select_docs_for_local_prompt(tokenizer, retrieved_documents_content, effective_max_new_tokens)
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append(
        {
            "role": "user",
            "content": _build_user_message(user_question, selected_docs, final_instruction)
        }
    )

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=enable_thinking_mode
    )

    print(f"最终Prompt (部分): {text[:500]}...")
    final_prompt_tokens = len(tokenizer.encode(text))
    print(f"最终Prompt token长度: {final_prompt_tokens}")

    try:
        input_ids = tokenizer.encode(text, return_tensors="pt").to(model.device)
        if final_prompt_tokens + effective_max_new_tokens > MODEL_MAX_CONTEXT_TOKENS:
            print(
                f"警告：最终Prompt和期望生成内容总长度 ({final_prompt_tokens + effective_max_new_tokens}) "
                f"超出模型最大上下文限制 ({MODEL_MAX_CONTEXT_TOKENS})。模型可能会截断或报错。"
            )

        generated_output = model.generate(
            input_ids,
            max_new_tokens=effective_max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.0
        )

        output_ids_tensor = generated_output[0]
        generated_sequence_ids = output_ids_tensor[len(input_ids[0]):].tolist()

        thinking_content = ""
        final_response_content = ""

        if enable_thinking_mode:
            try:
                end_think_token_id = tokenizer.convert_tokens_to_ids("</think>")
                if end_think_token_id in generated_sequence_ids:
                    end_think_index = len(generated_sequence_ids) - generated_sequence_ids[::-1].index(end_think_token_id)
                    thinking_content_ids = generated_sequence_ids[:end_think_index]
                    actual_response_ids = generated_sequence_ids[end_think_index + 1:]
                    thinking_content = tokenizer.decode(thinking_content_ids, skip_special_tokens=True).strip()
                    final_response_content = tokenizer.decode(actual_response_ids, skip_special_tokens=True).strip()
                else:
                    final_response_content = tokenizer.decode(generated_sequence_ids, skip_special_tokens=True).strip()
                    print("警告：在思考模式下未检测到 </think> token。全部输出作为最终响应。")
            except Exception as exc:
                print(f"解析思考内容时出错: {exc}。将全部输出作为最终响应。")
                final_response_content = tokenizer.decode(generated_sequence_ids, skip_special_tokens=True).strip()
        else:
            final_response_content = tokenizer.decode(generated_sequence_ids, skip_special_tokens=True).strip()

        if thinking_content:
            print(f"\n--- 模型的思考过程 ---\n{thinking_content}\n--------------------\n")

        return final_response_content
    except Exception as exc:
        print(f"模型生成失败: {exc}")
        if "CUDA out of memory" in str(exc):
            print("错误：显存不足！尝试减小 max_new_tokens 或启用量化。")
        return "生成内容时发生错误。"


def generate_text_with_qwen3(
    system_instruction: str,
    user_question: str,
    retrieved_documents_content: list[str],
    final_instruction: str,
    max_new_tokens: int | None = 512,
    temperature: float = 0.7,
    top_p: float = 0.8,
    presence_penalty: float = 1.5,
    enable_thinking_mode: bool = True
) -> str:
    """
    兼容旧调用名；根据配置自动选择本地模型或远程 API。
    """

    validate_llm_settings()

    if settings.uses_remote_llm():
        return _call_remote_openai_compatible(
            system_instruction=system_instruction,
            user_question=user_question,
            retrieved_documents_content=retrieved_documents_content,
            final_instruction=final_instruction,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p
        )

    return _generate_with_local_qwen(
        system_instruction=system_instruction,
        user_question=user_question,
        retrieved_documents_content=retrieved_documents_content,
        final_instruction=final_instruction,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        enable_thinking_mode=enable_thinking_mode
    )


def stream_text_with_qwen3(
    system_instruction: str,
    user_question: str,
    retrieved_documents_content: list[str],
    final_instruction: str,
    max_new_tokens: int | None = 512,
    temperature: float = 0.7,
    top_p: float = 0.8,
    enable_thinking_mode: bool = True
) -> Iterator[str]:
    """
    流式生成接口。远程模式下逐块返回；本地模式下暂时退化为一次性返回。
    """
    validate_llm_settings()

    if settings.uses_remote_llm():
        yield from _stream_remote_openai_compatible(
            system_instruction=system_instruction,
            user_question=user_question,
            retrieved_documents_content=retrieved_documents_content,
            final_instruction=final_instruction,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p
        )
        return

    yield generate_text_with_qwen3(
        system_instruction=system_instruction,
        user_question=user_question,
        retrieved_documents_content=retrieved_documents_content,
        final_instruction=final_instruction,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        enable_thinking_mode=enable_thinking_mode
    )
