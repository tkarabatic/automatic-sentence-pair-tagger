import csv
from dotenv import dotenv_values
import sqlite3

from helpers import (
    get_dict_key_for_value,
    get_path,
    get_unique_id_pairs,
    has_pair,
    is_keyword_match,
    write_to_file
)

config = dotenv_values('.env')

DB_NAME = 'sentence_similarity.db'
TABLE_NAME = 'sentence'
JUNCTION_TABLE_NAME = 'sentence_pair_similarity'


def db_action(fn):
    try:
        db_connection = sqlite3.connect(DB_NAME)
        cursor = db_connection.cursor()
        print("[CONNECTED]")
        result = fn(cursor)
        db_connection.commit()
        print("[DONE]")
        cursor.close()
        return result
    except sqlite3.Error as error:
        print("[ERROR]", error)
    finally:
        if (db_connection):
            db_connection.close()
            print("[DISCONNECTED]")


def check_db_connection(cursor):
    cursor.execute("SELECT sqlite_version();")
    print('\nSQLite DB version: %s\n' % (cursor.fetchall()))


def create_tables(cursor):
    print('creating tables...')
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS %s (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL
        );""" % (TABLE_NAME)
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS %s (
            first_sentence_id INTEGER NOT NULL,
            second_sentence_id INTEGER NOT NULL,
            is_match INTEGER NOT NULL CHECK(is_match IN (0, 1)),
            is_verified INTEGER NOT NULL CHECK(is_verified IN (0, 1)),
            PRIMARY KEY (first_sentence_id, second_sentence_id)
        );""" % (JUNCTION_TABLE_NAME)
    )


def read_sentence_pairs(is_match, is_verified=0):
    def fn(cursor):
        print('reading sentence pairs...')
        query = '''
            SELECT j.first_sentence_id, j.second_sentence_id
            FROM %s AS j
            INNER JOIN %s AS s1 ON j.first_sentence_id = s1.id
            INNER JOIN %s AS s2 ON j.second_sentence_id = s2.id
            WHERE j.is_match = %d AND j.is_verified = %d;
        ''' % (JUNCTION_TABLE_NAME, TABLE_NAME, TABLE_NAME, is_match,
               is_verified)
        cursor.execute(query)
        return cursor.fetchall()
    return fn


def store_sentences(cursor):
    print('storing sentences...')
    filename = config['SENTENCE_POOL_FILENAME']
    if not filename:
        print('Sentence filename not defined.')
        return
    existing = map(lambda row: row[1], db_action(get_select(TABLE_NAME)))
    to_store = list()
    file_path = get_path(filename)
    for text in open(file_path, 'rt').readlines():
        sentence = text[:-1]
        if sentence not in existing:
            to_store.append(sentence)
    if not len(to_store):
        print('No new sentences found.')
        return
    bulk_insert_query = 'INSERT INTO %s (text) VALUES (?);' % (TABLE_NAME)
    cursor.executemany(bulk_insert_query, [[s] for s in to_store])


def store_similarity_matches(cursor, rows):
    print('storing similarity matches...')
    # an upsert is used because the CSV data can override existing unverified
    # junction rows
    bulk_insert_query = '''
       INSERT INTO %s
       (first_sentence_id, second_sentence_id, is_match, is_verified)
       VALUES (?,?,?,?)
       ON CONFLICT (first_sentence_id, second_sentence_id) DO UPDATE SET
        is_match=excluded.is_match,
        is_verified=excluded.is_verified;
    ''' % (JUNCTION_TABLE_NAME)
    cursor.executemany(bulk_insert_query, rows)


def get_sentence_count(cursor):
    print('counting table rows...')
    cursor.execute('SELECT COUNT(*) FROM %s;' % (TABLE_NAME))
    result = cursor.fetchone()
    return result[0]


def get_select(table_name, where_conditions=''):
    def select(cursor):
        where = ' WHERE %s' % (where_conditions) if where_conditions else ''
        cursor.execute('SELECT * FROM %s%s;' % (table_name, where))
        return cursor.fetchall()
    return select


