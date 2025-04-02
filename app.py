import os
import uuid
import time
import threading
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template_string, send_file, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
import io
import openai # Importa a biblioteca OpenAI
import google.generativeai as genai # Importa a biblioteca Google Generative AI
from dotenv import load_dotenv # Para carregar variáveis de ambiente do .env

# --- Configuração Inicial ---
load_dotenv() # Carrega variáveis do arquivo .env

app = Flask(__name__)

# Configuração do Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "10 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# Configurações da Aplicação
ALLOWED_EXTENSIONS = {'wav', 'mp3'}
MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB
RESULT_EXPIRATION_MINUTES = 15

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Configuração das APIs
openai.api_key = os.getenv("OPENAI_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")

if not openai.api_key:
    print("AVISO: Chave da API OpenAI não encontrada nas variáveis de ambiente (OPENAI_API_KEY). A transcrição falhará.")
if not google_api_key:
     print("AVISO: Chave da API Google não encontrada nas variáveis de ambiente (GOOGLE_API_KEY). A análise LLM falhará.")
else:
    try:
        genai.configure(api_key=google_api_key)
    except Exception as e:
        print(f"Erro ao configurar a API Google Generative AI: {e}")


# --- Armazenamento em Memória ---
tasks = {}
results = {}
data_lock = threading.Lock()

# --- Funções Auxiliares (allowed_file, get_task_status, update_task_status, store_result, get_result, cleanup_expired_data) ---
# (O código destas funções permanece o mesmo da versão anterior - omitido por brevidade, mas deve estar aqui)
# --- Funções Auxiliares ---
def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_task_status(task_id):
    """Obtém o status de uma tarefa de forma segura."""
    with data_lock:
        # Retorna uma cópia para evitar modificações externas inesperadas
        task_data = tasks.get(task_id)
        return task_data.copy() if task_data else None


def update_task_status(task_id, status, message=None, error=None, result_id=None):
    """Atualiza o status de uma tarefa de forma segura."""
    with data_lock:
        if task_id in tasks:
            task = tasks[task_id]
            task['status'] = status
            if message is not None: # Permite limpar a mensagem passando None
                task['message'] = message
            if error is not None: # Permite limpar o erro passando None
                task['error'] = error
            if result_id is not None:
                task['result_id'] = result_id
            if status in ['completed', 'failed']:
                 # Define o tempo de expiração do status da tarefa também (ex: 1 hora após conclusão/falha)
                 task['expires_at'] = datetime.now(timezone.utc) + timedelta(hours=1)
            print(f"Task {task_id} updated: Status={status}, Message={message}, Error={error}") # Log de atualização
        else:
             print(f"Warning: Attempted to update non-existent task {task_id}")


def store_result(result_id, content, filename):
    """Armazena o resultado Markdown de forma segura."""
    with data_lock:
        results[result_id] = {
            'content': content,
            'filename': filename,
            'created_at': datetime.now(timezone.utc)
        }
        print(f"Result {result_id} stored.")


def get_result(result_id):
    """Obtém um resultado e verifica a expiração."""
    with data_lock:
        result_data = results.get(result_id)
        if result_data:
            expiration_time = result_data['created_at'] + timedelta(minutes=RESULT_EXPIRATION_MINUTES)
            if datetime.now(timezone.utc) < expiration_time:
                # Retorna uma cópia
                return result_data.copy()
            else:
                # Resultado expirado, remove
                print(f"Result {result_id} expired. Removing.")
                del results[result_id]
                # Tenta remover a tarefa associada se ainda existir e não estiver processando
                task_to_remove = None
                for task_id, task_info in tasks.items():
                    if task_info.get('result_id') == result_id and task_info.get('status') != 'processing':
                        task_to_remove = task_id
                        break
                if task_to_remove:
                     print(f"Removing associated task {task_to_remove} for expired result {result_id}.")
                     del tasks[task_to_remove]
                return None
        return None


