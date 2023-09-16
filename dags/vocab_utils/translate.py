from googletrans import Translator
from langdetect import detect

def translate_vocab(translator, vocab_dic, src, dest):
    tranlsated_dic = {}
    for vocab, details in vocab_dic.items():
        definition_lst = []
        try:
            for d in details["definitions"]:
                definition = translator.translate(d, src=src, dest=dest).text
                definition_lst.append(definition)
        except:
            definition_lst = []

        definition = translator.translate(vocab, src=src, dest=dest).text
        deitinition_lst = [definition] + definition_lst
        try:
            example_lst = [translator.translate(d, src=src, dest=dest).text for d in details["examples"]]
        except:
            example_lst = []
        try:
            synonyms_lst = [translator.translate(d, src=src, dest=dest).text for d in details["synonyms"]]
        except:
            synonyms_lst = []
        print(details["context"])

        tranlsated_dic[vocab] = {"definitions": definition_lst,
                                "examples": example_lst,
                                "synonyms": synonyms_lst,
                                "context": details["context"],
                                "audio_url": details["audio_url"]}
    return tranlsated_dic
