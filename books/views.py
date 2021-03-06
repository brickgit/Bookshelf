import datetime
import isbnlib
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.contrib import auth
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.forms.models import model_to_dict
from django.db.models import Q

from .models import Book, Reader, Bookshelf, Reading


def index(request):
    books = Book.objects.filter(verified=True).order_by('-published_date')[:30]
    return render(request, 'books/index.html', {'books': books})


def search(request):
    page = int(request.GET.get('p', '1'))
    if page < 1:
        page = 1

    query = request.POST.get('q', '')
    if query == '' and 'q' in request.GET:
        query = request.GET.get('q', '')

    if isbnlib.is_isbn10(query) or isbnlib.is_isbn13(query):
        try:
            book = Book.objects.filter(verified=True).get(Q(isbn10=query) | Q(isbn13=query))
            if request.user.is_authenticated:
                user = request.user
                bookshelf_set = Bookshelf.objects.filter(reader__user=user).filter(book=book)
                book.owned = bookshelf_set.count() == 1

            return render(request, 'books/detail.html', {'book': book})
        except Book.DoesNotExist:
            pass

    books = []
    total = 0

    if query != '':
        query_set = Book.objects.filter(
            Q(title__icontains=query)
            | Q(subtitle__icontains=query)
            | Q(authors__icontains=query)).filter(verified=True).order_by('-added_date')
        total = query_set.count()
        books = query_set[(10 * (page - 1)):10 * page]

    return render(request, 'books/search.html', {'q': query, 'books': books, 'total': total, 'page': page})


def detail(request, book_isbn13):
    try:
        book = Book.objects.filter(verified=True).get(isbn13=book_isbn13)
    except Book.DoesNotExist:
        book = None

    if request.user.is_authenticated and book is not None:
        user = request.user
        bookshelf_set = Bookshelf.objects.filter(reader__user=user).filter(book=book)
        book.owned = bookshelf_set.count() == 1

    return render(request, 'books/detail.html', {'book': book})


def add_book(request, book_isbn13):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')

    redirect = request.GET.get('redirect', '/')
    if redirect == '':
        redirect = '/'

    try:
        book = Book.objects.filter(verified=True).get(isbn13=book_isbn13)
    except Book.DoesNotExist:
        book = None

    if book is not None:
        reader = Reader.objects.get(user__id=request.user.id)
        if reader is not None:
            try:
                bookshelf = Bookshelf(reader=reader, book=book, added_date=datetime.date.today())
                bookshelf.save()
            except IntegrityError:
                pass

    return HttpResponseRedirect(redirect)


def remove_book(request, book_isbn13):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')

    redirect = request.GET.get('redirect', '/')
    if redirect == '':
        redirect = '/'

    try:
        book = Book.objects.filter(verified=True).get(isbn13=book_isbn13)
    except Book.DoesNotExist:
        book = None

    if book is not None:
        reader = Reader.objects.get(user__id=request.user.id)
        if reader is not None:
            bookshelf_set = Bookshelf.objects.filter(reader=reader).filter(book=book)
            if bookshelf_set.count() == 1:
                bookshelf_set.delete()

    return HttpResponseRedirect(redirect)


def rate_book(request, book_isbn13):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login first'})

    rate = request.POST.get('rate', None)
    if rate is not None:
        bookshelf_set = None
        try:
            reader = Reader.objects.get(user__id=request.user.id)
            book = Book.objects.filter(verified=True).get(isbn13=book_isbn13)
            if reader is not None and book is not None:
                bookshelf_set = Bookshelf.objects.filter(reader=reader).filter(book=book)
        except Book.DoesNotExist:
            pass

        if bookshelf_set is not None and bookshelf_set.count() == 1:
            bookshelf_set.update(rate=rate)

        bookshelf_set = Bookshelf.objects.filter(book=book)
        all_rates = 0.0
        count = 0
        for bookshelf in bookshelf_set:
            if bookshelf.rate is not None:
                all_rates += bookshelf.rate
                count += 1

        average_rate = all_rates / count
        book.rate = average_rate
        book.rate_count = count
        book.save()

    data = {
        'rate': rate,
    }

    return JsonResponse(data)


def reading(request, book_isbn13):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login first'})

    try:
        book = Book.objects.filter(verified=True).get(isbn13=book_isbn13)
        reader = Reader.objects.get(user__id=request.user.id)
        bookshelf = Bookshelf.objects.filter(book=book).filter(reader=reader).get()
        rate = bookshelf.rate
        reading_set = Reading.objects.filter(bookshelf__reader=reader).filter(bookshelf__book=book).order_by('-id')
        readings = [{"id": r.id, "start_date": r.start_date, "end_date": r.end_date, "progress": r.progress} for r in reading_set]
    except Book.DoesNotExist:
        book = None
        rate = None
        readings = None

    data = {
        'book': model_to_dict(book),
        'rate': rate,
        'readings': readings,
    }

    return JsonResponse(data)


