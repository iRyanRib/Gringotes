#langchain bibliotecas
from langchain.llms import OpenAI
from langchain.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain

from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
#biblioteca transformers do Pytorch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

from re import sub
from typing import Dict, List


#biblioteca para carregar arquivo .env
from dotenv import find_dotenv, load_dotenv

#biblioteca para tradução 
from google.cloud import translate_v2 as translate

#biblioteca do sistema para encerrar o processo
import sys

# Carregando o env
load_dotenv(find_dotenv())

#carregando o modelo e criando o classificador
embeddings = OpenAIEmbeddings()
model_id = 'philschmid/BERT-Banking77'
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForSequenceClassification.from_pretrained(model_id)
classifier = pipeline('text-classification', tokenizer=tokenizer, model=model)

#carregando recursos SQL
db = SQLDatabase.from_uri("sqlite:///Bank.db")
llm = OpenAI(temperature=0)
db_chain = SQLDatabaseChain.from_llm(llm, db)
db_chainDirect = SQLDatabaseChain.from_llm(llm, db, return_direct=True) #Retorna a query sem passar pelo LLM

#iniciando o  Google Cloud Translation API client
client = translate.Client.from_service_account_json('quick-discovery-395419-3351469312d3.json')

# Função para traduzir o texto para português
def translate_portuguese_to_english(text):
    translated = client.translate(text, target_language='en', source_language='pt-BR')
    translated['translatedText'] = translated['translatedText'].replace("&#39;", "'")
    return translated['translatedText']

# Retorna a classificação e porcentagem de chance
def match(user_input_t):
    result = classifier(user_input_t)
    classifier_label = result[0]['label']
    classifier_score = result[0]['score']
    return classifier_label, classifier_score

# Função para verificar se o contexto bancário está presente na frase
def verify_context(user_input):
    chat = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.15)

    # Template to use for the system message prompt
    template =  """
    Você é um auxiliar bancário, que tem a função de identificar se a solicitação {input}
    do usuário está condizente com um contexto de um atendimento bancario.
    
    Se a solicitação estiver presente no contexto, responda "sim", caso contrário, responda "não".
    """

    system_message_prompt = SystemMessagePromptTemplate.from_template(template)

    # Human question prompt
    human_template = "Verifique a frase: {input}"

    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    chat_prompt = ChatPromptTemplate.from_messages(
        [system_message_prompt, human_message_prompt]
    )

    chain = LLMChain(llm=chat, prompt=chat_prompt)
    
    response = chain.run(input=user_input)
    response = response.replace("\n", "")
    return response

#função para extrair cpf em um modelo padronizado
def extract_cpf(input_string):
    clean_string = sub(r'\D', '', input_string)
    if len(clean_string) == 11:
        return clean_string
    else:
        return None
#após verficação inicial de contexto é feita a classificação da demanda do usuário
def analyzer(user_input):
    global var
    resp = verify_context(user_input)
    if(resp == "sim"):
        user_input_traduzido = translate_portuguese_to_english(user_input)

        label, score = match(user_input_traduzido)
        if score >= 0.78:
            return label
        else:
            var = 1984
    else:
        var = 1984  

