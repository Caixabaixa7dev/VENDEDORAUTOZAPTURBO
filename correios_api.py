import aiohttp
from typing import Optional

BASE_URL = "https://api.correios.com.br"


async def calcular_frete(
    cep_origem: str,
    cep_destino: str,
    peso_kg: float,
    comprimento_cm: float = 35,
    altura_cm: float = 15,
    largura_cm: float = 25,
    valor_declarado: float = 100.0,
) -> Optional[dict]:
    cep_origem = cep_origem.replace("-", "").strip()
    cep_destino = cep_destino.replace("-", "").strip()

    if len(cep_destino) != 8 or not cep_destino.isdigit():
        return None

    servicos = ["04014", "04510"]
    results = []

    async with aiohttp.ClientSession() as session:
        for servico in servicos:
            payload = {
                "cepOrigem": cep_origem,
                "cepDestino": cep_destino,
                "peso": str(peso_kg),
                "formato": 1,
                "comprimento": str(comprimento_cm),
                "altura": str(altura_cm),
                "largura": str(largura_cm),
                "valorDeclarado": valor_declarado,
                "servico": servico,
                "prazoEntrega": 0,
            }
            headers = {"Content-Type": "application/json"}
            try:
                async with session.post(f"{BASE_URL}/frete/v1/calcular", json=payload, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results.append(data)
            except Exception:
                continue

    if not results:
        return _calcular_frete_fallback(cep_destino, peso_kg)

    best = min(results, key=lambda r: float(r.get("valor", "999")))
    return {
        "valor": float(best.get("valor", 0)),
        "prazo": int(best.get("prazo", 10)),
        "servico": "SEDEX" if servicos[0] == "04014" else "PAC",
    }


def _calcular_frete_fallback(cep_destino: str, peso_kg: float) -> dict:
    valor_base = 19.90 if peso_kg <= 0.5 else 24.90 if peso_kg <= 1 else 29.90 if peso_kg <= 2 else 39.90
    prazo = 7 if peso_kg > 2 else 5
    return {
        "valor": valor_base,
        "prazo": prazo,
        "servico": "PAC",
    }


def format_frete_info(frete: dict) -> str:
    if not frete:
        return "📦 *Frete não disponível para este CEP*"
    return (
        f"📦 *Frete disponível:*\n"
        f"• Serviço: {frete.get('servico', 'PAC')}\n"
        f"• Valor: R$ {frete['valor']:.2f}\n"
        f"• Prazo: {frete['prazo']} dias úteis\n"
    )
