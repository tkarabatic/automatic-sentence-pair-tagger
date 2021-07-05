from collections import defaultdict
import os
from nltk import pos_tag, word_tokenize
from nltk.corpus import stopwords, wordnet
from nltk.stem.wordnet import WordNetLemmatizer


SYN_GER = [
    'german', 'germany', 'hitler', 'hilter', 'ss', 'nazi', 'nazis', 'berlin',
    'reich', 'wehrmacht', 'axis', 'hilters', 'adolf hitler', 'fuhrer',
    'der fuhrer', 'federal republic of germany', 'frg', "hitler's", "germany's"
]
SYN_JAP = [
    'japan', 'japanese', 'japenese', 'hiroshima', 'nagasaki', 'kyoto',
    'kamikaze', 'tojo', 'tokyo', 'nippon', 'nihon', 'tojo hideki',
    'hideki tojo', "japan's"
]
SYN_ITA = [
    'italy', 'italian', 'italians', 'rome', 'mussolini', 'italia', 'il duce',
    'benito mussolini', "italy's"
]
SYN_JEW = [
    'jew', 'jewish', 'israel', 'israeli', 'yisrael', 'zion', 'sion', 'hebrew'
]
SYN_RUS = [
    'russia', 'ussr', 'soviet union', 'stalin', 'soviet', 'russian federation',
    'union of soviet socialist republics', 'soviet russia', 'joseph stalin',
    'russian soviet federated socialist republic',
    'iosif vissarionovich dzhugashvili', "russia's"
]
SYN_UK = [
    'uk', 'united kingdom', 'great britain', 'british', 'london', 'uks',
    'churchill', 'winston churchill', 'u.k.', 'u. k.', 'britain',
    'united kingdom of great britain and northern ireland',
    'sir winston leonard spenser churchill', 'winston s. churchill',
    "britain's", "churchill's", "uk's"
]
SYN_US = [
    'america', 'us', 'american', 'americans', 'usa', 'united states',
    'roosevelt', 'truman', 'eisenhower', 'united states of america', 'u.s.',
    'u. s.', 'u.s.a.', 'u. s. a.', 'the states', 'us army', 'u. s. army',
    'president truman', 'harry s. truman', 'harry truman',
    'franklin roosevelt', 'franklin delano roosevelt', 'presiden roosevelt',
    'dwight eisenhower', 'dwight d. eisenhower', 'ike',
    'president eisenhower', "america's"
]
SYN_NL = ['holland', 'netherlands', 'the netherlands', 'dutch', 'nederland']
COUNTRY_SYNONYMS = [
    SYN_GER, SYN_US, SYN_UK, SYN_RUS, SYN_JAP, SYN_ITA, SYN_JEW, SYN_NL
]
STOP_WORDS = list(set(stopwords.words('english'))) + [
    'world', 'war', 'two', '2', 'ii', 'wwii', 'what', 'where', 'how', 'why',
    'did', 'can', 'could', "'s", '?'
]
COUNTRY_KEYWORDS = [
    'africa', 'alaska', 'algeria', 'arabia', 'argentina', 'asia', 'australia',
    'austria', 'azerbaijan', 'balkans', 'brazil', 'bulgaria', 'canada',
    'china', 'croatia', 'denmark', 'etiopia', 'europe', 'finland', 'france',
    'greece', 'greenland', 'india', 'ireland', 'korea', 'macao', 'malta',
    'mexico', 'nigeria', 'normandy', 'norway', 'palestine', 'philippines',
    'poland', 'portugal', 'prussia', 'puerto rico', 'romania', 'saudi',
    'saudi arabia', 'scotland', 'siberia', 'singapore', 'spain', 'sweden',
    'switzerland', 'thailand', 'turkey', 'ukraine', 'vatican', 'venice',
    'vietnam', 'yugoslavia', 'albania', 'belarus', 'belgium', 'bosnia',
    'serbia', 'czech', 'niger', 'slovenia'
]