#classe principal do atendimento
class Alice_service:
    def __init__(self):
        self._orientacao = "" # Atributo protegido
        self._history: List[str] = [] # Atributo protegido
        self._user_input = ""
        self._alice_output = ""
        self.contaUsuario = None  # Initialize contaUsuario as an attribute to be used 
        self.codRast = ""

    #get e set dos atributos
    @property
    def alice_output(self):
        return self._alice_output
    
    @alice_output.setter
    def alice_output(self,alice_output):
        self._alice_output = alice_output
        
    @property
    def orientacao(self):
        return self._orientacao
    
    @orientacao.setter
    def orientacao(self,nova_orientacao):
        self._orientacao = nova_orientacao
        
    @property
    def history(self):
        return self._history
    
    @history.setter
    def history(self,novo_history):
        self._history = novo_history
        
    # Função para buscar frases semelhantes no banco de dados
    def atendimento(self,user_input,orientacao):
        
        self._user_input = user_input
        self._orientacao = orientacao
        #pré análise do input do usuário
        chat = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.15)

        # Template to use for the system message prompt
        template =  """
        Você é uma gentil atendente bancária do banco Gringottes, seu nome é Alice e tem 24 anos. 
        Sua função é realizar o atendimento do cliente seguindo esta orientação:{orientacao}
        de seu chefe para tomar a ação.Leve também em consideração o histórico da conversa abaixo após o símbolo
        '===' até o próximo símbolo'==='.
        ===
        {historico}.
        ===
        não diga olá nas frases depois da apresentação. 
        Não é necessário que se apresente de novo e nem mesmo cumprimente o usuário a cada ação.
        
        """
        system_message_prompt = SystemMessagePromptTemplate.from_template(template)

        human_message_prompt = HumanMessagePromptTemplate.from_template(self.orientacao)
        chat_prompt = ChatPromptTemplate.from_messages(
            [system_message_prompt, human_message_prompt]
        )

        chain = LLMChain(llm=chat, prompt=chat_prompt)

        response = chain.run(input=user_input,historico = self.history,orientacao=self.orientacao)
        response = response.replace("\n", "")
        return response
    #guarda input do usuário no histórico
    def human_step(self,human_input):
        human_input = human_input + '<FIM_TURNO_CLIENTE>'
        self.history.append(human_input)

    #verifica se o usuário quer sair do atendimento      
    def exit(self,user_input):
        orientacao = " verifique através da fala {input} se o usuário quer sair do atendimento, se sim retorne apenas sim se não retone apenas não"
        alice_output = self.atendimento(user_input,orientacao)
        if alice_output =="sim":
            orientacao = " dispeça e diga que o Banco Gringottes agradece pelo contato. Não diga mais nada além disso!"
            alice_output = self.atendimento(user_input,orientacao)
            print("\n alice turn =>",alice_output)
            sys.exit()

    #guarda output da alice no histórico       
    def alice_step(self,alice_output):
            # process human input
            alice_output = alice_output + '<FIM_TURNO_ATENDENTE>'
            self.history.append(alice_output)
    
    #função para o script de chegada de cartão
    def select_card_arrival(self,user_input,var):
        estagio_conversa_dict: Dict = {
        '1': "após verficação do numero da conta :{input} diga que a conta foi encontrada e  precisa do CPF para confirmar a titularidade",
        '2': "diga que não foi possível encontrar a conta:{input}, peça para que digite o número da conta novamente",
        '3': "diga que não foi possível verificar a titularidade da conta, peça para que digite novamente o cpf",
        '4': "Agradeça pela verificação e peça para o cliente aguardar um pouco que você vai verificar se o cartão foi enviado",
        '5': "Diga que o cartão já foi enviado, e que é só aguardar, além disso diga que se ele quiser acompanhar a entrega o código de rastreio segue abaixo:[CÓDIGO DE RASTREIO]",
        '6': "Peça desculpas, e diga que o cartão ainda não foi enviado mas que logo será. E diga que você tomará as providências para que o cartão seja enviado o mais rápido possível.",

        }
        match var:
            case 0:
                #verificação de existência da conta
                pergunta = "existe a conta {}? responda apenas com sim ou não minúsculos".format(user_input)
                resposta = db_chain.run(pergunta)
                if resposta == "sim":
                    self.contaUsuario = user_input #salva a conta do usuario para usos futuros
                    orientacao = estagio_conversa_dict["1"]
                    var = var + 1
                    return orientacao,var
                else :
                    orientacao = estagio_conversa_dict["2"]
                    return orientacao,var
            case 1:
                #verificação se o cpf fornecido é o mesmo da conta
                pergunta = "qual o cpf da conta {}?".format(self.contaUsuario)
                resposta = db_chainDirect.run(pergunta)
                cpf_db = resposta.strip("[]()'").split(',')[0].rstrip("'")
                cpf_user = extract_cpf(user_input)
                if cpf_user == cpf_db:
                    orientacao = estagio_conversa_dict["4"]
                    var = var + 1
                    return orientacao,var
                else:
                    orientacao = estagio_conversa_dict["3"]
                    return orientacao,var
            case 2:
                #verificação se o cartão já foi enviado
                pergunta = "verifique se o cartão da conta {} já foi enviado, responda somente com sim ou não minúsculos. Se sim, qual o número de rastreio".format(self.contaUsuario)
                resposta = db_chainDirect.run(pergunta)
                if resposta[2] == "1":                  
                    self.codRast = resposta[6:14]
                    orientacao = estagio_conversa_dict["5"]
                    var = var + 1
                    return orientacao,var
                else:
                    orientacao = estagio_conversa_dict["6"]
                    var = var + 1
                    return orientacao,var