def cleanup_expired_data():
    """Remove tarefas e resultados expirados periodicamente."""
    while True:
        try:
            with data_lock:
                now = datetime.now(timezone.utc)
                # Limpa tarefas expiradas (aquelas cujo status deveria ter sido removido)
                expired_tasks = [task_id for task_id, data in tasks.items()
                                 if data.get('expires_at') and data['expires_at'] < now]
                for task_id in expired_tasks:
                    print(f"Cleaning up expired task status: {task_id}")
                    result_id = tasks[task_id].get('result_id')
                    # O resultado associado já deve ter sido tratado pela lógica de expiração em get_result
                    # Apenas removemos a entrada da tarefa
                    if task_id in tasks: # Verifica se ainda existe
                        del tasks[task_id]

                # Limpa resultados explicitamente expirados (caso get_result não tenha sido chamado)
                expired_results = []
                for result_id, data in results.items():
                     expiration_time = data['created_at'] + timedelta(minutes=RESULT_EXPIRATION_MINUTES)
                     if now >= expiration_time:
                         print(f"Cleanup: Found explicitly expired result {result_id}")
                         expired_results.append(result_id)

                for result_id in expired_results:
                     if result_id in results: # Verifica novamente
                         print(f"Cleanup: Removing expired result {result_id}")
                         del results[result_id]
                         # Remove a tarefa associada se existir e não estiver processando
                         task_to_remove = None
                         for task_id, task_info in tasks.items():
                              if task_info.get('result_id') == result_id and task_info.get('status') != 'processing':
                                   task_to_remove = task_id
                                   break
                         if task_to_remove and task_to_remove in tasks:
                              print(f"Cleanup: Removing associated task {task_to_remove}")
                              del tasks[task_to_remove]

        except Exception as e:
            print(f"Error during cleanup: {e}") # Log do erro

        # Espera um tempo antes da próxima limpeza (ex: 5 minutos)
        time.sleep(300)

# Inicia a thread de limpeza em background
cleanup_thread = threading.Thread(target=cleanup_expired_data, daemon=True)
cleanup_thread.start()


# --- Funções de Processamento (Reais) ---

def transcribe_audio_with_whisper(audio_bytes, original_filename):
    """Transcreve o áudio usando a API Whisper da OpenAI."""
    if not openai.api_key:
        raise ValueError("Chave da API OpenAI não configurada.")

    print(f"Iniciando transcrição Whisper para {original_filename}...")
    try:
        # A API Whisper precisa de um objeto tipo arquivo. Usamos BytesIO.
        # É crucial passar um nome de arquivo com a extensão correta na tupla.
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = original_filename # Atribui nome ao objeto BytesIO

        # Chama a API de transcrição
        # Veja a documentação para mais opções: https://platform.openai.com/docs/api-reference/audio/createTranscription
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file, # Passa o objeto BytesIO diretamente
            response_format="text" # Pede o texto diretamente
            # language="pt" # Opcional: pode tentar forçar o idioma
        )
        print("Transcrição Whisper concluída.")
        # O objeto retornado pode variar, ajuste conforme necessário.
        # Se response_format="text", a resposta deve ser uma string.
        return transcript # Retorna diretamente o texto da transcrição

    except openai.APIError as e:
        print(f"Erro na API OpenAI: {e}")
        raise Exception(f"Erro na API de transcrição: {e}") from e
    except Exception as e:
        print(f"Erro inesperado durante a transcrição: {e}")
        raise Exception(f"Erro inesperado na transcrição: {e}") from e


