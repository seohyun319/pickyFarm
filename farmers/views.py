from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.views.generic import DetailView, ListView
from django.views import View
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q


# models
from .models import *
from products.models import Product
from users.models import Consumer
from editor_reviews.models import Editor_Review
from orders.models import Order_Detail, Order_Group

# forms
from .forms import *
from comments.forms import FarmerStoryCommentForm, FarmerStoryRecommentForm
from users.forms import SignUpForm
from addresses.forms import AddressForm


# farmer's page
def farmers_page(request):
    # farmer list
    farmer = Farmer.objects.all().order_by("-id")
    paginator = Paginator(farmer, 3)
    page = request.GET.get("page")
    farmers = paginator.get_page(page)

    # weekly hot farmer
    best_farmers = farmer.order_by("-sub_count")[:1]  # 조회수 대신 임의로

    # farmer's story list
    farmer_story = Farmer_Story.objects.all()
    paginator_2 = Paginator(farmer_story, 7)
    page_2 = request.GET.get("page_2")
    farmer_stories = paginator_2.get_page(page_2)

    ctx = {
        "best_farmers": best_farmers,
        "farmers": farmers,
        "farmer_stories": farmer_stories,
    }
    return render(request, "farmers/farmers_page.html", ctx)


# farmer input 검색 view - for AJAX
def farmer_search(request):
    search_key = request.GET.get("search_key")  # 검색어 가져오기
    search_list = Farmer.objects.all()
    if search_key:  # 검색어 존재 시
        search_list = search_list.filter(
            Q(farm_name__contains=search_key) | Q(user__nickname__contains=search_key)
        )
    search_list = search_list.order_by("-id")
    paginator = Paginator(search_list, 10)
    page = request.GET.get("page")
    farmers = paginator.get_page(page)
    ctx = {
        "farmers": farmers,
    }
    return render(request, "farmers/farmer_search.html", ctx)


# farmer category(채소, 과일, E.T.C) 검색 view - for AJAX
def farm_cat_search(request):
    search_cat = request.GET.get("search_cat")
    farmer = Farmer.objects.filter(farm_cat=search_cat).order_by("-id")
    paginator = Paginator(farmer, 3)
    page = request.GET.get("page")
    farmers = paginator.get_page(page)
    ctx = {
        "farmers": farmers,
    }
    return render(request, "farmers/farmer_search.html", ctx)


# farmer tag 검색 view - for AJAX
def farm_tag_search(request):
    search_tag = request.GET.get("search_tag")
    farmer = Farm_Tag.objects.get(tag=search_tag).farmer.all().order_by("-id")
    paginator = Paginator(farmer, 3)
    page = request.GET.get("page")
    farmers = paginator.get_page(page)
    ctx = {
        "farmers": farmers,
    }
    return render(request, "farmers/farmer_search.html", ctx)


# farmer story 검색 view - for AJAX
def farmer_story_search(request):
    select_val = request.GET.get("select_val")
    search_key_2 = request.GET.get("search_key_2")
    search_list = Farmer_Story.objects.all()
    if search_key_2:
        if select_val == "title":
            search_list = search_list.filter(Q(title__contains=search_key_2))
        elif select_val == "farm":
            search_list = search_list.filter(Q(farmer__farm_name__contains=search_key_2))
        elif select_val == "farmer":
            search_list = search_list.filter(Q(farmer__user__nickname__contains=search_key_2))
    search_list = search_list.order_by("-id")
    paginator = Paginator(search_list, 10)
    page_2 = request.GET.get("page_2")
    farmer_stories = paginator.get_page(page_2)
    ctx = {
        "farmer_stories": farmer_stories,
    }
    return render(request, "farmers/farmer_story_search.html", ctx)


# farmer's story create page
def farmer_story_create(request):
    try:
        user = request.user.farmer
    except ObjectDoesNotExist:
        return redirect(reverse("core:main"))
    if request.method == "POST":
        form = FarmerStoryForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data.get("title")
            # sub_title = form.cleaned_data.get('sub_title')
            content = form.cleaned_data.get("content")
            farmer_story = Farmer_Story(
                title=title,
                # sub_title=sub_title,
                content=content,
            )
            farmer_story.farmer = user
            farmer_story.save()
            return redirect(reverse("farmers:farmer_story_detail", args=[farmer_story.pk]))
        else:
            return redirect(reverse("core:main"))
    elif request.method == "GET":
        form = FarmerStoryForm()
        ctx = {
            "form": form,
        }
        return render(request, "farmers/farmer_story_create.html", ctx)


# farmer's story detail page
class Story_Detail(DetailView):
    model = Farmer_Story
    template_name = "farmers/farmer_story_detail.html"
    context_object_name = "main_story"

    def get_context_data(self, **kwargs):
        ctx = super(DetailView, self).get_context_data(**kwargs)
        farmer = self.get_object().farmer
        story = Farmer_Story.objects.all().order_by("-id")

        paginator = Paginator(story, 3)
        page = self.request.GET.get("page")
        stories = paginator.get_page(page)

        comments = self.get_object().farmer_story_comments.all()
        form = FarmerStoryCommentForm()

        ctx["farmer"] = farmer
        ctx["stories"] = stories
        ctx["tags"] = Farm_Tag.objects.all().filter(farmer=farmer)
        ctx["comments"] = comments
        ctx["form"] = form

        if self.request.user != AnonymousUser():
            ctx["user"] = self.request.user

        else:
            ctx["user"] = None

        return ctx

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)

        if self.request.session.get("_auth_user_id") is None:
            cookie_name = "farmer_story_hit"
        else:
            cookie_name = f'farmer_story_hit:{self.request.session["_auth_user_id"]}'

        if self.request.COOKIES.get(cookie_name) is None:
            response.set_cookie(cookie_name, self.kwargs["pk"], 3600)
            main_story = self.get_object()
            main_story.hits += 1
            main_story.save()
        else:
            cookie = self.request.COOKIES.get(cookie_name)
            cookies = cookie.split("|")

            if str(self.kwargs["pk"]) not in cookies:
                response.set_cookie(cookie_name, cookie + f'|{self.kwargs["pk"]}')
                main_story = self.get_object()
                main_story.hits += 1
                main_story.save()

        return response


