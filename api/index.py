import os
import math
import urllib.parse
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pymongo import MongoClient, ASCENDING, DESCENDING
from contextlib import asynccontextmanager

# إنشاء الفهارس (Indexes) تلقائياً عند بدء التطبيق لسرعة استجابة استثنائية
@asynccontextmanager
async def lifespan(app: FastAPI):
    # إنشاء الفهارس في الخلفية
    try:
        students_col.create_index([("id", ASCENDING)], unique=True)
        students_col.create_index([("rank", ASCENDING), ("id", ASCENDING)])
        # فهرس نصي للبحث السريع جداً بالاسم
        students_col.create_index([("name", "text")])
    except Exception as e:
        print(f"Index creation note: {e}")
    yield

app = FastAPI(lifespan=lifespan)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

username = urllib.parse.quote_plus('ahmedosman')
password = urllib.parse.quote_plus('i-fn@bBHV7rXMYj')
MONGO_URI = f"mongodb+srv://{username}:{password}@cluster0.8wawfsu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# استخدام PyMongo مع ضبط Connection Pooling
client = MongoClient(MONGO_URI, maxPoolSize=50, minPoolSize=10)
db = client['thanawya_results']
students_col = db['students']

# كاش إجمالي الطلاب لتجنب العد المتكرر في كل طلب
TOTAL_STUDENTS_CACHE = None

def get_total_students():
    global TOTAL_STUDENTS_CACHE
    if TOTAL_STUDENTS_CACHE is None:
        TOTAL_STUDENTS_CACHE = students_col.estimated_document_count()
    return TOTAL_STUDENTS_CACHE

@app.get("/api/search")
def search_student(
    q: str = Query("", min_length=0),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    sort: str = Query("id", regex="^(id|score)$")
):
    query_str = q.strip()
    skip = (page - 1) * limit
    sort_order = [("rank", ASCENDING), ("id", ASCENDING)] if sort == "score" else [("id", ASCENDING)]

    # 1. حالة عدم وجود كلمة بحث (تصفح عادي)
    if not query_str:
        filter_query = {}
        filtered_count = get_total_students()
    
    # 2. البحث برقم الجلوس (إذا كان إدخال أرقام)
    elif query_str.isdigit():
        target_id = int(query_str)
        # البحث المباشر برقم الجلوس بياخد 1ms فقط بفضل الـ Index
        filter_query = {"id": target_id}
        filtered_count = students_col.count_documents(filter_query)
        if filtered_count == 0:
            # إذا كتب جزء من رقم الجلوس
            filter_query = {"id": {"$gte": target_id}}

    # 3. البحث بالاسم
    else:
        # استخدام البحث بالـ Regex المحسن مع الـ Index
        filter_query = {"name": {"$regex": f"^{query_str}", "$options": "i"}}
        filtered_count = students_col.count_documents(filter_query)
        
        # إذا لم يجد نتائج بالـ Prefix، يبحث في أي مكان في الاسم
        if filtered_count == 0:
            filter_query = {"name": {"$regex": query_str, "$options": "i"}}
            filtered_count = students_col.count_documents(filter_query)

    # تنفيذ الاستعلام مع تحديد الحقول المطلوبة واستبعاد _id
    cursor = students_col.find(
        filter_query, 
        {"_id": 0, "id": 1, "name": 1, "score": 1, "status": 1, "rank": 1}
    ).sort(sort_order).skip(skip).limit(limit)
    
    rows = list(cursor)
    total_pages = math.ceil(filtered_count / limit) if filtered_count > 0 else 1

    return {
        "status": "success",
        "count": filtered_count,
        "total_students": get_total_students(),
        "page": page,
        "total_pages": total_pages,
        "data": rows
    }

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(html_path):
        html_path = os.path.join(os.getcwd(), "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html غير موجود</h1>"