def main():
    global var
    var = 0

    #inicializa a classe Alice_service
    alice = Alice_service()
    flag = False
    while True:
        user_input = " "
        #intrdução do atendimento     
        if var == 0:
            orientacao = "Apresente-se e pergunte como pode ajudar o cliente"
        #não identificação do usuário
        elif var == 1984:
            orientacao = "Diga que não entendeu, e peça mais detalhes"
            var = 0
        #retorno
        else:
            orientacao = "pergunte se pode ajudar o usuário em mais alguma coisa?"
            flag = True

        #turno da alice receber o input e orientacao para seguir
        alice_output = alice.atendimento(user_input,orientacao)
        print("\n alice turn =>",alice_output) 
        alice.alice_step(alice_output)

        user_input = input("\nUser Input  => ")
        
        if var!=0:
            orientacao = "Voce perguntou se o usuario quer mais ajuda.verifique se a resposta dele:{input} ele quer mais ajuda ou não.Se sim diga apenas sim. Se não diga apenas não"
            alice_output = alice.atendimento(user_input,orientacao)
            alice.alice_step(alice_output)
            if alice_output == "não":
                orientacao = "dispeça e diga que o Banco Gringottes agradece pelo contato. Não diga mais nada além disso!"
                alice_output = alice.atendimento(user_input,orientacao)
                print("\n alice turn =>",alice_output) 
                break
        if flag == False:
            alice.exit(user_input)
        flag = False
        label = analyzer(user_input)

        #entramos no ciclo de atendimento
        if label == "card_arrival":
            #1
            orientacao = "responda ao {input} pedindo o número da conta do cliente no final "
            #SCRIPT 1
            while True:           
                #sinaliza fim do turno humano e guarda no historico
                alice.human_step(user_input)
                
                #turno da alice receber o input e orientacao para seguir
                alice_output = alice.atendimento(user_input,orientacao)
                if var ==3:
                    #subsitui o código de rastreio da string pelo código real que não poderia ter sido passado para o servidor da OpenAI
                    alice_output = alice_output.replace("[CÓDIGO DE RASTREIO]", alice.codRast)
                    var = var + 1
                #sinaliza fim do turno da atendente e guarda no historico
                alice.alice_step(alice_output)
                print("\n alice turn =>",alice_output)           
                #turno humano
                if var == 0 or var == 1:
                    user_input = input("\nUser Input => ")
                    alice.exit(user_input)
                if var == 4:
                    break                                     
                orientacao,var = alice.select_card_arrival(user_input,var)                    
        else:
            orientacao = "Diga somente que você sabe que o assunto é {input}, mas você ainda não pode solucionar o problema. Diga somente isso"
            alice_output = alice.atendimento(label,orientacao)
            print("\n alice turn =>",alice_output)
main()