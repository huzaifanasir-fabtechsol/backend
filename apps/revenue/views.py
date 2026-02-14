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
from apps.revenue.models import Car, CarCategory, Order, OrderItem
from apps.revenue.serializers import CarSerializer, CarCategorySerializer, OrderSerializer, OrderItemSerializer, CreateOrderSerializer
from apps.expense.models import Expense

class CarCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CarCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CarCategory.objects.filter(user=self.request.user)
        search = self.request.query_params.get('search')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
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
        print('############################################')
        print(items_data)
        transaction_type = data.get('transaction_type')

        # Move all extra fields into other_details
        other_details = {
            'customer_name': data.pop('customer_name', ''),
            'seller_name': data.pop('seller_name', ''),
            'phone': data.pop('phone', ''),
            'address': data.pop('address', ''),
            'payment_method': data.pop('payment_method', ''),
            'account_number': data.pop('account_number', ''),
            'auction_house': data.pop('auction_house', '')  # only applies for auction
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

        # Create order (only use fields that exist in the model)
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
                notes=data.get('notes', '')
            )

            for item_data in items_data:
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

    @action(detail=True, methods=['get'])
    def generate_invoice(self, request, pk=None):
        order = self.get_object()
        is_auction = order.transaction_type == 'auction'

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
        # Title
        # --------------------------------------------------
        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=16
        )

        elements.append(Paragraph("INVOICE", title_style))
        elements.append(Spacer(1, 12))

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

        doc.build(elements)
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
            fontSize=7,
            leading=9
        )

        header = [
            'No.', 'Venue', 'Year', 'Model', 'Chassis',
            'Auction\nFee', 'Vehicle\nPrice', 'Consumption\nTax',
            'Recycling\nFee', 'Auto\nTax', 'Bid\nFee',
            'Bid Fee\nTax', 'Total'
        ]

        data = [header]

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

            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        return table


    # ======================================================
    # STANDARD (SALE / PURCHASE) TABLE
    # ======================================================

    def _build_standard_table(self, order, doc, styles):

        header = [
            'No.', 'Car Name', 'Model', 'Chassis',
            'Year', 'Price', 'Tax', 'Total'
        ]

        data = [header]

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
        ws['A5'] = 'Total Revenue (Sales + Auctions)'
        ws['B5'] = float(revenue)
        ws['A6'] = 'Total Cost (Purchases + Expenses)'
        ws['B6'] = float(cost)
        ws['A7'] = 'Net Profit'
        ws['B7'] = float(profit)
        ws['B7'].font = Font(bold=True)
        
        ws['A9'] = 'Breakdown'
        ws['A9'].font = Font(bold=True)
        ws['A10'] = 'Sales'
        ws['B10'] = float(sales)
        ws['A11'] = 'Auctions'
        ws['B11'] = float(auctions)
        ws['A12'] = 'Purchases'
        ws['B12'] = float(purchases)
        ws['A13'] = 'Expenses'
        ws['B13'] = float(total_expenses)
        
        ws['A15'] = 'Orders Detail'
        ws['A15'].font = Font(bold=True)
        ws.append(['Order No.', 'Type', 'Date', 'Customer', 'Amount'])
        for order in orders:
            ws.append([order.order_number, order.transaction_type, order.transaction_date.strftime('%Y-%m-%d'), 
                      order.customer_name, float(order.total_amount)])
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Report {start}_{end}.xlsx"'
        wb.save(response)
        return response

class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderItem.objects.filter(order__user=self.request.user)
