from django.shortcuts import render, redirect, reverse
from django.http import request, JsonResponse
from django.core import serializers
from django.contrib.auth.decorators import login_required
from .models import Product, Category, Question, Answer
from .forms import Question_Form, Answer_Form
from comments.forms import ProductRecommentForm
from django.utils import timezone
from math import ceil
from django.core.exceptions import ObjectDoesNotExist
from django import template
from datetime import date
import locale
import json


# ajax 이용시, http Fail status 장착한 response 생성
class FailedJsonResponse(JsonResponse):
    def __init__(self, data):
        super().__init__(data)
        data.status_code = 400

def store_list_all(request):
    cat_name = "all"
    page = int(request.GET.get('page', 1))
    sort = request.GET.get('sort', '최신순')
    page_size = 15
    limit = page_size * page
    offset = limit - page_size
    products_count = Product.objects.filter(open=True).count()
    products = Product.objects.filter(
        open=True).order_by('-create_at')
    if sort == '인기순':
        for product in products:
            product.calculate_sale_rate()
        products = products.order_by('sales_rate')
    elif sort == "마감임박순":
        products = products.order_by('stock')
    products = products[offset:limit]
    categories = Category.objects.filter(parent=None).order_by('name')
    page_total = ceil(products_count/page_size)
    ctx = {
        "cat_name":cat_name,
        "products": products,
        "categories": categories,
        "page": page,
        "page_total": page_total,
        "page_range": range(1, page_total),

    }
    return render(request, "products/products_list.html", ctx)


def store_list_cat(request, cat):
    big_cat = ['fruit', 'vege', 'others']
    cat_name = str(cat)
    products = []
    page = int(request.GET.get('page', 1))
    sort = request.GET.get('sort', '최신순')
    page_size = 15
    limit = page_size * page
    offset = limit - page_size
    if cat_name in big_cat:
        big_category = Category.objects.get(slug=cat)
        print(big_category)
        categories = big_category.children.all().order_by('name')
        try:
            products = Product.objects.filter(
                category__parent__slug=cat, open=True).order_by('create_at')
        except ObjectDoesNotExist:
            ctx = {
                "cat_name":cat_name,
                'big_category': big_category,
            }
            return render(request, "products/products_list.html", ctx)
    else:
        big_cat_name = {'과일':'fruit', '야채':'vege', '기타':'others'}
        categories = Category.objects.get(slug=cat)
        print(categories)
        cat_name = big_cat_name[categories.parent.name]
        print(cat_name)
        try:
            products = categories.products.filter(open=True).order_by('-create_at')
            categories = categories.parent.children.all().order_by('name')
        except ObjectDoesNotExist:
            ctx = {
                "cat_name":cat_name,
                "cateogries" : categories,
            }
            return render(request, "products/products_list.html", ctx)
        
    print(categories)
    print(products)
    if sort == '인기순':
        for product in products:
            product.calculate_sale_rate()
        products = products.order_by('sales_rate')
    elif sort == "마감임박순":
        products = products.order_by('stock')
    print(products)
    print(page)
    products_count = products.count()
    products = products[offset:limit]
    if products_count == 0:
        page_total = 1
    else:
        page_total = ceil(products_count/page_size)

    ctx = {
        "products": products,
        "cat_name":cat_name,
        "categories": categories,
        "page": page,
        "page_total": page_total,
        "page_range": range(1, page_total+1),
    }
    return render(request, "products/products_list.html", ctx)


register = template.Library()
@register.filter(name='range')
def _range(_min, args=None):
    _max, _step = None, None
    if args:
        if not isinstance(args, int):
            _max, _step = map(int, args.split(','))
        else:
            _max = args
    args = filter(None, (_min, _max, _step))
    return range(*args)

def product_detail(request, pk):
    try:
        product = Product.objects.get(pk=pk)
        product.calculate_total_rating_avg()
        farmer = product.farmer
        comments = product.product_comments.all().order_by('-create_at')
        questions = product.questions.all().order_by('-create_at')
        total_score = product.calculate_total_rating_avg()
        total_percent = total_score/5 * 100

        recomment_form = ProductRecommentForm()

        questions_total_pages = ceil(questions.count() / 5)
        print(questions_total_pages)

        questions = questions[0:5]
        
        ctx = {
            'product': product,
            'farmer': farmer,
            'comments': comments,
            'questions': questions,
            'total_score': range(int(total_score)),
            'remainder_score': range(5-int(total_score)),
            'total_percent': total_percent,
            'recomment_form': recomment_form,
            'question_total_pages' : range(1, questions_total_pages+1),
        }
        return render(request, "products/product_detail.html", ctx)
    except ObjectDoesNotExist:
        return redirect("/")


