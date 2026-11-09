# LivroLivre

Controle de acervo, leitores, empréstimos, devoluções e prazos de uma biblioteca de pequeno porte.

## Executar

1. Extraia todo o pacote para uma pasta em que você possa gravar arquivos.
2. Com Python 3.11 ou superior e Tcl/Tk instalados, abra esta pasta no PyCharm e execute `main.py` com o interpretador Python do projeto.
3. Na primeira execução, o SQLite cria `livrolivre.db` ao lado de `main.py`. Nas próximas, o programa recupera os registros desse mesmo arquivo.

No terminal, também é possível rodar `py -3 main.py` ou `python main.py`. `py -3 -m tkinter` verifica se o Tkinter está disponível. O aplicativo usa módulos da biblioteca padrão do Python.

## Conferir com dados fictícios

1. Em **Acervo**, cadastre **A Máquina do Tempo**, de **H. G. Wells**, gênero **Ficção**, ano **1895**, com **2 exemplares**.
2. Em **Leitores**, cadastre **Leitora de demonstração**, contato **leitora@example.com**.
3. Em **Empréstimos**, selecione a leitora, o título e **EX-0001** em um banco novo. Mantenha o prazo sugerido e clique em **Registrar**.
4. Em **Acervo**, confira **1 disponível**. Volte a **Empréstimos** e tente registrar a mesma cópia outra vez. O programa deve recusar a operação e manter uma única linha no histórico.
5. Selecione a linha e clique em **Registrar devolução**. O histórico deve exibir **Devolvido** e o acervo, **2 disponíveis**.
6. Feche e reabra o programa. Os registros devem aparecer novamente.

Para usar um banco separado, execute `py -3 main.py --banco demonstracao.db`. Escolha outro nome de arquivo quando quiser repetir o cenário desde o início.

## Regras

- Cada exemplar tem um código e admite um empréstimo ativo por vez.
- O prazo deve ser uma data válida no formato dia/mês/ano, igual ou posterior à retirada. A janela sugere sete dias.
- Atraso começa no dia seguinte ao vencimento. Use o filtro do histórico e o botão **Atualizar**.
- O acervo pode ser buscado por título, autor ou gênero, inclusive sem acentos. **Só disponíveis** exibe títulos com pelo menos uma cópia livre.
- A devolução libera o exemplar e conserva a linha no histórico.

## Código e testes

| Arquivo | Responsabilidade |
|---|---|
| `main.py` | Janela, formulários, tabelas, mensagens e navegação |
| `biblioteca.py` | Validação, regras de circulação e gravação no SQLite |
| `test_biblioteca.py` | Cenários T01 a T11 da lógica e do banco |
| `test_interface.py` | Cenário T12 na janela real do Tkinter |

Execute `py -3 -m unittest -v` a partir desta pasta. A interface requer um ambiente gráfico com Tkinter. Para rodar apenas os testes do banco, use `py -3 -m unittest -v test_biblioteca`. Os testes usam bancos temporários independentes do banco de uso.

## Demonstração rápida

Execute **demonstracao.py** no PyCharm para iniciar uma sessão separada com duas cópias disponíveis de *A Máquina do Tempo*, uma leitora fictícia e um empréstimo vencido de outro título. Na aba **Empréstimos**, selecione **Em atraso** para conferir o filtro. Essa sessão começa de novo a cada abertura. Para demonstrar a persistência, use o banco separado indicado no passo a passo acima.