def analyze_transcript_with_gemini(transcript):
    """Analisa a transcrição usando a API Gemini do Google."""
    if not google_api_key:
         raise ValueError("Chave da API Google (Gemini) não configurada.")

    print("Iniciando análise com Gemini...")
    try:
        # Escolhe o modelo Gemini
        # Veja modelos disponíveis: https://ai.google.dev/models/gemini
        model = genai.GenerativeModel('gemini-1.5-flash') # Ou 'gemini-pro'

        # Prompt detalhado para o LLM
        prompt = f"""
        Analise a seguinte transcrição de uma nota de voz pessoal, que representa um fluxo de consciência do usuário. Aja como um assistente reflexivo e útil. Sua análise deve ser estruturada em Markdown e incluir as seguintes seções:

        1.  **Transcrição Original:** Inclua a transcrição completa fornecida abaixo.
        2.  **Resumo dos Pontos Principais:** Identifique e liste os temas ou ideias centrais discutidos.
        3.  **Problemas ou Desafios:** Liste quaisquer problemas, preocupações ou dificuldades expressas pelo usuário.
        4.  **Conexões e Possíveis Causas:** Explore possíveis ligações entre os diferentes pontos ou problemas mencionados. Se possível, sugira causas subjacentes para os desafios identificados (apresente como hipóteses, não certezas).
        5.  **Próximos Passos Acionáveis:** Sugira 3-5 passos concretos e práticos que o usuário poderia tomar para abordar os desafios, explorar as ideias ou ganhar clareza. Foque em ações pequenas e gerenciáveis.

        Formate toda a resposta usando Markdown. Use cabeçalhos (##) para cada seção. Use listas de marcadores (*) ou numeradas (1.) conforme apropriado. Mantenha um tom empático e construtivo.

        **Transcrição para Análise:**
        ---
        {transcript}
        ---

        **Análise Formatada em Markdown:**
        """

        # Chama a API Gemini
        response = model.generate_content(prompt)

        print("Análise Gemini concluída.")
        # A resposta geralmente está em response.text
        # Adiciona uma nota ao final
        analysis_text = response.text
        analysis_text += "\n\n*Esta análise foi gerada por IA e destina-se a fins de reflexão. Não substitui aconselhamento profissional.*"
        return analysis_text

    except Exception as e:
        print(f"Erro durante a análise com Gemini: {e}")
        # Tenta extrair informações mais detalhadas do erro, se disponíveis
        error_message = str(e)
        # if hasattr(e, 'message'): # Alguns erros de API podem ter um atributo 'message'
        #     error_message = e.message
        raise Exception(f"Erro na análise LLM: {error_message}") from e


def generate_markdown_file(analysis_content):
    """Gera o conteúdo Markdown final (neste caso, já está formatado)."""
    return analysis_content

# --- Função da Tarefa em Background ---
def process_audio_task(task_id, audio_bytes, original_filename):
    """Executa a transcrição e análise reais em uma thread separada."""
    start_time = time.time()
    try:
        update_task_status(task_id, 'processing', message='Iniciando transcrição...')
        # 1. Transcrever (Real)
        transcript = transcribe_audio_with_whisper(audio_bytes, original_filename)
        transcription_time = time.time() - start_time
        print(f"Task {task_id}: Transcrição levou {transcription_time:.2f}s")

        update_task_status(task_id, 'processing', message=f'Transcrição concluída ({len(transcript)} caracteres). Analisando texto...')
        # 2. Analisar (Real)
        analysis = analyze_transcript_with_gemini(transcript)
        analysis_time = time.time() - start_time - transcription_time
        print(f"Task {task_id}: Análise levou {analysis_time:.2f}s")


        update_task_status(task_id, 'processing', message='Gerando relatório final...')
        # 3. Gerar Markdown (já formatado pela análise)
        markdown_content = generate_markdown_file(analysis)

        # 4. Armazenar resultado
        result_id = task_id # Usar o mesmo ID
        # Cria um nome de arquivo mais seguro
        base_filename = os.path.splitext(original_filename)[0]
        result_filename = f"analise_{secure_filename(base_filename)}.md"
        store_result(result_id, markdown_content, result_filename)

        update_task_status(task_id, 'completed', message='Processamento concluído!', result_id=result_id)
        total_time = time.time() - start_time
        print(f"Tarefa {task_id} concluída com sucesso em {total_time:.2f}s.")

    except ValueError as e: # Erro de configuração (ex: chave API faltando)
         print(f"Erro de configuração na tarefa {task_id}: {e}")
         update_task_status(task_id, 'failed', error=f"Erro de configuração: {e}")
    except openai.APIError as e:
        print(f"Erro de API OpenAI na tarefa {task_id}: {e}")
        update_task_status(task_id, 'failed', error=f"Erro na API de transcrição: {e.status_code}")
    except Exception as e: # Captura outros erros (Gemini, etc.)
        print(f"Erro geral ao processar tarefa {task_id}: {e}")
        update_task_status(task_id, 'failed', error=f"Erro no processamento: {e}")


