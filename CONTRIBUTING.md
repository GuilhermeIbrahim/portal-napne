# Contribuindo com o Portal NAPNE

Obrigado por contribuir com o Portal NAPNE! Este documento descreve como o repositório é organizado e como o trabalho deve ser registrado e desenvolvido, para que toda a equipe siga o mesmo padrão.

## Sumário

1. [Antes de começar](#antes-de-começar)
2. [Como reportar um problema ou sugerir uma melhoria](#como-reportar-um-problema-ou-sugerir-uma-melhoria)
3. [Labels](#labels)
4. [Convenção de branches](#convenção-de-branches)
5. [Enviando uma alteração (Pull Request)](#enviando-uma-alteração-pull-request)
6. [Acompanhamento do trabalho](#acompanhamento-do-trabalho)
7. [Configurando o ambiente local](#configurando-o-ambiente-local)
8. [O que não deve ser versionado](#o-que-não-deve-ser-versionado)

---

## Antes de começar

- A única branch permanente do projeto é a `main`.
- Toda issue que resultar em criação, alteração ou remoção de arquivos do repositório deve ser desenvolvida em uma branch própria, criada a partir da `main`.
- Nem toda issue precisa gerar uma branch: atividades como estudos, pesquisas ou discussões que não alteram arquivos do projeto podem ser concluídas sem a criação de uma branch.

## Como reportar um problema ou sugerir uma melhoria

Todo o trabalho é registrado como **issue**. Não abra uma issue em branco: utilize um dos formulários disponíveis em **Issues → New issue**:

| Tipo de trabalho | Formulário            | Label aplicada automaticamente |
| ----------------- | ---------------------- | ------------------------------- |
| Funcionalidade     | `Funcionalidade`       | `enhancement`                   |
| Bug                | `Bug`                  | `bug`                            |
| Tarefa técnica     | `Tarefa técnica`       | `task`                           |

- **Funcionalidade**: descreva o objetivo (papel, ação e benefício) e liste critérios de aceitação objetivos e verificáveis. Inclua o link do protótipo/Figma quando existir.
- **Bug**: descreva o problema, os passos para reproduzi-lo, o comportamento esperado e o comportamento observado. Anexe evidências (mensagens de erro, prints, vídeos) sempre que possível.
- **Tarefa técnica**: explique o objetivo técnico, a justificativa, o escopo (o que faz e o que não faz parte da tarefa) e os critérios de conclusão.

Depois de criada, cada issue deve receber também as Labels de área ou natureza técnica pertinentes (veja a seção seguinte) e ser adicionada ao Project da equipe.

## Labels

Toda issue que representa trabalho deve receber **uma, e somente uma**, destas Labels principais:

| Label         | Utilizada quando…                                                | Prefixo da branch |
| ------------- | ------------------------------------------------------------------ | ------------------ |
| `enhancement` | será criada ou melhorada uma funcionalidade                        | `feature/`         |
| `bug`         | será corrigido um erro                                              | `fix/`              |
| `task`        | será realizada uma tarefa técnica (inclusive documentação)          | `task/`             |

Depois, a issue pode receber uma ou mais Labels complementares de área ou natureza técnica, como:

`frontend`, `backend`, `database`, `documentation`, `testing`, `infrastructure`, `security`, `accessibility`, `refactoring`, `technical debt`.

Não crie Labels chamadas `feature` ou `fix` para representar tipo de trabalho — `feature/`, `fix/` e `task/` são **prefixos de branch**, não Labels.

A Label `blocked` indica que a atividade está impedida de prosseguir. Ela é uma condição adicional e não substitui o campo `Status` do Project — um item pode estar `In Progress` e, ao mesmo tempo, bloqueado. Se o bloqueio for causado por outra issue, registre também essa dependência.

## Convenção de branches

Toda branch de trabalho deve ser criada a partir da `main` e seguir o padrão:

```
prefixo/numero-da-issue-descricao-curta
```

O prefixo corresponde à Label principal da issue:

| Label principal | Prefixo    | Exemplo                       |
| ---------------- | ---------- | ------------------------------ |
| `enhancement`    | `feature/` | `feature/23-recuperar-senha`   |
| `bug`             | `fix/`     | `fix/41-corrigir-upload-imagem`|
| `task`            | `task/`    | `task/52-atualizar-django`     |

A barra `/` faz parte do nome da branch — ela **não cria uma pasta** dentro do repositório.

Alterações de documentação também são tratadas como tarefa técnica. Por exemplo, uma issue de documentação recebe as Labels `task` e `documentation`, mas a branch continua usando o prefixo `task/`:

```
task/60-atualizar-documentacao
```

Não serão utilizadas branches `develop`, `release/` ou `hotfix/`. O fluxo do projeto é propositalmente simples: `main` + branches temporárias de trabalho.

## Enviando uma alteração (Pull Request)

1. Crie a branch a partir da `main`, seguindo a convenção acima.
2. Faça as alterações necessárias e realize commits com mensagens claras sobre o que foi feito.
3. Abra um Pull Request para a `main`.
4. No corpo do Pull Request, inclua a expressão que referencia a issue correspondente, por exemplo:

```
Closes #23
```

Isso melhora a rastreabilidade entre branch, Pull Request e issue. O número da issue no nome da branch **não fecha a issue automaticamente** — apenas a expressão `Closes #<número>` no Pull Request faz isso quando ele é integrado à `main`.

5. Solicite a revisão de ao menos um outro integrante da equipe antes de integrar o Pull Request. Enquanto estiver em revisão, mova o item para `In Review` no Project.
6. Somente integre o Pull Request à `main` depois da revisão aprovada e dos critérios de aceitação/conclusão da issue atendidos.

## Acompanhamento do trabalho

O trabalho do repositório é acompanhado pelo Project da equipe. Ao abrir uma issue, adicione-a ao Project e preencha os campos aplicáveis:

- `Status` (`Backlog`, `Sprint Backlog (To do)`, `In Progress`, `In Review`, `Done`);
- `Prioridade` (`Alta`, `Média`, `Baixa`);
- `Esforço` (`P`, `M`, `G`);
- `Sprint`, quando a issue já tiver sido selecionada para uma sprint.

Uma issue nova normalmente entra no `Backlog`. Ela só recebe uma `Sprint` e passa para `Sprint Backlog (To do)` depois do planejamento da sprint pela equipe.

## Configurando o ambiente local

As dependências e os comandos do Django são sempre executados a partir da raiz do repositório:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Antes de rodar o projeto, copie `.env.example` para `.env` e preencha os valores reais das variáveis de ambiente.

## O que não deve ser versionado

Não inclua nos seus commits:

```
.env
venv/
__pycache__/
node_modules/
db.sqlite3
media/
```

Nem qualquer arquivo contendo senhas, tokens, chaves de acesso ou outras credenciais. O repositório deve guardar apenas o `.env.example`, com os nomes das variáveis e valores fictícios.

As **migrações do Django devem ser versionadas** normalmente — elas não entram nessa lista.