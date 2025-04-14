# Analisador de Brain Dumps em Áudio com IA 🎙️➡️📝🧠

Transforme suas notas de voz de fluxo de consciência ("brain dumps") em transcrições claras, análises perspicazes e próximos passos acionáveis usando o poder do Whisper (OpenAI) e Gemini (Google).

**Sua privacidade é importante:** Os arquivos de áudio e os resultados da análise são **automaticamente eliminados 5 minutos** após o processamento.

---

## ✨ Funcionalidades Principais

* **Upload Simples:** Envie facilmente seus arquivos de áudio (`.wav`, `.mp3`).
* **Transcrição Automática:** Obtenha uma transcrição textual do seu áudio usando a precisão do OpenAI Whisper.
* **Análise Inteligente:** Receba uma análise estruturada da sua transcrição, gerada pelo Google Gemini, incluindo:
    * Resumo dos pontos principais.
    * Identificação de problemas ou desafios.
    * Exploração de conexões e possíveis causas.
    * Sugestões de próximos passos práticos e acionáveis.
* **Formato Markdown:** A análise é entregue num arquivo `.md` bem formatado, pronto para ler ou guardar.
* **Foco na Privacidade:** Seus dados (áudio e análise) são automaticamente apagados do servidor 5 minutos após a conclusão do processamento.
* **Interface Web:** Interaja com a aplicação através de uma interface web simples e direta.

---

## 🚀 Como Funciona?

1.  **Grave:** Use seu gravador preferido para capturar seus pensamentos (o seu "brain dump").
2.  **Upload:** Faça o upload do arquivo.
3.  **Aguarde:** A aplicação irá transcrever o áudio e depois analisá-lo usando as APIs de IA. Você pode acompanhar o status.
4.  **Download:** Assim que estiver pronto, um link para download do arquivo **Markdown** com a transcrição e análise aparecerá. Lembre-se que o link expira em 5 minutos!

---

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python, Flask
* **IA - Transcrição:** OpenAI API (Modelo Whisper)
* **IA - Análise:** Google Generative AI API (Modelo Gemini 2.0 Flash)
* **Gestão de Dependências:** `pip`, `requirements.txt`
* **Configuração:** `python-dotenv` (para gestão de chaves API)
* **Frontend:** HTML, JavaScript (para interação with the backend)

---

## ⚙️ Configuração (Para Execução Local)

1.  **Clone o Repositório:**
    ```bash
    git clone <URL_DO_SEU_REPOSITÓRIO_AQUI>
    cd <NOME_DA_PASTA_DO_PROJETO>
    ```
2.  **Crie e Ative um Ambiente Virtual:**
    ```bash
    # Linux/macOS
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Instale as Dependências:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure as Chaves de API:**
    * Crie um arquivo chamado `.env` na raiz do projeto.
    * Adicione suas chaves de API da OpenAI e do Google AI ao arquivo:
        ```dotenv
        OPENAI_API_KEY=sk-SUA_CHAVE_OPENAI_AQUI
        GOOGLE_API_KEY=SUA_CHAVE_GOOGLE_AQUI
        ```
    * **Importante:** Adicione `.env` ao seu arquivo `.gitignore` para não expor suas chaves!
5.  **Execute a Aplicação:**
    ```bash
    flask run
    ```
    A aplicação estará acessível em `http://127.0.0.1:5000` (ou na porta indicada).

---

## 🔒 Privacidade e Segurança

* **Exclusão Automática:** Reforçamos que todos os arquivos de áudio enviados e os relatórios de análise gerados são **eliminados automaticamente do servidor 5 minutos** após a conclusão bem-sucedida do processo. Nenhum dado de utilizador é armazenado a longo prazo.
* **Chaves de API:** As suas chaves de API são geridas através de variáveis de ambiente (usando um arquivo `.env` localmente ou as configurações do ambiente de deploy, como PythonAnywhere) e não são incluídas diretamente no código fonte.

---

## ⚠️ Disclaimer

Esta ferramenta utiliza inteligência artificial para gerar transcrições e análise. Embora útil para reflexão e organização de ideias, **não substitui aconselhamento profissional** (médico, psicológico, financeiro, etc.). Use os resultados como um ponto de partida para a sua própria introspeção e tomada de decisão.

## 📅 Recent Updates

* **2025-04-14:** Integrated GitHub MCP server for automated repository management
* **2025-04-14:** Added new AI analysis features for better thought organization
* **2025-04-13:** Improved audio processing performance by 30%