# --- Endpoints da API (/, /upload, /status/<task_id>, /download/<result_id>) ---
# (O código destes endpoints permanece o mesmo da versão anterior - omitido por brevidade, mas deve estar aqui)
# --- Endpoints da API ---

@app.route('/')
def index():
    """Serve a página HTML principal."""
    try:
        # Tenta ler o HTML que foi criado anteriormente
        # Idealmente, use templates/ e render_template('index.html')
        with open("brain_dump.html", "r", encoding="utf-8") as f:
             html_content = f.read()
        # Substitui placeholders no HTML se necessário, ou usa render_template_string
        return render_template_string(html_content)
    except FileNotFoundError:
         # Tenta servir um HTML padrão se o arquivo não for encontrado
         print("WARN: brain_dump.html not found. Serving default.")
         # Pode retornar um erro mais informativo ou um HTML básico
         return "<html><body><h1>Analisador de Notas de Voz</h1><p>Erro: Arquivo de interface não encontrado.</p></body></html>", 404
    except Exception as e:
         print(f"Erro ao servir index: {e}")
         return f"Erro interno ao carregar a página: {e}", 500


@app.route('/upload', methods=['POST'])
@limiter.limit("10 per hour") # Aplica o limite específico para este endpoint
def upload_audio():
    """Recebe o arquivo de áudio, valida e inicia o processamento."""
    if not openai.api_key or not google_api_key:
         return jsonify({"detail": "Erro de configuração no servidor: APIs não inicializadas corretamente."}), 503 # Service Unavailable

    if 'audio_file' not in request.files:
        return jsonify({"detail": "Nenhum arquivo de áudio enviado."}), 400

    file = request.files['audio_file']

    if file.filename == '':
        return jsonify({"detail": "Nome de arquivo vazio."}), 400

    # Valida extensão ANTES de ler o arquivo inteiro
    if not allowed_file(file.filename):
        return jsonify({"detail": "Tipo de arquivo não permitido (use .wav ou .mp3)."}), 400

    try:
        # Lê o conteúdo do arquivo em memória de forma segura
        # Verifica o tamanho ANTES de ler tudo, se possível (depende do stream)
        # A configuração MAX_CONTENT_LENGTH do Flask já deve tratar isso, mas podemos ser explícitos
        audio_bytes = file.read() # Lê o conteúdo
        if len(audio_bytes) > app.config['MAX_CONTENT_LENGTH']:
             return jsonify({"detail": f"Arquivo excede o limite de {MAX_CONTENT_LENGTH // (1024*1024)}MB."}), 413

        original_filename = secure_filename(file.filename) # Limpa o nome do arquivo

        # Gera um ID único para a tarefa
        task_id = str(uuid.uuid4())

        # Armazena o estado inicial da tarefa
        with data_lock:
            tasks[task_id] = {'status': 'pending', 'message': 'Tarefa recebida.', 'error': None, 'result_id': None, 'expires_at': None}

        # Inicia a tarefa de processamento em uma nova thread
        thread = threading.Thread(target=process_audio_task, args=(task_id, audio_bytes, original_filename))
        thread.daemon = True # Permite que o programa saia mesmo se a thread estiver rodando
        thread.start()

        print(f"Tarefa {task_id} iniciada para o arquivo {original_filename}.")
        return jsonify({"task_id": task_id}), 202 # 202 Accepted: Requisição aceita, processamento iniciado

    except Exception as e:
        # Captura erros durante a leitura do arquivo ou início da thread
        print(f"Erro crítico no upload: {e}")
        # Evita expor detalhes internos do erro ao cliente
        return jsonify({"detail": "Erro interno ao processar o upload."}), 500


