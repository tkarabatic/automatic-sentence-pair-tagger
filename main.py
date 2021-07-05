from db import (
    get_matching_sentence_pairs,
    initialize,
    rate_unrated_pairs,
    write_pairs_to_csv
)


def main():
    # create the DB and populate it with data
    # initialize()

    # tag unrated sentence pairs as matching or non-matching
    # for i in range(65):
    #     rate_unrated_pairs(50000, False)

    # write matching pairs to output file
    matching_pairs = get_matching_sentence_pairs()
    write_pairs_to_csv(matching_pairs)


if __name__ == '__main__':
    main()
