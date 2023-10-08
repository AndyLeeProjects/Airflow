import requests
import json
from airflow.models import Variable
import logging
from googletrans import Translator
from vocab_utils.translate import translate_vocab

log = logging.getLogger(__name__)

def get_definitions(vocabs: list, vocab_origins: list, target_lang: str):
    """
    get_definitions()
        Using LinguaAPI, the definitions, examples, synonyms and contexts are gathered.
        Then they are stored into a dictionary format. 

    """
    vocab_dic = {}
    for ind, vocab in enumerate(vocabs):
        
        # DEFINE vocab_info_dic
        # try: Some vocabularies do not have definitions (ex: fugazi)
        url = "https://lingua-robot.p.rapidapi.com/language/v1/entries/en/" + \
            vocab.lower().strip(' ')

        headers = {
            "X-RapidAPI-Key": Variable.get("lingua_credentials"),
            "X-RapidAPI-Host": "lingua-robot.p.rapidapi.com"
        }

        # Request Data
        response = requests.request("GET", url, headers=headers)
        data = json.loads(response.text)

        try:
            vocab_dat = data['entries'][0]['lexemes']
        except IndexError:
            vocab_dat = None
            definitions = None
            synonyms = None
            examples = None
            audio_url = None

        def extract_audio_url(json_data):
            try:
                json_data = data['entries']
                for entry in json_data:
                    pronunciations = entry.get('pronunciations', [])
                    for pronunciation in pronunciations:
                        audio = pronunciation.get('audio')
                        if audio:
                            return audio['url']
            except IndexError:
                return None
            return None

        # GET DEFINITIONS
        # try: If the definition is not in Lingua Dictionary, output None
        try:
            definitions = [vocab_dat[j]['senses'][i]['definition']
                            for j in range(len(vocab_dat)) for i in range(len(vocab_dat[j]['senses']))]
            definitions = definitions[:5]
        except:
            pass

        # GET AUDIO URLS
        audio_url = extract_audio_url(data)

        # GET SYNONYMS
        # try: If synonyms are not in Lingua Dictionary, output None
        try:
            synonyms = [vocab_dat[j]['synonymSets'][i]['synonyms']
                        for j in range(len(vocab_dat)) for i in range(len(vocab_dat[j]['synonymSets']))]
        except:
            synonyms = None

        # GET EXAMPLES
        if vocab_origins[ind] != None:
            context = vocab_origins[ind]
        else:
            context = None

        try:
            examples += [vocab_dat[j]['senses'][i]['usageExamples']
                        for j in range(len(vocab_dat)) for i in range(len(vocab_dat[j]['senses']))
                        if 'usageExamples' in vocab_dat[j]['senses'][i].keys()]
        except:
            examples = None

        # Collect vocab details
        vocab_info_dic = {vocab: {'definitions': definitions,
                                  'examples': examples,
                                  'synonyms': synonyms,
                                  'context': context,
                                  'audio_url': audio_url}}

        if target_lang != 'en':
            translator = Translator()
            vocab_info_dic = translate_vocab(translator, vocab_info_dic, 'en', target_lang)

        vocab_dic.setdefault(vocab, []).append(vocab_info_dic[vocab])

    return vocab_dic
