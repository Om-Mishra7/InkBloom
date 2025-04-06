# Author: Om Mishra ( https://om-mishra.com | https://github.com/Om-Mishra7 )

# Importing the required libraries

import os
import base64
import re
import urllib.parse
import redis
import utils
import secrets
from datetime import datetime, timezone, timedelta
import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    url_for,
    redirect,
    request,
    session,
    jsonify,
    abort,
)
from flask_session import Session
from pymongo import MongoClient
import uuid


# Loading the environment variables

load_dotenv()

# Initializing the application

app = Flask(__name__)

# Setting the service version

service_version = "4.2.0"

# App Configuration

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

# Session Configuration

redis_url = os.getenv("REDIS_URL")
if not redis_url:
    raise RuntimeError("Environment variable REDIS_URL not set")

app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.from_url(redis_url)
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "inkbloom-session"

# Database Configuration

mongodb_url = os.getenv("MONGODB_URL")
if not mongodb_url:
    raise RuntimeError("Environment variable MONGODB_URL not set")

MONOGDB_CLIENT = MongoClient(mongodb_url)
DATABASE = MONOGDB_CLIENT["INKBLOOM"]


# Session Initialization

Session(app)


def calculate_read_time(html_content, words_per_minute=200, image_time_seconds=12):
    text_content = re.sub(r"<[^>]*>", "", html_content)  # Remove HTML tags
    word_count = len(re.findall(r"\w+", text_content))

    text_read_time_minutes = word_count / words_per_minute

    image_count = len(re.findall(r"<img [^>]*>", html_content))
    image_read_time_seconds = image_count * image_time_seconds

    total_read_time_minutes = text_read_time_minutes + (image_read_time_seconds / 60)
    return int(total_read_time_minutes)


# Application Template Filters


