from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Author, Book, Member, Loan
from .serializers import AuthorSerializer, BookSerializer, MemberSerializer, LoanSerializer
from rest_framework.decorators import action
from django.utils import timezone
from .tasks import send_loan_notification
from django.core.cache import cache
from rest_framework.pagination import PageNumberPagination
from django.conf import settings


class BookPagination(PageNumberPagination):
    page_size = settings.PAGE_SIZE
    page_size_query_param = 'page_size'
    max_page_size = settings.MAX_PAGE_SIZE

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    @action(detail=True, methods=['post'])
    def loan(self, request, pk=None):
        book = self.get_object()
        if book.available_copies < 1:
            return Response({'error': 'No available copies.'}, status=status.HTTP_400_BAD_REQUEST)
        member_id = request.data.get('member_id')
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan = Loan.objects.create(book=book, member=member)
        book.available_copies -= 1
        book.save()
        send_loan_notification.delay(loan.id)
        return Response({'status': 'Book loaned successfully.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get('member_id')
        try:
            loan = Loan.objects.get(book=book, member__id=member_id, is_returned=False)
        except Loan.DoesNotExist:
            return Response({'error': 'Active loan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.is_returned = True
        loan.return_date = timezone.now().date()
        loan.save()
        book.available_copies += 1
        book.save()
        return Response({'status': 'Book returned successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='list')
    def list_books(self, request):
        
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        cache_key = f'books_page_{page}_size_{page_size}'  # Unique cache key per page

        cached_books = cache.get(cache_key)
        if cached_books:
            return Response(cached_books, status=status.HTTP_200_OK)

        books = Book.objects.select_related('author').all()
        paginator = BookPagination()
        paginated_books = paginator.paginate_queryset(books, request)

        result = [
            {
                'title': book.title,
                'author': {
                    'first_name': book.author.first_name,
                    'first_name': book.author.last_name
                }
            }
            for book in paginated_books
        ]

        response = paginator.get_paginated_response(result).data
        # Store response in cache (valid for 60 seconds)
        # we can store for more time and use write throught technique to get update data from cache
        cache.set(cache_key, response, timeout=60)
        return Response(response, status=status.HTTP_200_OK)

        



class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer

    @action(detail=True, methods=['post'], url_path='extend-due-date')
    def extend_due_date (self, request, pk=None):
        loan = self.get_object()
        additional_days = request.data.get('additional_days')
        try:
            loan.due_date = loan.due_date + timedelta(days=additional_days)
            loan.save()
            return Response({'status': 'Loan exntended successfully.'}, status=status.HTTP_200_OK)

        except Loan.DoesNotExist:
            return Response({'error': 'Active loan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        
        


