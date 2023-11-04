# Author: Om Mishra ( https://projectrexa.dedyn.io | https://github.com/Om-Mishra7 )
# Contact Detail: inkbloom@projectrexa.dedyn.io ( Do not spam this email address please :) )
# Written for the InkBloom Project
# Date Created: 03-11-2023
# Last Modified: 03-11-2023

"""
This file contains the server side code for the web application InkBloom, a powerful and versatile blog application that simplifies the process of creating, managing, and sharing your thoughts with the world.
"""

# Importing the required libraries

import os
import re
from dotenv import load_dotenv
import redis
from flask import (
    Flask,
    render_template,
    url_for,
    flash,
    redirect,
    request,
    session,
    abort,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from pymongo import MongoClient

load_dotenv()  # Loading the environment variables


app = Flask(__name__)

# App Configuration

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")


# Session Configuration

app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.from_url(os.getenv("REDIS_URL"))
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "inkbloom-session"


# Database Configuration

MONOGDB_CLIENT = MongoClient(os.getenv("MONGODB_URL"))
DATABASE = MONOGDB_CLIENT[os.getenv("MONGODB_DATABASE")]


# Session Initialization

Session(app)


# Rate Limiter Configuration

pool = redis.connection.BlockingConnectionPool.from_url(os.getenv("REDIS_URL"))
limiter = Limiter(
    app=app,
    key_func=lambda: get_remote_address(),
    default_limits=["30/minute"],
    storage_uri=os.getenv("REDIS_URL"),
    storage_options={"connection_pool": pool},
    strategy="moving-window",
)

# Application User Routes


@app.route("/", methods=["GET"])
def index():
    """
    This function renders the home page of the application.
    """
    # session["logged_in"] = True
    # session["admin"] = True
    # session["profile_pic"] = "https://cdn.projectrexa.dedyn.io/projectrexa/assets/logo_no_background.png"
    blogs = DATABASE["BLOGS"].find().limit(10)
    featured_blogs = DATABASE["BLOGS"].find({"featured": True}).limit(5)
    return render_template("index.html", blogs=blogs, featured_blogs=featured_blogs)


@app.route("/blogs", methods=["GET"])
def blogs():
    """
    This function renders the blogs page of the application.
    """
    blogs = DATABASE["BLOGS"].find().limit(10)
    return render_template("blogs.html", blogs=blogs)


@app.route("/view/<blog_id>", methods=["GET"])
def view(blog_id):
    """
    This function renders the blog page of the application.
    """
    blog = DATABASE["BLOGS"].find_one({"_id": blog_id})
    if blog:
        return redirect("/blogs/view/" + blog["slug"])
    abort(404)


@app.route("/blogs/view/<blog_slug>", methods=["GET"])
def blog(blog_slug):
    """
    This function renders the blog page of the application.
    """
    blog = DATABASE["BLOGS"].find_one({"slug": blog_slug})
    if blog:
        return render_template("blog.html", blog=blog)
    abort(404)


@app.route("/blogs/create", methods=["GET", "POST"])
def create_blog():
    """
    This function renders the create blog page of the application.
    """
    if (
        request.method == "POST"
        and session["logged_in"]
        and session["user_role"] == "admin"
    ):
        blog_title = request.form["blog_title"]
        blog_content = request.form["blog_content"]
        blog_featured = request.form["blog_featured"]
        blog_slug = request.form["blog_slug"]
        blog = {
            "title": blog_title,
            "content": blog_content,
            "featured": blog_featured,
            "slug": blog_slug,
            "views": 0,
            "likes": 0,
            "comments_count": 0,
            "comments": [],
            "liked_by": [],
        }
        DATABASE["BLOGS"].insert_one(blog)
        flash("Blog created successfully!", "success")
        return redirect("/blogs")
    return render_template("create_blog.html")


@app.route("/blogs/edit/<blog_id>", methods=["GET", "POST"])
def edit_blog(blog_id):
    """
    This function renders the edit blog page of the application.
    """
    if (
        request.method == "POST"
        and session["logged_in"]
        and session["user_role"] == "admin"
    ):
        blog_title = request.form["blog_title"]
        blog_content = request.form["blog_content"]
        blog_featured = request.form["blog_featured"]
        blog_slug = request.form["blog_slug"]
        blog = {
            "title": blog_title,
            "content": blog_content,
            "featured": blog_featured,
            "slug": blog_slug,
        }
        DATABASE["BLOGS"].update_one({"_id": blog_id}, {"$set": blog})
        flash("Blog updated successfully!", "success")
        return redirect("/blogs")
    blog_data = DATABASE["BLOGS"].find_one({"_id": blog_id})
    if blog_data:
        return render_template("edit_blog.html", blog=blog_data)
    abort(404)


# Application API Routes


@app.route("/api/v1/statisics/views/<blog_id>", methods=["POST"])
@limiter.limit("30/minute")
def get_blog_views(blog_id):
    """
    This function returns the number of views of a blog post.
    """
    blog = DATABASE["BLOGS"].find_one({"_id": blog_id})
    if blog:
        DATABASE["BLOGS"].update_one({"_id": blog_id}, {"$inc": {"views": 1}})
        return str(blog["views"])
    abort(404)


@app.route("/api/v1/statisics/likes/<blog_id>", methods=["GET"])
@limiter.limit("30/minute")
def get_blog_likes(blog_id):
    """
    This function returns the number of likes of a blog post.
    """
    post_likes = DATABASE["BLOGS"].find_one({"_id": blog_id})["likes"]

    if post_likes:
        return str(post_likes), 200

    return "0", 200


@app.route("/api/v1/statisics/likes/<blog_id>", methods=["POST"])
@limiter.limit("10/minute")
def post_blog_likes(blog_id):
    """
    This function updates the number of likes of a blog post.
    """
    if request.method == "POST" and session["logged_in"]:
        if DATABASE["BLOGS"].find_one({"_id": blog_id, "liked_by": session["user_id"]}):
            DATABASE["BLOGS"].update_one(
                {"_id": blog_id}, {"$pull": {"liked_by": session["user_id"]}}
            )
            DATABASE["BLOGS"].update_one({"_id": blog_id}, {"$inc": {"likes": -1}})
        else:
            DATABASE["BLOGS"].update_one(
                {"_id": blog_id}, {"$push": {"liked_by": session["user_id"]}}
            )
            DATABASE["BLOGS"].update_one({"_id": blog_id}, {"$inc": {"likes": 1}})
        return {"status": "success", "message": "Like updated successfully!"}, 200
    abort(401)


@app.route("/api/v1/statisics/comments/<blog_id>", methods=["GET"])
@limiter.limit("30/minute")
def get_blog_comments(blog_id):
    """
    This function returns the comments of a blog post.
    """
    comments = DATABASE["BLOGS"].find_one({"_id": blog_id})["comments"]

    if comments:
        return comments, 200

    return [], 200


@app.route("/api/v1/statisics/comments/<blog_id>", methods=["POST"])
@limiter.limit("5/minute")
def post_blog_comments(blog_id):
    """
    This function updates the comments of a blog post.
    """
    if not session["logged_in"]:
        return {
            "status": "error",
            "message": "User authentication is required for posting a comment!",
        }, 401
    comment = (
        request.get_json()["comment"]
        if request.get_json() and "comment" in request.get_json()
        else None
    )
    if comment:
        DATABASE["BLOGS"].update_one(
            {"_id": blog_id},
            {
                "$push": {
                    "comments": {
                        "comment": comment,
                        "commented_by": session["user_id"],
                    }
                }
            },
        )
        DATABASE["BLOGS"].update_one({"_id": blog_id}, {"$inc": {"comments_count": 1}})

        return {"status": "success", "message": "Comment posted successfully!"}, 200
    abort(400)


@app.route("/api/v1/blog", methods=["GET"])
@limiter.limit("30/minute")
def get_blog():
    """
    This function returns a blog post.
    """
    if request.args.get("pagination"):
        pagination = int(request.args.get("pagination"))
        blogs = DATABASE["BLOGS"].find().skip(pagination).limit(10)
    else:
        blogs = DATABASE["BLOGS"].find().limit(10)

    return list(blogs), 200


if __name__ == "__main__":
    app.run(debug=True)
