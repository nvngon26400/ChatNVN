from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncIterator, Optional
import requests

from langchain.callbacks.streaming_aiter import AsyncIteratorCallbackHandler
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationSummaryBufferMemory
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .config import Settings, get_settings
from .document_loader import load_documents, split_documents
from .vectorstore import VectorStoreBuilder, get_retriever


class CustomerSupportChatbot:
    """High-level interface that manages ingestion and Q&A interactions."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._retriever = None
        self._prompt = _build_prompt()
        self._answer_cache: dict[str, str] = {}

    def init_index(self) -> None:
        """Initialize retriever with optional FAISS persistence to reduce cold-start latency."""
        if self._retriever:
            return
        builder = VectorStoreBuilder(self.settings)
        vector_store = None
        try:
            if self.settings.persist_index and not self.settings.reindex_on_start:
                persist_path = self.settings.persist_index_path
                if persist_path.exists():
                    vector_store = builder.load_from_disk(persist_path)
        except Exception:
            vector_store = None

        if vector_store is None:
            documents = load_documents(self.settings)
            chunks = split_documents(self.settings, documents)
            if self.settings.persist_index:
                vector_store = builder.build(chunks, persist_path=self.settings.persist_index_path)
            else:
                vector_store = builder.build(chunks)

        self._retriever = get_retriever(vector_store, k=self.settings.retriever_k)

    def _get_retriever(self):
        if not self._retriever:
            self.init_index()
        return self._retriever

    def build_chain(self, session_id: str = "default") -> ConversationalRetrievalChain:
        retriever = self._get_retriever()
        llm = self._create_llm()

        history_dir = Path("data/chat_history")
        history_dir.mkdir(parents=True, exist_ok=True)
        file_path = history_dir / f"{session_id}.json"

        chat_memory = FileChatMessageHistory(str(file_path))

        memory = ConversationSummaryBufferMemory(
            chat_memory=chat_memory,
            memory_key="chat_history",
            return_messages=True,
            llm=self._create_llm(),
            output_key="answer",
            max_token_limit=1200,
        )

        # Dùng default prompt của ConversationalRetrievalChain
        # Chain tự động xử lý chat_history với format đúng (list of messages)
        return ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            memory=memory,
            verbose=True,
            combine_docs_chain_kwargs={"prompt": self._prompt},
        )

    def ask(self, question: str, session_id: str = "default") -> str:
        if not question.strip():
            return "Vui lòng nhập câu hỏi hợp lệ."

        try:
            cache_key = f"{session_id}|{question.strip().lower()}"
            if cache_key in self._answer_cache:
                return self._answer_cache[cache_key]
            # Fallback: nếu không có dữ liệu nội bộ, gọi trực tiếp OpenAI
            if not self.settings.docs_exist:
                answer = self._ask_openai_direct(question)
                self._append_history(session_id, question, answer)
                self._answer_cache[cache_key] = answer
                return answer

            chain = self.build_chain(session_id=session_id)
            response = chain.invoke({"question": question})
            answer = response.get("answer", "Xin lỗi, không thể tạo phản hồi.")
            self._answer_cache[cache_key] = answer
            return answer
        except Exception as e:  # noqa: BLE001
            # Nếu lỗi liên quan đến token counting/model không được hỗ trợ, fallback gọi trực tiếp
            if "get_num_tokens_from_messages" in str(e) or "tiktoken" in str(e):
                try:
                    answer = self._ask_openai_direct(question)
                    self._append_history(session_id, question, answer)
                    self._answer_cache[cache_key] = answer
                    return answer
                except Exception:
                    pass
            import traceback
            error_msg = f"Lỗi khi xử lý câu hỏi: {str(e)}"
            print(f"Chatbot error: {error_msg}\n{traceback.format_exc()}")
            return f"Xin lỗi, đã xảy ra lỗi: {str(e)}"

    async def astream(self, question: str, session_id: str = "default") -> AsyncIterator[str]:
        if not question.strip():
            yield "Vui lòng nhập câu hỏi hợp lệ."
            return

        # Fallback: nếu không có dữ liệu nội bộ, trả lời trực tiếp và giả lập streaming
        if not self.settings.docs_exist:
            try:
                answer = self._ask_openai_direct(question)
                # stream theo từ để UX tương tự
                for tok in answer.split():
                    yield tok + " "
                self._append_history(session_id, question, answer)
                return
            except Exception as e:  # noqa: BLE001
                yield f"Lỗi gọi OpenAI: {str(e)}"
                return

        chain = self.build_chain(session_id=session_id)
        handler = AsyncIteratorCallbackHandler()
        streaming_llm = self._create_llm(streaming=True, callbacks=[handler])
        original_llm = chain.llm_chain.llm
        chain.llm_chain.llm = streaming_llm

        task = asyncio.create_task(chain.acall({"question": question}))
        try:
            async for token in handler.aiter():
                if token:
                    yield token
            await task
        finally:
            chain.llm_chain.llm = original_llm

    def _create_llm(self, *, streaming: bool = False, callbacks: Optional[list] = None) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.settings.chat_model,
            temperature=self.settings.chat_temperature,
            api_key=self.settings.openai_api_key,
            streaming=streaming,
            callbacks=callbacks or [],
            max_tokens=self.settings.max_tokens,
            timeout=self.settings.llm_timeout,
            max_retries=self.settings.llm_max_retries,
        )

    def _ask_openai_direct(self, question: str) -> str:
        """Gọi trực tiếp OpenAI Chat Completions khi không có docs nội bộ.

        Sử dụng model từ biến môi trường (OPENAI_MODEL) và endpoint
        https://api.openai.com/v1/chat/completions.
        """
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.chat_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Bạn là trợ lý tổng quát, trả lời ngắn gọn, rõ ràng,"
                        " cung cấp ví dụ khi hữu ích."
                    ),
                },
                {"role": "user", "content": question},
            ],
        }
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    def _append_history(self, session_id: str, question: str, answer: str) -> None:
        """Ghi lịch sử vào file để UI hiển thị lại trong sidebar."""
        history_dir = Path("data/chat_history")
        history_dir.mkdir(parents=True, exist_ok=True)
        file_path = history_dir / f"{session_id}.json"
        chat_history = FileChatMessageHistory(str(file_path))
        chat_history.add_user_message(question)
        chat_history.add_ai_message(answer)


def _build_prompt() -> ChatPromptTemplate:
    """Friendly, context-aware prompt that highlights company style."""

    system_message = (
        "Bạn là trợ lý chăm sóc khách hàng của một công ty SaaS. "
        "Nhiệm vụ của bạn là hỗ trợ khách hàng dựa trên tài liệu được cung cấp. "
        "\n\n"
        "Dưới đây là nội dung từ tài liệu nội bộ:\n"
        "---------------------\n"
        "{context}\n"
        "---------------------\n\n"
        "HƯỚNG DẪN TRẢ LỜI:\n"
        "1. Ưu tiên số 1: Sử dụng thông tin từ tài liệu nội bộ ở trên để trả lời.\n"
        "2. Nếu tài liệu KHÔNG chứa câu trả lời: Bạn ĐƯỢC PHÉP và KHUYẾN KHÍCH sử dụng kiến thức chung của mình để trả lời.\n"
        "3. Tuyệt đối KHÔNG trả lời 'Tôi không biết' hoặc 'Không tìm thấy thông tin' nếu bạn có thể trả lời bằng kiến thức chung (ví dụ: câu hỏi về thủ đô, kiến thức xã hội, lập trình cơ bản...).\n"
        "4. Luôn trả lời thân thiện và hữu ích."
    )

    # ConversationalRetrievalChain tự động inject chat_history, 
    # nên không cần MessagesPlaceholder ở đây
    from langchain_core.prompts import PromptTemplate
    
    return PromptTemplate.from_template(
        system_message + "\n\nCâu hỏi: {question}"
    )
