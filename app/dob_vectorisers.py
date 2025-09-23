from sklearn.feature_extraction.text import TfidfVectorizer

def dob_tokenizer(dob):
    return dob.split("-") if isinstance(dob, str) else ["0000", "00", "00"]

def get_dob_char_vectorizer():
    return TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), max_features=200)

def get_dob_token_vectorizer():
    return TfidfVectorizer(analyzer='word', tokenizer=dob_tokenizer, max_features=50)