POS_TAGS = defaultdict(lambda: wordnet.NOUN)
POS_TAGS['J'] = wordnet.ADJ
POS_TAGS['V'] = wordnet.VERB
POS_TAGS['R'] = wordnet.ADV

lemmatizer = WordNetLemmatizer()


def get_path(filename):
    CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(CURRENT_FOLDER, filename)


def write_to_file(items, filename, mode='w'):
    file = open(get_path(filename), mode)
    for it in items:
        file.write('%s\n' % (it))
    file.close()


def get_dict_key_for_value(dict, value):
    for key, val in dict.items():
        if val == value:
            return key


def has_pair(id_pair_set, id_1, id_2):
    return any([(id_1, id_2) in id_pair_set, (id_2, id_1) in id_pair_set])


def intersection(first_list, second_list):
    return [i for i in first_list if i in second_list]


# Note: we're disregarding same-id pairs because every sentence is implicitly
# equal to itself
def get_unique_id_pairs(sentence_ids):
    id_pairs = set()
    for id_1 in sentence_ids:
        for id_2 in sentence_ids:
            if id_2 != id_1 and not has_pair(id_pairs, id_1, id_2):
                id_pairs.add((id_1, id_2))
    return id_pairs


def get_word_lemmas(sentence):
    tokens = word_tokenize(sentence)
    lemmas = []
    for token, tag in pos_tag(tokens):
        lowercase = token.lower()
        if lowercase not in STOP_WORDS:
            lemma = lemmatizer.lemmatize(lowercase, POS_TAGS[tag[0]])
            lemmas.append(lemma)
    return lemmas


def get_keyword_lemmas(sentence):
    country_keywords = []
    other_keywords = []
    lowercase_sentence = sentence.lower()
    # first pass: extract country-related keyword strings if extant; they will
    # get separated in the lemmatizing process (e.g. 'united states' becomes
    # ['united', 'state']), losing their specific meaning
    for synlist in COUNTRY_SYNONYMS:
        for country_keyword in synlist:
            if country_keyword in lowercase_sentence:
                country_keywords.extend(synlist)
    # second pass (with lemmatization); since the country-related keywords
    # were not removed from the sentence itself in order to allow the POS
    # tagging to work properly, this step will exclude any lemmas that happen
    # to match the country keyword pool
    for lemma in get_word_lemmas(sentence):
        if lemma in country_keywords:
            continue
        for synlist in COUNTRY_SYNONYMS:
            if lemma in synlist:
                # an edge case that may occur if the non-lemmatized version of
                # a word was not present in the country keywords, but the
                # lemmatized version is (e.g. a possessive)
                if synlist[0] not in country_keywords:
                    country_keywords.extend(synlist)
                else:
                    continue
        for synset in wordnet.synsets(lemma):
            for ln in synset.lemma_names():
                kw = ln.replace('_', ' ').lower()
                if kw not in STOP_WORDS:
                    if kw in COUNTRY_KEYWORDS:
                        if kw not in country_keywords:
                            country_keywords.append(kw)
                    elif kw not in other_keywords:
                        other_keywords.append(kw)
    return country_keywords, other_keywords


def get_all_synonyms(lemma):
    kws = []
    for synset in wordnet.synsets(lemma):
        for ln in synset.lemma_names():
            kw = ln.replace('_', ' ').lower()
            kws.append(kw)
    return kws


def is_keyword_match(first_sentence, second_sentence, log_results=False):
    s1_country_kws, s1_other_kws = get_keyword_lemmas(first_sentence)
    s2_country_kws, s2_other_kws = get_keyword_lemmas(second_sentence)
    if log_results:
        print('s1', s1_country_kws, s1_other_kws)
        print('s2', s2_country_kws, s2_other_kws)
    if len(s1_country_kws) or len(s2_country_kws):
        country_intersection = intersection(s1_country_kws, s2_country_kws)
        if log_results:
            print('country intersection', country_intersection)
        if not len(country_intersection):
            return False
    other_intersection = intersection(s1_other_kws, s2_other_kws)
    if log_results:
        print('intersection 2', other_intersection)
    return len(other_intersection) > 0
