from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.http import HttpResponse
from django.db.models import Sum, Q
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from apps.revenue.models import Car, CarCategory, Order, OrderItem, Customer, CompanyAccount, Auction
from apps.revenue.serializers import CarSerializer, CarCategorySerializer, OrderSerializer, OrderItemSerializer, CreateOrderSerializer, CustomerSerializer, CompanyAccountSerializer, AuctionSerializer
from apps.expense.models import Expense
from django.conf import settings
from apps.account.models import User

class CarCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CarCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CarCategory.objects.filter(user=self.request.user)
        search = self.request.query_params.get('search')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(company__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CarViewSet(viewsets.ModelViewSet):
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Car.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user).order_by('-created_at')
        
        payment_status = self.request.query_params.get('payment_status')
        transaction_type = self.request.query_params.get('transaction_type')
        transaction_catagory = self.request.query_params.get('transaction_catagory')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        search = self.request.query_params.get('search')
        
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        if transaction_catagory:
            queryset = queryset.filter(transaction_catagory=transaction_catagory)
        if start_date:
            queryset = queryset.filter(transaction_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(transaction_date__lte=end_date)
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(customer_name__icontains=search) |
                Q(notes__icontains=search)
            )
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        orders = Order.objects.filter(user=request.user)
        expenses = Expense.objects.filter(user=request.user)
        
        approved_amount = orders.filter(payment_status='completed').aggregate(total=Sum('total_amount'))['total'] or 0
        pending_amount = orders.filter(payment_status='pending').aggregate(total=Sum('total_amount'))['total'] or 0
        total_expense = expenses.aggregate(total=Sum('amount'))['total'] or 0
        total_purchase = orders.filter(transaction_type='purchase').aggregate(total=Sum('total_amount'))['total'] or 0
        latest_orders = orders.order_by('-transaction_date')[:10].values('transaction_date', 'transaction_type', 'payment_status', 'total_amount')
        
        return Response({
            'approved_amount': float(approved_amount),
            'pending_amount': float(pending_amount),
            'total_expense': float(total_expense),
            'total_purchase': float(total_purchase),
            'latest_orders': list(latest_orders)
        })

    @action(detail=False, methods=['post'])
    def create_with_items(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        items_data = data.pop('items')
        customer_id = data.pop('customer_id', None)
        company_account_id = data.pop('company_account_id', None)
        auction_id = data.pop('auction_id', None)

        # Validate foreign keys
        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id, user=request.user)
            except Customer.DoesNotExist:
                return Response({'error': 'Customer not found'}, status=status.HTTP_400_BAD_REQUEST)

        company_account = None
        if company_account_id:
            try:
                company_account = CompanyAccount.objects.get(id=company_account_id, user=request.user)
            except CompanyAccount.DoesNotExist:
                return Response({'error': 'Company account not found'}, status=status.HTTP_400_BAD_REQUEST)

        auction = None
        if auction_id:
            try:
                auction = Auction.objects.get(id=auction_id, user=request.user)
            except Auction.DoesNotExist:
                return Response({'error': 'Auction not found'}, status=status.HTTP_400_BAD_REQUEST)

        # Move all extra fields into other_details
        other_details = {
            'customer_name': data.pop('customer_name', ''),
            'seller_name': data.pop('seller_name', ''),
            'phone': data.pop('phone', ''),
            'address': data.pop('address', ''),
            'payment_method': data.pop('payment_method', ''),
            'account_number': data.pop('account_number', ''),
            'my_payment_method': data.pop('my_payment_method', ''),
            'my_account_number': data.pop('my_account_number', ''),
            'auction_house': data.pop('auction_house', '')
        }

        # Check categories exist
        category_ids = [item['category'] for item in items_data]
        existing_categories = CarCategory.objects.filter(id__in=category_ids, user=request.user).values_list('id', flat=True)
        missing_categories = set(category_ids) - set(existing_categories)
        if missing_categories:
            return Response(
                {'error': f'Categories with IDs {list(missing_categories)} do not exist or do not belong to you'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create order number
        today = datetime.now().date()
        date_str = today.strftime('%Y%m%d')
        last_order = Order.objects.filter(order_number__startswith=f'ORD-{date_str}').order_by('-order_number').first()
        new_num = int(last_order.order_number.split('-')[-1]) + 1 if last_order else 1
        order_number = f'ORD-{date_str}-{new_num:03d}'

        # Calculate total_amount
        total_amount = sum(
            item.get('auction_fee', 0) + item['vehicle_price'] +
            item.get('consumption_tax', 0) + item.get('recycling_fee', 0) +
            item.get('automobile_tax', 0) + item.get('bid_fee', 0) +
            item.get('bid_fee_tax', 0)
            for item in items_data
        )

        # Create order
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                order_number=order_number,
                total_amount=total_amount,
                other_details=other_details,
                transaction_type=data['transaction_type'],
                transaction_catagory=data['transaction_catagory'],
                transaction_date=data['transaction_date'],
                payment_status=data['payment_status'],
                notes=data.get('notes', ''),
                customer=customer,
                company_account=company_account,
                auction=auction
            )

            for item_data in items_data:
                category = CarCategory.objects.get(id=item_data['category'])
                car, _ = Car.objects.get_or_create(
                    user=request.user,
                    category_id=item_data['category'],
                    name=item_data['name'],
                    model=item_data['model'],
                    chassis_number=item_data['chassis_number'],
                    year=item_data['year']
                )

                subtotal = (
                    item_data.get('auction_fee', 0) + item_data['vehicle_price'] +
                    item_data.get('consumption_tax', 0) + item_data.get('recycling_fee', 0) +
                    item_data.get('automobile_tax', 0) + item_data.get('bid_fee', 0) +
                    item_data.get('bid_fee_tax', 0)
                )

                OrderItem.objects.create(
                    order=order,
                    car=car,
                    car_category=category,
                    venue=item_data.get('venue', ''),
                    year_type=item_data.get('year', ''),
                    auction_fee=item_data.get('auction_fee', 0),
                    vehicle_price=item_data['vehicle_price'],
                    consumption_tax=item_data.get('consumption_tax', 0),
                    recycling_fee=item_data.get('recycling_fee', 0),
                    automobile_tax=item_data.get('automobile_tax', 0),
                    bid_fee=item_data.get('bid_fee', 0),
                    bid_fee_tax=item_data.get('bid_fee_tax', 0),
                    subtotal=subtotal,
                    notes=item_data.get('notes', '')
                )

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def _add_watermark(self, canvas, doc, text="DRAFT"):
        canvas.saveState()  # Save current state

        # Set font and color
        canvas.setFont("Helvetica-Bold", 80)
        canvas.setFillColor(colors.lightgrey)
        canvas.setFillAlpha(0.5)  # Lighter watermark

        # Move to center of page
        width, height = doc.pagesize
        canvas.translate(width / 2, height / 2)

        # Rotate text diagonally
        canvas.rotate(45)

        # Draw centered watermark
        canvas.drawCentredString(0, 0, text)

        canvas.restoreState()

    @action(detail=True, methods=['get'])
    def generate_invoice(self, request, pk=None):
        order = self.get_object()
        is_auction = order.transaction_type == 'auction'
        user = User.objects.filter(role='admin').first()
        if not user:
            return Response({'error': 'Admin user not found'}, status=404)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice {order.order_number}.pdf"'

        pagesize = landscape(A4) if is_auction else A4

        doc = SimpleDocTemplate(
            response,
            pagesize=pagesize,
            topMargin=25,
            bottomMargin=25,
            leftMargin=30,
            rightMargin=30
        )

        elements = []
        styles = getSampleStyleSheet()

        # --------------------------------------------------
        # Company Details (Dynamic)
        # --------------------------------------------------

        company_name = user.company_name
        company_address = user.company_address
        company_phone = user.company_phone
        company_website = user.company_website
        company_email = user.company_email

        # Styles
        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=18,
            spaceAfter=6
        )

        company_style = ParagraphStyle(
            'CompanyStyle',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=9,
            textColor=colors.grey
        )

        sub_title_style = ParagraphStyle(
            'SubTitle',
            parent=styles['Heading2'],
            alignment=TA_CENTER,
            fontSize=14,
            spaceBefore=10,
            spaceAfter=12
        )

        # Company Header Section
        elements.append(Paragraph(company_name, title_style))
        elements.append(Paragraph(f"Address: {company_address}", company_style))
        elements.append(Paragraph(f"Phone: {company_phone}", company_style))
        elements.append(Paragraph(f"Email: {company_email}", company_style))
        elements.append(Paragraph(company_website, company_style))
        elements.append(Spacer(1, 12))

        elements.append(Paragraph("INVOICE", sub_title_style))
        elements.append(Spacer(1, 18))

        # --------------------------------------------------
        # Basic Info Section
        # --------------------------------------------------

        elements.append(self._build_info_table(order, styles))
        elements.append(Spacer(1, 18))

        # --------------------------------------------------
        # Items Table
        # --------------------------------------------------

        if is_auction:
            elements.append(self._build_auction_table(order, doc, styles))
        else:
            elements.append(self._build_standard_table(order, doc, styles))
        doc.build(
            elements,
            onFirstPage=lambda canvas, doc: self._add_watermark(canvas, doc, company_name),
            onLaterPages=lambda canvas, doc: self._add_watermark(canvas, doc, company_name),
        )

        return response


    # ======================================================
    # INFO TABLE
    # ======================================================

    def _build_info_table(self, order, styles):

        od = order.other_details or {}

        data = [
            ['Invoice No:', order.order_number, '', 'Date:', order.transaction_date.strftime('%Y-%m-%d')],
            ['Type:', order.get_transaction_type_display(), '', 'Category:', order.get_transaction_catagory_display()],
        ]

        if order.transaction_type == 'purchase':
            data += [
                ['Seller:', od.get('seller_name', ''), '', 'Phone:', od.get('phone', '')],
                ['Address:', od.get('address', ''), '', '', '']
            ]

        elif order.transaction_type in ['sale', 'auction']:
            data += [
                ['Buyer:', od.get('customer_name', ''), '', 'Phone:', od.get('phone', '')],
                ['Address:', od.get('address', ''), '', '', '']
            ]

            if order.transaction_type == 'auction':
                data.append(['Auction House:', od.get('auction_house', ''), '', '', ''])
            data.append(['Payment Status:', order.payment_status.capitalize(), '', '', ''])

        if od.get('payment_method'):
            data.append([
                'Payment Method:',
                od.get('payment_method', ''),
                '',
                'Account:',
                od.get('account_number', '')
            ])

        table = Table(data, colWidths=[90, 200, 40, 90, 150])

        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT')
        ]))

        return table


    # ======================================================
    # AUCTION TABLE
    # ======================================================

    def _build_auction_table(self, order, doc, styles):

        small_style = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=6,
            leading=9
        )

        header = [
            'No.', 'Venue', 'Year', 'Model', 'Chassis',
            'Auction\nFee', 'Vehicle\nPrice', 'Consumption\nTax',
            'Recycling\nFee', 'Auto\nTax', 'Bid\nFee',
            'Bid Fee\nTax', 'Total'
        ]
        header_style = ParagraphStyle(
            'HeaderSmall',
            parent=styles['Normal'],
            fontSize=6,      # smaller font
            leading=8,       # line spacing
            alignment=TA_CENTER,
            textColor=colors.whitesmoke,
        )

        header_row = [Paragraph(cell, header_style) for cell in header]
        data = [header_row]

        totals = {
            'auction_fee': 0,
            'vehicle_price': 0,
            'consumption_tax': 0,
            'recycling_fee': 0,
            'automobile_tax': 0,
            'bid_fee': 0,
            'bid_fee_tax': 0,
            'subtotal': 0
        }

        for idx, item in enumerate(order.items.all(), 1):

            data.append([
                str(idx),
                Paragraph(item.venue or '', small_style),
                item.year_type or '',
                Paragraph(item.car.model or '', small_style),
                Paragraph(item.car.chassis_number or '', small_style),
                f'{item.auction_fee:,.0f}',
                f'{item.vehicle_price:,.0f}',
                f'{item.consumption_tax:,.0f}',
                f'{item.recycling_fee:,.0f}',
                f'{item.automobile_tax:,.0f}',
                f'{item.bid_fee:,.0f}',
                f'{item.bid_fee_tax:,.0f}',
                f'{item.subtotal:,.0f}',
            ])

            for key in totals.keys():
                totals[key] += getattr(item, key)

        data.append([
            '', '', '', '', 'Total:',
            f'{totals["auction_fee"]:,.0f}',
            f'{totals["vehicle_price"]:,.0f}',
            f'{totals["consumption_tax"]:,.0f}',
            f'{totals["recycling_fee"]:,.0f}',
            f'{totals["automobile_tax"]:,.0f}',
            f'{totals["bid_fee"]:,.0f}',
            f'{totals["bid_fee_tax"]:,.0f}',
            f'{totals["subtotal"]:,.0f}',
        ])

        available_width = doc.width

        fixed_width = 25 + 60 + 35 + 100 + 110
        remaining = available_width - fixed_width
        numeric_width = remaining / 8

        col_widths = [
            25, 60, 35, 100, 110
        ] + [numeric_width] * 8

        table = Table(data, colWidths=col_widths, repeatRows=1)

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),

            # Text columns left
            ('ALIGN', (1, 1), (4, -2), 'LEFT'),

            # Numbers right
            ('ALIGN', (5, 1), (-1, -2), 'RIGHT'),

            # Header center
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Total row styling
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (5, -1), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 1), (-1, -2), 7),  # Data rows
            ('FONTSIZE', (0, -1), (-1, -1), 7),  # Total row

            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        return table


    # ======================================================
    # STANDARD (SALE / PURCHASE) TABLE
    # ======================================================

    def _build_standard_table(self, order, doc, styles):
        header_style = ParagraphStyle(
            'HeaderSmall',
            parent=styles['Normal'],
            fontSize=6,      # smaller font
            leading=8,       # line spacing
            alignment=TA_CENTER,
            textColor=colors.whitesmoke,
        )

        header = [
            'No.', 'Car Name', 'Model', 'Chassis',
            'Year', 'Price', 'Tax', 'Total'
        ]
        header_row = [Paragraph(cell, header_style) for cell in header]
        data = [header_row]

        totals = {
            'vehicle_price': 0,
            'consumption_tax': 0,
            'subtotal': 0
        }

        for idx, item in enumerate(order.items.all(), 1):
            data.append([
                str(idx),
                item.car.name,
                item.car.model,
                item.car.chassis_number,
                str(item.car.year),
                f'{item.vehicle_price:,.2f}',
                f'{item.consumption_tax:,.2f}',
                f'{item.subtotal:,.2f}',
            ])

            totals['vehicle_price'] += item.vehicle_price
            totals['consumption_tax'] += item.consumption_tax
            totals['subtotal'] += item.subtotal

        data.append([
            '', '', '', '', 'Total:',
            f'{totals["vehicle_price"]:,.2f}',
            f'{totals["consumption_tax"]:,.2f}',
            f'{totals["subtotal"]:,.2f}',
        ])

        available_width = doc.width
        col_widths = [
            30,
            available_width * 0.20,
            available_width * 0.15,
            available_width * 0.18,
            50,
            available_width * 0.12,
            available_width * 0.12,
            available_width * 0.12,
        ]

        table = Table(data, colWidths=col_widths, repeatRows=1)

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),

            ('ALIGN', (1, 1), (4, -2), 'LEFT'),
            ('ALIGN', (5, 1), (-1, -2), 'RIGHT'),
            ('FONTSIZE', (0, 1), (-1, -2), 7),  # Data rows
            ('FONTSIZE', (0, -1), (-1, -1), 7),  # Total row

            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (5, -1), (-1, -1), 'RIGHT'),

            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        return table

    @action(detail=False, methods=['get'])
    def financial_report(self, request):
        period = request.query_params.get('period', 'month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        today = datetime.now().date()
        
        if start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        elif period == 'today':
            start = end = today
        elif period == 'month':
            start = today.replace(day=1)
            end = today
        elif period == 'year':
            start = today.replace(month=1, day=1)
            end = today
        else:
            start = today.replace(day=1)
            end = today
        
        orders = Order.objects.filter(user=request.user, transaction_date__range=[start, end])
        expenses = Expense.objects.filter(user=request.user, date__range=[start, end])
        
        sales = orders.filter(transaction_type='sale').aggregate(total=Sum('total_amount'))['total'] or 0
        purchases = orders.filter(transaction_type='purchase').aggregate(total=Sum('total_amount'))['total'] or 0
        auctions = orders.filter(transaction_type='auction').aggregate(total=Sum('total_amount'))['total'] or 0
        total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
        
        revenue = sales + auctions
        cost = purchases + total_expenses
        profit = revenue - cost
        
        wb = Workbook()
        ws = wb.active
        ws.title = 'Financial Report'
        
        ws['A1'] = 'Financial Report'
        ws['A1'].font = Font(size=16, bold=True)
        ws['A2'] = f'Period: {start} to {end}'
        
        ws['A4'] = 'Summary'
        ws['A4'].font = Font(bold=True)
        ws['A5'] = 'Currency'
        ws['B5'] = '$'
        ws['A6'] = 'Total Revenue (Sales + Auctions)'
        ws['B6'] = f'$ {float(revenue)}'
        ws['A7'] = 'Total Cost (Purchases + Expenses)'
        ws['B7'] = f'$ {float(cost)}'
        ws['A8'] = 'Net Profit'
        ws['B8'] = f'$ {float(profit)}'
        ws['B9'].font = Font(bold=True)
        
        ws['A10'] = 'Breakdown'
        ws['A10'].font = Font(bold=True)
        ws['A11'] = 'Sales'
        ws['B11'] = f'$ {float(sales)}'
        ws['A12'] = 'Auctions'
        ws['B12'] = f'$ {float(auctions)}'
        ws['A13'] = 'Purchases'
        ws['B13'] = f'$ {float(purchases)}'
        ws['A14'] = 'Expenses'
        ws['B14'] = f'$ {float(total_expenses)}'
        
        ws['A16'] = 'Transactions Detail'
        ws['A16'].font = Font(bold=True)
        ws.append(['Type', 'Date', 'Payment Status', 'Amount'])
        
        for order in orders:
            ws.append([order.transaction_type.capitalize(), order.transaction_date.strftime('%Y-%m-%d'), 
                      order.payment_status, f'$ {float(order.total_amount)}'])
        
        for exp in expenses:
            ws.append(['Expense', exp.date.strftime('%Y-%m-%d'), 'completed', f'$ {float(exp.amount)}'])
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Report {start}_{end}.xlsx"'
        wb.save(response)
        return response



    @action(detail=False, methods=['get'])
    def reports(self, request):
        from rest_framework.pagination import PageNumberPagination
        
        report_type = request.query_params.get('type', 'orders')
        period = request.query_params.get('period', 'month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        payment_status = request.query_params.get('payment_status')
        search = request.query_params.get('search')
        page_size = int(request.query_params.get('pageSize', 10))
        
        today = datetime.now().date()
        
        if start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        elif period == 'today':
            start = end = today
        elif period == 'month':
            start = today.replace(day=1)
            end = today
        elif period == 'year':
            start = today.replace(month=1, day=1)
            end = today
        else:
            start = today.replace(day=1)
            end = today
        
        data = []
        
        if report_type in ['all', 'expenses']:
            if period == 'all':
                expenses = Expense.objects.filter(user=request.user)
            else:
                expenses = Expense.objects.filter(user=request.user, date__range=[start, end])
            if search:
                expenses = expenses.filter(Q(description__icontains=search))
            for exp in expenses:
                data.append({
                    'transaction_type': 'expense',
                    'transaction_date': exp.date,
                    'payment_status': 'completed',
                    'total_amount': exp.amount
                })
        
        if report_type in ['all', 'orders', 'sales', 'purchases', 'auctions']:
            if period == 'all':
                queryset = Order.objects.filter(user=request.user)
            else:
                queryset = Order.objects.filter(user=request.user, transaction_date__range=[start, end])
            
            if report_type == 'sales':
                queryset = queryset.filter(transaction_type='sale')
            elif report_type == 'purchases':
                queryset = queryset.filter(transaction_type='purchase')
            elif report_type == 'auctions':
                queryset = queryset.filter(transaction_type='auction')
            
            if payment_status:
                queryset = queryset.filter(payment_status=payment_status)
            if search:
                queryset = queryset.filter(Q(order_number__icontains=search) | Q(customer_name__icontains=search))
            
            for order in queryset.values('transaction_type', 'transaction_date', 'payment_status', 'total_amount'):
                data.append(order)
        
        data.sort(key=lambda x: x['transaction_date'], reverse=True)
        
        paginator = PageNumberPagination()
        paginator.page_size = page_size
        paginated = paginator.paginate_queryset(data, request)
        
        return paginator.get_paginated_response(paginated)


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderItem.objects.filter(order__user=self.request.user)


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Customer.objects.filter(user=self.request.user)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CompanyAccountViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CompanyAccount.objects.filter(user=self.request.user)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(bank_name__icontains=search) |
                Q(account_number__icontains=search)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AuctionViewSet(viewsets.ModelViewSet):
    serializer_class = AuctionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Auction.objects.filter(user=self.request.user)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
