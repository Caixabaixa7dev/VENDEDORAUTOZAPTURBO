from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Product, ProductVariant

PRODUTOS = [
    {
        "sku": "CAM-OVS-PRE",
        "nome": "Camiseta Oversized Preta",
        "descricao": "Camiseta oversized em algodão penteado 250g/m². Modelagem soltinha, ombro a ombro. Ideal para looks streetwear.",
        "preco": 89.90,
        "categoria": "Camisetas",
        "subcategoria": "Oversized",
        "cores": ["Preta", "Branca", "Cinza Mescla"],
        "tamanhos": ["P", "M", "G", "GG", "XGG"],
    },
    {
        "sku": "CAM-OVS-BRA",
        "nome": "Camiseta Oversized Branca",
        "descricao": "Camiseta oversized branca em algodão penteado 250g/m². Modelagem soltinha. Atemporal e versátil.",
        "preco": 89.90,
        "categoria": "Camisetas",
        "subcategoria": "Oversized",
        "cores": ["Branca", "Preta", "Cinza Mescla"],
        "tamanhos": ["P", "M", "G", "GG", "XGG"],
    },
    {
        "sku": "CAM-BAS-PRE",
        "nome": "Camiseta Básica Preta",
        "descricao": "Camiseta básica preta em algodão fio 30. Modelagem regular, confortável para o dia a dia.",
        "preco": 59.90,
        "categoria": "Camisetas",
        "subcategoria": "Básica",
        "cores": ["Preta", "Branca", "Cinza", "Marinha"],
        "tamanhos": ["P", "M", "G", "GG", "XGG"],
    },
    {
        "sku": "CAM-BAS-BRA",
        "nome": "Camiseta Básica Branca",
        "descricao": "Camiseta básica branca em algodão fio 30. Modelagem regular, essencial no guarda-roupa.",
        "preco": 59.90,
        "categoria": "Camisetas",
        "subcategoria": "Básica",
        "cores": ["Branca", "Preta", "Cinza", "Marinha"],
        "tamanhos": ["P", "M", "G", "GG", "XGG"],
    },
    {
        "sku": "CAM-REG-PRE",
        "nome": "Camiseta Regata Preta",
        "descricao": "Regata preta em algodão fio 30. Modelagem regular, ideal para looks casuais e dias quentes.",
        "preco": 49.90,
        "categoria": "Regatas",
        "subcategoria": "Básica",
        "cores": ["Preta", "Branca", "Cinza"],
        "tamanhos": ["P", "M", "G", "GG"],
    },
    {
        "sku": "CAM-REG-BRA",
        "nome": "Camiseta Regata Branca",
        "descricao": "Regata branca em algodão fio 30. Modelagem regular, confortável e versátil.",
        "preco": 49.90,
        "categoria": "Regatas",
        "subcategoria": "Básica",
        "cores": ["Branca", "Preta", "Cinza"],
        "tamanhos": ["P", "M", "G", "GG"],
    },
    {
        "sku": "CAL-JOG-PRE",
        "nome": "Calça Jogger Preta",
        "descricao": "Calça jogger preta em moletom 300g/m². Cintura elástica com cordão, punhos justos. Conforto máximo.",
        "preco": 119.90,
        "categoria": "Calças",
        "subcategoria": "Jogger",
        "cores": ["Preta", "Cinza", "Marinha"],
        "tamanhos": ["P", "M", "G", "GG", "XGG"],
    },
    {
        "sku": "CAL-JOG-CIN",
        "nome": "Calça Jogger Cinza",
        "descricao": "Calça jogger cinza em moletom 300g/m². Cintura elástica com cordão. Perfeita para looks urbanos.",
        "preco": 119.90,
        "categoria": "Calças",
        "subcategoria": "Jogger",
        "cores": ["Cinza", "Preta", "Marinha"],
        "tamanhos": ["P", "M", "G", "GG", "XGG"],
    },
    {
        "sku": "CAL-BER-PRE",
        "nome": "Calça Bermuda Preta",
        "descricao": "Bermuda preta em sarja 240g/m². Modelagem regular, 3 bolsos. Ideal para dias quentes.",
        "preco": 79.90,
        "categoria": "Calças",
        "subcategoria": "Bermuda",
        "cores": ["Preta", "Verde Militar", "Bege"],
        "tamanhos": ["P", "M", "G", "GG"],
    },
    {
        "sku": "CONJ-MOL-PRE",
        "nome": "Conjunto Moletom Preto",
        "descricao": "Conjunto completo: jaqueta + calça moletom preto 320g/m². Frio interno. Look completo e estiloso.",
        "preco": 199.90,
        "categoria": "Conjuntos",
        "subcategoria": "Moletom",
        "cores": ["Preto", "Cinza", "Marinho"],
        "tamanhos": ["P", "M", "G", "GG", "XGG"],
    },
    {
        "sku": "CONJ-MOL-CIN",
        "nome": "Conjunto Moletom Cinza",
        "descricao": "Conjunto completo: jaqueta + calça moletom cinza 320g/m². Frio interno. Conforto e estilo.",
        "preco": 199.90,
        "categoria": "Conjuntos",
        "subcategoria": "Moletom",
        "cores": ["Cinza", "Preto", "Marinho"],
        "tamanhos": ["P", "M", "G", "GG", "XGG"],
    },
    {
        "sku": "CONJ-SEL-PRE",
        "nome": "Conjunto Seleção Preta",
        "descricao": "Conjunto de moletom preto com detalhes em vermelho. Jaqueta + calça. Estilo brasileiro.",
        "preco": 179.90,
        "categoria": "Conjuntos",
        "subcategoria": "Seleção",
        "cores": ["Preta", "Verde", "Amarela"],
        "tamanhos": ["P", "M", "G", "GG"],
    },
    {
        "sku": "MOL-COM-PRE",
        "nome": "Moletom Canguru Preto",
        "descricao": "Moletom canguru preto 300g/m² com capuz e bolso frontal. Algodão penteado, toque macio.",
        "preco": 139.90,
        "categoria": "Moletons",
        "subcategoria": "Canguru",
        "cores": ["Preto", "Cinza", "Marinho", "Vinho"],
        "tamanhos": ["P", "M", "G", "GG", "XGG"],
    },
    {
        "sku": "MOL-COM-CIN",
        "nome": "Moletom Canguru Cinza",
        "descricao": "Moletom canguru cinza 300g/m² com capuz e bolso frontal. Conforto térmico e estilo.",
        "preco": 139.90,
        "categoria": "Moletons",
        "subcategoria": "Canguru",
        "cores": ["Cinza", "Preto", "Marinho", "Vinho"],
        "tamanhos": ["P", "M", "G", "GG", "XGG"],
    },
    {
        "sku": "CAM-LIN-BRA",
        "nome": "Camisa Linho Branca",
        "descricao": "Camisa social em linho branco. Modelagem slim, ideal para eventos e trabalho. Fresca e elegante.",
        "preco": 149.90,
        "categoria": "Camisas",
        "subcategoria": "Linho",
        "cores": ["Branca", "Azul Claro", "Rosa Claro"],
        "tamanhos": ["P", "M", "G", "GG", "XGG"],
    },
    {
        "sku": "CAM-POL-PRE",
        "nome": "Camisa Polo Preta",
        "descricao": "Camisa polo preta em algodão piquet 220g/m². Gola polo com botões. Elegância casual.",
        "preco": 99.90,
        "categoria": "Camisas",
        "subcategoria": "Polo",
        "cores": ["Preta", "Branca", "Azul Marinho", "Verde"],
        "tamanhos": ["P", "M", "G", "GG", "XGG"],
    },
    {
        "sku": "BONÉ-ABA-PRE",
        "nome": "Boné Aba Reta Preto",
        "descricao": "Boné aba reta preto em poliéster 100%. Fecho ajustável. Estilo streetwear.",
        "preco": 49.90,
        "categoria": "Acessórios",
        "subcategoria": "Bonés",
        "cores": ["Preto", "Branco", "Cinza", "Vermelho"],
        "tamanhos": ["Único"],
    },
    {
        "sku": "TOUCA-PRE",
        "nome": "Touca Preta",
        "descricao": "Touca preta em tricot acrílico. Modelagem justa. Ideal para looks de inverno.",
        "preco": 34.90,
        "categoria": "Acessórios",
        "subcategoria": "Toucas",
        "cores": ["Preta", "Cinza", "Marinha", "Vermelha"],
        "tamanhos": ["Único"],
    },
    {
        "sku": "MEIA-3P-PRE",
        "nome": "Kit 3 Pares Meias Pretas",
        "descricao": "Kit 3 pares de meias cano médio preta. Algodão confortável. Tamanho único.",
        "preco": 29.90,
        "categoria": "Acessórios",
        "subcategoria": "Meias",
        "cores": ["Preto", "Branco"],
        "tamanhos": ["Único"],
    },
    {
        "sku": "SHORT-JEAN-AZU",
        "nome": "Shorts Jeans Azul",
        "descricao": "Shorts jeans azul claro. Modelagem regular, 5 bolsos. Ideal para o verão.",
        "preco": 89.90,
        "categoria": "Calças",
        "subcategoria": "Shorts",
        "cores": ["Azul Claro", "Azul Escuro", "Preto"],
        "tamanhos": ["38", "40", "42", "44", "46"],
    },
]


async def seed_database(session: AsyncSession):
    from sqlalchemy import func

    result = await session.execute(select(func.count()).select_from(Product))
    count = result.scalar()

    if count > 0:
        return

    for prod_data in PRODUTOS:
        cores = prod_data.pop("cores")
        tamanhos = prod_data.pop("tamanhos")
        product = Product(**prod_data)
        session.add(product)
        await session.flush()

        for cor in cores:
            for tamanho in tamanhos:
                variant = ProductVariant(
                    product_id=product.id,
                    cor=cor,
                    tamanho=tamanho,
                    estoque=50,
                )
                session.add(variant)

    await session.commit()