@app.template_filter("format_timestamp")
def format_timestamp(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f").strftime("%d %B %Y")


@app.template_filter("rss_timestamp")
def rss_timestamp(s):
    return utils.format_datetime(
        datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
    )


@app.template_filter("sitemap_timestamp")
def sitemap_timestamp(s):
    return s.strftime("%Y-%m-%d")


@app.template_filter("url_encode")
def urlencode(s):
    return urllib.parse.quote(s)


@app.context_processor
def app_version():
    return dict(service_version=service_version)


@app.context_processor
def csrf_token():
    session["csrf_token"] = secrets.token_hex(16)
    return dict(csrf_token=session["csrf_token"])


# After-request function for setting headers


@app.after_request
def add_header(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    # response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Connection"] = "keep-alive"
    return response


# Application Routes


@app.route("/", methods=["GET"])
def index():
    if (
        session.get("user") is not None
        and session.get("user").get("username") == "om-mishra7"
    ):
        blogs_pipeline = [
            {"$sort": {"_id": -1}},
            {
                "$lookup": {
                    "from": "USERS",
                    "localField": "blog_author.user_id",
                    "foreignField": "user_id",
                    "as": "author_details",
                }
            },
            {"$unwind": "$author_details"},
        ]
        featured_blogs_pipeline = [
            {"$match": {"blog_metadata.featured": True}},
            {"$sort": {"_id": -1}},
            {"$limit": 5},
            {
                "$lookup": {
                    "from": "USERS",
                    "localField": "blog_author.user_id",
                    "foreignField": "user_id",
                    "as": "author_details",
                }
            },
            {"$unwind": "$author_details"},
        ]
    else:
        blogs_pipeline = [
            {"$match": {"blog_metadata.visibility": "public"}},
            {"$sort": {"_id": -1}},
            {
                "$lookup": {
                    "from": "USERS",
                    "localField": "blog_author.user_id",
                    "foreignField": "user_id",
                    "as": "author_details",
                }
            },
            {"$unwind": "$author_details"},
        ]
        featured_blogs_pipeline = [
            {
                "$match": {
                    "blog_metadata.visibility": "public",
                    "blog_metadata.featured": True,
                }
            },
            {"$sort": {"_id": -1}},
            {"$limit": 5},
            {
                "$lookup": {
                    "from": "USERS",
                    "localField": "blog_author.user_id",
                    "foreignField": "user_id",
                    "as": "author_details",
                }
            },
            {"$unwind": "$author_details"},
        ]

    blogs = list(DATABASE["BLOGS"].aggregate(blogs_pipeline))
    featured_blogs = list(DATABASE["BLOGS"].aggregate(featured_blogs_pipeline))

    return render_template("index.html", blogs=blogs, featured_blogs=featured_blogs)


@app.route("/blog/new-blog", methods=["GET"])
def new_blog():
    if (
        session.get("user") is None
        and session.get("user").get("username") != "om-mishra7"
    ):
        return redirect(url_for("login"))
    return render_template("create_blog.html")


@app.route("/api/blog", methods=["POST"])
def create_blog():
    if (
        session.get("user") is None
        and session.get("user").get("username") != "om-mishra7"
    ):
        return redirect(url_for("login"))
    blog_title = request.form.get("title")
    blog_description = request.form.get("description")
    blog_slug = request.form.get("slug").lower()
    blog_tags = [
        tag.strip() for tag in request.form.get("tags").lower().strip().split(",")
    ]
    blog_category = request.form.get("category").lower()
    blog_visibility = request.form.get("visibility").lower()
    blog_featured = request.form.get("featured")
    blog_cover = request.files.get("cover")
    blog_content = request.form.get("content")

    if (
        not blog_title
        or not blog_description
        or not blog_slug
        or not blog_tags
        or not blog_category
        or not blog_visibility
        or not blog_cover
        or not blog_content
    ):
        return jsonify(
            {
                "status": "error",
                "message": f"The following fields are required: {'Title' if not blog_title else ''} {'Description' if not blog_description else ''} {'Slug' if not blog_slug else ''} {'Tags' if not blog_tags else ''} {'Category' if not blog_category else ''} {'Visibility' if not blog_visibility else ''} {'Cover' if not blog_cover else ''} {'Content' if not blog_content else ''}",
            }
        )

    # All images in the content are base64 encoded, so we need to extract them and upload them to the CDN and replace the base64 encoded images with the CDN URLs

    image_urls = []

    # Find all base64-encoded images in the blog content
    base64_images = re.findall(
        r'<img src="data:image/([^;]+);base64,([^"]+)"', blog_content
    )

    # Loop through each base64-encoded image found
    for image_type, image_data in base64_images:
        # Decode the base64 image data
        try:
            image = base64.b64decode(image_data)
        except base64.binascii.Error:
            return jsonify(
                {
                    "status": "error",
                    "message": "Invalid base64 image data found!",
                }
            )

        # Send a POST request to upload the image to the CDN
        try:
            image_upload_response = requests.post(
                "https://api.cdn.om-mishra.com/v1/upload-file",
                headers={
                    "X-Authorization": os.getenv("CDN_API_KEY"),
                },
                files={
                    "file": base64.b64decode(image_data),
                },
                data={
                    # Hashing the image content to generate a unique object path
                    "object_path": f"blogs/media/{str(hash(image))[1:8]}.png",
                },
                timeout=5,
            )

            # Check if the image upload was successful
            if image_upload_response.status_code != 200:
                return jsonify(
                    {
                        "status": "error",
                        "message": "The blog creation failed, due to an invalid response from the Image Upload API!",
                    }
                )

            # Append the URL of the uploaded image to the image_urls list
            image_urls.append(image_upload_response.json().get("file_url"))

        except Exception as e:
            return jsonify(
                {
                    "status": "error",
                    "message": f"Image upload failed: {str(e)}",
                }
            )

    # Replace base64-encoded images in the blog content with their respective uploaded URLs
    for index, (image_type, image_data) in enumerate(base64_images):
        if index < len(image_urls):
            blog_content = blog_content.replace(
                f"data:image/{image_type};base64,{image_data}",
                f"https://wsrv.nl/?url={image_urls[index]}&output=webp&quality=80&q=80&maxage=30d",
            )

    # Calculate the read time of the blog
    blog_read_time = calculate_read_time(blog_content)

    # Upload the cover image to the CDN
    cover_upload_response = requests.post(
        "https://api.cdn.om-mishra.com/v1/upload-file",
        headers={
            "X-Authorization": os.getenv("CDN_API_KEY"),
        },
        files={
            "file": blog_cover,
        },
        data={
            "object_path": f"blogs/covers/{str(uuid.uuid4())}.png",
        },
        timeout=5,
    )

    # Check if the cover image upload was successful
    if cover_upload_response.status_code != 200:
        return jsonify(
            {
                "status": "error",
                "message": "The blog creation failed, due to an invalid response from the Cover Image Upload API!",
            }
        )

    # Insert the blog into the database
    data = {
        "blog_id": str(uuid.uuid4()),
        "blog_metadata": {
            "title": blog_title,
            "description": blog_description,
            "slug": f"{blog_category}:-{blog_slug}-{str(secrets.token_hex(4))}",
            "tags": blog_tags,
            "category": blog_category,
            "visibility": blog_visibility,
            "featured": True if blog_featured else False,
            "cover_url": cover_upload_response.json()["file_url"],
            "read_time": blog_read_time,
            "number_of_views": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
        "blog_content": blog_content,
        "blog_author": {
            "user_id": session.get("user").get("user_id"),
        },
    }

    DATABASE["BLOGS"].insert_one(data)

    return jsonify(
        {
            "status": "success",
            "slug": data["blog_metadata"]["slug"],
            "message": "The blog has been successfully created!",
        }
    )


@app.route("/blog/<slug>", methods=["GET"])
def blog(slug):
    blog_data = DATABASE["BLOGS"].find_one({"blog_metadata.slug": slug})
    if blog_data is None:
        abort(404)
    if blog_data["blog_metadata"]["visibility"] == "private":
        if (
            session.get("user") is None
            or session.get("user").get("user_id") != blog_data["blog_author"]["user_id"]
        ):
            abort(401)
    author_data = DATABASE["USERS"].find_one(
        {"user_id": blog_data["blog_author"]["user_id"]}
    )
    comments = list(
        DATABASE["COMMENTS"].aggregate(
            [
                {"$match": {"comment_metadata.blog_id": blog_data["blog_id"]}},
                {"$sort": {"_id": -1}},
                {
                    "$lookup": {
                        "from": "USERS",
                        "localField": "comment_author.user_id",
                        "foreignField": "user_id",
                        "as": "author_details",
                    }
                },
                {"$unwind": "$author_details"},
            ]
        )
    )
    DATABASE["BLOGS"].update_one(
        {"blog_id": blog_data["blog_id"]},
        {"$set": {"blog_metadata.number_of_views": blog_data["blog_metadata"]["number_of_views"] + 1}},
    )
    return render_template("blog.html", blog=blog_data, author=author_data, comments=comments)


@app.route("/blog/<id>/edit", methods=["GET"])
def edit_blog(id):
    if (
        session.get("user") is None
        and session.get("user").get("username") != "om-mishra7"
    ):
        return redirect(url_for("login"))
    blog_data = DATABASE["BLOGS"].find_one({"blog_id": id})
    if blog_data is None:
        abort(404)
    blog_data["blog_metadata"]["tags"] = ", ".join(blog_data["blog_metadata"]["tags"])
    blog_data["blog_metadata"]["slug"] = blog_data["blog_metadata"]["slug"].split(":-")[
        1
    ]
    return render_template("edit_blog.html", blog=blog_data)


@app.route("/api/blog/<id>", methods=["PUT"])
def update_blog(id):
    if (
        session.get("user") is None
        and session.get("user").get("username") != "om-mishra7"
    ):
        return redirect(url_for("login"))
    blog_data = DATABASE["BLOGS"].find_one({"blog_id": id})
    if blog_data is None:
        abort(404)
    blog_title = request.form.get("title")
    blog_description = request.form.get("description")
    blog_slug = request.form.get("slug").lower()
    blog_tags = [
        tag.strip() for tag in request.form.get("tags").lower().strip().split(",")
    ]
    blog_category = request.form.get("category").lower()
    blog_visibility = request.form.get("visibility").lower()
    blog_featured = request.form.get("featured")
    blog_cover = request.files.get("cover")
    blog_content = request.form.get("content")

    if (
        not blog_title
        or not blog_description
        or not blog_slug
        or not blog_tags
        or not blog_category
        or not blog_visibility
        or not blog_content
    ):
        return jsonify(
            {
                "status": "error",
                "message": f"The following fields are required: {'Title' if not blog_title else ''} {'Description' if not blog_description else ''} {'Slug' if not blog_slug else ''} {'Tags' if not blog_tags else ''} {'Category' if not blog_category else ''} {'Visibility' if not blog_visibility else ''} {'Content' if not blog_content else ''}",
            }
        )

    # All images in the content are base64 encoded, so we need to extract them and upload them to the CDN and replace the base64 encoded images with the CDN URLs

    image_urls = []

    # Find all base64-encoded images in the blog content
    base64_images = re.findall(
        r'<img src="data:image/([^;]+);base64,([^"]+)"', blog_content
    )

    # Loop through each base64-encoded image found
    for image_type, image_data in base64_images:
        # Decode the base64 image data
        try:
            image = base64.b64decode(image_data)
        except base64.binascii.Error:
            return jsonify(
                {
                    "status": "error",
                    "message": "Invalid base64 image data found!",
                }
            )

        # Send a POST request to upload the image to the CDN
        try:
            image_upload_response = requests.post(
                "https://api.cdn.om-mishra.com/v1/upload-file",
                headers={
                    "X-Authorization": os.getenv("CDN_API_KEY"),
                },
                files={
                    "file": base64.b64decode(image_data),
                },
                data={
                    # Hashing the image content to generate a unique object path
                    "object_path": f"blogs/media/{str(hash(image))[1:8]}.png",
                },
                timeout=5,
            )

            # Check if the image upload was successful
            if image_upload_response.status_code != 200:
                return jsonify(
                    {
                        "status": "error",
                        "message": "The blog update failed, due to an invalid response from the Image Upload API!",
                    }
                )

            # Append the URL of the uploaded image to the image_urls list
            image_urls.append(image_upload_response.json().get("file_url"))

        except Exception as e:
            return jsonify(
                {
                    "status": "error",
                    "message": f"Image upload failed: {str(e)}",
                }
            )

    # Replace base64-encoded images in the blog content with their respective uploaded URLs

    for index, (image_type, image_data) in enumerate(base64_images):
        if index < len(image_urls):
            blog_content = blog_content.replace(
                f"data:image/{image_type};base64,{image_data}",
                f"https://wsrv.nl/?url={image_urls[index]}&output=webp&quality=80&q=80&maxage=30d",
            )

    # Calculate the read time of the blog
    blog_read_time = calculate_read_time(blog_content)

    # Upload the cover image to the CDN
    if blog_cover:
        cover_upload_response = requests.post(
            "https://api.cdn.om-mishra.com/v1/upload-file",
            headers={
                "X-Authorization": os.getenv("CDN_API_KEY"),
            },
            files={
                "file": blog_cover,
            },
            data={
                "object_path": f"blogs/covers/{str(uuid.uuid4())}.png",
            },
            timeout=5,
        )

        # Check if the cover image upload was successful
        if cover_upload_response.status_code != 200:
            return jsonify(
                {
                    "status": "error",
                    "message": "The blog update failed, due to an invalid response from the Cover Image Upload API!",
                }
            )

        # Update the blog cover URL
        blog_data["blog_metadata"]["cover_url"] = cover_upload_response.json()[
            "file_url"
        ]

    # Update the blog data
    blog_data["blog_metadata"]["title"] = blog_title
    blog_data["blog_metadata"]["description"] = blog_description
    blog_data["blog_metadata"]["slug"] = f"{blog_category}:-{blog_slug}"
    blog_data["blog_metadata"]["tags"] = [
        tag.strip() for tag in request.form.get("tags").lower().strip().split(",")
    ]
    blog_data["blog_metadata"]["category"] = blog_category
    blog_data["blog_metadata"]["visibility"] = blog_visibility
    blog_data["blog_metadata"]["featured"] = True if blog_featured else False
    blog_data["blog_metadata"]["read_time"] = blog_read_time
    blog_data["blog_metadata"]["updated_at"] = datetime.now()
    blog_data["blog_content"] = blog_content

    DATABASE["BLOGS"].update_one({"blog_id": id}, {"$set": blog_data})

    return jsonify(
        {
            "status": "success",
            "message": "The blog has been successfully updated!",
            "slug": blog_data["blog_metadata"]["slug"],
        }
    )

@app.route("/api/blog/<id>/comment", methods=["POST"])
def create_comment(id):
    blog_data = DATABASE["BLOGS"].find_one({"blog_id": id})
    if blog_data is None:
        abort(404)
    comment_content = request.form.get("content")
    if not comment_content:
        return jsonify(
            {
                "status": "error",
                "message": "The comment content is required!",
            }
        )
    comment_data = {
        "comment_id": str(uuid.uuid4()),
        "comment_content": comment_content,
        "comment_author": {
            "user_id": session.get("user").get("user_id"),
        },
        "comment_metadata": {
            "created_at": datetime.now(),
            "blog_id": blog_data["blog_id"],
        },
    }
    DATABASE["COMMENTS"].insert_one(comment_data)

    return jsonify(
        {
            "status": "success",
            "message": "The comment has been successfully created!",
        }
    )

@app.route("/api/blog/<id>/comment/<comment_id>/delete", methods=["GET"])
def delete_comment(id, comment_id):
    comment_data = DATABASE["COMMENTS"].find_one({"comment_id": comment_id})
    if comment_data is None:
        abort(404)
    if session.get("user").get("user_id") != comment_data["comment_author"]["user_id"]:
        abort(401)
    DATABASE["COMMENTS"].delete_one({"comment_id": comment_id})

    return redirect((f"/blog/{DATABASE['BLOGS'].find_one({'blog_id': id})['blog_metadata']['slug']}"))


# Application Auth Routes


@app.route("/auth/login", methods=["GET"])
def login():
    session["auth_state"] = secrets.token_hex(16)
    return redirect(f'https://accounts.om-mishra.com/api/v1/oauth2/authorize?client_id=ebbf4742-7ad2-4ecc-a9a0-8d3c3c1da164&state={session["auth_state"]}')

@app.route("/auth/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/oauth/_handler", methods=["GET"])
def github_callback():
    code = request.args.get("code")
    if not code:
        return redirect(
            url_for(
                "index",
                message="The authentication attempt failed, due to missing code parameter!",
            )
        )

    if request.args.get("state") != session.get("auth_state"):
        return redirect(
            url_for(
                "index",
                message="The authentication attempt failed, due to mismatched state parameter!",
            )
        )

    oauth_response = requests.post(
        "https://accounts.om-mishra.com/api/v1/oauth2/user-info",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "client_id": 'ebbf4742-7ad2-4ecc-a9a0-8d3c3c1da164',
            "client_secret": os.getenv("OM_MISHRA_ACCOUNTS_CLIENT_SECRET"),
            "code": code,
        },
    )

    if oauth_response.status_code != 200:
        return redirect(
            url_for(
                "index",
                message="The authentication attempt failed, due to invalid response from GitHub!",
            )
        )
    
    user_data = oauth_response.json()["user"]

    if (
        DATABASE["USERS"].find_one({"account_info.oauth_id": user_data["user_public_id"]}) is None
    ):
        DATABASE["USERS"].insert_one(
            {
                "user_id": user_data["user_public_id"],
                "user_info": {
                    "username": user_data["user_profile"]["user_name"],
                    "name": user_data["user_profile"]["user_display_name"],
                    "avatar_url": user_data["user_profile"]["user_profile_picture"],
                },
                "account_info": {
                    "oauth_provider": "om-mishra",
                    "oauth_id": user_data["user_public_id"],
                    "created_at": datetime.now(),
                    "last_login": datetime.now(),
                    "is_active": True,
                },
            }
        )
    else:
        user_id = DATABASE["USERS"].find_one(
            {"account_info.oauth_id": user_data["user_public_id"]}
        )["user_id"]

        DATABASE["USERS"].update_one(
            {"account_info.oauth_id": user_data["user_public_id"]},
            {"$set": {"account_info.last_login": datetime.now(), "user_info.avatar_url": user_data["user_profile"]["user_profile_picture"]}},
        )

    user_info = DATABASE["USERS"].find_one({"user_id": user_data["user_public_id"]})

    session["user"] = {
        "user_id": user_info["user_id"],
        "username": user_info["user_info"]["username"],
        "name": user_info["user_info"]["name"],
        "avatar_url": f"{user_info['user_info']['avatar_url']}",
    }

    session["is_authenticated"] = True

    return redirect(url_for("index"))


# Application Search Routes

@app.route("/api/search", methods=["GET"])
def search_api():
    query = request.args.get("query")
    limit = 5
    if not query:
        return jsonify(
            {
                "status": "error",
                "message": "The search query is required!",
            }
        )

    # Escape special characters in the query
    escaped_query = re.escape(query.strip().replace("%20", " "))
    fuzzy_query = f".*{escaped_query}.*"

    pipeline = [
        {
            "$match": {
                "$or": [
                    {"blog_metadata.title": {"$regex": fuzzy_query, "$options": "i"}},
                    {"blog_metadata.description": {"$regex": fuzzy_query, "$options": "i"}},
                    {"blog_metadata.tags.tag_name": {"$regex": fuzzy_query, "$options": "i"}},
                    {"blog_metadata.category": {"$regex": fuzzy_query, "$options": "i"}},
                ]
            }
        },
        {
            "$group": {
                "_id": "$blog_id",
                "blog_id": {"$first": "$blog_id"},
                "blog_metadata": {"$first": "$blog_metadata"},
            }
        },
        {
            "$limit": limit
        },
        {
            "$project": {
                "_id": 0,
                "blog_id": 1,
                "blog_metadata": 1,
            }
        }
    ]

    search_results = list(DATABASE["BLOGS"].aggregate(pipeline))

    return jsonify(
        {
            "status": "success",
            "results": search_results,
        }
    )

@app.route("/tags/<tag>", methods=["GET"])
def tags(tag):
    return redirect(url_for("search", tags=tag))

@app.route("/category/<category>", methods=["GET"])
def category(category):
    return redirect(url_for("search", category=category))

@app.route("/search", methods=["GET"])
def search():
    tags = request.args.getlist("tags")
    category = request.args.get("category")
    publish_date_lt = request.args.get("publish_date_lt")
    publish_date_gt = request.args.get("publish_date_gt")
    publish_date_lte = request.args.get("publish_date_lte")
    publish_date_gte = request.args.get("publish_date_gte")
    views_lt = request.args.get("views_lt", type=int)
    views_gt = request.args.get("views_gt", type=int)
    views_lte = request.args.get("views_lte", type=int)
    views_gte = request.args.get("views_gte", type=int)

    if tags == [] and not category and not publish_date_lt and not publish_date_gt and not publish_date_lte and not publish_date_gte and views_lt is None and views_gt is None and views_lte is None and views_gte is None:
        return abort(400)

    # Building the match stage
    match_stage = {"$match": {"blog_metadata.visibility": "public"}}  # Consider only public blog posts
    
    if tags:
        match_stage["$match"]["blog_metadata.tags"] = {"$in": tags}
    
    if category:
        match_stage["$match"]["blog_metadata.category"] = category
    
    if publish_date_lt:
        if "blog_metadata.publish_date" not in match_stage["$match"]:
            match_stage["$match"]["blog_metadata.created_at"] = {}
        match_stage["$match"]["blog_metadata.created_at"]["$lt"] = datetime.strptime(publish_date_lt, "%Y-%m-%d")
    
    if publish_date_gt:
        if "blog_metadata.publish_date" not in match_stage["$match"]:
            match_stage["$match"]["blog_metadata.created_at"] = {}
        match_stage["$match"]["blog_metadata.created_at"]["$gt"] = datetime.strptime(publish_date_gt, "%Y-%m-%d")
    
    if publish_date_lte:
        if "blog_metadata.publish_date" not in match_stage["$match"]:
            match_stage["$match"]["blog_metadata.created_at"] = {}
        match_stage["$match"]["blog_metadata.created_at"]["$lte"] = datetime.strptime(publish_date_lte, "%Y-%m-%d")
    
    if publish_date_gte:
        if "blog_metadata.publish_date" not in match_stage["$match"]:
            match_stage["$match"]["blog_metadata.created_at"] = {}
        match_stage["$match"]["blog_metadata.created_at"]["$gte"] = datetime.strptime(publish_date_gte, "%Y-%m-%d")
    
    if views_lt is not None:
        if "blog_metadata.views" not in match_stage["$match"]:
            match_stage["$match"]["blog_metadata.number_of_views"] = {}
        match_stage["$match"]["blog_metadata.number_of_views"]["$lt"] = views_lt
    
    if views_gt is not None:
        if "blog_metadata.views" not in match_stage["$match"]:
            match_stage["$match"]["blog_metadata.number_of_views"] = {}
        match_stage["$match"]["blog_metadata.number_of_views"]["$gt"] = views_gt
    
    if views_lte is not None:
        if "blog_metadata.views" not in match_stage["$match"]:
            match_stage["$match"]["blog_metadata.number_of_views"] = {}
        match_stage["$match"]["blog_metadata.number_of_views"]["$lte"] = views_lte
    
    if views_gte is not None:
        if "blog_metadata.views" not in match_stage["$match"]:
            match_stage["$match"]["blog_metadata.number_of_views"] = {}
        match_stage["$match"]["blog_metadata.number_of_views"]["$gte"] = views_gte

    # Building the group stage
    lookup_stage = {
        "$lookup": {
            "from": "USERS",
            "localField": "blog_author.user_id",
            "foreignField": "user_id",
            "as": "author_details"
        }
    }

    # Unwind the author_details array
    unwind_stage = {
        "$unwind": "$author_details"
    }

    # Add author details into each blog record
    add_fields_stage = {
        "$addFields": {
            "author_details": "$author_details"
        }
    }

    # Building the group stage
    group_stage = {
        "$group": {
            "_id": "$blog_metadata.category",
            "averageViews": {"$avg": "$blog_metadata.number_of_views"},
            "totalBlogs": {"$sum": 1},
            "blogs": {"$push": "$$ROOT"}
        }
    }

    # Building the sort stage
    sort_stage = {
        "$sort": {"averageViews": -1}  # Sort by average views in descending order
    }

    # Projecting the final output
    projection_stage = {
        "$project": {
            "_id": 0,
            "category": "$_id",
            "averageViews": 1,
            "totalBlogs": 1,
            "blogs": {
                "$map": {
                    "input": "$blogs",
                    "as": "blog",
                    "in": {
                        "blog_id": "$$blog.blog_id",
                        "blog_metadata": "$$blog.blog_metadata",
                        "author_details": "$$blog.author_details"
                    }
                }
            }
        }
    }

    # Constructing the pipeline
    pipeline = [
        match_stage,
        lookup_stage,
        unwind_stage,
        add_fields_stage,
        group_stage,
        sort_stage,
        projection_stage
    ]

    # Running the aggregation pipeline
    search_results = list(DATABASE["BLOGS"].aggregate(pipeline))

    return render_template("search.html", search_results=search_results, tags=tags, category=category, publish_date_lt=publish_date_lt, publish_date_gt=publish_date_gt, publish_date_lte=publish_date_lte, publish_date_gte=publish_date_gte, views_lt=views_lt, views_gt=views_gt, views_lte=views_lte, views_gte=views_gte)



@app.errorhandler(429)
@app.errorhandler(404)
@app.errorhandler(401)
@app.errorhandler(400)
@app.errorhandler(500)
def handle_errors(e):
    error_messages = {
        429: "Too many requests, please try again later!",
        404: "Page not found!",
        401: "You are not authorized to access this page!",
        400: "Bad request!",
        500: "Internal server error!",
    }
    status_code = getattr(e, "code", 500)
    return {
        "status": "error",
        "message": error_messages.get(status_code, "Unknown error"),
    }, status_code
