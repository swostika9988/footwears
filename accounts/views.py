import os
import json
import uuid
import requests
from weasyprint import CSS, HTML
from products.models import *
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from home.models import ShippingAddress
from django.contrib.auth.models import User
from django.template.loader import get_template
from accounts.models import Profile, Cart, CartItem, Order, OrderItem
from base.emails import send_account_activation_email
from django.views.decorators.http import require_POST
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import redirect, render, get_object_or_404
from accounts.forms import UserUpdateForm, UserProfileForm, ShippingAddressForm, CustomPasswordChangeForm
from products.models import Product, Category
from products.forms import ProductForm
from django.contrib.auth import logout
from django.conf import settings
import hmac, hashlib, base64
from datetime import datetime
from django.utils.crypto import get_random_string
import time

class KhaltiPayment:
    def __init__(self):
        self.KHALTI_SECRET_KEY = settings.KHALTI_SECRET_KEY
        self.WEBSITE_URL = 'http://127.0.0.1:8000'  # e.g., https://yourdomain.com
        self.SUCCESS_URL = self.WEBSITE_URL + reverse('khalti_success')
        self.FAILURE_URL = self.WEBSITE_URL + reverse('failure')
        self.INITIATE_URL = "https://dev.khalti.com/api/v2/epayment/initiate/"
        self.LOOKUP_URL = "https://dev.khalti.com/api/v2/epayment/lookup/"
        self.REDIRECT_URL = None  # Will be filled after initiate

    def _generate_signature(self, user_id, amount, tax_amount):
        """Encode user/order info safely"""
        payload = {
            'user_id': user_id,
            'amount': amount,
            'tax_amount': tax_amount,
            'rand': get_random_string(8)  # Add randomness for safety
        }
        json_str = json.dumps(payload)
        encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
        return encoded

    def _decode_signature(self, signature):
        """Decode the unique signature back to original data"""
        try:
            decoded_bytes = base64.urlsafe_b64decode(signature.encode())
            decoded_str = decoded_bytes.decode()
            payload = json.loads(decoded_str)
            return payload
        except Exception:
            return None

    def initiate_payment(self, user_id, amount=90, tax_amount=10):
        """Initiate Khalti Payment and return frontend-friendly data"""
        purchase_order_id = self._generate_signature(user_id, amount, tax_amount)
        purchase_order_name = "Order for User {}".format(user_id)

        payload = {
            "return_url": self.SUCCESS_URL,
            "website_url": self.WEBSITE_URL,
            "amount": int(amount * 100),  # Convert to paisa
            "purchase_order_id": purchase_order_id,
            "purchase_order_name": purchase_order_name,
        }

        headers = {
            "Authorization": f"Key {self.KHALTI_SECRET_KEY}"
        }
        print(f'payload for khalti initative payment : {payload}')
        response = requests.post(self.INITIATE_URL, data=payload, headers=headers)
        resp_data = response.json()
        print(f'response of payment start : {resp_data}')
        if response.status_code == 200 and resp_data.get("payment_url"):
            self.REDIRECT_URL = resp_data["payment_url"]
            return {
                'url': self.REDIRECT_URL,
                'button_text': 'Pay with Khalti',
                'signature': purchase_order_id,
                'success_url': self.SUCCESS_URL,
                'failure_url': self.FAILURE_URL,
                'fields': {}  # Add if you need custom POST fields
            }
        else:
            return {
                'error': resp_data.get('detail', 'Payment initiation failed.'),
                'success_url': self.SUCCESS_URL,
                'failure_url': self.FAILURE_URL
            }

    def verify_payment(self, pidx):
        """Verify the payment status"""
        headers = {
            "Authorization": f"Key {self.KHALTI_SECRET_KEY}"
        }
        payload = {
            "pidx": pidx
        }
        response = requests.post(self.LOOKUP_URL, data=payload, headers=headers)
        resp_data = response.json()
        return resp_data