def question_paging(request):
    product_pk = request.POST.get('product_pk', None)
    page_num = (int)(request.POST.get('page_num', None))

    try:
        product = Product.objects.get(pk = product_pk)
        questions = product.questions.all().order_by('-create_at')
    except ObjectDoesNotExist:
        data = {
            'status' : 0,
        }
        return JsonResponse(data)
    
    offset = 5
    questions_limit = page_num * offset
    questions = questions[questions_limit-5 : questions_limit]
    questions_list = []
    locale.setlocale(locale.LC_TIME, 'ko_KR.UTF-8')
    for q in questions:
        q_dict = { 'status':q.status }
        print(q_dict)
        q_dict['pk'] = q.pk
        q_dict['title']=q.title
        print(q_dict)
        q_dict['consumer'] = q.consumer.user.nickname
        print(q_dict)
        q_dict['create_at'] = q.create_at.strftime("%Y년%m월%d일")
        print(q_dict)
        questions_list.append(q_dict)
        del q_dict

    print(questions_list)
    data = {
        'status':1,
        'questions':questions_list
    }

    return JsonResponse(data)

@login_required
def create_question(request):
    product_pk = None
    consumer = request.user.consumer

    # GET 방식을 통해 product의 pk 값을 전달
    product_pk = int(request.GET.get('product'))
    print(f'싱품 pk : {product_pk}')

    # 문의 작성 GET - 문의 작성 가능한 form render
    if request.method == 'GET':
        form = Question_Form()
        ctx = {
            'form' : form,
        }
        return render(request, 'products/create_question.html', ctx)
    else :
        # 문의 작성 POST - 제목, 글, 이미지 전달 받음
        form = Question_Form(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data.get('title')
            content = form.cleaned_data.get('content')
            image = form.cleaned_data.get('image')
            status = False
            try:
                product = Product.objects.get(pk = product_pk)
            except ObjectDoesNotExist:
                print("존재하지 않는 상품 pk")
                return redirect(reverse('core:main'))
            # 상품 문의 등록
            new_question = Question(title=title, content=content, image=image, status=status, consumer=consumer, product=product)
            new_question.save()
            return redirect(reverse("products:product_detail", args=[product_pk]))
        else:
            # 상품 question create form validation 오류
            print("상품 question create form validation 오류")
            return redirect(reverse('core:main'))

@login_required
def read_qna(request, pk):

    # url pattern으로 전달 받은 Question pk 값으로 Question record 가져오기
    question = Question.objects.get(pk = pk)

    ctx = {
        'question': question,
        'answer': 0,
    }
    
    # 답변 완료된 문의라면 ctx의 answer에 answer record 넣기
    if(question.status is True):
        print("상품 문의에 답변 있음")
        ctx['answer'] = question.answer

    # 답변 대기 중인 상태면 ctx의 answer에는 0이 전달됨
    return render(request, "products/read_question.html", ctx)




#농가 마이페이지 - 문의/리뷰 관리 > 답변하기/답변수정 누를 시 
@login_required
def create_answer(request, pk):

    question = Question.objects.get(pk=pk)
    product = question.product

    # 접근하는 유져가 농가 계정임을 확인
    try:
        farmer = request.user.farmer
    except:
        return redirect(reverse("core:main"))
    
    # 접근하는 농가 계정이 문의와 관련있는 농가 계정임을 확인
    if farmer is not product.farmer:
        return redirect(reverse("core:main"))

    # GET : 문의 내용과 답변 입력 form 반환
    if request.method == 'GET':
        form = Answer_Form()
        ctx = {
            'question': question,
            'form': form,
        }
        return render(request, "farmers/mypage_create_answer.html", ctx)
    # POST : 답변 등록 
    else:
        form = Answer_Form(request.POST)
        if form.is_valid():
            answer = Answer(content = form.cleaned_data.get('content'), question = question, farmer = farmer)
            answer.save()
        else:
            return redirect(reverse("core:main"))
        return redirect(reverse("core:main")) # 추후 파머스 마이페이지 리뷰/문의 관리로 이동 하도록 수정



# @login_required
# def update_answer(request, pk):






    
        

