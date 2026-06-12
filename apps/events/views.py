from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q, Min
from .models import Event, Category, Seat


class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            Event.objects.filter(is_published=True)
            .select_related('category')
            .annotate(min_seat_price=Min('seats__price'))
        )
        q = self.request.GET.get('q', '').strip()
        category_slug = self.request.GET.get('category', '').strip()

        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(location__icontains=q)
            )
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['search_query'] = self.request.GET.get('q', '')
        context['current_category'] = self.request.GET.get('category', '')
        return context


class EventDetailView(DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        seats = Seat.objects.filter(event=event)
        context['total_seats'] = seats.count()
        context['available_seats'] = seats.filter(status=Seat.STATUS_AVAILABLE).count()

        # Prix minimum disponible
        available = seats.filter(status=Seat.STATUS_AVAILABLE)
        if available.exists():
            context['min_price'] = available.order_by('price').first().price
        else:
            context['min_price'] = None

        # Prix par catégorie
        from django.db.models import Min
        context['price_vip'] = seats.filter(category=Seat.SEAT_VIP).aggregate(p=Min('price'))['p']
        context['price_gold'] = seats.filter(category=Seat.SEAT_GOLD).aggregate(p=Min('price'))['p']
        context['price_standard'] = seats.filter(category=Seat.SEAT_STANDARD).aggregate(p=Min('price'))['p']

        return context


def event_seat_map(request, slug):
    event = get_object_or_404(Event, slug=slug, is_published=True)
    seats = Seat.objects.filter(event=event).order_by('row', 'number')

    rows = {}
    for seat in seats:
        if seat.row not in rows:
            rows[seat.row] = []
        rows[seat.row].append(seat)

    # Calculer les coordonnées SVG pour chaque siège
    row_keys = sorted(rows.keys())
    SVG_START_X = 80
    SVG_START_Y = 30
    SEAT_W = 52
    SEAT_H = 45
    ROW_GAP = 10
    COL_GAP = 8

    for row_idx, row_key in enumerate(row_keys):
        seats_in_row = rows[row_key]
        for col_idx, seat in enumerate(seats_in_row):
            seat.x_coord = SVG_START_X + col_idx * (SEAT_W + COL_GAP)
            seat.y_coord = SVG_START_Y + row_idx * (SEAT_H + ROW_GAP)
            seat.text_x = seat.x_coord + SEAT_W // 2
            seat.text_y = seat.y_coord + SEAT_H // 2 + 5
            seat.row_y_text = seat.y_coord + SEAT_H // 2 + 5

    # Calculer la viewBox SVG en fonction du nombre de sièges
    max_seats_per_row = max(len(s) for s in rows.values()) if rows else 10
    svg_width = max(800, SVG_START_X + max_seats_per_row * (SEAT_W + COL_GAP) + 40)
    svg_height = max(300, SVG_START_Y + len(row_keys) * (SEAT_H + ROW_GAP) + 40)

    return render(request, 'events/seat_map.html', {
        'event': event,
        'seat_rows': rows,
        'svg_width': svg_width,
        'svg_height': svg_height,
    })