def all_readings(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login first'})

    reader = Reader.objects.get(user__id=request.user.id)
    reading_set = Reading.objects.filter(bookshelf__reader=reader).order_by('-start_date')
    readings = [{"id": r.id, "book_title": r.bookshelf.book.title, "start_date": r.start_date, "end_date": r.end_date,
                 "progress": r.progress} for r in reading_set]

    data = {
        'readings': readings,
    }

    return JsonResponse(data)


def update_reading(request, book_isbn13):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login first'})

    reading_id = request.POST.get('reading-id', '')
    start_date = request.POST.get('start-date', '')
    end_date = request.POST.get('end-date', '')

    new_start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    new_end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d') if end_date != '' else None

    bookshelf_set = None
    try:
        reader = Reader.objects.get(user__id=request.user.id)
        book = Book.objects.filter(verified=True).get(isbn13=book_isbn13)
        if reader is not None and book is not None:
            bookshelf_set = Bookshelf.objects.filter(reader=reader).filter(book=book)
    except Book.DoesNotExist:
        pass

    if bookshelf_set is not None and bookshelf_set.count() == 1:
        reading_set = Reading.objects.filter(id=reading_id, bookshelf=bookshelf_set[0])
        if reading_set.count() == 1:
            reading_set.update(start_date=new_start_date, end_date=new_end_date)

    return reading(request, book_isbn13)


def start_reading(request, book_isbn13):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login first'})

    bookshelf_set = None
    try:
        reader = Reader.objects.get(user__id=request.user.id)
        book = Book.objects.filter(verified=True).get(isbn13=book_isbn13)
        if reader is not None and book is not None:
            bookshelf_set = Bookshelf.objects.filter(reader=reader).filter(book=book)
    except Book.DoesNotExist:
        pass

    if bookshelf_set is not None and bookshelf_set.count() == 1:
        try:
            new_reading = Reading(bookshelf=bookshelf_set[0], start_date=datetime.date.today(), end_date=None, progress='R')
            new_reading.save()
        except IntegrityError:
            pass

    return reading(request, book_isbn13)


def abandon_reading(request, book_isbn13):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login first'})

    bookshelf_set = None
    try:
        reader = Reader.objects.get(user__id=request.user.id)
        book = Book.objects.filter(verified=True).get(isbn13=book_isbn13)
        if reader is not None and book is not None:
            bookshelf_set = Bookshelf.objects.filter(reader=reader).filter(book=book)
    except Book.DoesNotExist:
        pass

    if bookshelf_set is not None and bookshelf_set.count() == 1:
        reading_set = Reading.objects.filter(bookshelf=bookshelf_set[0], end_date=None)
        if reading_set.count() == 1:
            reading_set.update(end_date=datetime.date.today(), progress='A')

    return reading(request, book_isbn13)


def finish_reading(request, book_isbn13):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login first'})

    bookshelf_set = None
    try:
        reader = Reader.objects.get(user__id=request.user.id)
        book = Book.objects.filter(verified=True).get(isbn13=book_isbn13)
        if reader is not None and book is not None:
            bookshelf_set = Bookshelf.objects.filter(reader=reader).filter(book=book)
    except Book.DoesNotExist:
        pass

    if bookshelf_set is not None and bookshelf_set.count() == 1:
        reading_set = Reading.objects.filter(bookshelf=bookshelf_set[0], end_date=None)
        if reading_set.count() == 1:
            reading_set.update(end_date=datetime.date.today(), progress='F')

    return reading(request, book_isbn13)


def delete_reading(request, book_isbn13):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login first'})

    reading_id = request.POST.get('reading-id', '')

    bookshelf_set = None
    try:
        reader = Reader.objects.get(user__id=request.user.id)
        book = Book.objects.filter(verified=True).get(isbn13=book_isbn13)
        if reader is not None and book is not None:
            bookshelf_set = Bookshelf.objects.filter(reader=reader).filter(book=book)
    except Book.DoesNotExist:
        pass

    if bookshelf_set is not None and bookshelf_set.count() == 1:
        reading_set = Reading.objects.filter(id=reading_id, bookshelf=bookshelf_set[0])
        if reading_set.count() == 1:
            reading_set.delete()

    return reading(request, book_isbn13)


def my_books(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')

    reader = Reader.objects.get(user__id=request.user.id)
    books = Bookshelf.objects.filter(book__verified=True).filter(reader=reader).order_by('-id')

    return render(request, 'readers/my_books.html', {'books': books})


def login(request):
    redirect = request.POST.get('redirect', '/')
    if redirect == '':
        redirect = '/'

    if request.user.is_authenticated:
        return HttpResponseRedirect(redirect)

    username = request.POST.get('username', '')
    password = request.POST.get('password', '')

    user = auth.authenticate(username=username, password=password)

    if user is not None and user.is_active:
        auth.login(request, user)

    return HttpResponseRedirect(redirect)


def logout(request):
    auth.logout(request)
    redirect = request.GET.get('redirect', '/')
    if redirect == '':
        redirect = '/'
    return HttpResponseRedirect(redirect)


def register(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/')

    username = request.POST.get('username', '')
    email = request.POST.get('email', '')
    password = request.POST.get('password', '')
    error = ''

    if username != '' and email != '' and password != '':
        try:
            user = User.objects.create_user(username, email, password)

            reader = Reader(user=user)
            reader.save()

            auth.login(request, user)

            return HttpResponseRedirect('/')
        except IntegrityError:
            error = 'Please try another username'

    return render(request, 'readers/register.html', {'error': error})
