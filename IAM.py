import os
import json
import time
import threading
import requests
import speech_recognition as sr
import pyttsx3


# ============================================================
# IAM - Intelligent Artificial Machine
# ============================================================

class IAM:
    def __init__(
        self,
        model="IAM",
        ollama_url="http://localhost:11434/api/chat",
        memory_file="memory.json"
    ):
        self.model = model
        self.ollama_url = ollama_url
        self.memory_file = memory_file

        self.running = True
        self.voice_enabled = True
        self.listening = False

        # Histórico da conversa atual
        self.conversation = []

        # Memória permanente
        self.memory = self.load_memory()

        # Reconhecimento de voz
        self.recognizer = sr.Recognizer()

        # TTS
        self.tts = pyttsx3.init()

        self.configure_tts()

        # Modo atual
        self.mode = "assistente"

        # Prompts dos modos
        self.modes = {
            "assistente": """
Você está no MODO ASSISTENTE.

Converse naturalmente com o usuário.
Ajude com perguntas, estudos, tecnologia e tarefas gerais.
Use português brasileiro.
Se o usuário estiver descontraído, você pode usar humor.
""",

            "programador": """
Você está no MODO PROGRAMADOR.

Seu foco principal é programação e desenvolvimento de software.

Você deve:
- analisar código;
- encontrar bugs;
- explicar erros;
- corrigir código;
- criar código;
- refatorar;
- melhorar arquitetura;
- explicar algoritmos;
- sugerir boas práticas;
- ajudar com Python, JavaScript, TypeScript,
  C, C++, C#, Java, Rust, Go, HTML, CSS,
  SQL, Bash e PowerShell.

Quando corrigir código:
1. explique o problema;
2. explique a causa;
3. apresente a correção;
4. explique as mudanças.

Priorize código seguro, legível e manutenível.
""",

            "ciberseguranca": """
Você está no MODO CIBERSEGURANÇA.

Seu foco é segurança defensiva e testes autorizados.

Você pode ajudar com:
- análise de logs;
- hardening;
- auditoria;
- análise de vulnerabilidades;
- monitoramento;
- segurança de servidores;
- análise de redes;
- análise defensiva de malware;
- resposta a incidentes;
- scripts de segurança;
- testes em laboratórios e sistemas autorizados.

Nunca presuma autorização para atacar sistemas de terceiros.

Priorize defesa, detecção, mitigação e ambientes autorizados.
""",

            "humor": """
Você está no MODO HUMOR.

Seja mais descontraída.
Use sarcasmo, ironia e humor absurdo quando apropriado.

Pode fazer piadas sobre:
- programação;
- bugs;
- computadores;
- servidores;
- inteligência artificial;
- tecnologia.

Não incentive violência real, ódio ou crimes.

Mesmo no modo humor, continue sendo útil e correta.
""",

            "profissional": """
Você está no MODO PROFISSIONAL.

Responda de maneira objetiva, técnica e profissional.

Evite piadas e comentários desnecessários.

Priorize:
- precisão;
- clareza;
- organização;
- segurança;
- linguagem profissional.
"""
        }

    # ========================================================
    # CONFIGURAÇÃO TTS
    # ========================================================

    def configure_tts(self):
        """Configura a voz da IAM."""

        self.tts.setProperty("rate", 175)
        self.tts.setProperty("volume", 1.0)

        try:
            voices = self.tts.getProperty("voices")

            # Procura uma voz em português
            for voice in voices:
                voice_data = (
                    str(voice.id) +
                    " " +
                    str(voice.name)
                ).lower()

                if (
                    "portuguese" in voice_data
                    or "brazil" in voice_data
                    or "pt-br" in voice_data
                    or "portugu" in voice_data
                ):
                    self.tts.setProperty("voice", voice.id)
                    break

        except Exception as e:
            print(f"[TTS] Não foi possível configurar voz: {e}")

    # ========================================================
    # MEMÓRIA
    # ========================================================

    def load_memory(self):
        """Carrega a memória persistente."""

        if not os.path.exists(self.memory_file):
            return {
                "user": {},
                "facts": [],
                "preferences": [],
                "projects": [],
                "conversation_summary": ""
            }

        try:
            with open(
                self.memory_file,
                "r",
                encoding="utf-8"
            ) as file:
                return json.load(file)

        except Exception as e:
            print(f"[MEMÓRIA] Erro ao carregar: {e}")

            return {
                "user": {},
                "facts": [],
                "preferences": [],
                "projects": [],
                "conversation_summary": ""
            }

    def save_memory(self):
        """Salva a memória no disco."""

        try:
            with open(
                self.memory_file,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    self.memory,
                    file,
                    ensure_ascii=False,
                    indent=4
                )

        except Exception as e:
            print(f"[MEMÓRIA] Erro ao salvar: {e}")

    def remember(self, category, value):
        """Adiciona uma informação à memória."""

        if category not in self.memory:
            self.memory[category] = []

        if isinstance(self.memory[category], list):

            if value not in self.memory[category]:
                self.memory[category].append(value)

        elif isinstance(self.memory[category], dict):
            print(
                "[MEMÓRIA] Use remember_user() "
                "para informações do usuário."
            )

        self.save_memory()

    def remember_user(self, key, value):
        """Salva informação específica do usuário."""

        if "user" not in self.memory:
            self.memory["user"] = {}

        self.memory["user"][key] = value

        self.save_memory()

    def forget_memory(self):
        """Apaga toda a memória."""

        self.memory = {
            "user": {},
            "facts": [],
            "preferences": [],
            "projects": [],
            "conversation_summary": ""
        }

        self.save_memory()

        return "Memória apagada."

    def get_memory_context(self):
        """Transforma a memória em contexto para o LLM."""

        memory_text = ""

        user = self.memory.get("user", {})

        if user:
            memory_text += "\nINFORMAÇÕES DO USUÁRIO:\n"

            for key, value in user.items():
                memory_text += f"- {key}: {value}\n"

        facts = self.memory.get("facts", [])

        if facts:
            memory_text += "\nFATOS MEMORIZADOS:\n"

            for fact in facts[-20:]:
                memory_text += f"- {fact}\n"

        preferences = self.memory.get(
            "preferences",
            []
        )

        if preferences:
            memory_text += "\nPREFERÊNCIAS:\n"

            for preference in preferences[-20:]:
                memory_text += f"- {preference}\n"

        projects = self.memory.get(
            "projects",
            []
        )

        if projects:
            memory_text += "\nPROJETOS:\n"

            for project in projects[-20:]:
                memory_text += f"- {project}\n"

        return memory_text

    # ========================================================
    # MODOS
    # ========================================================

    def set_mode(self, mode):
        """Troca o modo da IAM."""

        mode = mode.lower().strip()

        aliases = {
            "normal": "assistente",
            "assist": "assistente",
            "programacao": "programador",
            "programação": "programador",
            "dev": "programador",
            "codigo": "programador",
            "ciber": "ciberseguranca",
            "cyber": "ciberseguranca",
            "seguranca": "ciberseguranca",
            "segurança": "ciberseguranca",
            "security": "ciberseguranca",
            "profissional": "profissional",
            "humor": "humor"
        }

        mode = aliases.get(mode, mode)

        if mode not in self.modes:
            return False

        self.mode = mode

        return True

    # ========================================================
    # OLLAMA
    # ========================================================

    def check_ollama(self):
        """Verifica se o Ollama está funcionando."""

        try:
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5
            )

            return response.status_code == 200

        except requests.RequestException:
            return False

    def ask_ollama(self, user_text):
        """Envia mensagem para o Ollama."""

        system_prompt = f"""
Você é a IAM — Intelligent Artificial Machine.

IDENTIDADE:
Você é uma IA pessoal especializada em programação,
tecnologia, automação e cibersegurança.

PERSONALIDADE:
- inteligente
- confiante
- espontânea
- adaptável
- natural
- técnica quando necessário

Você pode usar humor, sarcasmo e ironia quando apropriado.

Nunca invente ações que não realizou.

Nunca diga que executou um comando se você não executou.

Se não souber algo, diga que não sabe.

Responda em português brasileiro por padrão.

MODO ATUAL:
{self.mode.upper()}

INSTRUÇÕES DO MODO:
{self.modes[self.mode]}

MEMÓRIA:
{self.get_memory_context()}
"""

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        # Mantém apenas as últimas mensagens para
        # evitar crescimento infinito do contexto.
        messages.extend(
            self.conversation[-20:]
        )

        messages.append(
            {
                "role": "user",
                "content": user_text
            }
        )

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }

        try:
            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=300
            )

            response.raise_for_status()

            data = response.json()

            answer = data["message"]["content"]

            # Salva conversa
            self.conversation.append(
                {
                    "role": "user",
                    "content": user_text
                }
            )

            self.conversation.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )

            return answer

        except requests.exceptions.ConnectionError:
            return (
                "Não consegui conectar ao Ollama. "
                "Verifique se o servidor está funcionando "
                "com 'ollama serve'."
            )

        except requests.exceptions.Timeout:
            return (
                "O Ollama demorou demais para responder. "
                "O modelo pode estar carregando ou o "
                "computador pode estar sem recursos."
            )

        except Exception as e:
            return f"Erro ao consultar o Ollama: {e}"

    # ========================================================
    # TEXT-TO-SPEECH
    # ========================================================

    def speak(self, text):
        """Converte texto em voz."""

        if not self.voice_enabled:
            return

        if not text:
            return

        try:
            self.tts.say(text)
            self.tts.runAndWait()

        except Exception as e:
            print(f"[TTS] Erro: {e}")

    # ========================================================
    # SPEECH-TO-TEXT
    # ========================================================

    def listen(self):
        """Escuta o microfone e converte fala para texto."""

        try:
            with sr.Microphone() as source:

                self.listening = True

                print("\n🎤 IAM está ouvindo...")

                self.recognizer.adjust_for_ambient_noise(
                    source,
                    duration=0.5
                )

                audio = self.recognizer.listen(
                    source,
                    timeout=8,
                    phrase_time_limit=30
                )

                self.listening = False

            print("🧠 Processando voz...")

            try:
                text = self.recognizer.recognize_google(
                    audio,
                    language="pt-BR"
                )

                return text

            except sr.UnknownValueError:
                return ""

            except sr.RequestError as e:
                print(
                    f"[STT] Serviço de reconhecimento indisponível: {e}"
                )

                return ""

        except sr.WaitTimeoutError:
            self.listening = False

            return ""

        except Exception as e:
            self.listening = False

            print(f"[MIC] Erro: {e}")

            return ""

    # ========================================================
    # COMANDOS
    # ========================================================

    def process_command(self, text):
        """
        Processa comandos internos da IAM.

        Retorna:
        True  -> comando processado
        False -> mensagem deve ir para o LLM
        """

        command = text.lower().strip()

        # ----------------------------------------------------
        # SAIR
        # ----------------------------------------------------

        if command in [
            "sair",
            "exit",
            "quit",
            "desligar iam",
            "encerrar"
        ]:

            self.running = False

            self.speak("Sistema IAM sendo encerrado.")

            return True

        # ----------------------------------------------------
        # VOZ
        # ----------------------------------------------------

        if command in [
            "voz ativada",
            "ativar voz",
            "ligar voz"
        ]:

            self.voice_enabled = True

            self.speak("Voz ativada.")

            return True

        if command in [
            "voz desativada",
            "desativar voz",
            "desligar voz"
        ]:

            self.voice_enabled = False

            print("🔇 Voz desativada.")

            return True

        # ----------------------------------------------------
        # MODOS
        # ----------------------------------------------------

        if command.startswith("modo "):

            requested_mode = command[5:].strip()

            if self.set_mode(requested_mode):

                response = (
                    f"Modo {self.mode} ativado."
                )

                print(f"🔄 {response}")

                self.speak(response)

            else:

                response = (
                    "Modo não encontrado. "
                    "Use assistente, programador, "
                    "cibersegurança, humor ou profissional."
                )

                print(response)

                self.speak(response)

            return True

        # ----------------------------------------------------
        # MEMÓRIA
        # ----------------------------------------------------

        if command == "apagar memória":

            response = self.forget_memory()

            print(response)

            self.speak(response)

            return True

        if command.startswith("lembrar que "):

            value = text[len("lembrar que "):].strip()

            self.remember(
                "facts",
                value
            )

            response = (
                "Certo. Salvei essa informação na memória."
            )

            print(response)

            self.speak(response)

            return True

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        if command in [
            "status",
            "status da iam"
        ]:

            ollama_status = (
                "online"
                if self.check_ollama()
                else "offline"
            )

            response = (
                f"IAM online. "
                f"Modo atual: {self.mode}. "
                f"Ollama: {ollama_status}. "
                f"Voz: "
                f"{'ativada' if self.voice_enabled else 'desativada'}."
            )

            print(response)

            self.speak(response)

            return True

        return False

    # ========================================================
    # PROCESSAMENTO
    # ========================================================

    def process(self, text):
        """Processa uma mensagem."""

        if not text:
            return

        print(f"\n👤 Você: {text}")

        # Comando interno
        if self.process_command(text):
            return

        # LLM
        print("🤖 IAM: pensando...")

        answer = self.ask_ollama(text)

        print(
            f"\n🤖 IAM [{self.mode}]:\n{answer}"
        )

        # Voz
        if self.voice_enabled:

            # Executa TTS em thread separada
            voice_thread = threading.Thread(
                target=self.speak,
                args=(answer,),
                daemon=True
            )

            voice_thread.start()

    # ========================================================
    # MODO TEXTO
    # ========================================================

    def text_mode(self):

        print("\n======================================")
        print("       IAM - INTELLIGENT AI MACHINE")
        print("======================================")

        print(f"Modelo: {self.model}")
        print(f"Modo: {self.mode}")

        print("\nComandos:")
        print("  modo programador")
        print("  modo cibersegurança")
        print("  modo humor")
        print("  modo profissional")
        print("  modo assistente")
        print("  lembrar que ...")
        print("  apagar memória")
        print("  status")
        print("  ativar voz")
        print("  desativar voz")
        print("  sair")

        print("\nDigite sua mensagem.\n")

        while self.running:

            try:
                text = input("Você > ").strip()

                if text:
                    self.process(text)

            except KeyboardInterrupt:

                print("\n\nEncerrando IAM...")

                self.running = False

            except EOFError:

                self.running = False

    # ========================================================
    # MODO VOZ
    # ========================================================

    def voice_mode(self):

        print("\n======================================")
        print("          IAM - MODO VOZ")
        print("======================================")

        print("🎤 Microfone ativo.")
        print("Fale com a IAM.")
        print("Diga 'sair' para encerrar.\n")

        while self.running:

            text = self.listen()

            if not text:
                continue

            print(f"👤 Você: {text}")

            if text.lower().strip() == "sair":

                self.running = False

                self.speak(
                    "Até mais. Sistema IAM encerrado."
                )

                break

            self.process(text)

    # ========================================================
    # MODO HÍBRIDO
    # ========================================================

    def hybrid_mode(self):

        print("\n======================================")
        print("             IAM ONLINE")
        print("======================================")

        print("⌨️ Texto disponível")
        print("🎤 Microfone disponível")
        print("🔊 Voz disponível")
        print()

        print("Digite:")
        print("  /voz     -> falar com a IAM")
        print("  /texto   -> voltar ao texto")
        print("  /sair    -> encerrar")
        print()

        while self.running:

            try:

                command = input("IAM > ").strip()

                if command == "/voz":

                    self.voice_mode()

                    if self.running:
                        print("\nVoltando ao modo texto...\n")

                    continue

                if command == "/texto":

                    continue

                if command == "/sair":

                    self.running = False

                    self.speak(
                        "Sistema IAM encerrado."
                    )

                    break

                if command:

                    self.process(command)

            except KeyboardInterrupt:

                print("\nEncerrando IAM...")

                self.running = False

            except EOFError:

                self.running = False


# ============================================================
# INICIALIZAÇÃO
# ============================================================

def main():

    iam = IAM(
        model="IAM",
        ollama_url="http://localhost:11434/api/chat",
        memory_file="memory.json"
    )

    print("""
╔══════════════════════════════════════════╗
║       IAM - INTELLIGENT AI MACHINE       ║
╠══════════════════════════════════════════╣
║ Programação                              ║
║ Cibersegurança                           ║
║ Automação                                ║
║ Memória                                  ║
║ Speech-to-Text                           ║
║ Text-to-Speech                            ║
║ Ollama                                   ║
╚══════════════════════════════════════════╝
""")

    print("🔎 Verificando Ollama...")

    if iam.check_ollama():

        print("🟢 Ollama online.")

    else:

        print("🔴 Ollama não respondeu.")
        print()
        print("Execute:")
        print("  ollama serve")
        print()

    print(f"🧠 Modelo: {iam.model}")
    print(f"⚙️ Modo: {iam.mode}")
    print()

    iam.hybrid_mode()


if __name__ == "__main__":
    main()