# farmer detail page
def farmer_detail(request, pk):
    farmer = Farmer.objects.get(pk=pk)
    tags = Farm_Tag.objects.all().filter(farmer=farmer)
    products = Product.objects.all().filter(farmer=farmer)
    stories = Farmer_Story.objects.all().filter(farmer=farmer)
    editor_reviews = Editor_Review.objects.filter(farm=farmer)

    ctx = {
        "farmer": farmer,
        "tags": tags,
        "products": products,
        "stories": stories,
        "editor_reviews": editor_reviews,
    }
    return render(request, "farmers/farmer_detail.html", ctx)


# 입점 신청 page
def farm_apply(request):
    if request.method == "POST":
        form = FarmApplyForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, "farmers/farm_apply_complete.html")
        else:
            return redirect(reverse("core:main"))
    else:
        print("get")
        form = FarmApplyForm()
        ctx = {
            "form": form,
        }
        return render(request, "farmers/farm_apply.html", ctx)


# 입점 등록 page
class FarmEnroll(View):
    def get(self, request, step):
        if step == 1:
            form = SignUpForm()
            addressform = AddressForm()
            ctx = {
                "form": form,
                "addressform": addressform,
            }
            return render(request, "farmers/farm_enroll_1.html", ctx)
        elif step == 2:
            farm_form = FarmEnrollForm()
            ctx = {
                "farm_form": farm_form,
            }
            return render(request, "farmers/farm_enroll_2.html", ctx)
        elif step == 3:
            return render(request, "farmers/farm_enroll_3.html")
        return redirect(reverse("core:main"))

    def post(self, request, step):
        form = SignUpForm(request.POST)
        addressform = AddressForm(request.POST)
        farmer_form = FarmEnrollForm(request.POST)

        # farm enroll step 1
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            # Consumer.objects.create(user=user, grade=1)
            address = addressform.save(commit=False)
            # address.user = user
            # address.is_default = True
            # address.save()
            return redirect(reverse("farmers:farm_enroll", kwargs={"step": "step_2"}))

        # farm enroll step 2
        if farmer_form.is_valid():
            print("farm enroll 2 form valid")
            farmer_form.save(commit=False)
            return redirect(reverse("farmers:farm_enroll", kwargs={"step": "step_3"}))

        # farm enroll step 3
        agree_1 = request.POST.get("agree-1")
        agree_2 = request.POST.get("agree-2")
        if agree_1 is not None and agree_2 is not None:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                form.save()
                address.save()
                farmer_form.save()
                Consumer.objects.create(user=user, grade=1)
                login(request, user=user)
                return redirect(reverse("core:main"))
        else:
            print("farm enroll form 3까지 못갔어요,,,")
            return redirect(reverse("core:main"))

        print("redirect to main")
        return redirect(reverse("core:main"))


# 농가 정보 수정 페이지
def farm_info_update(request, pk):
    farmer = Farmer.objects.get(pk=pk)
    if request.method == "POST":
        farm_form = FarmEnrollForm(request.POST, request.FILES, instance=farmer)
    else:
        # farm_form = FarmEnrollForm(instance=farmer)
        farm_form = FarmEnrollForm()

    ctx = {"farmer": farmer, "farm_form": farm_form}
    return render(request, "farmers/farm_info_update.html", ctx)


"""
Farmer mypage section
"""


class FarmerMyPageBase(ListView):
    def get_context_data(self, **kwargs):
        """ context에 필요한 내용은 각 클래스에서 overriding하여 추가"""

        context = super().get_context_data(**kwargs)
        context["farmer"] = Farmer.objects.get(user=self.request.user)
        return context

    def render_to_response(self, context, **response_kwargs):
        """로그인한 farmer외의 접근을 막는 코드입니다. 절대 수정 금지"""

        if not Farmer.objects.filter(user=self.request.user).exists():
            return redirect(reverse("core:main"))

        return super().render_to_response(context, **response_kwargs)


class FarmerMyPageOrderManage(FarmerMyPageBase):
    """ 농가 주문관리 페이지 """

    model = Order_Detail
    template_name = "farmers/mypage/farmer_mypage_order.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["orders"] = []
        orders = Order_Detail.objects.filter(product__farmer=self.request.user.farmer).order_by(
            "order_group"
        )

        order_list = []
        order_list.append(orders.first())

        for i in range(1, len(orders)):
            if orders[i].order_group != orders[i - 1].order_group:
                context["orders"].append(order_list)
                order_list = [orders[i]]

            else:
                order_list.append(orders[i])

        context["orders"].append(order_list)

        return context


class FarmerMyPageProductManage(FarmerMyPageBase):
    """ 농가 상품관리 페이지 """

    model = Product
    context_object_name = "products"
    template_name = "farmers/mypage/product/farmer_mypage_product.html"

    def get_queryset(self):
        products = Product.objects.filter(farmer=self.request.user.farmer)

        return products


class FarmerMyPagePaymentManage(FarmerMyPageBase):
    """ 농가 정산관리 페이지 """

    pass


class FarmerMyPageReviewQnAManage(FarmerMyPageBase):
    """ 농가 문의/리뷰관리 페이지 """

    pass
