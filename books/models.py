from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Book(models.Model):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200, blank=True)
    authors = models.CharField(max_length=200, blank=True)
    publisher = models.CharField(max_length=100, blank=True)
    published_date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=5000, blank=True)
    isbn10 = models.CharField(max_length=10, null=True, default=None, unique=True, blank=True)
    isbn13 = models.CharField(max_length=13, null=True, default=None, unique=True, blank=True)
    page_count = models.IntegerField(blank=True)
    image_url = models.URLField(blank=True)
    language = models.CharField(max_length=10, blank=True)
    categories = models.CharField(max_length=100, blank=True)
    added_date = models.DateField(blank=True, null=True)
    updated_date = models.DateField(blank=True, null=True)
    verified = models.BooleanField(default=False)
    verified_date = models.DateField(blank=True, null=True)
    rate = models.FloatField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    rate_count = models.IntegerField(default=0)

    def __str__(self):
        return self.title + " by " + self.authors


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)


class Reader(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True)

    def __str__(self):
        return self.user.username


class Bookshelf(models.Model):
    reader = models.ForeignKey(Reader, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    added_date = models.DateField(blank=True, null=True)
    rate = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        unique_together = ("reader", "book")

    def __str__(self):
        return self.reader.user.username + " added " + self.book.title + " on " + str(self.added_date)


class Reading(models.Model):
    bookshelf = models.ForeignKey(Bookshelf, on_delete=models.CASCADE)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    READING = 'R'
    FINISHED = 'F'
    ABANDONED = 'A'
    PROGRESS_CHOICES = (
        (READING, 'Reading'),
        (FINISHED, 'Finished'),
        (ABANDONED, 'Abandoned'),
    )
    progress = models.CharField(max_length=1, choices=PROGRESS_CHOICES, default=READING)

    def __str__(self):
        return self.bookshelf.reader.user.username + " read " + self.bookshelf.book.title + \
               " in " + str(self.start_date) + " - " + str(self.end_date)
