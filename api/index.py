import os
import math
import urllib.parse
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pymongo import MongoClient, ASCENDING, DESCENDING

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

username = urllib.parse.quote_plus('ahmedosman')
password = urllib.parse.quote_plus('i-fn@bBHV7rXMYj')
MONGO_URI = f"mongodb+srv://{username}:{password}@cluster0.8wawfsu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client['thanawya_results']
students_col = db['students']

@app.get("/api/search")
def search_student(
    q: str = Query("", min_length=0),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    sort: str = Query("id", regex="^(id|score)$")
):
    total_students = students_col.count_documents({})
    query_str = q.strip()
    skip = (page - 1) * limit

    sort_order = [("rank", ASCENDING), ("id", ASCENDING)] if sort == "score" else [("id", ASCENDING)]

    if not query_str:
        filter_query = {}
    elif query_str.isdigit():
        # البحث برقم الجلوس (إما بيبدأ بالرقم أو يطابقه)
        filter_query = {"id": int(query_str)} if len(query_str) > 5 else {"$expr": {"$regexMatch": {"input": {"$toString": "$id"}, "regex": f"^{query_str}"}}}
    else:
        # البحث بالاسم (مع عدم الحساسية لحالة الأحرف)
        filter_query = {"name": {"$regex": query_str, "$options": "i"}}

    filtered_count = students_col.count_documents(filter_query)
    cursor = students_col.find(filter_query, {"_id": 0}).sort(sort_order).skip(skip).limit(limit)
    rows = list(cursor)

    total_pages = math.ceil(filtered_count / limit) if filtered_count > 0 else 1

    return {
        "status": "success",
        "count": filtered_count,
        "total_students": total_students,
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