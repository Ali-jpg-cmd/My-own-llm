"""
LLM Service for handling different model providers
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Optional imports for free/minimal setup
try:
    import torch  # type: ignore
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline  # type: ignore
except Exception:  # pragma: no cover
    torch = None
    AutoTokenizer = None
    AutoModelForCausalLM = None
    pipeline = None

try:
    import openai  # type: ignore
except Exception:  # pragma: no cover
    openai = None

try:
    import anthropic  # type: ignore
except Exception:  # pragma: no cover
    anthropic = None

try:
    from llama_cpp import Llama  # type: ignore
except Exception:  # pragma: no cover
    Llama = None

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GenerationRequest:
    """Request for text generation"""
    prompt: str
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 0.9
    model: str = "default"
    stop_sequences: Optional[List[str]] = None


@dataclass
class GenerationResponse:
    """Response from text generation"""
    text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model_used: str
    provider: str
    response_time_ms: int
    cost: float = 0.0


class LLMService:
    """Service for handling LLM interactions"""
    
    def __init__(self):
        self.models = {}
        self.tokenizers = {}
        self.pipelines = {}
        self.llamacpp_model: Optional[Llama] = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize available models"""
        try:
            provider = settings.llm_provider.lower()
            if provider == "huggingface":
                self._load_huggingface_model()
            elif provider == "openai":
                self._initialize_openai()
            elif provider == "anthropic":
                self._initialize_anthropic()
            elif provider in ("llamacpp", "llama.cpp", "llama-cpp"):
                self._load_llamacpp_model()
            else:
                logger.warning(f"Unknown LLM provider '{settings.llm_provider}', defaulting to llama.cpp")
                self._load_llamacpp_model()
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
    
    def _load_huggingface_model(self):
        """Load Hugging Face model (requires transformers + torch)"""
        if AutoTokenizer is None or AutoModelForCausalLM is None or pipeline is None:
            raise RuntimeError("transformers/torch not installed. Install them or switch to llama.cpp.")
        try:
            logger.info(f"Loading Hugging Face model: {settings.llm_model}")
            tokenizer = AutoTokenizer.from_pretrained(settings.llm_model, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                settings.llm_model,
                torch_dtype=(torch.float16 if torch is not None else None),
                device_map="auto",
                trust_remote_code=True
            )
            pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device_map="auto")
            self.models["default"] = model
            self.tokenizers["default"] = tokenizer
            self.pipelines["default"] = pipe
            logger.info("Hugging Face model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Hugging Face model: {e}")
            raise

    def _load_llamacpp_model(self):
        """Load llama.cpp model from GGUF path (CPU-only by default, free)."""
        if Llama is None:
            raise RuntimeError("llama-cpp-python not installed. pip install llama-cpp-python")
        model_path = settings.llm_model_path
        if not model_path or not os.path.exists(model_path):
            raise RuntimeError(
                f"llama.cpp model file not found at '{model_path}'. Download a GGUF model and set LLM_MODEL_PATH."
            )
        logger.info(f"Loading llama.cpp model from: {model_path}")
        self.llamacpp_model = Llama(
            model_path=model_path,
            n_ctx=settings.llm_context_size,
            n_gpu_layers=settings.llm_n_gpu_layers,
            n_threads=settings.llm_threads or None,
            verbose=False,
        )
        logger.info("llama.cpp model loaded successfully")

    def _initialize_openai(self):
        """Initialize OpenAI client (optional)"""
        if openai is None:
            raise RuntimeError("openai package not installed. Install it or use llama.cpp for free setup.")
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        openai.api_key = settings.openai_api_key
        logger.info("OpenAI client initialized")
    
    def _initialize_anthropic(self):
        """Initialize Anthropic client (optional)"""
        if anthropic is None:
            raise RuntimeError("anthropic package not installed. Install it or use llama.cpp for free setup.")
        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")
        self.anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        logger.info("Anthropic client initialized")
    
    async def generate_text(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using the specified model"""
        start_time = time.time()
        provider = settings.llm_provider.lower()
        
        if provider == "huggingface":
            response = await self._generate_huggingface(request)
        elif provider == "openai":
            response = await self._generate_openai(request)
        elif provider == "anthropic":
            response = await self._generate_anthropic(request)
        else:
            response = await self._generate_llamacpp(request)
        
        response.response_time_ms = int((time.time() - start_time) * 1000)
        response.cost = self._calculate_cost(response.total_tokens)
        return response
    
    async def _generate_huggingface(self, request: GenerationRequest) -> GenerationResponse:
        if pipeline is None:
            raise RuntimeError("transformers/torch not installed.")
        pipe = self.pipelines.get("default")
        if not pipe:
            raise ValueError("Hugging Face model not loaded")
        tokenizer = self.tokenizers["default"]
        inputs = tokenizer(request.prompt, return_tensors="pt")
        input_tokens = int(inputs.input_ids.shape[1])
        outputs = pipe(
            request.prompt,
            max_new_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
        generated_text = outputs[0]["generated_text"]
        output_text = generated_text[len(request.prompt):]
        output_tokens = len(tokenizer.encode(output_text))
        total_tokens = input_tokens + output_tokens
        return GenerationResponse(
            text=output_text.strip(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            model_used=settings.llm_model,
            provider="huggingface",
            response_time_ms=0,
        )

    async def _generate_llamacpp(self, request: GenerationRequest) -> GenerationResponse:
        if self.llamacpp_model is None:
            self._load_llamacpp_model()
        llm = self.llamacpp_model
        assert llm is not None
        # Tokenize to count input
        input_tokens = len(llm.tokenize(request.prompt.encode("utf-8")))
        result = llm(
            request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=request.stop_sequences or None,
        )
        text = result["choices"][0]["text"]
        output_tokens = len(llm.tokenize(text.encode("utf-8")))
        total_tokens = input_tokens + output_tokens
        model_name = os.path.basename(settings.llm_model_path or "model.gguf")
        return GenerationResponse(
            text=text.strip(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            model_used=model_name,
            provider="llamacpp",
            response_time_ms=0,
        )

    async def _generate_openai(self, request: GenerationRequest) -> GenerationResponse:
        if openai is None:
            raise RuntimeError("openai package not installed.")
        response = openai.ChatCompletion.create(
            model=request.model or "gpt-3.5-turbo",
            messages=[{"role": "user", "content": request.prompt}],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=request.stop_sequences,
        )
        return GenerationResponse(
            text=response.choices[0].message.content,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            model_used=request.model or "gpt-3.5-turbo",
            provider="openai",
            response_time_ms=0,
        )
    
    async def _generate_anthropic(self, request: GenerationRequest) -> GenerationResponse:
        if anthropic is None:
            raise RuntimeError("anthropic package not installed.")
        response = self.anthropic_client.messages.create(
            model=request.model or "claude-3-sonnet-20240229",
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            messages=[{"role": "user", "content": request.prompt}],
        )
        return GenerationResponse(
            text=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            model_used=request.model or "claude-3-sonnet-20240229",
            provider="anthropic",
            response_time_ms=0,
        )
    
    def _calculate_cost(self, total_tokens: int) -> float:
        # Free local setup => cost 0
        return 0.0
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        models: List[Dict[str, Any]] = []
        provider = settings.llm_provider.lower()
        if provider in ("llamacpp", "llama.cpp", "llama-cpp"):
            models.append({
                "id": settings.llm_model_path or "model.gguf",
                "name": "Local GGUF Model (llama.cpp)",
                "provider": "llamacpp",
                "type": "text-generation",
            })
        if provider == "huggingface" and settings.llm_model:
            models.append({
                "id": settings.llm_model,
                "name": "Local LLaMA Model",
                "provider": "huggingface",
                "type": "text-generation",
            })
        if provider == "openai":
            models.extend([
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "openai", "type": "chat"},
            ])
        if provider == "anthropic":
            models.extend([
                {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "provider": "anthropic", "type": "chat"},
            ])
        return models


# Global LLM service instance
llm_service = LLMService()
