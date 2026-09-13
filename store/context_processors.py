from django.conf import settings
from django.db.models import Q
from django.core.cache import cache
from .models import Cart, SiteLogo, NavMenu, SocialMediaLink, Page, Partner, PartnerWallet, Wishlist, Notification, Product, NewsTicker, PaymentIcon, HomepageSettings


def site_info(request):
    site_logo = SiteLogo.objects.first()
    site_name = site_logo.site_name if site_logo and site_logo.site_name else 'Uddoktar Dokan'
    site_tagline = site_logo.site_tagline if site_logo else ''
    search_ph = NewsTicker.objects.filter(type='search_placeholder', is_active=True).first()
    search_placeholder = (getattr(site_logo, 'search_placeholder', '') or '').strip()
    if not search_placeholder:
        search_placeholder = search_ph.text if search_ph else 'পণ্যের নাম, কোড, ক্যাটাগরি ও সাব-ক্যাটাগরি লিখে সার্চ করুন'
    social_links = SocialMediaLink.objects.filter(is_active=True)
    payment_icons = PaymentIcon.objects.filter(is_active=True)
    footer_pages = Page.objects.filter(is_active=True, show_in_footer=True)
    header_pages = Page.objects.filter(is_active=True, show_in_header=True)
    news_items = list(NewsTicker.objects.filter(type='ticker', is_active=True))
    return {
        'site_logo': site_logo,
        'site_name': site_name,
        'site_tagline': site_tagline,
        'search_placeholder': search_placeholder,
        'site_phone': getattr(site_logo, 'site_phone', '') or settings.SITE_PHONE,
        'site_whatsapp': getattr(site_logo, 'site_whatsapp', '') or settings.SITE_WHATSAPP,
        'site_email': getattr(site_logo, 'site_email', '') or '',
        'site_address_bd': getattr(site_logo, 'site_address_bd', '') or settings.SITE_ADDRESS_BD,
        'site_address_us': getattr(site_logo, 'site_address_us', '') or settings.SITE_ADDRESS_US,
        'footer_about': getattr(site_logo, 'footer_about', ''),
        'newsletter_title': getattr(site_logo, 'newsletter_title', '') or 'Sign up for newsletter',
        'newsletter_subtitle': getattr(site_logo, 'newsletter_subtitle', '') or 'Get the latest deals and special offers',
        'footer_copyright': getattr(site_logo, 'footer_copyright', ''),
        'site_facebook': settings.SITE_FACEBOOK,
        'site_youtube': settings.SITE_YOUTUBE,
        'social_links': social_links,
        'payment_icons': payment_icons,
        'show_newsletter_section': getattr(site_logo, 'show_newsletter_section', True),
        'show_contact_section': getattr(site_logo, 'show_contact_section', True),
        'show_follow_us_section': getattr(site_logo, 'show_follow_us_section', True),
        'show_policy_buttons': getattr(site_logo, 'show_policy_buttons', True),
        'show_copyright_bar': getattr(site_logo, 'show_copyright_bar', True),
        'show_payment_icons': getattr(site_logo, 'show_payment_icons', True),
        'footer_pages': footer_pages,
        'header_pages': header_pages,
        'news_items': news_items,
    }


def nav_menu(request):
    return {'nav_items': NavMenu.objects.filter(is_active=True)}


def category_menu(request):
    from .category_tree import get_tree
    return {'category_tree': get_tree()}


def page_settings(request):
    return {'page_settings': HomepageSettings.load()}


def cart_count(request):
    cart_items_count = 0
    cart_total = 0
    cart_items_list = []
    cart = None
    if request.user.is_authenticated:
        cache_key = f'cart_{request.user.id}'
        cached = cache.get(cache_key)
        if cached is not None:
            return {'cart_items_count': cached[0], 'cart_total': cached[1], 'cart_items_list': []}
        cart = Cart.objects.filter(user=request.user, is_active=True).first()
    else:
        session_id = request.session.session_key
        if session_id:
            cart = Cart.objects.filter(session_id=session_id, is_active=True).first()
    if cart:
        cart_items_count = cart.total_items()
        cart_total = cart.total_amount()
        cart_items_list = list(cart.items.select_related('product')[:5])
    return {'cart_items_count': cart_items_count, 'cart_total': cart_total, 'cart_items_list': cart_items_list}


def wallet_balance(request):
    balance = None
    if request.user.is_authenticated:
        try:
            partner = request.user.partner
            wallet = PartnerWallet.objects.filter(partner=partner).first()
            if wallet:
                balance = wallet.balance
        except (Partner.DoesNotExist, AttributeError):
            pass
    return {'wallet_balance': balance}


def wishlist_count(request):
    count = 0
    if request.user.is_authenticated:
        wl = Wishlist.objects.filter(user=request.user).first()
        if wl:
            count = wl.total_items()
    else:
        sid = request.session.session_key
        if sid:
            wl = Wishlist.objects.filter(session_id=sid, user__isnull=True).first()
            if wl:
                count = wl.total_items()
    return {'wishlist_count': count}


def unread_notifications(request):
    count = 0
    if request.user.is_authenticated:
        cache_key = f'unread_notif_{request.user.id}'
        count = cache.get(cache_key)
        if count is None:
            count = Notification.objects.filter(user=request.user, is_read=False).count()
            try:
                partner = request.user.partner
                count += Notification.objects.filter(partner=partner, is_read=False).count()
            except (Partner.DoesNotExist, AttributeError):
                pass
            cache.set(cache_key, count, 60)
    return {'unread_notifications': count}


def wishlist_compare_ids(request):
    w_ids = set()
    if request.user.is_authenticated:
        wl = Wishlist.objects.filter(user=request.user).first()
        if wl:
            w_ids = set(wl.items.values_list('product_id', flat=True))
    else:
        sid = request.session.session_key
        if sid:
            wl = Wishlist.objects.filter(session_id=sid, user__isnull=True).first()
            if wl:
                w_ids = set(wl.items.values_list('product_id', flat=True))
    c_ids = request.session.get('compare', [])
    return {'wishlist_ids': w_ids, 'compare_ids': c_ids}


def recently_viewed_products(request):
    ids = request.session.get('recently_viewed', [])
    products = Product.objects.filter(id__in=ids, available=True, trashed=False).filter(Q(partner__isnull=True) | Q(partner__show_products=True)) if ids else []
    ordered = []
    for pid in ids:
        for p in products:
            if p.id == pid:
                ordered.append(p)
                break
    return {'recently_viewed': ordered[:6]}
