import os
import asyncio
import aiohttp
from typing import Optional

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://api.nvidia.com/v1")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3-8b-instruct")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

SYSTEM_PROMPT = """Você é o atendente virtual da ZAPTURBO, uma loja de moda masculina brasileira.
Seu papel é ATENDER e VENDER — seja natural, educado e persuasivo como um bom vendedor.

TOM DE VOZ:
- Português brasileiro natural e informal
- Use emojis com moderação (😊👍✅)
- Seja solícito e proativo em ajudar
- Trate o cliente pelo nome quando souber

FLUXO DE VENDA:
1. Descubra o que o cliente procura (peça, cor, tamanho)
2. Ofereça opções específicas com preços
3. Confirme os itens, cores e tamanhos
4. Some o valor e incentive a compra
5. Após pagamento, colete endereço e CEP para frete
6. Confirme o pedido e dê prazo de entrega

REGRAS IMPORTANTES:
- NUNCA invente preços ou produtos — use as funções de busca
- Se perguntarem sobre algo fora do catálogo, diga que não tem disponível
- Para calcular frete, peça o CEP
- Ofereça frete grátis acima de R$ 199,00
- Se o cliente pedir algo que você não pode resolver, chame o administrador
- NÃO peça dados sensíveis (CPF, senha, cartão)
- Seja paciente com clientes indecisos
- SEMPRE tente finalizar a venda

PRODUTOS DISPONÍVEIS:
Consulte via função buscar_produtos"""


def _get_config() -> dict:
    if LLM_PROVIDER == "nvidia":
        return {
            "api_key": NVIDIA_API_KEY,
            "model": NVIDIA_MODEL,
            "base_url": NVIDIA_BASE_URL,
            "name": "NVIDIA",
        }
    return {
        "api_key": OPENROUTER_API_KEY,
        "model": OPENROUTER_MODEL,
        "base_url": OPENROUTER_BASE_URL,
        "name": "OpenRouter",
    }


async def process_message(
    message: str,
    history: list[dict],
    phone: str,
    customer_name: Optional[str] = None,
) -> str:
    cfg = _get_config()

    if not cfg["api_key"]:
        return f"⚠️ Atendente offline (chave {cfg['name']} não configurada). Tente novamente mais tarde."

    messages = [_build_system_prompt(customer_name)]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": message})

    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500,
    }

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    if cfg["name"] == "OpenRouter":
        headers["HTTP-Referer"] = "https://zapturbo.onrender.com"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{cfg['base_url']}/chat/completions",
                json=payload,
                headers=headers,
                timeout=30,
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return f"⚠️ Erro no atendimento: serviço temporariamente indisponível. Tente novamente!"

                data = await resp.json()
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                return content
    except asyncio.TimeoutError:
        return "⏳ Estou processando sua solicitação... Pode repetir?"
    except Exception:
        return "⚠️ Falha na comunicação. Tente novamente em instantes."


def _build_system_prompt(customer_name: Optional[str] = None) -> dict:
    prompt = SYSTEM_PROMPT
    if customer_name:
        prompt = f"ATENDENDO: {customer_name}\n\n" + prompt
    return {"role": "system", "content": prompt}
