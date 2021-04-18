# Automatic sentence pair tagger
[![PEP8](https://img.shields.io/badge/code%20style-pep8-orange.svg)](https://www.python.org/dev/peps/pep-0008/)

A simple app that leverages an `SQLite` database and synonym searches to locate
semantic pair candidates.

It supports reading verified sentence pairs from an existing `.csv` file.

## **Notes:**

  Inverse sentence pairs are not stored in the DB; `s1-s2` is considered to be
  equivalent to `s2-s1`. Same-sentence pairs are also excluded, since they
  require no evaluation. The initial number of unrated pairs is equal to:
  
    item_count! / (2!(item_count - 2)!)
  
  For example, a corpus consisting of `3875` unique sentences should result in
  
    3875! / (2 x 3873!) = (3875 x 3874) / 2 = 7505875

  unrated pairs.

  If `250` rows are present in the verified sentence file, the number of unrated
  pairs after the call to the `initialize()` function should be `7505625`.

## **TODO:**

Implement the generation of two `.csv` files:
* a list of automatically rated sentence pairs that can then be manually verified
* a list of all the sentence pairs in the corpus, which should include both
same-sentence pairs (`s1-s1`) and inverse pairs (`s1-s2` and `s2-s1`)
