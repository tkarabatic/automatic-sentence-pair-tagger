from db import initialize, rate_unrated_pairs


def main():
    # create the DB and populate it with data
    initialize()

    # tag unrated sentence pairs as matching or non-matching
    rate_unrated_pairs(50, True)


if __name__ == '__main__':
    main()
