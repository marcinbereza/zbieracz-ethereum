"""
This module contains the Flask routes for a site traversal application.

The routes in this module handle the navigation and password validation 
for the site traversal application.
"""

import time

from urllib.parse import quote as url_quote
from flask import render_template, redirect, make_response, request


from app import app, GRAPH


def get_node_by_id(node_id):
    """
    Get a node from the GRAPH dictionary by its ID.

    Args:
        node_id (int): The ID of the node.

    Returns:
        dict: The node with the specified ID.

    Raises:
        ValueError: If no node with the specified ID is found.
    """
    for node in GRAPH["nodes"]:
        if node["id"] == node_id:
            return node
    raise ValueError(f"Node with id {node_id} not found")


def get_node_by_href(href):
    """
    Get a node from the GRAPH dictionary by its href.

    Args:
        href (str): The href of the node.

    Returns:
        dict: The node with the specified href.

    Raises:
        ValueError: If no node with the specified href is found.
    """
    for node in GRAPH["nodes"]:
        if node["href"] == href:
            return node
    raise ValueError(f"Node with href {href} not found")

@app.route("/robots.txt")
def robot_txt():
    return "User-agent: *\nDisallow:\n", 200, {"Content-Type": "text/plain"}

@app.route("/")
def root_page():
    """
    Route for the root page.

    Returns:
        str: The rendered index.html template with the start node's href.
    """
    start_node = get_node_by_id(0)
    href = f"/{url_quote(start_node['href'])}"
    return render_template("index.html", href=href)


@app.route("/<href>")
def index(href):
    """
    Route for a specific node.

    Args:
        href (str): The href of the node.

    Returns:
        str: The rendered node.html template with the links and node information.
    """
    time.sleep(.1)  # Simulate a delay for demonstration purposes
    node = get_node_by_href(href)
    node_id = node["id"]
    if node["secret"] == "yes" and node["access"] == "forbidden":
        password = node["password"]
        headers = {"X-Password": password}
        template_context = render_template("password_form.html", node=node)
        response = make_response(template_context, headers)
        return response
    links = []
    for link in GRAPH["links"]:
        if link["source"] == node_id:
            target = {
                "id": link["target"],
                "href": get_node_by_id(link["target"])["href"],
            }
            links.append(target)
    return render_template("node.html", links=links, node=node)


@app.route("/validate_password/<href>", methods=["POST"])
def validate_password(href):
    """
    Route for validating the password of a node.

    Args:
        href (str): The href of the node.

    Returns:
        redirect: Redirects to the node's href if the password is correct,
        otherwise redirects to the root page.
    """
    node = get_node_by_href(href)
    password = node["password"]
    if password == request.form["password"]:
        node["access"] = "allowed"
        return redirect(f"/{url_quote(href)}")
    return redirect("/")
