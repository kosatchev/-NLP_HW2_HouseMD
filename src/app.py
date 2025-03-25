from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from transformers import GPT2Tokenizer, GPT2LMHeadModel
import logging
from functools import lru_cache
from pathlib import Path
from typing import Tuple
import asyncio

# ======================
# Конфигурация приложения
# ======================
class AppConfig:
    MODEL_DIR = Path("./models/")
    STATIC_DIR = Path("static")
    TEMPLATES_DIR = Path("templates")
    
    MODEL_PARAMS = {
        "max_new_tokens": 50,
        "temperature": 0.7,
        "top_p": 0.9,
        "repetition_penalty": 1.2,
        "pad_token_id": None,
    }
    MAX_CONCURRENT_REQUESTS = 5  # Лимит одновременных запросов

# ================
# Инициализация API
# ================
app = FastAPI(title="AI Chat Assistant")
app.mount("/static", StaticFiles(directory=AppConfig.STATIC_DIR), name="static")

# Семафор для ограничения одновременных запросов
request_semaphore = asyncio.Semaphore(AppConfig.MAX_CONCURRENT_REQUESTS)

# ================
# Логирование
# ================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ===================
# Модель и обработка данных
# ===================
class ChatRequest(BaseModel):
    message: str

@lru_cache(maxsize=None)
def load_model_resources() -> Tuple[GPT2LMHeadModel, GPT2Tokenizer]:
    """Загружает модель и токенизатор (синхронная операция)"""
    try:
        logger.info("Loading model and tokenizer...")
        
        model_path = AppConfig.MODEL_DIR / "Gpt-model"
        tokenizer_path = AppConfig.MODEL_DIR / "Gpt-tokenizer"

        tokenizer = GPT2Tokenizer.from_pretrained(
            tokenizer_path,
            padding_side='left'
        )
        
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = GPT2LMHeadModel.from_pretrained(model_path)
        model.eval()
        
        AppConfig.MODEL_PARAMS["pad_token_id"] = tokenizer.eos_token_id

        logger.info("Model and tokenizer successfully loaded")
        return model, tokenizer

    except Exception as e:
        logger.error(f"Model loading failed: {str(e)}")
        raise RuntimeError(f"Model loading error: {str(e)}")

async def async_generate_answer(context: str) -> str:
    """Асинхронная генерация ответа"""
    try:
        model, tokenizer = load_model_resources()
        
        # Выполняем синхронные операции в отдельном потоке
        loop = asyncio.get_running_loop()
        
        # Токенизация
        inputs = await loop.run_in_executor(
            None,
            lambda: tokenizer(
                context,
                return_tensors="pt",
                truncation=True,
                max_length=tokenizer.model_max_length - AppConfig.MODEL_PARAMS["max_new_tokens"]
            )
        )
        
        # Генерация
        outputs = await loop.run_in_executor(
            None,
            lambda: model.generate(
                inputs.input_ids,
                **AppConfig.MODEL_PARAMS
            )
        )
        
        # Декодирование
        full_response = await loop.run_in_executor(
            None,
            lambda: tokenizer.decode(outputs[0], skip_special_tokens=True)
        )
        
        return full_response.split(context)[-1].strip()

    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        raise

# ===================
# Маршруты API
# ===================
@app.get("/", response_class=HTMLResponse)
async def serve_interface():
    """Обслуживает главную страницу интерфейса"""
    try:
        index_path = AppConfig.TEMPLATES_DIR / "index.html"
        with open(index_path, "r") as file:
            return HTMLResponse(content=file.read())
    except FileNotFoundError:
        error_message = "<h1>Error: Template file not found</h1>"
        return HTMLResponse(content=error_message, status_code=500)

@app.post("/chat")
async def process_chat_request(request: ChatRequest):
    """Обрабатывает запросы чата с ограничением одновременных запросов"""
    async with request_semaphore:
        try:
            context = request.message.strip()
            if not context:
                raise HTTPException(
                    status_code=400,
                    detail="Empty request: Please provide a message"
                )

            response = await async_generate_answer(context)
            return {"response": response}

        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Request processing failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error: Please try again later"
            )

# ===================
# Запуск приложения
# ===================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8008,
        log_config=None
    )
    