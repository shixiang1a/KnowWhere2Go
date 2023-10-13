import nltk
from urllib import parse

# 按照阈值切分句子
def cut_page(page_detail, mode, cut_length=100):
    if mode == "sentence":
        sentences = nltk.sent_tokenize(page_detail)
        split_sentences = []
        length = 0
        string = ""
        for sentence in sentences:
            length += len(nltk.word_tokenize(sentence))
            if len(nltk.word_tokenize(sentence)) > cut_length:
                continue
            if length + len(nltk.word_tokenize(sentence)) > cut_length:
                split_sentences.append(string)
                string = sentence
                length = len(nltk.word_tokenize(sentence))
            else:
                string += sentence
                length += len(nltk.word_tokenize(sentence))
        if string != "":
            split_sentences.append(string)
    return split_sentences


# 从url中提取域名
def url_to_domain(url):
	o = parse.urlparse(url)
	domain = o.hostname
	return domain


# 判断网页是否是英文网站
def is_english(_char):
    for s in _char:
        if (u'\u0041' <= s <= u'\u005a') or (u'\u0061' <= s <= u'\u007a'):
            return True
    return False