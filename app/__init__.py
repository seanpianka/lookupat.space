import json
import os
import random

from flask import Flask, render_template, redirect, url_for


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
POSTS_FNAME = os.path.join(BASE_DIR, 'posts.json')


application = Flask(__name__)
application.config.from_object('config')


T = application.config["T"]


@application.route("/")
def index():
    """ Index page, where pictures will be shown. """
    return render_template("index.html", T=T)


@application.route("/fetch/<t>")
def fetch(t):
    if t != T:
        return redirect(url_for("index"))

    with open(POSTS_FNAME) as f:
        posts = json.load(f)

    posts_src = "\n".join(
        [
            render_template(
                "base/post.html",
                archive_url=p["link"],
                image_url=p["imag"] if "imag" in p else "",
                video_data=p["vide"] if "vide" in p else {},
                title=p["desc"],
                description=p["date"],
                explanation=p["expl"],
                credit=p["cred"],
            )
            for p in random.sample(posts, 4)
        ]
    )

    return posts_src


if __name__ == "__main__":
    main()
