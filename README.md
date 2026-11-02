# Estoque API

API HTTP educacional para gerenciar produtos, quantidades e preços com Python e SQLite.
Projeto criado com assistência de IA, pensado para estudo de backend e evolução prática.

## Executar

Requer Python 3.10 ou superior, sem dependências externas.

```sh
python app.py
```

A API escuta somente em `127.0.0.1:8000`. Abra `/health` no navegador para conferir.
O arquivo `estoque.db` é criado na pasta atual. Use `--db outro.db --port 8001`
para escolher outro banco e porta. No Windows, pode usar `py` no lugar de `python`.

## Endpoints

| Método | Caminho | Resultado |
| --- | --- | --- |
| GET | `/health` | Estado da API |
| GET | `/products` | Todos os produtos |
| POST | `/products` | Cria produto (201) |
| GET | `/products/1` | Consulta produto |
| PUT | `/products/1` | Substitui todos os campos |
| DELETE | `/products/1` | Exclui produto (204) |
| GET | `/summary` | Produtos, unidades e valor total em centavos |

POST e PUT exigem `Content-Type: application/json` e o corpo:

```json
{"name":"Caderno","quantity":3,"price_cents":1250}
```

Preços usam centavos inteiros: `1250` equivale a R$ 12,50. Isso evita erros de
arredondamento comuns ao representar dinheiro com ponto flutuante.
`quantity` e `price_cents` aceitam inteiros de 0 a 1 bilhão; booleanos são rejeitados.
Nomes devem ter entre 1 e 120 caracteres. O corpo tem limite de 16 KiB.

Exemplo no PowerShell:

```powershell
$produto = @{ name = "Caderno"; quantity = 3; price_cents = 1250 } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/products -Method Post -ContentType "application/json" -Body $produto
Invoke-RestMethod -Uri http://127.0.0.1:8000/products
Invoke-RestMethod -Uri http://127.0.0.1:8000/summary
```

Entradas inválidas retornam 400; produtos ou rotas inexistentes, 404; métodos
incompatíveis nas rotas de produtos, 405; falhas SQLite, 503.

## Testes

```sh
python -m unittest discover -s tests -v
```

Os testes iniciam um servidor HTTP real em porta temporária e verificam o ciclo
de cadastro, consulta, atualização, exclusão, resumo, validação e persistência.

## Decisões e limites

- Consultas SQL parametrizadas e restrições no banco protegem a integridade.
- Conexões independentes por operação atendem às threads do servidor.
- PUT substitui o produto; não existe atualização parcial nem movimentação de estoque.
- Não há autenticação, HTTPS, paginação, rate limiting ou trilha de auditoria.
- `http.server` é usado para aprender HTTP; este projeto não é um servidor de produção.
- Não exponha a API à internet nem use dados reais de clientes.

## Próximas evoluções para estudar

Adicionar movimentações de entrada e saída em transações, paginação, documentação
OpenAPI e autenticação em um framework de produção.
Para apresentar no currículo, estude o fluxo HTTP → validação → SQLite → resposta
e implemente uma evolução própria com testes.