class EsewaPayment:
    def __init__(self):
        self.PRODUCT_CODE = "EPAYTEST"
        self.SUCCESS_URL = "http://127.0.0.1:8000/accounts/success"
        self.FAILURE_URL = "http://127.0.0.1:8000/accounts/failure"
        self.SIGNED_FIELDS = "total_amount,transaction_uuid,product_code"
        self.REDIRECT_URL = 'https://rc-epay.esewa.com.np/api/epay/main/v2/form'
        self.SECRET_KEY = b"8gBm/:&EnhH.1/q"
        # replace with your actual eSewa key

    @classmethod
    def decode_transaction_uuid(self,transaction_uuid: str) -> int:
        """
        Extracts the user_id from transaction_uuid of format 'user_id-timestamp'.
        """
        try:
            user_id_str = transaction_uuid.split("-")[0]
            return int(user_id_str)
        except (IndexError, ValueError):
            return None

    def generate_signature(self,total_amount, transaction_uuid, product_code, secret_key):
        message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
        signature = hmac.new(
            secret_key.encode(), message.encode(), hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode()

    def get_form(self, user_id, amount=90,tax_amount=10):
        # Derived values
        total_amount = round(amount + tax_amount, 2)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        transaction_uuid = f"{user_id}-{timestamp}"
        signature = self.generate_signature(
            total_amount=total_amount,
            transaction_uuid=transaction_uuid,
            product_code=self.PRODUCT_CODE,
            secret_key=self.SECRET_KEY.decode()
        )
        return {
            'url': self.REDIRECT_URL,
            'button_text': 'Pay with eSewa',
            'signature': signature,
            'success_url': self.SUCCESS_URL,
            'failure_url': self.FAILURE_URL,
            'fields': {
                "amount": str(amount),
                "tax_amount": str(tax_amount),
                "total_amount": str(total_amount),
                "transaction_uuid": transaction_uuid,
                "product_code": self.PRODUCT_CODE,
                "product_service_charge": "0",
                "product_delivery_charge": "0",
                "success_url": self.SUCCESS_URL,
                "failure_url": self.FAILURE_URL,
                "signed_field_names": self.SIGNED_FIELDS,
                "signature": signature
            }
        }


# Create your views here.


def login_page(request):
    next_url = request.GET.get('next') # Get the next URL from the query parameter
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_obj = User.objects.filter(username=username)

        if not user_obj.exists():
            messages.warning(request, 'Account not found!')
            return HttpResponseRedirect(request.path_info)

        if not user_obj[0].profile.is_email_verified:
            messages.error(request, 'Account not verified!')
            return HttpResponseRedirect(request.path_info)

        user_obj = authenticate(username=username, password=password)
        if user_obj:
            login(request, user_obj)
            messages.success(request, 'Login Successfull.')

            # Check if the next URL is safe
            if url_has_allowed_host_and_scheme(url=next_url, allowed_hosts=request.get_host()):
                return redirect(next_url)
            else:
                return redirect('index')

        messages.warning(request, 'Invalid credentials.')
        return HttpResponseRedirect(request.path_info)

    return render(request, 'accounts/login.html')


def register_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        user_obj = User.objects.filter(username=username, email=email)

        if user_obj.exists():
            messages.info(request, 'Username or email already exists!')
            return HttpResponseRedirect(request.path_info)

        user_obj = User.objects.create(
            username=username, first_name=first_name, last_name=last_name, email=email)
        user_obj.set_password(password)
        user_obj.save()

        profile = Profile.objects.get(user=user_obj)
        profile.email_token = str(uuid.uuid4())
        profile.save()

        send_account_activation_email(email, profile.email_token)
        messages.success(request, "An email has been sent to your mail.")
        return HttpResponseRedirect(request.path_info)

    return render(request, 'accounts/register.html')


@login_required
def user_logout(request):
    logout(request)
    messages.warning(request, "Logged Out Successfully!")
    return redirect('index')


def activate_email_account(request, email_token):
    try:
        user = Profile.objects.get(email_token=email_token)
        user.is_email_verified = True
        user.save()
        messages.success(request, 'Account verification successful.')
        return redirect('login')
    except Exception as e:
        return HttpResponse('Invalid email token.')


@login_required
def add_to_cart(request, uid):
    try:
        variant = request.GET.get('size')
        if not variant:
            messages.warning(request, 'Please select a size variant!')
            return redirect(request.META.get('HTTP_REFERER'))

        product = get_object_or_404(Product, uid=uid)
        cart, _ = Cart.objects.get_or_create(user=request.user, is_paid=False)
        size_variant = get_object_or_404(SizeVariant, size_name=variant)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, size_variant=size_variant)
        if not created:
            cart_item.quantity += 1
            cart_item.save()

        messages.success(request, 'Item added to cart successfully.')

    except Exception as e:
        messages.error(request, 'Error adding item to cart.', str(e))

    return redirect(reverse('cart'))


