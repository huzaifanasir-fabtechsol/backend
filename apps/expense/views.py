from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from apps.expense.models import Expense, ExpenseCategory, Restaurant
from apps.expense.serializers import ExpenseSerializer, ExpenseCategorySerializer, RestaurantSerializer
from apps.revenue.models import Transaction
from apps.revenue.serializers import TransactionSerializer
from apps.account.models import User

class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExpenseCategory.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _add_watermark(self, canvas, doc, text="INVOICE"):
            canvas.saveState()
            canvas.setFont("HeiseiMin-W3", 80)
            canvas.setFillColor(colors.lightgrey)
            canvas.setFillAlpha(0.15)

            width, height = doc.pagesize
            canvas.translate(width / 2, height / 2)
            canvas.rotate(45)
            canvas.drawCentredString(0, 0, text)

            canvas.restoreState()

    def _add_page_decorations(self, canvas, doc):
        from django.conf import settings
        import os
        from reportlab.lib.utils import ImageReader
        self._add_watermark(canvas, doc, "Ilyas Sons 合同会社")

        logo_path = os.path.join(settings.MEDIA_ROOT, "logo.png")
        if os.path.exists(logo_path):
            logo = ImageReader(logo_path)

            logo_width = 120
            logo_height = 40

            x = doc.leftMargin
            y = doc.pagesize[1] - logo_height - 10

            canvas.drawImage(
                logo,
                x,
                y,
                width=logo_width,
                height=logo_height,
                mask='auto'
            )


    @action(detail=True, methods=['get'])
    def generate_receipt(self, request, pk=None):
        expense = self.get_object()
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
        user = request.user

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="expense_{expense.id}.pdf"'

        doc = SimpleDocTemplate(response, pagesize=A4, topMargin=20, bottomMargin=20, leftMargin=20, rightMargin=20)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle('Title', parent=styles['Normal'], fontSize=24, alignment=TA_CENTER, fontName='HeiseiMin-W3')
        elements.append(Paragraph("経費領収書", title_style))
        elements.append(Spacer(1, 15))

        # Company info on right
        header_data = [
            ["", "", user.company_name],
            ["", "", user.company_address],
            ["", "", f"TEL/FAX: {user.company_phone}"],
            ["", "", user.business_registration],
            ["", "", f"Date: {expense.date}"]
        ]
        header_table = Table(header_data, colWidths=[doc.width * 0.4, doc.width * 0.2, doc.width * 0.4])
        header_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (2, 0), (2, -1), 'HeiseiMin-W3')
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10))

        from reportlab.platypus import HRFlowable
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
        elements.append(Spacer(1, 15))

        # Expense details
        detail_data = [
            ["タイトル:", expense.title],
            ["額:", f"¥ {expense.amount:,.0f}"],
            ["カテゴリ:", expense.category.name if expense.category else 'N/A'],
            ["説明:", expense.description or '-']
        ]

        if expense.transaction:
            detail_data.extend([
                ["トランザクションID:", str(expense.transaction.id)],
                ["取引:", expense.transaction.description],
                ["取引金額:", f"¥ {expense.transaction.withdraw:,.0f}"]
            ])

        if expense.restaurant:
            detail_data.append(["レストラン:", expense.restaurant.name])

        detail_table = Table(detail_data, colWidths=[doc.width * 0.3, doc.width * 0.7])
        detail_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('FONTNAME', (0, 0), (-1, -1), 'HeiseiMin-W3'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8)
        ]))
        elements.append(detail_table)
        doc.build(
            elements,
            onFirstPage=self._add_page_decorations,
            onLaterPages=self._add_page_decorations,
        )
        return response

    @action(detail=False, methods=['get'])
    def export_pdf(self, request):
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
        user = request.user

        # Apply filters
        queryset = self.get_queryset()
        date = request.query_params.get('date')
        category = request.query_params.get('category')
        search = request.query_params.get('search')

        if date:
            queryset = queryset.filter(date=date)
        if category:
            queryset = queryset.filter(category_id=category)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(category__name__icontains=search)
            )

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="expenses.pdf"'

        doc = SimpleDocTemplate(response, pagesize=A4, topMargin=20, bottomMargin=20, leftMargin=20, rightMargin=20)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle('タイトル', parent=styles['Normal'], fontSize=24, alignment=TA_CENTER, fontName='HeiseiMin-W3')
        elements.append(Paragraph("経費請求書", title_style))
        elements.append(Spacer(1, 15))

        # Header with company info and filters
        header_data = []
        left_col = []
        if date:
            left_col.append(f"日付: {date}")
        if category:
            cat = ExpenseCategory.objects.filter(id=category).first()
            if cat:
                left_col.append(f"カテゴリ: {cat.name}")
        # left_col.append(f"Generated: {request.user.email}")

        right_col = [user.company_name, user.company_address, f"TEL/FAX: {user.company_phone}", user.business_registration]

        max_rows = max(len(left_col), len(right_col))
        for i in range(max_rows):
            header_data.append([
                left_col[i] if i < len(left_col) else "",
                "",
                right_col[i] if i < len(right_col) else ""
            ])

        header_table = Table(header_data, colWidths=[doc.width * 0.4, doc.width * 0.2, doc.width * 0.4])
        header_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'HeiseiMin-W3')
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10))

        from reportlab.platypus import HRFlowable
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
        elements.append(Spacer(1, 15))

        # Table
        table_data = [['Sr', '日付', 'タイトル', 'カテゴリ', '取引', 'レストラン', '額']]
        total = 0
        for idx, expense in enumerate(queryset, 1):
            table_data.append([
                str(idx),
                str(expense.date),
                expense.title,
                expense.category.name if expense.category else '-',
                f"{expense.transaction.id}" if expense.transaction else '-',
                expense.restaurant.name if expense.restaurant else '-',
                f"¥ {expense.amount:,.0f}"
            ])
            total += expense.amount

        table_data.append(['', '', '', '', '', '合計:', f"¥ {total:,.0f}"])

        table = Table(table_data, colWidths=[30, 60, 100, 80, 70, 80, 70])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'HeiseiMin-W3'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('FONTNAME', (0, 1), (-1, -1), 'HeiseiMin-W3'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
        ]))
        elements.append(table)

        doc.build(
            elements,
            onFirstPage=self._add_page_decorations,
            onLaterPages=self._add_page_decorations,
        )
        return response

    @action(detail=False, methods=['get'])
    def available_transactions(self, request):
        search = request.query_params.get('search', '')
        date = request.query_params.get('date', '')
        account_id = request.query_params.get('account_id', '')
        
        queryset = Transaction.objects.filter(user=request.user)
        
        if account_id:
            queryset = queryset.filter(company_account_id=account_id)
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(notes__icontains=search)
            )
        if date:
            queryset = queryset.filter(date=date)
            
        serializer = TransactionSerializer(queryset, many=True)
        return Response(serializer.data)

class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Restaurant.objects.filter(user=self.request.user)
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(location__icontains=search)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
