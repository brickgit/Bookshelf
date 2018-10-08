import time
import sqlite3
import argparse
from fetcher import fetcher

import environ
import psycopg2

root = environ.Path(__file__) - 3
base_path = root()
env = environ.Env(DEBUG=(bool, False), )
env_path = base_path + '/.envrc'
environ.Env.read_env(env_path)


def save(db, conn, books):
    count_book = 0
    count_category = 0
    for book in books:
        info = book.get('volumeInfo', None)
        if info is None:
            continue

        bk, categories = parse_book(info)
        if categories is not None:
            for category in categories:
                count_category += 1 if insert_category_psql(conn, category) else 0

        if bk is None:
            continue

        if db == "psql":
            count_book += 1 if insert_book_psql(conn, bk) else 0
        elif db == "sqlite":
            count_book += 1 if insert_book_sqlite(conn, bk) else 0
        else:
            pass

    return count_book, count_category


def insert_book_psql(conn, book):
    insert = '''INSERT INTO books_book (
                            title, subtitle, authors, publisher, published_date, description,
                            isbn10, isbn13, page_count, image_url, language, added_date,
                            verified, verified_date, rate_count, categories)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
    try:
        cur = conn.cursor()
        cur.execute(insert, (
            book['title'], book['subtitle'], book['authors'], book['publisher'], book['published_date'],
            book['description'], book['isbn10'], book['isbn13'], book['page_count'], book['image_url'],
            book['language'], book['added_date'], False, None, 0, book['categories']))
        conn.commit()
        return True
    except (psycopg2.IntegrityError, psycopg2.DataError):
        conn.rollback()
        return False


def insert_category_psql(conn, category):
    insert = '''INSERT INTO books_category (name) VALUES (%s)'''
    try:
        cur = conn.cursor()
        cur.execute(insert, (category,))
        conn.commit()
        return True
    except (psycopg2.IntegrityError, psycopg2.DataError):
        conn.rollback()
        return False


def insert_book_sqlite(conn, book):
    insert = '''INSERT INTO books_book (
                            title, subtitle, authors, publisher, published_date, description,
                            isbn10, isbn13, page_count, image_url, language, added_date,
                            verified, verified_date, rate_count, categories)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
    try:
        conn.execute(insert, (
            book['title'], book['subtitle'], book['authors'], book['publisher'], book['published_date'],
            book['description'], book['isbn10'], book['isbn13'], book['page_count'], book['image_url'],
            book['language'], book['added_date'], False, None, 0, book['categories']))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def parse_book(info):
    book = {}
    categories = None

    cate = info.get('categories', None)
    if cate is not None:
        book['categories'] = ', '.join(cate)
        categories = set(cate)
    else:
        book['categories'] = ''

    isbn10 = ''
    isbn13 = ''
    isbns = info.get('industryIdentifiers', None)
    if isbns is not None:
        for isbn in isbns:
            if isbn['type'] == 'ISBN_10':
                isbn10 = isbn['identifier']
            elif isbn['type'] == 'ISBN_13':
                isbn13 = isbn['identifier']

    if isbn10 == '' and isbn13 == '':
        return None, categories

    book['isbn10'] = isbn10
    book['isbn13'] = isbn13

    book['title'] = info.get('title', '')
    book['subtitle'] = info.get('subtitle', '')

    book['authors'] = ', '.join(info.get('authors', ''))

    book['publisher'] = info.get('publisher', '')
    book['published_date'] = info.get('publishedDate', '')
    if len(book['published_date']) < 10:
        return None, categories

    book['description'] = info.get('description', '')
    book['page_count'] = info.get('pageCount', 0)

    image_links = info.get('imageLinks', None)
    book['image_url'] = image_links.get('thumbnail', '') if image_links is not None else ''
    if book['image_url'] == '':
        return None, categories

    book['language'] = info.get('language', '')
    book['added_date'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

    return book, categories


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Query string")
    parser.add_argument("-d", "--database", help="Database", default="sqlite")
    args = parser.parse_args()
    return args.query, args.database


def main():
    query, db = get_arguments()

    if db == "psql":
        conn = psycopg2.connect(
            database=env("DATABASE_NAME"),
            user=env("DATABASE_USER"),
            host=env("DATABASE_URL"),
            password=env("DATABASE_PASSWORD"))
    elif db == "sqlite":
        sqlite_path = base_path + "/" + env("SQLITE_NAME")
        conn = sqlite3.connect(sqlite_path)
    else:
        return

    total = 0
    count_fetched = 0
    count_book_inserted = 0
    count_category_inserted = 0

    while count_fetched <= total:
        data = fetcher.fetch(query, count_fetched, env('GOOGLE_BOOKS_API_KEY'))
        books = data.get('items', None)
        if books is None:
            break

        count_book, count_category = save(db, conn, books)
        count_book_inserted += count_book
        count_category_inserted += count_category
        total = data.get('totalItems', 0)
        count_fetched += len(books)
        print(str(count_fetched) + ' / ' + str(total))

    conn.close()
    print(str(count_book_inserted) + " books inserted!")
    print(str(count_category_inserted) + " categories inserted!")


if __name__ == "__main__":
    main()
