# Báo cáo xây dựng chatbot hỗ trợ khách hàng

## Mục tiêu
- Chatbot trả lời câu hỏi về sản phẩm/dịch vụ của công ty giả định.
- Trích xuất tri thức từ tài liệu nội bộ ở định dạng PDF và DOCX.
- Giữ ngữ cảnh hội thoại và theo dõi qua LangSmith để giám sát chất lượng.
- Cung cấp demo CLI có thể vận hành thực tế, kèm tài liệu báo cáo & nguồn dữ liệu mẫu.

## Kiến trúc tổng thể
1. **Tầng cấu hình** (`config.py`): nạp biến môi trường (.env), kiểm tra khóa bắt buộc, map model/temperature, kích hoạt LangSmith tracing (ENV).
2. **Tầng dữ liệu** (`scripts/update_docs.py`, `document_loader.py`): script tạo dữ liệu mẫu cả DOCX/PDF; loader duyệt `data/docs` với `PyPDFLoader` + `Docx2txtLoader`.
3. **Vector store** (`vectorstore.py`): embeddings OpenAI + `FAISS`, kèm hook lưu/persist nếu mở rộng.
4. **Chuỗi hội thoại** (`chatbot.py`): `ConversationalRetrievalChain` + `ConversationBufferMemory` giữ ngữ cảnh, config từ `Settings`.
5. **Demo CLI & observability** (`scripts/demo.py`): vòng lặp chat, cấu hình Typer + Rich, auto-stream trace lên LangSmith.

## Luồng xử lý
```
docs -> loader -> text splitter -> embeddings -> FAISS retriever
      question + chat history -> ConversationalRetrievalChain -> answer
```

## Công nghệ
- **LangChain**: loaders, splitters, vector store, conversational chain.
- **LangChain OpenAI**: ChatOpenAI + embeddings.
- **LangSmith**: thiết lập tracing qua biến môi trường.
- **FAISS**: lưu trữ vector cục bộ, nhanh cho demo.

## Các vấn đề & cách xử lý
| Vấn đề | Cách giải quyết |
| --- | --- |
| Không có sẵn tài liệu nội bộ | Viết `scripts/update_docs.py` để sinh cả DOCX + PDF chứa nội dung giàu ngữ nghĩa. |
| Quản lý khóa API / LangSmith | `.env` template + `Settings` kiểm tra `OPENAI_API_KEY` và tự bật tracing khi có `LANGCHAIN_API_KEY`. |
| Độ trễ phản hồi | Cho phép cấu hình `CHAT_TEMPERATURE`, gợi ý streaming/persist vector store trong README. |
| Bảo toàn ngữ cảnh | Dùng `ConversationBufferMemory` và chuẩn hóa prompt retrieval. |
| Quan sát hành vi | LangSmith tracing tự bật khi chạy demo, xem trực tiếp trên dashboard `mock-support-chatbot`. |

## Kiểm thử
- `tests/test_document_pipeline.py`: tạo PDF/DOCX tạm, verify loader + splitter.
- Khi cần có thể thêm test end-to-end mô phỏng hội thoại (chuẩn bị sẵn hạ tầng pytest).

## Hướng dẫn vận hành
1. `uv sync` (hoặc `pip install -e .`).
2. Chạy `uv run python -m scripts.update_docs` để tạo dữ liệu mẫu hoặc thả tài liệu thật vào `data/docs`.
3. Điền khóa OpenAI + LangSmith + (tùy chọn) `CHAT_TEMPERATURE` trong `.env`.
4. `uv run python -m scripts.demo` và theo dõi trace ở https://smith.langchain.com (project `mock-support-chatbot`).

## Hướng mở rộng
- Persist FAISS hoặc chuyển sang Pinecone/Chroma server để khởi động nhanh hơn.
- Tích hợp công cụ thao tác ticket/calendar qua LangChain tool-calling.
- Đổi model sang Azure OpenAI / Anthropic nếu cần compliance.
- Xây dựng UI web (FastAPI + React) và bổ sung streaming để cải thiện UX.


