from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta
from decimal import Decimal
from .models import (
    Category, Partner, Product, Cart, CartItem,
    Order, OrderItem, BlogPost, Contact, ProductReview,
    Coupon, ServerFee, Slider, HomeBanner, NavMenu
)


class CategoryModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Electronics',
        )

    def test_category_creation(self):
        self.assertEqual(self.category.name, 'Electronics')
        self.assertTrue(self.category.slug)

    def test_category_str(self):
        self.assertEqual(str(self.category), 'Electronics')

    def test_category_parent_child(self):
        child = Category.objects.create(name='Mobile Phones', parent=self.category)
        self.assertEqual(child.parent, self.category)
        self.assertIn(child, self.category.children.all())


class ProductModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            price=Decimal('100.00'),
            old_price=Decimal('120.00'),
            stock=10,
            available=True,
            label='new',
        )

    def test_product_creation(self):
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.price, Decimal('100.00'))

    def test_product_slug_auto_generated(self):
        self.assertTrue(self.product.slug)

    def test_product_available_scope(self):
        self.assertTrue(Product.objects.filter(available=True).exists())

    def test_product_ordering(self):
        older = Product.objects.create(name='Older Product', category=self.category, price=Decimal('50.00'))
        older.created = self.product.created - timedelta(days=1)
        older.save(update_fields=['created'])
        products = Product.objects.all()
        self.assertEqual(products[0], self.product)


class PartnerModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='partner1', password='test123')
        self.partner = Partner.objects.create(
            user=self.user,
            name='Test Partner',
            phone='01700000000',
            address='Dhaka',
            is_dealer=True,
        )

    def test_partner_creation(self):
        self.assertEqual(self.partner.name, 'Test Partner')
        self.assertTrue(self.partner.is_dealer)

    def test_formatted_address(self):
        self.partner.address_street = '123 Road'
        self.partner.address_upazila = 'Savar'
        self.partner.address_district = 'Dhaka'
        self.partner.address_division = 'Dhaka'
        addr = self.partner.formatted_address
        self.assertIn('Savar', addr)


class CartModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cartuser', password='test123')
        self.category = Category.objects.create(name='Category')
        self.product = Product.objects.create(
            name='Cart Product', category=self.category, price=Decimal('50.00'), stock=5
        )
        self.cart = Cart.objects.create(user=self.user)

    def test_add_item(self):
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.assertEqual(self.cart.total_items(), 2)

    def test_cart_total(self):
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=3)
        self.assertEqual(self.cart.total_amount(), Decimal('150.00'))

    def test_cart_item_subtotal(self):
        item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=4)
        self.assertEqual(item.subtotal(), Decimal('200.00'))


class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='orderuser', password='test123')
        self.category = Category.objects.create(name='Category')
        self.product = Product.objects.create(
            name='Order Product', category=self.category, price=Decimal('75.00'), stock=10
        )
        self.order = Order.objects.create(
            user=self.user,
            name='John Doe',
            phone='01711111111',
            address='Dhaka',
            total=Decimal('150.00'),
            payment_method='Cash on Delivery',
        )

    def test_order_creation(self):
        self.assertEqual(self.order.name, 'John Doe')
        self.assertEqual(self.order.status, 'pending')

    def test_order_item_creation(self):
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=self.product.price,
            quantity=2,
        )
        self.assertEqual(self.order.items.count(), 1)

    def test_order_status_choices(self):
        valid_statuses = ['pending', 'processing', 'completed', 'cancelled']
        self.assertIn(self.order.status, valid_statuses)


class BlogPostModelTest(TestCase):
    def setUp(self):
        self.post = BlogPost.objects.create(
            title='Test Blog Post',
            content='This is test content.',
            author='Admin',
        )

    def test_blog_creation(self):
        self.assertEqual(self.post.title, 'Test Blog Post')
        self.assertTrue(self.post.slug)

    def test_blog_defaults(self):
        self.assertEqual(self.post.views, 0)
        self.assertEqual(self.post.comments, 0)


class ContactModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(
            name='Test User',
            email='test@example.com',
            message='Hello, this is a test message.',
        )

    def test_contact_creation(self):
        self.assertEqual(self.contact.name, 'Test User')
        self.assertEqual(self.contact.email, 'test@example.com')

    def test_contact_ordering(self):
        self.assertIsNotNone(self.contact.created)


class CouponModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Category')
        self.product = Product.objects.create(
            name='Coupon Product', category=self.category, price=Decimal('1000.00'), stock=10
        )
        self.coupon = Coupon.objects.create(
            code='TEST10',
            discount_type='percentage',
            discount_value=Decimal('10'),
            min_order_amount=Decimal('500.00'),
            max_discount=Decimal('100.00'),
            valid_from='2025-01-01',
            valid_to='2030-12-31',
        )

    def test_coupon_discount_calculation(self):
        discount = self.coupon.calculate_discount(Decimal('1000.00'), [self.product])
        self.assertEqual(discount, Decimal('100.00'))  # capped at max_discount

    def test_coupon_small_order_discount(self):
        discount = self.coupon.calculate_discount(Decimal('200.00'), [self.product])
        self.assertEqual(discount, Decimal('20.00'))  # 10% of 200 = 20


class ServerFeeModelTest(TestCase):
    def setUp(self):
        self.fixed_fee = ServerFee.objects.create(
            name='Delivery Fee', fee_type='fixed', value=Decimal('50.00')
        )
        self.percent_fee = ServerFee.objects.create(
            name='Service Charge', fee_type='percentage', value=Decimal('5.00')
        )

    def test_fixed_fee_calculation(self):
        self.assertEqual(self.fixed_fee.calculate(Decimal('1000.00')), Decimal('50.00'))

    def test_percentage_fee_calculation(self):
        self.assertEqual(self.percent_fee.calculate(Decimal('1000.00')), Decimal('50.00'))


class ProductReviewModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reviewuser', password='test123')
        self.category = Category.objects.create(name='Category')
        self.product = Product.objects.create(
            name='Review Product', category=self.category, price=Decimal('100.00')
        )
        self.review = ProductReview.objects.create(
            product=self.product, user=self.user, rating=5, comment='Excellent!'
        )

    def test_review_creation(self):
        self.assertEqual(self.review.rating, 5)
        self.assertEqual(self.review.comment, 'Excellent!')

    def test_review_rating_choices(self):
        self.assertIn(self.review.rating, [1, 2, 3, 4, 5])


class HomePageViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Category')
        self.product = Product.objects.create(
            name='Home Product', category=self.category, price=Decimal('100.00'), available=True
        )
        img = SimpleUploadedFile('test.jpg', b'test', content_type='image/jpeg')
        Slider.objects.create(title='Slider 1', image=img, is_active=True, order=0)
        HomeBanner.objects.create(title='Banner 1', image=img, is_active=True, order=0)

    def test_home_page_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Home Product')


class ShopViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Category')
        self.product = Product.objects.create(
            name='Shop Product', category=self.category, price=Decimal('100.00'), available=True
        )

    def test_shop_page_loads(self):
        response = self.client.get(reverse('shop_grid'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Shop Product')


class ProductDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Category')
        self.product = Product.objects.create(
            name='Detail Product', category=self.category, price=Decimal('100.00'), available=True, slug='detail-product'
        )

    def test_product_detail_loads(self):
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detail Product')


class CartViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='cartview', password='test123')
        self.category = Category.objects.create(name='Category')
        self.product = Product.objects.create(
            name='Cart Product', category=self.category, price=Decimal('100.00'), stock=5, available=True
        )

    def test_cart_page_supports_anonymous(self):
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)

    def test_add_to_cart(self):
        self.client.login(username='cartview', password='test123')
        response = self.client.post(reverse('add_to_cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)

    def test_cart_with_items(self):
        self.client.login(username='cartview', password='test123')
        self.client.post(reverse('add_to_cart', args=[self.product.id]))
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)


class AuthViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='authuser', password='test123')

    def test_login_page(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(reverse('login'), {'username': 'authuser', 'password': 'test123'})
        self.assertEqual(response.status_code, 302)

    def test_login_failure(self):
        response = self.client.post(reverse('login'), {'username': 'authuser', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')


class BlogViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.post = BlogPost.objects.create(
            title='Test Blog', content='Blog content', slug='test-blog'
        )

    def test_blog_list(self):
        response = self.client.get(reverse('blog_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Blog')

    def test_blog_detail(self):
        response = self.client.get(reverse('blog_detail', args=[self.post.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Blog')
        self.assertContains(response, 'Blog content')


class ContactViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_contact_page(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)

    def test_contact_submission(self):
        response = self.client.post(reverse('contact'), {
            'name': 'Test User',
            'email': 'test@example.com',
            'message': 'Test message content.',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Contact.objects.filter(email='test@example.com').exists())


class NavMenuModelTest(TestCase):
    def setUp(self):
        self.menu = NavMenu.objects.create(
            title='Home', url='home', url_type='named_url', order=0, is_active=True
        )

    def test_menu_creation(self):
        self.assertEqual(self.menu.title, 'Home')
        self.assertEqual(self.menu.url, 'home')
        self.assertEqual(self.menu.kind, 'link')
        self.assertFalse(self.menu.open_new_tab)

    def test_get_url_named(self):
        self.assertEqual(self.menu.get_url(), reverse('home'))

    def test_get_url_path(self):
        item = NavMenu.objects.create(title='X', url='/shop/', url_type='path', order=1)
        self.assertEqual(item.get_url(), '/shop/')

    def test_get_url_invalid_name_returns_hash(self):
        item = NavMenu.objects.create(title='Bad', url='no_such_url_xyz', url_type='named_url', order=2)
        self.assertEqual(item.get_url(), '#')

    def test_get_url_special_kinds(self):
        cat = NavMenu.objects.create(title='Categories', kind='categories', url='shop', url_type='named_url', order=3)
        self.assertEqual(cat.get_url(), reverse('shop'))
        acc = NavMenu.objects.create(title='Account', kind='account', url='dashboard', url_type='named_url', order=4)
        self.assertEqual(acc.get_url(), '#')


class CheckoutViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='checkoutuser', password='test123')
        self.category = Category.objects.create(name='Category')
        self.product = Product.objects.create(
            name='Checkout Product', category=self.category, price=Decimal('100.00'), stock=5, available=True
        )

    def test_checkout_requires_login(self):
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 302)

    def test_checkout_with_cart_items(self):
        self.client.login(username='checkoutuser', password='test123')
        self.client.post(reverse('add_to_cart', args=[self.product.id]))
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 200)


class OrderFlowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='orderflow', password='test123')
        self.category = Category.objects.create(name='Category')
        self.product = Product.objects.create(
            name='Flow Product', category=self.category, price=Decimal('100.00'), stock=5, available=True
        )

    def test_complete_order_flow(self):
        self.client.login(username='orderflow', password='test123')
        self.client.post(reverse('add_to_cart', args=[self.product.id]))
        response = self.client.post(reverse('checkout'), {
            'name': 'Flow User',
            'phone': '01700000000',
            'address': 'Dhaka',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.filter(name='Flow User').exists())