def store_similarity_from_csv(cursor):
    print('storing similarity from CSV...')
    filename = config['VERIFIED_SENTENCE_FILENAME']
    if not filename:
        print('Filename not defined.')
        return
    # being verified, the CSV data rows should override existing unverified
    # rows
    sentences, unrated_id_pairs = get_unrated_sentence_data(True)
    with open(get_path(filename), newline='\n') as file:
        reader = csv.reader(file, delimiter=',')
        new_id_pairs = list()
        for first_sentence, second_sentence, is_match in reader:
            first_id = get_dict_key_for_value(sentences, first_sentence)
            second_id = get_dict_key_for_value(sentences, second_sentence)
            if not first_id or not second_id:
                continue
            if has_pair(unrated_id_pairs, first_id, second_id):
                new_id_pairs.append([first_id, second_id, int(is_match), 1])
        if len(new_id_pairs):
            print('New pair count: %d' % (len(new_id_pairs)))
            store_similarity_matches(cursor, new_id_pairs)
        else:
            print('No new pairs to store.')


def store_similarity_from_data(rows):
    return lambda cursor: store_similarity_matches(cursor, rows)


def initialize():
    print('initializing...')
    db_action(create_tables)
    db_action(store_sentences)
    print('Sentence count: %d' % (db_action(get_sentence_count)))
    db_action(store_similarity_from_csv)


def get_unrated_sentence_data(include_unverified=False):
    print('fetching unrated sentence data...')
    sentence_rows = db_action(get_select(TABLE_NAME))
    sentences = {}
    sentence_ids = []
    for id, text in sentence_rows:
        sentences[id] = text
        sentence_ids.append(id)
    all_id_pairs = get_unique_id_pairs(sentence_ids)
    # only return the pairs that do not have a junction table entry;
    # if include_unverified is True, unverified junction rows will also be
    # treated as unrated
    junction_where = 'is_verified = 1' if include_unverified else ''
    junction_rows = db_action(get_select(JUNCTION_TABLE_NAME, junction_where))
    rated_id_pairs = {(row[0], row[1]) for row in junction_rows}
    unrated_id_pairs = set()
    for id_1, id_2 in all_id_pairs:
        if not has_pair(rated_id_pairs, id_1, id_2):
            unrated_id_pairs.add((id_1, id_2))
    print('Unrated pair count: %d' % (len(unrated_id_pairs)))
    return sentences, unrated_id_pairs


def rate_unrated_pairs(batch_size=50, log_results=False):
    print('rating unrated pairs...')
    sentences, unrated_id_pairs = get_unrated_sentence_data()
    pairs = unrated_id_pairs
    if batch_size < len(unrated_id_pairs):
        pairs = list(unrated_id_pairs)[:batch_size]
    rated = list()
    for id_1, id_2 in pairs:
        sentence_1 = sentences[id_1]
        sentence_2 = sentences[id_2]
        is_match = is_keyword_match(sentence_1, sentence_2, log_results)
        if log_results:
            print('%s %s -> %d' % (sentence_1, sentence_2, int(is_match)))
        rated.append([id_1, id_2, is_match, 0])
    return db_action(store_similarity_from_data(rated))


def get_matching_sentence_pairs(is_verified=False):
    return db_action(read_sentence_pairs(1, int(is_verified)))


def get_non_matching_sentence_pairs(is_verified=False):
    return db_action(read_sentence_pairs(0, int(is_verified)))


def write_pairs_to_csv(sentence_pairs, is_match=1):
    print('writing sentence pairs to file...')
    filename = config['OUTPUT_SENTENCE_FILENAME']
    if not filename:
        print('Output sentence filename not defined.')
        return
    sentence_rows = db_action(get_select(TABLE_NAME))
    sentences = {}
    for id, text in sentence_rows:
        sentences[id] = text
    rows = []
    for pair in sentence_pairs:
        sentence_1 = sentences[pair[0]]
        sentence_2 = sentences[pair[1]]
        rows.append('%s,%s,%d' % (sentence_1, sentence_2, is_match))
    write_to_file(rows, filename)
    print('done')
