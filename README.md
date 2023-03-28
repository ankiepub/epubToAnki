# epubToAnki
Help language learning by creating Anki flash cards for words in epub files.

See main.py for getting started.

Here is the basic workflow:
1. Install python packages. See pip_freeze_out.txt for packages I had installed. I don't know if all are needed.

2. Set up directories like this:

Your root directorie contains the python files plus directory folders like this (for Spanish):
/cache/spanish :cache is stored here
/spanish
/spanish/already_imported
/spanish/output
/spanish/books

3. Put some books in /spanish/books/

Currently, only epub is supported.

Books should be ordered alphabetically. If you add a series, you can naem them like this:
- 01 the saga begins.epub
- 02 another book.epub
- 03 the third book.epub

4. Edit settings.py to point to your Anki media folder and add a deepl key

Google Translate works OK but Deepl is better at preserving the span tags which help for sample sentences.

5. Edit main.py to tell it what to do.

You can either output words by chapter or by frequency across all books. I did by chapter for the first book and then by frequency for the rest of the books.

6. Run main.py to generate a csv file (and mp3 files)

Usually if you have too many worrds, something will timeout. If this happens, rerun it in a little while.

7. Upload the csv file to Anki.

Note that the CSV file has the following fields:

1 word, 2 translation, 3 audio, 4 lemma, 5 context, 6 sample sentence, 7 sample sentence in english, 8 etymology

You will need fields for all of these when you import.

8. Move the file into /spanish/already_imported/

9. Start learning on Anki

10. Run the script for the next chapter/block of words to import