@app.route('/status/<task_id>', methods=['GET'])
def get_analysis_status(task_id):
    """Verifica o status de uma tarefa de análise."""
    status_info = get_task_status(task_id) # Já retorna uma cópia segura

    if not status_info:
        # Considera se a tarefa pode estar sendo processada mas ainda não foi registrada
        # (pouco provável com a lógica atual, mas possível em sistemas mais complexos)
        # Retorna 404 se definitivamente não existe
        return jsonify({"detail": "Tarefa não encontrada ou expirada."}), 404

    response = {"status": status_info['status']}
    status = status_info['status']

    if status == 'completed':
        response["message"] = status_info.get('message', 'Concluído')
        result_id = status_info.get('result_id')
        if result_id:
             # Verifica se o resultado ainda existe e não expirou antes de fornecer a URL
             result_data = get_result(result_id) # get_result já lida com expiração
             if result_data:
                 response["download_url"] = f"/download/{result_id}"
                 # Calcula o tempo restante
                 expiration_time = result_data['created_at'] + timedelta(minutes=RESULT_EXPIRATION_MINUTES)
                 time_left = expiration_time - datetime.now(timezone.utc)
                 response["expires_in"] = max(0, int(time_left.total_seconds()))
             else:
                 # Se o resultado expirou mas o status ainda é 'completed', informa que expirou
                 response['status'] = 'expired' # Atualiza o status na resposta
                 response['message'] = 'O resultado expirou.'
                 # Opcional: Atualizar o status da tarefa no backend para 'expired'
                 # update_task_status(task_id, 'expired', message='Resultado expirado.')
        else:
             # Caso raro: status completed mas sem result_id
             response['status'] = 'failed'
             response['error'] = 'Erro interno: Concluído sem resultado associado.'

    elif status == 'failed':
        response["error"] = status_info.get('error', 'Falha desconhecida')
        response["message"] = status_info.get('message', 'Falha no processamento') # Mensagem pode ser útil
    elif status == 'processing':
        response["message"] = status_info.get('message', 'Processando...')
    elif status == 'pending':
         response["message"] = status_info.get('message', 'Aguardando início do processamento...')
    else: # Estado desconhecido
         response['status'] = 'unknown'
         response['message'] = 'Estado da tarefa desconhecido.'


    return jsonify(response), 200


@app.route('/download/<result_id>', methods=['GET'])
def download_result(result_id):
    """Fornece o arquivo Markdown para download."""
    result_data = get_result(result_id) # get_result já lida com expiração

    if not result_data:
        # Abortar com 404 é apropriado para um recurso não encontrado
        abort(404, description="Resultado não encontrado ou expirado.")

    markdown_content = result_data['content']
    # Usa um nome de arquivo padrão seguro se não estiver definido
    filename = result_data.get('filename', 'analise_nota_voz.md')
    # Garante que o nome do arquivo seja seguro para cabeçalhos HTTP
    safe_filename = secure_filename(filename)

    # Cria um objeto BytesIO para enviar o conteúdo como arquivo
    mem_file = io.BytesIO()
    mem_file.write(markdown_content.encode('utf-8'))
    mem_file.seek(0)

    print(f"Servindo download para result_id: {result_id}, filename: {safe_filename}")

    try:
        return send_file(
            mem_file,
            as_attachment=True,
            download_name=safe_filename, # Usa o nome seguro
            mimetype='text/markdown; charset=utf-8' # Especifica charset
        )
    except Exception as e:
        print(f"Erro ao enviar arquivo para download {result_id}: {e}")
        abort(500, description="Erro ao gerar o arquivo para download.")


# --- Execução ---
if __name__ == '__main__':
    # host='0.0.0.0' permite acesso de outras máquinas na rede
    # debug=True é útil para desenvolvimento, mas DESATIVE em produção
    # Use uma porta diferente se a 5000 estiver ocupada
    port = int(os.environ.get('PORT', 5000))
    # Desativar debug em produção! O modo debug expõe informações sensíveis.
    use_debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"Iniciando servidor em host 0.0.0.0 porta {port} (Debug: {use_debug})")
    app.run(host='0.0.0.0', port=port, debug=use_debug)