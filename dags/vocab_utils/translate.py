from googletrans import Translator
from langdetect import detect

def translate_vocab(translator, vocab_dic, src, dest):
    tranlsated_dic = {}
    for vocab, details in vocab_dic.items():
        definition_lst = [translator.translate(vocab, src=src, dest=dest).text] +\
            [translator.translate(d, src=src, dest=dest).text for d in details["definitions"]]
        example_lst = [translator.translate(d, src=src, dest=dest).text for d in details["examples"]]
        synonyms_lst = [translator.translate(d, src=src, dest=dest).text for d in details["synonyms"]]
        audio_lst = [translator.translate(d, src=src, dest=dest).text for d in details["audio_url"]]
    
    tranlsated_dic[vocab] = {"definitions": definition_lst,
                              "examples": example_lst,
                              "synonyms": synonyms_lst,
                              "audio_url": audio_lst}
    return tranlsated_dic