@login_required
def cart(request):
    cart_obj = None
    payment = None
    user = request.user

    try:
        cart_obj = Cart.objects.get(is_paid=False, user=user)

    except Exception as e:
        messages.warning(request, "Your cart is empty. Please add a product to cart.", str(e))
        return redirect(reverse('index'))

    if request.method == 'POST':
        coupon = request.POST.get('coupon')
        coupon_obj = Coupon.objects.filter(coupon_code__exact=coupon).first()

        if not coupon_obj:
            messages.warning(request, 'Invalid coupon code.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        if cart_obj and cart_obj.coupon:
            messages.warning(request, 'Coupon already exists.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        if coupon_obj and coupon_obj.is_expired:
            messages.warning(request, 'Coupon code expired.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        if cart_obj and coupon_obj and cart_obj.get_cart_total() < coupon_obj.minimum_amount:
            messages.warning(
                request, f'Amount should be greater than {coupon_obj.minimum_amount}')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        if cart_obj and coupon_obj:
            cart_obj.coupon = coupon_obj
            cart_obj.save()
            messages.success(request, 'Coupon applied successfully.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    if cart_obj:
        cart_total_in_paise = int(cart_obj.get_cart_total_price_after_coupon() * 100)

        if cart_total_in_paise < 100:
            messages.warning(
                request, 'Total amount in cart is less than the minimum required amount (1.00 INR). Please add a product to the cart.')
            return redirect('index')
    # lets create payments forms
    esewa_formddata = {}
    khalti_formdata = {}
    try:
        esewa = EsewaPayment()
        esewa_formddata=  esewa.get_form(
            user_id=user.id,
        )
        khalti = KhaltiPayment()
        khalti_formdata = khalti.initiate_payment(
            user_id=user.id
        )

    except Exception as e:
        pass

    context = {
        'cart': cart_obj,
        'payment': payment,
        'quantity_range': range(1, 6),
        'payment_method': [esewa_formddata],
        'khalti_formdata': khalti_formdata,

    }
    return render(request, 'accounts/cart.html', context)

def generate_uid():
    timestamp = int(time.time() * 1000)
    unique_part = uuid.uuid4().hex[:6]  # 6 hex digits from UUID
    return f"{timestamp}{unique_part}"


def khalti_success(request):
    pidx = request.GET.get('pidx')
    signature = request.GET.get('purchase_order_id')  # You sent this during initiation

    payment = KhaltiPayment()
    decoded_data = payment._decode_signature(signature)

    if not decoded_data:
        return redirect('cart')
    payment_info = payment.verify_payment(pidx)

    if payment_info.get("status") == "Completed":
        # Save payment to DB using decoded_data['user_id'], decoded_data['amount'], etc.
        user_id = decoded_data.get('user_id',None)
        if user_id:
            cart = Cart.objects.filter(user=user_id) #get_object_or_404(Cart, user=user_id)
            if cart:
                cart = cart.last()
                # Mark the cart as paid
                cart.is_paid = True
                cart.razorpay_order_id = generate_uid()
                cart.save()
                # Create the order after payment is confirmed
                order = create_order(cart)
                order_id = order.order_id
                context = {'order_id': order_id, 'order': order}
                return render(request, 'payment_success/payment_success.html', context)
            else:
                return redirect('cart')
        else:
            return redirect('cart')
    else:
        return redirect('cart')


@require_POST
@login_required
def update_cart_item(request):
    try:
        data = json.loads(request.body)
        cart_item_id = data.get("cart_item_id")
        quantity = int(data.get("quantity"))

        cart_item = CartItem.objects.get(uid=cart_item_id, cart__user=request.user, cart__is_paid=False)
        cart_item.quantity = quantity
        cart_item.save()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def remove_cart(request, uid):
    try:
        cart_item = get_object_or_404(CartItem, uid=uid)
        cart_item.delete()
        messages.success(request, 'Item removed from cart.')

    except Exception as e:
        print(e)
        messages.warning(request, 'Error removing item from cart.')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def remove_coupon(request, cart_id):
    cart = Cart.objects.get(uid=cart_id)
    cart.coupon = None
    cart.save()

    messages.success(request, 'Coupon Removed.')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def failure(request):
    return redirect('cart')

# Payment success view
def success(request):
    data = json.loads(base64.b64decode(request.body))
    transaction_uuid = data["transaction_uuid"]
    user_id = EsewaPayment.decode_transaction_uuid(transaction_uuid)
    cart = get_object_or_404(Cart, user=user_id)

    # Mark the cart as paid
    cart.is_paid = True
    cart.save()

    # Create the order after payment is confirmed
    order = create_order(cart)
    order_id = order.order_id
    context = {'order_id': order_id, 'order': order}
    return render(request, 'payment_success/payment_success.html', context)


# HTML to PDF Conversion
def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)

    static_root = settings.STATIC_ROOT
    css_files = [
        os.path.join(static_root, 'css', 'bootstrap.css'),
        os.path.join(static_root, 'css', 'responsive.css'),
        os.path.join(static_root, 'css', 'ui.css'),
    ]
    css_objects = [CSS(filename=css_file) for css_file in css_files]
    pdf_file = HTML(string=html).write_pdf(stylesheets=css_objects)

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{context_dict["order"].order_id}.pdf"'
    return response


def download_invoice(request, order_id):
    order = Order.objects.filter(order_id=order_id).first()
    order_items = order.order_items.all()

    context = {
        'order': order,
        'order_items': order_items,
    }

    pdf = render_to_pdf('accounts/order_pdf_generate.html', context)
    if pdf:
        return pdf
    return HttpResponse("Error generating PDF", status=400)


@login_required
def profile_view(request, username):
    user_name = get_object_or_404(User, username=username)
    user = request.user
    profile = user.profile

    user_form = UserUpdateForm(instance=user)
    profile_form = UserProfileForm(instance=profile)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    context = {
        'user_name': user_name,
        'user_form': user_form,
        'profile_form': profile_form
    }

    return render(request, 'accounts/profile.html', context)


@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        else:
            messages.warning(request, 'Please correct the error below.')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def update_shipping_address(request):
    shipping_address = ShippingAddress.objects.filter(
        user=request.user, current_address=True).first()

    if request.method == 'POST':
        form = ShippingAddressForm(request.POST, instance=shipping_address)
        if form.is_valid():
            shipping_address = form.save(commit=False)
            shipping_address.user = request.user
            shipping_address.current_address = True
            shipping_address.save()

            messages.success(request, "The Address Has Been Successfully Saved/Updated!")

            form = ShippingAddressForm()
        else:
            form = ShippingAddressForm(request.POST, instance=shipping_address)
    else:
        form = ShippingAddressForm(instance=shipping_address)

    return render(request, 'accounts/shipping_address_form.html', {'form': form})


# Order history view
@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    return render(request, 'accounts/order_history.html', {'orders': orders})


# Create an order view
def create_order(cart,payment_mode='khalti'):
    order, created = Order.objects.get_or_create(
        user=cart.user,
        order_id=cart.razorpay_order_id,
        payment_status="Paid",
        shipping_address=cart.user.profile.shipping_address,
        payment_mode=payment_mode,
        order_total_price=cart.get_cart_total(),
        coupon=cart.coupon,
        grand_total=cart.get_cart_total_price_after_coupon(),
    )

    # Create OrderItem instances for each item in the cart
    cart_items = CartItem.objects.filter(cart=cart)
    for cart_item in cart_items:
        OrderItem.objects.get_or_create(
            order=order,
            product=cart_item.product,
            size_variant=cart_item.size_variant,
            color_variant=cart_item.color_variant,
            quantity=cart_item.quantity,
            product_price=cart_item.get_product_price()
        )

    return order


# Order Details view
@login_required
def order_details(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)
    context = {
        'order': order,
        'order_items': order_items,
        'order_total_price': sum(item.get_total_price() for item in order_items),
        'coupon_discount': order.coupon.discount_amount if order.coupon else 0,
        'grand_total': order.get_order_total_price()
    }
    return render(request, 'accounts/order_details.html', context)


# Delete user account feature
@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Your account has been deleted successfully.")
        return redirect('index')


#Dashboard
def dashboard(request):
    pie_labels = ['Men', 'Women', 'Kids']
    pie_data = [40, 30, 30]
    line_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May']
    line_data = [100, 200, 150, 300, 250]
    context = {
        'pie_labels': pie_labels,
        'pie_data': pie_data,
        'line_labels': line_labels,
        'line_data': line_data
    }
    return render(request, 'dashboard/dashboard.html', context)

def category_list(request):
    return render(request, 'dashboard/category_list.html')

def add_category(request):
    return render(request, 'dashboard/add_category.html')

def product_list(request):
    products = Product.objects.all()
    return render(request, 'dashboard/product.html', {'products': products})

def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        images = request.FILES.getlist('images')
        if form.is_valid():
            product = form.save()
            for img in images:
                ProductImage.objects.create(product=product, image=img)
            return redirect('product_list')  # make sure this URL name exists
    else:
        form = ProductForm()
    return render(request, 'dashboard/add_product.html', {'form': form})


def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('accounts:product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'dashboard/edit_product.html', {'form': form})

def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect('accounts:product_list')

def logout_view(request):
    logout(request)
    return redirect('accounts:login')

